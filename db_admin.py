"""
Database administration utilities.
"""

import sqlite3
import threading
from utils import clear_screen, print_bold, print_separator
from config_banner import display_banner
from config_init import initialize_config

config = initialize_config()

thread_local = threading.local()


def get_db_connection():
    """
    Get a thread-local SQLite database connection.

    This function checks if the current thread has a database connection
    stored in thread-local storage. If not, it creates a new connection
    to the 'bulletins.db' SQLite database and stores it in thread-local
    storage. This ensures that each thread has its own database connection.

    Returns:
        sqlite3.Connection: A SQLite database connection object.
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

    This function establishes a connection to the database, creates the tables, commits the changes, and then closes the connection.
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
    conn.close()


def list_bulletins():
    """
    Retrieve and list all bulletins from the database.

    This function connects to the database, retrieves all bulletins, and prints
    their details in a formatted manner. If no bulletins are found, it prints
    a message indicating that.

    Returns:
        list: A list of tuples, where each tuple contains the details of a bulletin
              (id, board, sender_short_name, date, subject, unique_id).
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, board, sender_short_name, date, subject, unique_id FROM bulletins"
    )
    bulletins = c.fetchall()
    if bulletins:
        print_bold("Bulletins:")
        for bulletin in bulletins:
            print_bold(
                f"(ID: {bulletin[0]}, Board: {bulletin[1]}, Poster: {bulletin[2]}, Subject: {bulletin[4]})"
            )
    else:
        print_bold("No bulletins found.")
    print_separator()
    return bulletins


def list_mail():
    """
    Retrieve and list all mail entries from the database.

    This function connects to the database, retrieves all mail entries, and prints
    them in a formatted manner. Each mail entry includes the following details:
    - ID
    - Sender
    - Sender's short name
    - Recipient
    - Date
    - Subject
    - Unique ID

    If no mail entries are found, it prints a message indicating that no mail was found.

    Returns:
        list: A list of tuples, where each tuple contains the details of a mail entry.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, sender, sender_short_name, recipient, date, subject, unique_id FROM mail"
    )
    mail = c.fetchall()
    if mail:
        print_bold("Mail:")
        for mail in mail:
            print_bold(
                f"(ID: {mail[0]}, Sender: {mail[2]}, Recipient: {mail[3]}, Subject: {mail[5]})"
            )
    else:
        print_bold("No mail found.")
    print_separator()
    return mail


def list_channels():
    """
    Retrieve and list all channels from the database.

    This function connects to the database, retrieves all channels, and prints
    their details in a formatted manner. If no channels are found, it prints
    a message indicating that no channels were found. It also prints a separator
    after listing the channels.

    Returns:
        list: A list of tuples, where each tuple contains the id, name, and url
              of a channel.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, url FROM channels")
    channels = c.fetchall()
    if channels:
        print_bold("Channels:")
        for channel in channels:
            print_bold(f"(ID: {channel[0]}, Name: {channel[1]}, URL: {channel[2]})")
    else:
        print_bold("No channels found.")
    print_separator()
    return channels


def delete_bulletin():
    """
    Deletes bulletins from the database based on user input.

    Prompts the user to enter the bulletin ID(s) to delete, separated by commas.
    If the user enters 'X', the deletion process is cancelled.
    Otherwise, the specified bulletins are deleted from the database.

    Returns:
        None
    """
    bulletins = list_bulletins()
    if bulletins:
        bulletin_ids = input_bold(
            "Enter the bulletin ID(s) to delete (comma-separated) or 'X' to cancel: "
        ).split(",")
        if "X" in [id.strip().upper() for id in bulletin_ids]:
            print_bold("Deletion cancelled.")
            print_separator()
            return
        conn = get_db_connection()
        c = conn.cursor()
        for bulletin_id in bulletin_ids:
            c.execute("DELETE FROM bulletins WHERE id = ?", (bulletin_id.strip(),))
        conn.commit()
        print_bold(f"Bulletin(s) with ID(s) {", ".join(bulletin_ids)} deleted.")
        print_separator()


