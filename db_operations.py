"""
Database utilities.
"""

import logging
import sqlite3
import threading
import uuid
from datetime import datetime
from meshtastic import BROADCAST_NUM  # type: ignore
from utils import (
    send_bulletin_to_bbs_nodes,
    send_delete_bulletin_to_bbs_nodes,
    send_delete_mail_to_bbs_nodes,
    send_mail_to_bbs_nodes,
    send_message,
    send_channel_to_bbs_nodes,
)


thread_local = threading.local()


def get_db_connection():
    """
    Retrieves a thread-local SQLite database connection.

    If a connection does not already exist for the current thread, a new one is created
    and stored in thread-local storage. This ensures that each thread has its own
    separate database connection.

    Returns:
        sqlite3.Connection: The SQLite database connection for the current thread.
    """
    if not hasattr(thread_local, "connection"):
        thread_local.connection = sqlite3.connect("bulletins.db")
    return thread_local.connection


def initialize_database():
    """
    Initializes the database by creating the necessary tables if they do not already exist.

    The following tables are created:
    - bulletins: Stores bulletin board messages with columns for id, board, sender_short_name, date, subject, content, and unique_id.
    - mail: Stores mail messages with columns for id, sender, sender_short_name, recipient, date, subject, content, and unique_id.
    - channels: Stores channel information with columns for id, name, and url.

    This function commits the changes to the database and prints a confirmation message once the schema is initialized.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS bulletins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board TEXT NOT NULL,
                    sender_short_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    unique_id TEXT NOT NULL
                )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS mail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    sender_short_name TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    date TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    unique_id TEXT NOT NULL
                );"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL
                );"""
    )
    conn.commit()
    print("Database schema initialized.")


def add_channel(name, url, bbs_nodes=None, interface=None):
    """
    Adds a new channel to the database and optionally sends the channel information to BBS nodes.

    Args:
        name (str): The name of the channel.
        url (str): The URL of the channel.
        bbs_nodes (list, optional): A list of BBS nodes to send the channel information to. Defaults to None.
        interface (object, optional): The interface used to send the channel information to BBS nodes. Defaults to None.

    Returns:
        None
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO channels (name, url) VALUES (?, ?)", (name, url))
    conn.commit()

    if bbs_nodes and interface:
        send_channel_to_bbs_nodes(name, url, bbs_nodes, interface)


def get_channels():
    """
    Retrieve all channels from the database.

    This function connects to the database, executes a query to select the
    name and URL of all channels, and returns the results.

    Returns:
        list of tuple: A list of tuples where each tuple contains the name
        and URL of a channel.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, url FROM channels")
    return c.fetchall()


def add_bulletin(
    board, sender_short_name, subject, content, bbs_nodes, interface, unique_id=None
):
    """
    Adds a bulletin to the database and optionally sends it to BBS nodes and group chat if urgent.

    Args:
        board (str): The name of the bulletin board.
        sender_short_name (str): The short name of the sender.
        subject (str): The subject of the bulletin.
        content (str): The content of the bulletin.
        bbs_nodes (list): List of BBS nodes to send the bulletin to.
        interface (object): The interface used to send the bulletin.
        unique_id (str, optional): A unique identifier for the bulletin. Defaults to None.

    Returns:
        str: The unique identifier of the added bulletin.
    """
    conn = get_db_connection()
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not unique_id:
        unique_id = str(uuid.uuid4())
    c.execute(
        "INSERT INTO bulletins (board, sender_short_name, date, subject, content, unique_id) VALUES (?, ?, ?, ?, ?, ?)",
        (board, sender_short_name, date, subject, content, unique_id),
    )
    conn.commit()
    if bbs_nodes and interface:
        send_bulletin_to_bbs_nodes(
            board, sender_short_name, subject, content, unique_id, bbs_nodes, interface
        )

    # New logic to send group chat notification for urgent bulletins
    if board.lower() == "urgent":
        notification_message = (
            f"💥NEW URGENT BULLETIN💥\nFrom: {sender_short_name}\nTitle: {subject}"
        )
        send_message(notification_message, BROADCAST_NUM, interface)

    return unique_id


def get_bulletins(board):
    """
    Retrieve bulletins from the database for a specified board.

    Args:
        board (str): The name of the board to retrieve bulletins from.

    Returns:
        list of tuple: A list of tuples where each tuple contains the following fields:
            - id (int): The unique identifier of the bulletin.
            - subject (str): The subject of the bulletin.
            - sender_short_name (str): The short name of the sender.
            - date (str): The date the bulletin was created.
            - unique_id (str): The unique identifier of the bulletin.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, subject, sender_short_name, date, unique_id FROM bulletins WHERE board = ? COLLATE NOCASE",
        (board,),
    )
    return c.fetchall()


def get_bulletin_content(bulletin_id):
    """
    Retrieve the content of a bulletin from the database based on the bulletin ID.

    Args:
        bulletin_id (int): The ID of the bulletin to retrieve.

    Returns:
        tuple: A tuple containing the sender's short name, date, subject, content, and unique ID of the bulletin.
               Returns None if no bulletin is found with the given ID.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT sender_short_name, date, subject, content, unique_id FROM bulletins WHERE id = ?",
        (bulletin_id,),
    )
    return c.fetchone()


