"""
JS8Call utilities.
"""

from socket import socket, AF_INET, SOCK_STREAM
import json
import time
import sqlite3
import configparser
import logging

from meshtastic import BROADCAST_NUM  # type: ignore

from command_handlers import handle_help_command
from utils import send_message, update_user_state
from config_init import CONFIG_FILE


def from_message(content):
    """
    Parses a JSON-formatted string and returns the corresponding dictionary.

    Args:
        content (str): The JSON-formatted string to be parsed.

    Returns:
        dict: The parsed dictionary if the input is valid JSON, otherwise an empty dictionary.
    """
    try:
        return json.loads(content)
    except ValueError:
        return {}


def to_message(typ, value="", params=None):
    """
    Convert the given type, value, and parameters into a JSON-formatted message.

    Args:
        typ (str): The type of the message.
        value (str, optional): The value of the message. Defaults to an empty string.
        params (dict, optional): Additional parameters for the message. Defaults to an empty dictionary.

    Returns:
        str: A JSON-formatted string representing the message.
    """
    if params is None:
        params = {}
    return json.dumps({"type": typ, "value": value, "params": params})


class JS8CallClient:
    """
    JS8CallClient class
    """

    def __init__(self, interface, logger=None):
        self.logger = logger or logging.getLogger("js8call")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)

        self.server = (
            self.config.get("js8call", "host", fallback=None),
            self.config.getint("js8call", "port", fallback=None),
        )
        self.db_file = self.config.get("js8call", "db_file", fallback=None)
        self.js8groups = self.config.get("js8call", "js8groups", fallback="").split(",")
        self.store_messages = self.config.getboolean(
            "js8call", "store_messages", fallback=True
        )
        self.js8urgent = self.config.get("js8call", "js8urgent", fallback="").split(",")
        self.js8groups = [group.strip() for group in self.js8groups]
        self.js8urgent = [group.strip() for group in self.js8urgent]

        self.connected = False
        self.sock = None
        self.db_conn = None
        self.interface = interface

        if self.db_file:
            self.db_conn = sqlite3.connect(self.db_file)
            self.create_tables()
        else:
            self.logger.info(
                "JS8Call configuration not found. Skipping JS8Call integration."
            )

    def create_tables(self):
        """
        Creates the necessary tables in the database if they do not already exist.

        This method creates three tables:
        - messages: Stores individual messages with columns for id, sender, receiver, message, and timestamp.
        - groups: Stores group messages with columns for id, sender, groupname, message, and timestamp.
        - urgent: Stores urgent messages with columns for id, sender, groupname, message, and timestamp.

        If the database connection is not established, the method returns immediately.

        Logs an informational message once the tables are created or verified.
        """
        if not self.db_conn:
            return

        with self.db_conn:
            self.db_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT,
                    receiver TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            self.db_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT,
                    groupname TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            self.db_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS urgent (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT,
                    groupname TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
        self.logger.info("Database tables created or verified.")

    def insert_message(self, table, sender, recipient, message):
        """
        Inserts a message into the specified table in the database.

        This method saves a message along with its sender and receiver or group name into the specified table.
        If the database connection is not available, it logs an error message.

        Parameters:
        -----------
        table : str
            The name of the table where the message should be inserted. It can be 'messages', 'groups', or 'urgent'.

        sender : str
            The meshtastic node identifier of the sender who issued the command

        recipient : str
            The identifier of the receiver of the message or the group name.

        message : str
            The content of the message.

        Example Usage:
        --------------
        client.insert_message('messages', sender='CALLSIGN1', receiver_or_group='CALLSIGN2', message='This is a message.')
        client.insert_message('groups', sender='CALLSIGN1', receiver_or_group='GroupName', message='This is a group message.')
        client.insert_message('urgent', sender='CALLSIGN1', receiver_or_group='UrgentGroupName', message='This is an urgent message.')
        """

        if not self.db_conn:
            self.logger.error("Database connection is not available.")
            return

        try:
            with self.db_conn:
                self.db_conn.execute(
                    f"""
                    INSERT INTO {table} (sender, { "receiver" if table == "messages" else "groupname" }, message)
                    VALUES (?, ?, ?)
                """,
                    (sender, recipient, message),
                )
        except sqlite3.Error as e:
            self.logger.error("Failed to insert message into %s table: %s", table, e)

    def process(self, message):
        """
        Processes incoming messages and handles them based on their type and content.

        Args:
            message (dict): The incoming message to process. Expected keys are 'type', 'value', and 'params'.

        Returns:
            None

        The function performs the following actions:
        - Checks if the message type is in the list of recognized types.
        - If the type is 'RX.DIRECTED' and the value is present, it parses the message.
        - Logs the received message and processes it based on the receiver:
            - If the receiver is in the urgent list, inserts the message as urgent and sends a notification.
            - If the receiver is in the groups list, inserts the message into the groups.
            - If message storing is enabled, inserts the message into the general messages.
        """
        typ = message.get("type", "")
        value = message.get("value", "")
        # pylint: disable = unused-variable
        params = message.get("params", {})

        if not typ:
            return

        rx_types = [
            "RX.ACTIVITY",
            "RX.DIRECTED",
            "RX.SPOT",
            "RX.CALL_ACTIVITY",
            "RX.CALL_SELECTED",
            "RX.DIRECTED_ME",
            "RX.ECHO",
            "RX.DIRECTED_GROUP",
            "RX.META",
            "RX.MSG",
            "RX.PING",
            "RX.PONG",
            "RX.STREAM",
        ]

        if typ not in rx_types:
            return

        if typ == "RX.DIRECTED" and value:
            parts = value.split(" ")
            if len(parts) < 3:
                self.logger.warning(f"Unexpected message format: {value}")
                return

            sender = parts[0]
            receiver = parts[1]
            msg = " ".join(parts[2:]).strip()

            self.logger.info(
                f"Received JS8Call message: {sender} to {receiver} - {msg}"
            )

            if receiver in self.js8urgent:
                self.insert_message("urgent", sender, receiver, msg)
                notification_message = f"💥 URGENT JS8Call Message Received 💥\nFrom: {sender}\nCheck BBS for message"
                send_message(notification_message, BROADCAST_NUM, self.interface)
            elif receiver in self.js8groups:
                self.insert_message("groups", sender, receiver, msg)
            elif self.store_messages:
                self.insert_message("messages", sender, receiver, msg)
        else:
            pass

    def send(self, *args, **kwargs):
        """
        Sends a message through the socket.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments. Expected to contain 'params' dictionary.

        Keyword Args:
            params (dict): Dictionary of parameters to include in the message. If '_ID' is not present,
                           it will be added with the current timestamp in milliseconds.

        Returns:
            None
        """
        params = kwargs.get("params", {})
        if "_ID" not in params:
            # pylint: disable = consider-using-f-string
            params["_ID"] = "{}".format(
                int(time.time() * 1000)
            )
            kwargs["params"] = params
        message = to_message(*args, **kwargs)
        self.sock.send((message + "\n").encode("utf-8"))  # Convert to bytes

    def connect(self):
        """
        Establishes a connection to the JS8Call server and processes incoming messages.

        This method attempts to connect to the JS8Call server using the provided server configuration.
        If the server configuration is not found, it logs an informational message and skips the connection attempt.
        Upon successful connection, it sends a "STATION.GET_STATUS" command to the server and enters a loop to
        receive and process incoming messages.

        The loop continues to receive messages from the server, decode them, and process them as long as the
        connection is maintained. If the connection is refused, it logs an error message.

        Raises:
            ConnectionRefusedError: If the connection to the JS8Call server is refused.

        Logs:
            - Info: When the server configuration is not found or when attempting to connect to the server.
            - Error: If the connection to the server is refused.
        """
        if not self.server[0] or not self.server[1]:
            self.logger.info(
                "JS8Call server configuration not found. Skipping JS8Call connection."
            )
            return

        self.logger.info("Connecting to %s", self.server)
        self.sock = socket(AF_INET, SOCK_STREAM)
        try:
            self.sock.connect(self.server)
            self.connected = True
            self.send("STATION.GET_STATUS")

            while self.connected:
                content = self.sock.recv(65500).decode(
                    "utf-8"
                )  # Decode received bytes to string
                if not content:
                    continue  # Skip empty content

                try:
                    message = json.loads(content)
                except ValueError:
                    continue  # Skip invalid JSON content

                if not message:
                    continue  # Skip empty message

                self.process(message)
        except ConnectionRefusedError:
            self.logger.error(f"Connection to JS8Call server {self.server} refused.")
        finally:
            self.sock.close()

    def close(self):
        """
        Closes the connection by setting the connected attribute to False.
        """
        self.connected = False


def handle_js8call_command(sender_id, interface):
    """
    Handles the JS8Call command by sending a menu response to the sender and updating the user's state.

    Args:
        sender_id (str): The ID of the sender who initiated the command.
        interface (object): The interface object used to send messages and interact with the user.

    Returns:
        None
    """
    response = (
        "JS8Call Menu:\n[G]roup Messages\n[S]tation Messages\n[U]rgent Messages\nE[X]IT"
    )
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {"command": "JS8CALL_MENU", "step": 1})

