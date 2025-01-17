#!/usr/bin/env python3

"""
TC²-BBS Server for Meshtastic by TheCommsChannel (TC²)
Date: 07/14/2024
Version: 0.1.6

Description:
The system allows for mail message handling, bulletin boards, and a channel
directory. It uses a configuration file for setup details and an SQLite3
database for data storage. Mail messages and bulletins are synced with
other BBS servers listed in the config.ini file.
"""

import logging
import time

from config_init import initialize_config, get_interface, init_cli_parser, merge_config
from db_operations import initialize_database
from js8call_integration import JS8CallClient
from message_processing import on_receive
from pubsub import pub  # type: ignore
from config_banner import display_banner

# General logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# JS8Call logging
js8call_logger = logging.getLogger("js8call")
js8call_logger.setLevel(logging.DEBUG)
js8call_handler = logging.StreamHandler()
js8call_handler.setLevel(logging.DEBUG)
js8call_formatter = logging.Formatter(
    "%(asctime)s - JS8Call - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
)
js8call_handler.setFormatter(js8call_formatter)
js8call_logger.addHandler(js8call_handler)


def main():
    """
    Main function to initialize and run the Meshtastic BBS server.

    This function performs the following steps:
    1. Parses command-line arguments.
    2. Initializes the system configuration.
    3. Merges command-line arguments with the system configuration.
    4. Displays a banner with the service name.
    5. Logs the BBS nodes and nodes with urgent board permissions.
    6. Initializes the interface with BBS nodes and allowed nodes.
    7. Logs the service name and interface type.
    8. Initializes the database.
    9. Subscribes to MQTT topics to receive packets.
    10. Initializes and starts the JS8Call client if configured.
    11. Runs an infinite loop to keep the server running.
    12. Handles graceful shutdown on keyboard interrupt.

    Raises:
        KeyboardInterrupt: If the server is interrupted by the user.
    """
    args = init_cli_parser()
    config_file = None
    if args.config is not None:
        config_file = args.config
    system_config = initialize_config(config_file)

    merge_config(system_config, args)

    display_banner(system_config["service_name"])

    logging.info(
        "Configured to sync with the following BBS nodes: %s",
        system_config["bbs_nodes"],
    )

    logging.info(
        "Nodes with Urgent board permissions: %s", system_config["allowed_nodes"]
    )

    interface = get_interface(system_config)
    interface.bbs_nodes = system_config["bbs_nodes"]
    interface.allowed_nodes = system_config["allowed_nodes"]

    logging.info(
        "%s is running on %s interface...",
        system_config["service_name"],
        system_config["interface_type"],
    )

    initialize_database()

    def receive_packet(packet, interface):
        on_receive(packet, interface)

    pub.subscribe(receive_packet, system_config["mqtt_topic"])

    # Initialize and start JS8Call Client if configured
    js8call_client = JS8CallClient(interface)
    js8call_client.logger = js8call_logger

    if js8call_client.db_conn:
        js8call_client.connect()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Shutting down the server...")
        interface.close()
        if js8call_client.connected:
            js8call_client.close()


if __name__ == "__main__":
    main()
