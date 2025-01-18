"""
Command handlers utilities.
"""

import configparser
import logging
import random
import time
from typing import List

from meshtastic import BROADCAST_NUM  # type: ignore

from db_operations import (
    add_bulletin,
    add_mail,
    delete_mail,
    get_bulletin_content,
    get_bulletins,
    get_mail,
    get_mail_content,
    add_channel,
    get_channels,
    get_sender_id_by_mail_id,
)
from utils import (
    get_node_id_from_num,
    get_node_info,
    get_node_short_name,
    send_message,
    update_user_state,
)

# Read the configuration for menu options
config = configparser.ConfigParser()
config.read("config.ini")

main_menu_items = config["menu"]["main_menu_items"].split(",")
bbs_menu_items = config["menu"]["bbs_menu_items"].split(",")
utilities_menu_items = config["menu"]["utilities_menu_items"].split(",")
service_name = config["service"]["name"]


def build_menu(items: List[str], menu_name: str):
    """
    Builds a menu string based on the provided items and menu name.

    Args:
        items (list of str): A list of single-character strings representing menu options.
        menu_name (str): The name of the menu to be displayed at the top.

    Returns:
        str: A formatted menu string with each item on a new line.
    """
    menu_str = f"{menu_name}\n"
    for item in items:
        if item.strip() == "Q":
            menu_str += "[Q]uick Commands\n"
        elif item.strip() == "B":
            menu_str += "[B]BS\n"
        elif item.strip() == "U":
            menu_str += "[U]tilities\n"
        elif item.strip() == "X":
            menu_str += "E[X]IT\n"
        elif item.strip() == "M":
            menu_str += "[M]ail\n"
        elif item.strip() == "C":
            menu_str += "[C]hannel Dir\n"
        elif item.strip() == "J":
            menu_str += "[J]S8CALL\n"
        elif item.strip() == "S":
            menu_str += "[S]tats\n"
        elif item.strip() == "F":
            menu_str += "[F]ortune\n"
        elif item.strip() == "W":
            menu_str += "[W]all of Shame\n"
    return menu_str


def handle_help_command(sender_id: int | str, interface, menu_name=None):
    """
    Handles the help command by updating the user state and building the appropriate menu response.

    Parameters:
    sender_id (int|str): The ID of the sender.
    interface (object): The interface through which the command was received.
    menu_name (str, optional): The name of the menu to display. Defaults to None.

    Returns:
    None
    """
    response = "Nothing to reply"
    if menu_name:
        update_user_state(sender_id, {"command": "MENU", "menu": menu_name, "step": 1})
        if menu_name == "bbs":
            response = build_menu(bbs_menu_items, "Menu")
        elif menu_name == "utilities":
            response = build_menu(utilities_menu_items, "Utilities Menu")
    else:
        update_user_state(
            sender_id, {"command": "MAIN_MENU", "step": 1}
        )  # Reset to main menu state
        mail = get_mail(get_node_id_from_num(sender_id, interface))
        response = build_menu(main_menu_items, f"{service_name} (✉️:{len(mail)})")
    send_message(response, sender_id, interface)


def get_node_name(node_id: str | int, interface):
    """
    Retrieve the long name of a node given its ID.

    Args:
        node_id (str| int): The unique identifier of the node.
        interface (object): The interface object that contains node information.

    Returns:
        str: The long name of the node if available, otherwise a default name in the format "Node {node_id}".
    """
    node_info = interface.nodes.get(node_id)
    if node_info:
        return node_info["user"]["longName"]
    return f"Node {node_id}"


def handle_mail_command(sender_id, interface):
    """
    Handles the mail command by sending a mail menu to the user and updating the user's state.

    Parameters:
    sender_id (str): The ID of the sender who issued the mail command.
    interface (object): The interface object used to send messages and interact with the user.

    Returns:
    None
    """
    response = "Mail Menu\nWhat would you like to do with mail?\n[R]ead  [S]end E[X]IT"
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {"command": "MAIL", "step": 1})


def handle_bulletin_command(sender_id, interface):
    """
    Handles the bulletin command by sending a bulletin menu message to the user and updating the user's state.

    Args:
        sender_id (str): The ID of the sender who issued the command.
        interface (object): The interface object used to send messages and interact with the user.

    Returns:
        None
    """
    response = "Bulletin Menu\nWhich board would you like to enter?\n[G]eneral  [I]nfo  [N]ews  [U]rgent"
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {"command": "BULLETIN_MENU", "step": 1})


def handle_exit_command(sender_id, interface):
    """
    Handles the 'exit' command from a user.

    This function sends a message to the user indicating how to get help and updates the user's state to None.

    Args:
        sender_id (str): The ID of the user sending the command.
        interface (object): The interface through which the message is sent.

    Returns:
        None
    """
    send_message("Type 'HELP' for a list of commands.", sender_id, interface)
    update_user_state(sender_id, None)


def handle_stats_command(sender_id, interface):
    """
    Handles the 'stats' command from a user.

    This function sends a response message to the user with a menu of stats options
    and updates the user's state to indicate that they are in the 'STATS' command flow.

    Args:
        sender_id (str): The ID of the user who sent the command.
        interface (object): The interface through which the message is sent.

    Returns:
        None
    """
    response = "Stats Menu\nWhat stats would you like to view?\n[N]odes  [H]ardware  [R]oles  E[X]IT"
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {"command": "STATS", "step": 1})