def delete_bulletin(bulletin_id, bbs_nodes, interface):
    """
    Deletes a bulletin from the database and notifies BBS nodes.

    Args:
        bulletin_id (int): The ID of the bulletin to be deleted.
        bbs_nodes (list): A list of BBS nodes to notify about the deletion.
        interface (object): The interface used to communicate with the BBS nodes.

    Returns:
        None
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM bulletins WHERE id = ?", (bulletin_id,))
    conn.commit()
    send_delete_bulletin_to_bbs_nodes(bulletin_id, bbs_nodes, interface)


def add_mail(
    sender_id,
    sender_short_name,
    recipient_id,
    subject,
    content,
    bbs_nodes,
    interface,
    unique_id=None,
):
    """
    Adds a mail entry to the database and optionally sends it to BBS nodes.

    Args:
        sender_id (str): The ID of the sender.
        sender_short_name (str): The short name of the sender.
        recipient_id (str): The ID of the recipient.
        subject (str): The subject of the mail.
        content (str): The content of the mail.
        bbs_nodes (list): A list of BBS nodes to send the mail to.
        interface (object): The interface used to send the mail to BBS nodes.
        unique_id (str, optional): A unique identifier for the mail. If not provided, a new UUID will be generated.

    Returns:
        str: The unique identifier of the mail.
    """
    conn = get_db_connection()
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not unique_id:
        unique_id = str(uuid.uuid4())
    c.execute(
        "INSERT INTO mail (sender, sender_short_name, recipient, date, subject, content, unique_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sender_id, sender_short_name, recipient_id, date, subject, content, unique_id),
    )
    conn.commit()
    if bbs_nodes and interface:
        send_mail_to_bbs_nodes(
            sender_id,
            sender_short_name,
            recipient_id,
            subject,
            content,
            unique_id,
            bbs_nodes,
            interface,
        )
    return unique_id


def get_mail(recipient_id):
    """
    Retrieve mail for a specific recipient from the database.

    Args:
        recipient_id (int): The ID of the recipient whose mail is to be retrieved.

    Returns:
        list of tuple: A list of tuples, each containing the following fields:
            - id (int): The ID of the mail.
            - sender_short_name (str): The short name of the sender.
            - subject (str): The subject of the mail.
            - date (str): The date the mail was sent.
            - unique_id (str): The unique identifier of the mail.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, sender_short_name, subject, date, unique_id FROM mail WHERE recipient = ?",
        (recipient_id,),
    )
    return c.fetchall()


def get_mail_content(mail_id, recipient_id):
    """
    Retrieve the content of a mail for a specific recipient.

    Args:
        mail_id (int): The ID of the mail to retrieve.
        recipient_id (int): The ID of the recipient.

    Returns:
        tuple: A tuple containing the sender's short name, date, subject, content, and unique ID of the mail if found, otherwise None.
    """
    # TODO: ensure only recipient can read mail
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT sender_short_name, date, subject, content, unique_id FROM mail WHERE id = ? and recipient = ?",
        (
            mail_id,
            recipient_id,
        ),
    )
    return c.fetchone()


def delete_mail(unique_id, recipient_id, bbs_nodes, interface):
    """
    Deletes a mail entry from the database and synchronizes the deletion with BBS nodes.

    Args:
        unique_id (str): The unique identifier of the mail to be deleted.
        recipient_id (str): The identifier of the recipient of the mail.
        bbs_nodes (list): A list of BBS nodes to synchronize the deletion with.
        interface (object): The interface used to communicate with the BBS nodes.

    Raises:
        Exception: If an error occurs during the deletion process.

    Logs:
        Logs an error if no mail is found with the given unique_id.
        Logs the attempt to delete the mail.
        Logs the successful deletion and synchronization message.
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT recipient FROM mail WHERE unique_id = ?", (unique_id,))
        result = c.fetchone()
        if result is None:
            logging.error("No mail found with unique_id: %s", unique_id)
            return  # Early exit if no matching mail found
        recipient_id = result[0]
        logging.info(
            "Attempting to delete mail with unique_id: %s by %s",
            unique_id,
            recipient_id,
        )
        c.execute(
            "DELETE FROM mail WHERE unique_id = ? and recipient = ?",
            (
                unique_id,
                recipient_id,
            ),
        )
        conn.commit()
        send_delete_mail_to_bbs_nodes(unique_id, bbs_nodes, interface)
        logging.info(
            "Mail with unique_id: %s deleted and sync message sent.", unique_id
        )
    except Exception as e:
        logging.error("Error deleting mail with unique_id %s: %s", unique_id, e)
        raise


def get_sender_id_by_mail_id(mail_id):
    """
    Retrieve the sender ID associated with a given mail ID from the database.

    Args:
        mail_id (int): The ID of the mail whose sender ID is to be retrieved.

    Returns:
        int or None: The sender ID if found, otherwise None.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT sender FROM mail WHERE id = ?", (mail_id,))
    result = c.fetchone()
    if result:
        return result[0]
    return None