# pylint: disable = unused-argument
def handle_js8call_steps(sender_id, message, step, interface, state):
    """
    Handles the steps for processing JS8Call messages based on the current step and user input.

    Args:
        sender_id (str): The ID of the sender.
        message (str): The message received from the sender.
        step (int): The current step in the JS8Call message handling process.
        interface (object): The interface object used for communication.
        state (dict): The current state of the message handling process.

    Returns:
        None
    """
    message = message.lower().strip()
    if len(message) == 2 and message[1] == "x":
        message = message[0]

    if step == 1:
        choice = message
        if choice == "x":
            handle_help_command(sender_id, interface, "bbs")
            return
        elif choice == "g":
            handle_group_messages_command(sender_id, interface)
        elif choice == "s":
            handle_station_messages_command(sender_id, interface)
        elif choice == "u":
            handle_urgent_messages_command(sender_id, interface)
        else:
            send_message("Invalid option. Please choose again.", sender_id, interface)
            handle_js8call_command(sender_id, interface)


def handle_group_messages_command(sender_id, interface):
    """
    Handles the command to display group messages menu to the user.

    This function connects to the 'js8call.db' SQLite database, retrieves the list of distinct group names from the 'groups' table,
    and sends a formatted menu of these groups to the user. If no groups are available, it notifies the user accordingly and
    calls the `handle_js8call_command` function.

    Args:
        sender_id (str): The ID of the user sending the command.
        interface (object): The interface object used to send messages and interact with the user.

    Returns:
        None
    """
    conn = sqlite3.connect("js8call.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT groupname FROM groups")
    groups = c.fetchall()
    if groups:
        response = "Group Messages Menu:\n" + "\n".join(
            [f"[{i}] {group[0]}" for i, group in enumerate(groups)]
        )
        send_message(response, sender_id, interface)
        update_user_state(
            sender_id, {"command": "GROUP_MESSAGES", "step": 1, "groups": groups}
        )
    else:
        send_message("No group messages available.", sender_id, interface)
        handle_js8call_command(sender_id, interface)