def handle_fortune_command(sender_id, interface):
    """
    Handle the fortune command by sending a random fortune message to the sender.

    This function reads fortunes from a file named 'fortunes.txt', selects a random fortune,
    and sends it to the specified sender through the given interface. If the file is empty
    or an error occurs, an appropriate error message is sent instead.

    Args:
        sender_id (str): The ID of the sender to whom the fortune message will be sent.
        interface (object): The interface used to send the message.

    Raises:
        FileNotFoundError: If the 'fortunes.txt' file does not exist.
        IOError: If there is an error reading the 'fortunes.txt' file.
        ValueError: If there is an error processing the fortune data.
        KeyError: If there is an error processing the fortune data.
        TypeError: If there is an error processing the fortune data.
    """
    try:
        with open("fortunes.txt", "r", encoding="utf-8") as file:
            fortunes = file.readlines()
        if not fortunes:
            send_message("No fortunes available.", sender_id, interface)
            return
        fortune = random.choice(fortunes).strip()
        decorated_fortune = f"{fortune}"
        send_message(decorated_fortune, sender_id, interface)
    except (ValueError, KeyError, TypeError) as e:
        send_message(f"Error generating fortune: {e}", sender_id, interface)


def handle_stats_steps(sender_id, message, step, interface):
    """
    Handles the different steps of the stats command based on the user's input message.

    Args:
        sender_id (str): The ID of the sender.
        message (str): The message sent by the user.
        step (int): The current step in the stats command process.
        interface (object): The interface object containing nodes and other relevant data.

    Returns:
        None

    The function processes the user's message and performs different actions based on the step and the content of the message:
    - If the message is 'x', it calls the help command handler.
    - If the message is 'n', it calculates and sends the total number of nodes seen in different timeframes.
    - If the message is 'h', it calculates and sends the count of different hardware models.
    - If the message is 'r', it calculates and sends the count of different roles.
    """
    message = message.lower().strip()
    if len(message) == 2 and message[1] == "x":
        message = message[0]

    if step == 1:
        choice = message
        if choice == "x":
            handle_help_command(sender_id, interface)
            return
        elif choice == "n":
            current_time = int(time.time())
            timeframes = {
                "All time": None,
                "Last 24 hours": 86400,
                "Last 8 hours": 28800,
                "Last hour": 3600,
            }
            total_nodes_summary = []

            for period, seconds in timeframes.items():
                if seconds is None:
                    total_nodes = len(interface.nodes)
                else:
                    time_limit = current_time - seconds
                    total_nodes = sum(
                        1
                        for node in interface.nodes.values()
                        if node.get("lastHeard") is not None
                        and node["lastHeard"] >= time_limit
                    )
                total_nodes_summary.append(f"- {period}: {total_nodes}")

            response = "Total nodes seen:\n" + "\n".join(total_nodes_summary)
            send_message(response, sender_id, interface)
            handle_stats_command(sender_id, interface)
        elif choice == "h":
            hw_models = {}
            for node in interface.nodes.values():
                hw_model = node["user"].get("hwModel", "Unknown")
                hw_models[hw_model] = hw_models.get(hw_model, 0) + 1
            response = "Hardware Models:\n" + "\n".join(
                [f"{model}: {count}" for model, count in hw_models.items()]
            )
            send_message(response, sender_id, interface)
            handle_stats_command(sender_id, interface)
        elif choice == "r":
            roles = {}
            for node in interface.nodes.values():
                role = node["user"].get("role", "Unknown")
                roles[role] = roles.get(role, 0) + 1
            response = "Roles:\n" + "\n".join(
                [f"{role}: {count}" for role, count in roles.items()]
            )
            send_message(response, sender_id, interface)
            handle_stats_command(sender_id, interface)