def delete_mail():
    """
    Deletes mail entries from the database based on user input.

    Prompts the user to enter mail ID(s) to delete. If the user enters 'X', the deletion is cancelled.
    Otherwise, the specified mail entries are deleted from the database.

    Steps:
    1. Lists all mail entries.
    2. Prompts the user to enter mail ID(s) to delete or 'X' to cancel.
    3. If 'X' is entered, the deletion is cancelled.
    4. Connects to the database.
    5. Deletes the specified mail entries from the database.
    6. Commits the changes to the database.
    7. Prints a confirmation message with the deleted mail ID(s).

    Returns:
        None
    """
    mail = list_mail()
    if mail:
        mail_ids = input_bold(
            "Enter the mail ID(s) to delete (comma-separated) or 'X' to cancel: "
        ).split(",")
        if "X" in [id.strip().upper() for id in mail_ids]:
            print_bold("Deletion cancelled.")
            print_separator()
            return
        conn = get_db_connection()
        c = conn.cursor()
        for mail_id in mail_ids:
            c.execute("DELETE FROM mail WHERE id = ?", (mail_id.strip(),))
        conn.commit()
        print_bold(f"Mail with ID(s) {", ".join(mail_ids)} deleted.")
        print_separator()


def delete_channel():
    """
    Deletes one or more channels from the database based on user input.

    Prompts the user to enter the channel ID(s) to delete, separated by commas.
    If the user enters 'X', the deletion process is cancelled.
    Otherwise, the specified channels are deleted from the database.

    Returns:
        None
    """
    channels = list_channels()
    if channels:
        channel_ids = input_bold(
            "Enter the channel ID(s) to delete (comma-separated) or 'X' to cancel: "
        ).split(",")
        if "X" in [id.strip().upper() for id in channel_ids]:
            print_bold("Deletion cancelled.")
            print_separator()
            return
        conn = get_db_connection()
        c = conn.cursor()
        for channel_id in channel_ids:
            c.execute("DELETE FROM channels WHERE id = ?", (channel_id.strip(),))
        conn.commit()
        print_bold(f"Channel(s) with ID(s) {", ".join(channel_ids)} deleted.")
        print_separator()


def display_menu():
    """
    Displays a menu with options for listing and deleting bulletins, mail, and channels.

    Menu options:
    1. List Bulletins
    2. List Mail
    3. List Channels
    4. Delete Bulletins
    5. Delete Mail
    6. Delete Channels
    7. Exit
    """
    print("Menu:")
    print("1. List Bulletins")
    print("2. List Mail")
    print("3. List Channels")
    print("4. Delete Bulletins")
    print("5. Delete Mail")
    print("6. Delete Channels")
    print("7. Exit")


def input_bold(prompt):
    """
    Displays a prompt in bold text, waits for user input, and then resets the text formatting.

    Args:
        prompt (str): The message to display to the user.

    Returns:
        str: The user's input.
    """
    print("\033[1m")  # ANSI escape code for bold text
    response = input(prompt)
    print("\033[0m")  # ANSI escape code to reset text
    return response


def main():
    """
    Main function to run the database administration tool.

    This function displays a banner, initializes the database, and enters a loop
    to display a menu and handle user choices. The available choices allow the user
    to list bulletins, mail, and channels, as well as delete bulletins, mail, and channels.
    The loop continues until the user chooses to exit.

    Choices:
        1: List bulletins
        2: List mail
        3: List channels
        4: Delete a bulletin
        5: Delete mail
        6: Delete a channel
        7: Exit the tool

    Prompts the user for input and handles invalid choices by displaying an error message.
    """
    display_banner(config["service_name"])
    initialize_database()
    while True:
        display_menu()
        choice = input_bold("Enter your choice: ")
        clear_screen()
        if choice == "1":
            list_bulletins()
        elif choice == "2":
            list_mail()
        elif choice == "3":
            list_channels()
        elif choice == "4":
            delete_bulletin()
        elif choice == "5":
            delete_mail()
        elif choice == "6":
            delete_channel()
        elif choice == "7":
            break
        else:
            print_bold("Invalid choice. Please try again.")
            print_separator()


if __name__ == "__main__":
    main()
