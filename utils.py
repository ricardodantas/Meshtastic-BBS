"""
General utilities.
"""

import logging
import time
import os
from typing import Any, Dict, List

user_states = {}


def clear_screen():
    """
    Clears the terminal screen.

    This function clears the terminal screen by executing the appropriate
    system command based on the operating system. It uses 'cls' for Windows
    and 'clear' for Unix-based systems.

    Returns:
        None
    """
    os.system("cls" if os.name == "nt" else "clear")


def update_user_state(user_id, state):
    """
    Update the state of a user in the user_states dictionary.

    Args:
        user_id (str): The unique identifier of the user.
        state (Any): The new state to be assigned to the user.

    Returns:
        None
    """
    user_states[user_id] = state


def get_user_state(user_id) -> str | None:
    """
    Retrieve the state of a user by their user ID.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        The state of the user as a string if found, otherwise None.
    """
    return user_states.get(user_id, None)


def send_message(message, destination, interface) -> None:
    """
    Sends a message to a specified destination using the provided interface. The message is split into chunks if it exceeds the maximum payload size.

    Args:
        message (str): The message to be sent.
        destination (int): The destination ID to which the message should be sent.
        interface: The interface object used to send the message.

    Returns:
        None

    Raises:
        Exception: If there is an error while sending the message.

    Logs:
        Info: Logs the details of the message being sent.
        Error: Logs any errors encountered during the sending process.
    """
    max_payload_size = 200
    for i in range(0, len(message), max_payload_size):
        chunk = message[i : i + max_payload_size]
        try:
            message_sent = interface.sendText(
                text=chunk, destinationId=destination, wantAck=True, wantResponse=False
            )
            node_id = get_node_id_from_num(destination, interface)
            chunk = chunk.replace("\n", "\\n")
            logging.info(
                "Sending message to user '%s' (%s) with sendID %s: \"%s\"",
                get_node_short_name(node_id, interface),
                node_id,
                message_sent.id,
                chunk,
            )
        except (ConnectionError, TimeoutError, ValueError) as e:
            logging.error("REPLY SEND ERROR %s", str(e))
        time.sleep(2)


def get_node_info(interface, short_name) -> List[Dict[str, Any]]:
    """
    Retrieve information about nodes with a specific short name from the given interface.

    Args:
        interface: The interface object containing node information.
        short_name (str): The short name of the node to search for.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing node information,
                              where each dictionary has the keys 'num', 'shortName', and 'longName'.
    """
    nodes = [
        {
            "num": node_id,
            "shortName": node["user"]["shortName"],
            "longName": node["user"]["longName"],
        }
        for node_id, node in interface.nodes.items()
        if node["user"]["shortName"].lower() == short_name
    ]
    return nodes


def get_node_id_from_num(node_num, interface) -> str | None:
    """
    Retrieve the node ID corresponding to a given node number.

    Args:
        node_num (int): The number of the node to find.
        interface (object): The interface object containing node information.

    Returns:
        str | None: The node ID if found, otherwise None.
    """
    for node_id, node in interface.nodes.items():
        if node["num"] == node_num:
            return node_id
    return None


def get_node_short_name(node_id, interface) -> str | None:
    """
    Retrieve the short name of a node given its ID and interface.

    Args:
        node_id: The unique identifier of the node.
        interface: The interface object that contains node information.

    Returns:
        The short name of the node as a string if found, otherwise None.
    """
    node_info = interface.nodes.get(node_id)
    if node_info:
        return node_info["user"]["shortName"]
    return None


def send_bulletin_to_bbs_nodes(
    board, sender_short_name, subject, content, unique_id, bbs_nodes, interface
) -> None:
    """
    Sends a bulletin message to a list of BBS nodes.

    Args:
        board (str): The name of the bulletin board.
        sender_short_name (str): The short name of the sender.
        subject (str): The subject of the bulletin.
        content (str): The content of the bulletin.
        unique_id (str): A unique identifier for the bulletin.
        bbs_nodes (list): A list of node IDs to send the bulletin to.
        interface: The communication interface to use for sending the message.

    Returns:
        None
    """
    message = f"BULLETIN|{board}|{sender_short_name}|{subject}|{content}|{unique_id}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_mail_to_bbs_nodes(
    sender_id,
    sender_short_name,
    recipient_id,
    subject,
    content,
    unique_id,
    bbs_nodes,
    interface,
) -> None:
    """
    Sends an email message to BBS nodes.

    Args:
        sender_id (str): The ID of the sender.
        sender_short_name (str): The short name of the sender.
        recipient_id (str): The ID of the recipient.
        subject (str): The subject of the email.
        content (str): The content of the email.
        unique_id (str): A unique identifier for the email.
        bbs_nodes (list): A list of BBS node IDs to send the email to.
        interface: The interface used to send the message.

    Returns:
        None
    """
    message = f"MAIL|{sender_id}|{sender_short_name}|{recipient_id}|{subject}|{content}|{unique_id}"
    logging.info(
        "SERVER SYNC: Syncing new mail message %s sent from %s to other BBS systems.",
        subject,
        sender_short_name,
    )
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_delete_bulletin_to_bbs_nodes(bulletin_id, bbs_nodes, interface) -> None:
    """
    Sends a delete bulletin message to a list of BBS nodes.

    Args:
        bulletin_id (str): The ID of the bulletin to be deleted.
        bbs_nodes (list): A list of node IDs to which the delete message will be sent.
        interface (object): The interface used to send the message.

    Returns:
        None
    """
    message = f"DELETE_BULLETIN|{bulletin_id}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_delete_mail_to_bbs_nodes(unique_id, bbs_nodes, interface) -> None:
    """
    Sends a delete mail synchronization message to a list of BBS nodes.

    Args:
        unique_id (str): The unique identifier for the delete mail operation.
        bbs_nodes (list): A list of node IDs to which the delete mail message will be sent.
        interface: The communication interface used to send the message.

    Returns:
        None
    """
    message = f"DELETE_MAIL|{unique_id}"
    logging.info(
        "SERVER SYNC: Sending delete mail sync message with unique_id: %s", unique_id
    )
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_channel_to_bbs_nodes(name, url, bbs_nodes, interface) -> None:
    """
    Sends a channel message to a list of BBS nodes.

    Args:
        name (str): The name of the channel.
        url (str): The URL of the channel.
        bbs_nodes (list): A list of node IDs to send the message to.
        interface: The interface used to send the message.

    Returns:
        None
    """
    message = f"CHANNEL|{name}|{url}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def print_bold(message) -> None:
    """
    Print a message in bold text.

    Args:
        message (str): The message to be printed in bold.
    """
    print("\033[1m" + message + "\033[0m")  # Bold text


def print_separator() -> None:
    """
    Prints a bold separator line consisting of equal signs.

    This function calls the `print_bold` function to print a line of
    equal signs ("========================") in bold format.
    """
    print_bold("========================")