def handle_bb_steps(sender_id, message, step, state, interface, bbs_nodes):
    """
    Handles the bulletin board steps for a user.

    Parameters:
    sender_id (str): The ID of the sender.
    message (str): The message sent by the user.
    step (int): The current step in the bulletin board process.
    state (dict): The current state of the user.
    interface (object): The interface object for sending and receiving messages.
    bbs_nodes (list): The list of bulletin board system nodes.

    Steps:
    1. Select a bulletin board.
    2. Choose to read or post a bulletin.
    3. Read a selected bulletin.
    4. Enter the subject of a new bulletin.
    5. Enter the content of a new bulletin.

    Returns:
    None
    """
    boards = {0: "General", 1: "Info", 2: "News", 3: "Urgent"}
    if step == 1:
        if message.lower() == "e":
            handle_help_command(sender_id, interface, "bbs")
            return
        board_name = boards[int(message)]
        bulletins = get_bulletins(board_name)
        response = f"{board_name} has {len(bulletins)} messages.\n[R]ead  [P]ost"
        send_message(response, sender_id, interface)
        update_user_state(
            sender_id, {"command": "BULLETIN_ACTION", "step": 2, "board": board_name}
        )

    elif step == 2:
        board_name = state["board"]
        if message.lower() == "r":
            bulletins = get_bulletins(board_name)
            if bulletins:
                send_message(
                    f"Select a bulletin number to view from {board_name}:",
                    sender_id,
                    interface,
                )
                for bulletin in bulletins:
                    send_message(f"[{bulletin[0]}] {bulletin[1]}", sender_id, interface)
                update_user_state(
                    sender_id,
                    {"command": "BULLETIN_READ", "step": 3, "board": board_name},
                )
            else:
                send_message(f"No bulletins in {board_name}.", sender_id, interface)
                handle_bb_steps(sender_id, "e", 1, state, interface, bbs_nodes)
        elif message.lower() == "p":
            if board_name.lower() == "urgent":
                node_id = get_node_id_from_num(sender_id, interface)
                allowed_nodes = interface.allowed_nodes
                logging.info(
                    "Checking permissions for node_id: %s with allowed_nodes: %s",
                    node_id,
                    allowed_nodes,
                )  # Debug statement
                if allowed_nodes and node_id not in allowed_nodes:
                    send_message(
                        "You don't have permission to post to this board.",
                        sender_id,
                        interface,
                    )
                    handle_bb_steps(sender_id, "e", 1, state, interface, bbs_nodes)
                    return
            send_message(
                "What is the subject of your bulletin? Keep it short.",
                sender_id,
                interface,
            )
            update_user_state(
                sender_id, {"command": "BULLETIN_POST", "step": 4, "board": board_name}
            )

    elif step == 3:
        bulletin_id = int(message)
        # pylint: disable = unused-variable
        sender_short_name, date, subject, content, unique_id = get_bulletin_content(
            bulletin_id
        )
        send_message(
            f"From: {sender_short_name}\nDate: {date}\nSubject: {subject}\n- - - - - - -\n{content}",
            sender_id,
            interface,
        )
        board_name = state["board"]
        handle_bb_steps(sender_id, "e", 1, state, interface, bbs_nodes)

    elif step == 4:
        subject = message
        send_message(
            "Send the contents of your bulletin. Send a message with END when finished.",
            sender_id,
            interface,
        )
        update_user_state(
            sender_id,
            {
                "command": "BULLETIN_POST_CONTENT",
                "step": 5,
                "board": state["board"],
                "subject": subject,
                "content": "",
            },
        )

    elif step == 5:
        if message.lower() == "end":
            board = state["board"]
            subject = state["subject"]
            content = state["content"]
            node_id = get_node_id_from_num(sender_id, interface)
            node_info = interface.nodes.get(node_id)
            if node_info is None:
                send_message(
                    "Error: Unable to retrieve your node information.",
                    sender_id,
                    interface,
                )
                update_user_state(sender_id, None)
                return
            sender_short_name = node_info["user"].get("shortName", f"Node {sender_id}")
            unique_id = add_bulletin(
                board, sender_short_name, subject, content, bbs_nodes, interface
            )
            send_message(
                f"Your bulletin '{subject}' has been posted to {board}.\n(╯°□°)╯[{board}]",
                sender_id,
                interface,
            )
            handle_bb_steps(sender_id, "e", 1, state, interface, bbs_nodes)
        else:
            state["content"] += message + "\n"
            update_user_state(sender_id, state)