def handle_station_messages_command(sender_id, interface):
    """
    Handles the command to retrieve and send station messages.

    This function connects to the 'js8call.db' SQLite database, retrieves all messages
    from the 'messages' table, and sends them to the specified sender via the given interface.
    If no messages are found, it sends a message indicating that no station messages are available.
    After processing the messages, it calls the handle_js8call_command function.

    Args:
        sender_id (str): The ID of the sender to whom the messages will be sent.
        interface (object): The interface object used to send messages.

    Returns:
        None
    """
    conn = sqlite3.connect("js8call.db")
    c = conn.cursor()
    c.execute("SELECT sender, receiver, message, timestamp FROM messages")
    messages = c.fetchall()
    if messages:
        response = "Station Messages:\n" + "\n".join(
            [
                f"[{i+1}] {msg[0]} -> {msg[1]}: {msg[2]} ({msg[3]})"
                for i, msg in enumerate(messages)
            ]
        )
        send_message(response, sender_id, interface)
    else:
        send_message("No station messages available.", sender_id, interface)
    handle_js8call_command(sender_id, interface)


def handle_urgent_messages_command(sender_id, interface):
    """
    Handles the command to retrieve and send urgent messages.

    This function connects to the 'js8call.db' SQLite database, retrieves all
    urgent messages from the 'urgent' table, and sends them to the specified
    sender via the given interface. If no urgent messages are available, it
    sends a message indicating that.

    Args:
        sender_id (str): The ID of the sender requesting the urgent messages.
        interface (object): The interface used to send the messages.

    Returns:
        None
    """
    conn = sqlite3.connect("js8call.db")
    c = conn.cursor()
    c.execute("SELECT sender, groupname, message, timestamp FROM urgent")
    messages = c.fetchall()
    if messages:
        response = "Urgent Messages:\n" + "\n".join(
            [
                f"[{i+1}] {msg[0]} -> {msg[1]}: {msg[2]} ({msg[3]})"
                for i, msg in enumerate(messages)
            ]
        )
        send_message(response, sender_id, interface)
    else:
        send_message("No urgent messages available.", sender_id, interface)
    handle_js8call_command(sender_id, interface)

# pylint: disable = unused-argument
def handle_group_message_selection(sender_id, message, step, state, interface):
    """
    Handles the selection of a group message by the user.

    Args:
        sender_id (str): The ID of the sender.
        message (str): The message containing the group selection.
        step (int): The current step in the message handling process.
        state (dict): The current state, including available groups.
        interface (object): The interface used to send messages.

    Raises:
        IndexError: If the selected group index is out of range.
        ValueError: If the message cannot be converted to an integer.

    Side Effects:
        Sends a message to the sender with the messages from the selected group,
        or an error message if the selection is invalid or there are no messages.
    """
    groups = state["groups"]
    try:
        group_index = int(message)
        groupname = groups[group_index][0]

        conn = sqlite3.connect("js8call.db")
        c = conn.cursor()
        c.execute(
            "SELECT sender, message, timestamp FROM groups WHERE groupname=?",
            (groupname,),
        )
        messages = c.fetchall()

        if messages:
            response = f"Messages for group {groupname}:\n" + "\n".join(
                [
                    f"[{i+1}] {msg[0]}: {msg[1]} ({msg[2]})"
                    for i, msg in enumerate(messages)
                ]
            )
            send_message(response, sender_id, interface)
        else:
            send_message(f"No messages for group {groupname}.", sender_id, interface)
    except (IndexError, ValueError):
        send_message(
            "Invalid group selection. Please choose again.", sender_id, interface
        )
        handle_group_messages_command(sender_id, interface)

    handle_js8call_command(sender_id, interface)
