#!/bin/sh
if [ ! -f "/config/config.ini" ]; then
    cp "/meshtastic-bbs/example_config.ini" "/config/config.ini"
fi
if [ ! -f "/config/fortunes.txt" ]; then
    cp "/meshtastic-bbs/fortunes.txt" "/config/fortunes.txt"
fi