def handle_mail_steps(sender_id, message, step, state, interface, bbs_nodes):
    """
    Handles the steps for the mail command in a multi-step process.

    Parameters:
    sender_id (str): The ID of the sender.
    message (str): The message content sent by the user.
    step (int): The current step in the mail handling process.
    state (dict): The current state of the user.
    interface (object): The interface object for communication.
    bbs_nodes (list): List of BBS nodes.

    Steps:
    1. Initial step where the user chooses to read, send, or exit mail.
    2. User selects a mail to read.
    3. User provides the short name of the node to send a message to.
    4. User decides to keep, delete, or reply to a message.
    5. User provides the subject of the message.
    6. User selects a specific node if multiple nodes match the short name.
    7. User writes the content of the message and sends it.
    8. User confirms if they want to perform another mail command.

    Returns:
    None
    """
    message = message.strip()
    if len(message) == 2 and message[1] == "x":
        message = message[0]

    if step == 1:
        choice = message.lower()
        if choice == "r":
            sender_node_id = get_node_id_from_num(sender_id, interface)
            mail = get_mail(sender_node_id)
            if mail:
                send_message(
                    f"You have {len(mail)} mail messages. Select a message number to read:",
                    sender_id,
                    interface,
                )
                for msg in mail:
                    send_message(
                        f"-{msg[0]}-\nDate: {msg[3]}\nFrom: {msg[1]}\nSubject: {msg[2]}",
                        sender_id,
                        interface,
                    )
                update_user_state(sender_id, {"command": "MAIL", "step": 2})
            else:
                send_message(
                    "There are no messages in your mailbox.", sender_id, interface
                )
                update_user_state(sender_id, None)
        elif choice == "s":
            send_message(
                "What is the Short Name of the node you want to leave a message for?",
                sender_id,
                interface,
            )
            update_user_state(sender_id, {"command": "MAIL", "step": 3})
        elif choice == "x":
            handle_help_command(sender_id, interface)

    elif step == 2:
        mail_id = int(message)
        try:
            sender_node_id = get_node_id_from_num(sender_id, interface)
            sender, date, subject, content, unique_id = get_mail_content(
                mail_id, sender_node_id
            )
            send_message(
                f"Date: {date}\nFrom: {sender}\nSubject: {subject}\n{content}",
                sender_id,
                interface,
            )
            send_message(
                "What would you like to do with this message?\n[K]eep  [D]elete  [R]eply",
                sender_id,
                interface,
            )
            update_user_state(
                sender_id,
                {
                    "command": "MAIL",
                    "step": 4,
                    "mail_id": mail_id,
                    "unique_id": unique_id,
                    "sender": sender,
                    "subject": subject,
                    "content": content,
                },
            )
        except TypeError:
            logging.info("Node %s tried to access non-existent message", sender_id)
            send_message("Mail not found", sender_id, interface)
            update_user_state(sender_id, None)

    elif step == 3:
        short_name = message.lower()
        nodes = get_node_info(interface, short_name)
        if not nodes:
            send_message(
                "I'm unable to find that node in my database.", sender_id, interface
            )
            handle_mail_command(sender_id, interface)
        elif len(nodes) == 1:
            recipient_id = nodes[0]["num"]
            recipient_name = get_node_name(recipient_id, interface)
            send_message(
                f"What is the subject of your message to {recipient_name}?\nKeep it short.",
                sender_id,
                interface,
            )
            update_user_state(
                sender_id, {"command": "MAIL", "step": 5, "recipient_id": recipient_id}
            )
        else:
            send_message(
                "There are multiple nodes with that short name. Which one would you like to leave a message for?",
                sender_id,
                interface,
            )
            for i, node in enumerate(nodes):
                send_message(f"[{i}] {node['longName']}", sender_id, interface)
            update_user_state(sender_id, {"command": "MAIL", "step": 6, "nodes": nodes})

    elif step == 4:
        if message.lower() == "d":
            unique_id = state["unique_id"]
            sender_node_id = get_node_id_from_num(sender_id, interface)
            delete_mail(unique_id, sender_node_id, bbs_nodes, interface)
            send_message("The message has been deleted 🗑️", sender_id, interface)
            update_user_state(sender_id, None)
        elif message.lower() == "r":
            sender = state["sender"]
            send_message(
                f"Send your reply to {sender} now, followed by a message with END",
                sender_id,
                interface,
            )
            update_user_state(
                sender_id,
                {
                    "command": "MAIL",
                    "step": 7,
                    "reply_to_mail_id": state['mail_id'],
                    "subject": f"Re: {state['subject']}",
                    "content": "",
                },
            )
        else:
            send_message(
                "The message has been kept in your inbox.✉️", sender_id, interface
            )
            update_user_state(sender_id, None)

    elif step == 5:
        subject = message
        send_message(
            "Send your message. You can send it in multiple messages if it's too long for one.\nSend a single message with END when you're done",
            sender_id,
            interface,
        )
        update_user_state(
            sender_id,
            {
                "command": "MAIL",
                "step": 7,
                "recipient_id": state["recipient_id"],
                "subject": subject,
                "content": "",
            },
        )

    elif step == 6:
        selected_node_index = int(message)
        selected_node = state["nodes"][selected_node_index]
        recipient_id = selected_node["num"]
        recipient_name = get_node_name(recipient_id, interface)
        send_message(
            f"What is the subject of your message to {recipient_name}?\nKeep it short.",
            sender_id,
            interface,
        )
        update_user_state(
            sender_id, {"command": "MAIL", "step": 5, "recipient_id": recipient_id}
        )

    elif step == 7:
        if message.lower() == "end":
            if "reply_to_mail_id" in state:
                recipient_id = get_sender_id_by_mail_id(
                    state["reply_to_mail_id"]
                )  # Get the sender ID from the mail ID
            else:
                recipient_id = state.get("recipient_id")
            subject = state["subject"]
            content = state["content"]
            recipient_name = get_node_name(recipient_id, interface)

            sender_short_name = get_node_short_name(
                get_node_id_from_num(sender_id, interface), interface
            )
            unique_id = add_mail(
                get_node_id_from_num(sender_id, interface),
                sender_short_name,
                recipient_id,
                subject,
                content,
                bbs_nodes,
                interface,
            )
            send_message(
                f"Mail has been posted to the mailbox of {recipient_name}.\n(╯°□°)╯",
                sender_id,
                interface,
            )

            notification_message = f"You have a new mail message from {sender_short_name}. Check your mailbox by responding to this message with CM."
            send_message(notification_message, recipient_id, interface)

            update_user_state(sender_id, None)
            update_user_state(sender_id, {"command": "MAIL", "step": 8})
        else:
            state["content"] += message + "\n"
            update_user_state(sender_id, state)

    elif step == 8:
        if message.lower() == "y":
            handle_mail_command(sender_id, interface)
        else:
            send_message(
                "Okay, feel free to send another command.", sender_id, interface
            )
            update_user_state(sender_id, None)


def handle_wall_of_shame_command(sender_id, interface):
    """
    Handles the "wall of shame" command which lists devices with battery levels below 20%.

    Args:
        sender_id (str): The ID of the sender issuing the command.
        interface (object): The interface object containing nodes and their metrics.

    Returns:
        None: Sends a message with the list of devices with low battery levels.
    """
    response = "Devices with battery levels below 20%:\n"
    # pylint: disable = unused-variable
    for node_id, node in interface.nodes.items():
        metrics = node.get("deviceMetrics", {})
        battery_level = metrics.get("batteryLevel", 101)
        if battery_level < 20:
            long_name = node["user"]["longName"]
            response += f"{long_name} - Battery {battery_level}%\n"
    if response == "Devices with battery levels below 20%:\n":
        response = "No devices with battery levels below 20% found."
    send_message(response, sender_id, interface)


def handle_channel_directory_command(sender_id, interface):
    """
    Handles the channel directory command by sending a response message to the user
    and updating the user's state.

    Args:
        sender_id (str): The ID of the sender/user who issued the command.
        interface (object): The interface object used to send messages and interact with the user.

    Returns:
        None
    """
    response = "CHANNEL DIRECTORY\nWhat would you like to do?\n[V]iew  [P]ost  E[X]IT"
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {"command": "CHANNEL_DIRECTORY", "step": 1})


def handle_channel_directory_steps(sender_id, message, step, state, interface):
    """
    Handles the steps for the channel directory command based on the current step and user input.

    Parameters:
    sender_id (str): The ID of the sender.
    message (str): The message sent by the user.
    step (int): The current step in the channel directory process.
    state (dict): The current state of the user.
    interface (object): The interface to send messages and interact with the user.

    Steps:
    1. Initial step where the user can choose to view channels ('v'), add a channel ('p'), or get help ('x').
    2. User selects a channel to view from the list of available channels.
    3. User provides a name for the new channel to be added to the directory.
    4. User provides the URL or PSK for the new channel, which is then added to the directory.

    Returns:
    None
    """
    message = message.strip()
    if len(message) == 2 and message[1] == "x":
        message = message[0]

    if step == 1:
        choice = message
        if choice.lower() == "x":
            handle_help_command(sender_id, interface)
            return
        elif choice.lower() == "v":
            channels = get_channels()
            if channels:
                response = "Select a channel number to view:\n" + "\n".join(
                    [f"[{i}] {channel[0]}" for i, channel in enumerate(channels)]
                )
                send_message(response, sender_id, interface)
                update_user_state(
                    sender_id, {"command": "CHANNEL_DIRECTORY", "step": 2}
                )
            else:
                send_message(
                    "No channels available in the directory.", sender_id, interface
                )
                handle_channel_directory_command(sender_id, interface)
        elif choice.lower == "p":
            send_message("Name your channel for the directory:", sender_id, interface)
            update_user_state(sender_id, {"command": "CHANNEL_DIRECTORY", "step": 3})

    elif step == 2:
        channel_index = int(message)
        channels = get_channels()
        if 0 <= channel_index < len(channels):
            channel_name, channel_url = channels[channel_index]
            send_message(
                f"Channel Name: {channel_name}\nChannel URL:\n{channel_url}",
                sender_id,
                interface,
            )
        handle_channel_directory_command(sender_id, interface)

    elif step == 3:
        channel_name = message
        send_message(
            "Send a message with your channel URL or PSK:", sender_id, interface
        )
        update_user_state(
            sender_id,
            {"command": "CHANNEL_DIRECTORY", "step": 4, "channel_name": channel_name},
        )

    elif step == 4:
        channel_url = message
        channel_name = state["channel_name"]
        add_channel(channel_name, channel_url)
        send_message(
            f"Your channel '{channel_name}' has been added to the directory.",
            sender_id,
            interface,
        )
        handle_channel_directory_command(sender_id, interface)


def handle_send_mail_command(sender_id, message, interface, bbs_nodes):
    """
    Handles the 'send mail' command by parsing the message, validating the recipient,
    and sending the mail to the specified recipient.

    Args:
        sender_id (int): The ID of the sender node.
        message (str): The message containing the mail command and its parameters.
        interface (object): The interface object used for communication.
        bbs_nodes (list): The list of BBS nodes.

    Returns:
        None

    Raises:
        configparser.Error: If there is an error in the configuration.
        IOError: If there is an I/O error.

    The expected format of the message is:
        "SM,,{short_name},,{subject},,{message}"

    The function performs the following steps:
        1. Splits the message into parts.
        2. Validates the number of parts.
        3. Retrieves the recipient node information based on the short name.
        4. Validates the recipient node.
        5. Sends the mail to the recipient.
        6. Notifies the recipient about the new mail.
        7. Handles any errors that occur during the process.
    """
    try:
        parts = message.split(",,", 3)
        if len(parts) != 4:
            send_message(
                "Send Mail Quick Command format:\nSM,,{short_name},,{subject},,{message}",
                sender_id,
                interface,
            )
            return

        _, short_name, subject, content = parts
        nodes = get_node_info(interface, short_name.lower())
        if not nodes:
            send_message(
                f"Node with short name '{short_name}' not found.", sender_id, interface
            )
            return
        if len(nodes) > 1:
            send_message(
                f"Multiple nodes with short name '{short_name}' found. Please be more specific.",
                sender_id,
                interface,
            )
            return

        recipient_id = nodes[0]["num"]
        recipient_name = get_node_name(recipient_id, interface)
        sender_short_name = get_node_short_name(
            get_node_id_from_num(sender_id, interface), interface
        )
        # pylint: disable = unused-variable
        unique_id = add_mail(
            get_node_id_from_num(sender_id, interface),
            sender_short_name,
            recipient_id,
            subject,
            content,
            bbs_nodes,
            interface,
        )
        send_message(f"Mail has been sent to {recipient_name}.", sender_id, interface)

        notification_message = f"You have a new mail message from {sender_short_name}. Check your mailbox by responding to this message with CM."
        send_message(notification_message, recipient_id, interface)

    except (configparser.Error, IOError) as e:
        logging.error("Error processing send mail command: %s", e)
        send_message("Error processing send mail command.", sender_id, interface)


def handle_check_mail_command(sender_id, interface):
    """
    Handles the 'check mail' command for a given sender.

    This function retrieves the mail for the sender, formats a response message
    listing the available messages, and sends it back to the sender. If there are
    no new messages, it informs the sender accordingly. It also updates the user's
    state to indicate that they are in the process of checking their mail.

    Args:
        sender_id (int): The ID of the sender requesting to check their mail.
        interface (object): The interface object used to interact with the messaging system.

    Raises:
        Exception: If an error occurs while processing the command, it logs the error
                   and sends an error message to the sender.
    """
    try:
        sender_node_id = get_node_id_from_num(sender_id, interface)
        mail = get_mail(sender_node_id)
        if not mail:
            send_message("You have no new messages.", sender_id, interface)
            return

        response = "You have the following messages:\n"
        for i, msg in enumerate(mail):
            response += f"{i + 1:02d}. From: {msg[1]}, Subject: {msg[2]}\n"
        response += "\nPlease reply with the number of the message you want to read."
        send_message(response, sender_id, interface)

        update_user_state(sender_id, {"command": "CHECK_MAIL", "step": 1, "mail": mail})

    except (ValueError, KeyError, TypeError) as e:
        logging.error("Error processing check mail command: %s", e)
        send_message("Error processing check mail command.", sender_id, interface)


def handle_read_mail_command(sender_id, message, state, interface):
    """
    Handles the 'read mail' command from a user.

    This function retrieves and displays a specific mail message based on the user's input.
    It validates the message number, fetches the mail content, and sends it back to the user.
    It also updates the user's state to prompt for further actions on the mail.

    Args:
        sender_id (str): The ID of the user who sent the command.
        message (str): The message containing the mail number to be read.
        state (dict): The current state of the user, including the list of mails.
        interface (object): The interface used to send messages back to the user.

    Raises:
        ValueError: If the message number is not a valid integer.
        Exception: If any other error occurs during the processing of the command.
    """
    try:
        mail = state.get("mail", [])
        message_number = int(message) - 1

        if message_number < 0 or message_number >= len(mail):
            send_message(
                "Invalid message number. Please try again.", sender_id, interface
            )
            return

        mail_id = mail[message_number][0]
        sender_node_id = get_node_id_from_num(sender_id, interface)
        sender, date, subject, content, unique_id = get_mail_content(
            mail_id, sender_node_id
        )
        response = f"Date: {date}\nFrom: {sender}\nSubject: {subject}\n\n{content}"
        send_message(response, sender_id, interface)
        send_message(
            "What would you like to do with this message?\n[K]eep  [D]elete  [R]eply",
            sender_id,
            interface,
        )
        update_user_state(
            sender_id,
            {
                "command": "CHECK_MAIL",
                "step": 2,
                "mail_id": mail_id,
                "unique_id": unique_id,
                "sender": sender,
                "subject": subject,
                "content": content,
            },
        )

    except ValueError:
        send_message(
            "Invalid input. Please enter a valid message number.", sender_id, interface
        )
    except (KeyError, TypeError) as e:
        logging.error("Error processing read mail command: %s", e)
        send_message("Error processing read mail command.", sender_id, interface)


def handle_delete_mail_confirmation(sender_id, message, state, interface, bbs_nodes):
    """
    Handles the confirmation for deleting a mail message.

    Parameters:
    sender_id (str): The ID of the sender.
    message (str): The message containing the user's choice.
    state (dict): The current state of the user.
    interface (object): The interface object for communication.
    bbs_nodes (list): The list of BBS nodes.

    Returns:
    None

    The function processes the user's choice to either delete the mail, reply to it, or keep it in the inbox.
    It updates the user state and sends appropriate messages based on the user's choice.
    """
    try:
        choice = message.lower().strip()
        if len(choice) == 2 and choice[1] == "x":
            choice = choice[0]

        if choice == "d":
            unique_id = state["unique_id"]
            sender_node_id = get_node_id_from_num(sender_id, interface)
            delete_mail(unique_id, sender_node_id, bbs_nodes, interface)
            send_message("The message has been deleted", sender_id, interface)
            update_user_state(sender_id, None)
        elif choice == "r":
            sender = state["sender"]
            send_message(
                f"Send your reply to {sender} now, followed by a message with END",
                sender_id,
                interface,
            )
            update_user_state(
                sender_id,
                {
                    "command": "MAIL",
                    "step": 7,
                    "reply_to_mail_id": state["mail_id"],
                    "subject": f"Re: {state['subject']}",
                    "content": "",
                },
            )
        else:
            send_message(
                "The message has been kept in your inbox.✉️", sender_id, interface
            )
            update_user_state(sender_id, None)

    except (ValueError, KeyError, TypeError) as e:
        logging.error("Error processing delete mail confirmation: %s", e)
        send_message("Error processing delete mail confirmation.", sender_id, interface)


def handle_post_bulletin_command(sender_id, message, interface, bbs_nodes):
    """
    Handles the 'Post Bulletin' command by parsing the message, creating a bulletin, and sending appropriate responses.

    Args:
        sender_id (int): The ID of the sender.
        message (str): The message containing the bulletin details.
        interface (object): The interface used for communication.
        bbs_nodes (list): The list of bulletin board system nodes.

    Raises:
        Exception: If there is an error processing the command.

    The expected message format is:
        PB,,{board_name},,{subject},,{content}

    If the board name is "urgent", a broadcast notification is sent to all users.
    """
    try:
        parts = message.split(",,", 3)
        if len(parts) != 4:
            send_message(
                "Post Bulletin Quick Command format:\nPB,,{board_name},,{subject},,{content}",
                sender_id,
                interface,
            )
            return

        _, board_name, subject, content = parts
        sender_short_name = get_node_short_name(
            get_node_id_from_num(sender_id, interface), interface
        )
        # pylint: disable = unused-variable
        unique_id = add_bulletin(
            board_name, sender_short_name, subject, content, bbs_nodes, interface
        )
        send_message(
            f"Your bulletin '{subject}' has been posted to {board_name}.",
            sender_id,
            interface,
        )

        if board_name.lower() == "urgent":
            notification_message = (
                f"💥NEW URGENT BULLETIN\nFrom: {sender_short_name}\nTitle: {subject}"
            )
            send_message(notification_message, BROADCAST_NUM, interface)

    except (ValueError, KeyError, TypeError) as e:
        logging.error("Error processing post bulletin command: %s", e)
        send_message("Error processing post bulletin command.", sender_id, interface)


def handle_check_bulletin_command(sender_id, message, interface):
    """
    Handles the "Check Bulletin" command from a user.

    This function processes a message to check bulletins on a specified board.
    It validates the message format, retrieves the bulletins from the specified board,
    and sends a response back to the user with the list of bulletins or an error message if applicable.

    Args:
        sender_id (str): The ID of the user who sent the command.
        message (str): The message containing the command and board name.
        interface (object): The interface object used to send messages back to the user.

    Raises:
        ValueError: If there is an error in processing the command.
        KeyError: If there is an error in processing the command.
        TypeError: If there is an error in processing the command.

    Returns:
        None
    """
    try:
        # Split the message only once
        parts = message.split(",,", 1)
        if len(parts) != 2 or not parts[1].strip():
            send_message(
                "Check Bulletins Quick Command format:\nCB,,board_name",
                sender_id,
                interface,
            )
            return

        boards = {0: "General", 1: "Info", 2: "News", 3: "Urgent"}  # list of boards
        board_name = (
            parts[1].strip().capitalize()
        )  # get board name from quick command and capitalize it
        board_name = boards[
            next(key for key, value in boards.items() if value == board_name)
        ]  # search for board name in list

        bulletins = get_bulletins(board_name)
        if not bulletins:
            send_message(
                f"No bulletins available on {board_name} board.", sender_id, interface
            )
            return

        response = f"Bulletins on {board_name} board:\n"
        for i, bulletin in enumerate(bulletins):
            response += f"[{i+1:02d}] Subject: {bulletin[1]}, From: {bulletin[2]}, Date: {bulletin[3]}\n"
        response += "\nPlease reply with the number of the bulletin you want to read."
        send_message(response, sender_id, interface)

        update_user_state(
            sender_id,
            {
                "command": "CHECK_BULLETIN",
                "step": 1,
                "board_name": board_name,
                "bulletins": bulletins,
            },
        )

    except (ValueError, KeyError, TypeError) as e:
        logging.error("Error processing check bulletin command: %s", e)
        send_message("Error processing check bulletin command.", sender_id, interface)


def handle_read_bulletin_command(sender_id, message, state, interface):
    """
    Handles the command to read a bulletin.

    This function processes a command to read a specific bulletin from a list of bulletins
    stored in the state. It validates the bulletin number provided in the message, retrieves
    the bulletin content, and sends it back to the sender.

    Args:
        sender_id (str): The ID of the sender who issued the command.
        message (str): The message containing the bulletin number to read.
        state (dict): The current state containing the list of bulletins.
        interface (object): The interface used to send messages back to the sender.

    Raises:
        ValueError: If the message cannot be converted to an integer.
        Exception: For any other errors that occur during processing.

    Returns:
        None
    """
    try:
        bulletins = state.get("bulletins", [])
        message_number = int(message) - 1

        if message_number < 0 or message_number >= len(bulletins):
            send_message(
                "Invalid bulletin number. Please try again.", sender_id, interface
            )
            return

        bulletin_id = bulletins[message_number][0]
        # pylint: disable = unused-variable
        sender, date, subject, content, unique_id = get_bulletin_content(bulletin_id)
        response = f"Date: {date}\nFrom: {sender}\nSubject: {subject}\n\n{content}"
        send_message(response, sender_id, interface)

        update_user_state(sender_id, None)

    except ValueError:
        send_message(
            "Invalid input. Please enter a valid bulletin number.", sender_id, interface
        )
    except (KeyError, TypeError) as e:
        logging.error("Error processing read bulletin command: %s", e)
        send_message("Error processing read bulletin command.", sender_id, interface)


def handle_post_channel_command(sender_id, message, interface):
    """
    Handles the 'post channel' command by parsing the message and adding a new channel to the directory.

    Args:
        sender_id (str): The ID of the sender of the command.
        message (str): The message containing the command and channel details.
        interface (object): The interface object that provides access to BBS nodes and messaging functions.

    Raises:
        ValueError: If there is an issue with the values provided in the message.
        KeyError: If there is a missing key in the provided data.
        TypeError: If there is a type mismatch in the provided data.

    The expected format of the message is:
        "CHP,,{channel_name},,{channel_url}"

    If the message format is incorrect, a help message is sent back to the sender.
    If the channel is successfully added, a confirmation message is sent back to the sender.
    If an error occurs during processing, an error message is logged and sent back to the sender.
    """
    try:
        parts = message.split("|", 3)
        if len(parts) != 3:
            send_message(
                "Post Channel Quick Command format:\nCHP,,{channel_name},,{channel_url}",
                sender_id,
                interface,
            )
            return

        _, channel_name, channel_url = parts
        bbs_nodes = interface.bbs_nodes
        add_channel(channel_name, channel_url, bbs_nodes, interface)
        send_message(
            f"Channel '{channel_name}' has been added to the directory.",
            sender_id,
            interface,
        )

    except (ValueError, KeyError, TypeError) as e:
        logging.error("Error processing post channel command: %s", e)
        send_message("Error processing post channel command.", sender_id, interface)


def handle_check_channel_command(sender_id, interface):
    """
    Handles the 'check channel' command by retrieving available channels and prompting the user to select one.

    Args:
        sender_id (str): The ID of the user who sent the command.
        interface (object): The interface through which messages are sent and received.

    Raises:
        Exception: If there is an error processing the command.

    The function performs the following steps:
    1. Retrieves the list of available channels.
    2. Sends a message to the user with the list of channels.
    3. Updates the user's state to indicate that they are in the process of checking channels.
    4. Logs and sends an error message if an exception occurs.
    """
    try:
        channels = get_channels()
        if not channels:
            send_message(
                "No channels available in the directory.", sender_id, interface
            )
            return

        response = "Available Channels:\n"
        for i, channel in enumerate(channels):
            response += f"{i + 1:02d}. Name: {channel[0]}\n"
        response += "\nPlease reply with the number of the channel you want to view."
        send_message(response, sender_id, interface)

        update_user_state(
            sender_id, {"command": "CHECK_CHANNEL", "step": 1, "channels": channels}
        )

    except (ValueError, KeyError, TypeError) as e:
        logging.error("Error processing check channel command: %s", e)
        send_message("Error processing check channel command.", sender_id, interface)


def handle_read_channel_command(sender_id, message, state, interface):
    """
    Handles the command to read a channel's information based on the provided message.

    Args:
        sender_id (str): The ID of the sender who issued the command.
        message (str): The message containing the channel number to read.
        state (dict): The current state containing channel information.
        interface (object): The interface used to send messages back to the sender.

    Returns:
        None

    Raises:
        ValueError: If the message cannot be converted to an integer.
        KeyError: If the 'channels' key is not found in the state dictionary.
        TypeError: If the state is not a dictionary or channels is not a list.

    Logs:
        Logs errors for ValueError, KeyError, and TypeError during processing.
    """
    try:
        channels = state.get("channels", [])
        message_number = int(message) - 1

        if message_number < 0 or message_number >= len(channels):
            send_message(
                "Invalid channel number. Please try again.", sender_id, interface
            )
            return

        channel_name, channel_url = channels[message_number]
        response = f"Channel Name: {channel_name}\nChannel URL: {channel_url}"
        send_message(response, sender_id, interface)

        update_user_state(sender_id, None)

    except ValueError as e:
        logging.error("ValueError processing read channel command: %s", e)
        send_message(
            "Invalid input. Please enter a valid channel number.", sender_id, interface
        )
    except KeyError as e:
        logging.error("KeyError processing read channel command: %s", e)
        send_message("Error processing read channel command.", sender_id, interface)
    except TypeError as e:
        logging.error("TypeError processing read channel command: %s", e)
        send_message("Error processing read channel command.", sender_id, interface)


def handle_list_channels_command(sender_id, interface):
    """
    Handles the command to list available channels.

    This function retrieves the list of available channels and sends a message
    to the sender with the list. If no channels are available, it notifies the
    sender. It also updates the user's state to indicate that the list channels
    command is in progress.

    Args:
        sender_id (str): The ID of the sender who issued the command.
        interface (object): The interface object used to send messages.

    Raises:
        Exception: If an error occurs while processing the command.
    """
    try:
        channels = get_channels()
        if not channels:
            send_message(
                "No channels available in the directory.", sender_id, interface
            )
            return

        response = "Available Channels:\n"
        for i, channel in enumerate(channels):
            response += f"{i+1:02d}. Name: {channel[0]}\n"
        response += "\nPlease reply with the number of the channel you want to view."
        send_message(response, sender_id, interface)

        update_user_state(
            sender_id, {"command": "LIST_CHANNELS", "step": 1, "channels": channels}
        )

    except (configparser.Error, IOError) as e:
        logging.error("Error processing list channels command: %s", e)
        send_message("Error processing list channels command.", sender_id, interface)


def handle_quick_help_command(sender_id, interface):
    """
    Handles the quick help command by sending a predefined response message
    containing a list of available quick commands and their usage information.

    Args:
        sender_id (str): The ID of the sender requesting the quick help.
        interface (object): The interface through which the message will be sent.

    Returns:
        None
    """
    response = (
        "QUICK COMMANDS\nSend command below for usage info:\nSM,, - Send "
        "Mail\nCM - Check Mail\nPB,, - Post Bulletin\nCB,, - Check Bulletins\n"
    )
    send_message(response, sender_id, interface)
