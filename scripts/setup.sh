#!/bin/bash

# Clone the repository
git clone https://github.com/ricardodantas/meshtastic-bbs.git

cd meshtastic-bbs || exit

# Check if poetry is already installed
if command -v poetry >/dev/null 2>&1; then
    echo "poetry is already installed."
else
    # Linux, macOS, Windows (WSL)
    curl -sSL https://install.python-poetry.org | python3 -
    exec "$SHELL"
fi

# Check if example_config.ini is available
if [ ! -f config.ini ]; then
    if [ -f example_config.ini ]; then
        echo "Renaming example_config.ini to config.ini..."
        mv example_config.ini config.ini
    else
        echo "example_config.ini not found in the current directory."
        exit 1
    fi
else
    echo "config.ini already exists."
fi

# Detect the current user
CURRENT_USER=$(whoami)
echo "Current user: $CURRENT_USER"

# Update meshtastic-bbs.service with the current user
SERVICE_FILE="meshtastic-bbs.service"
if [ -f "$SERVICE_FILE" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/User=pi/User=$CURRENT_USER/g" $SERVICE_FILE
        sed -i '' "s|/home/pi|/home/$CURRENT_USER|g" $SERVICE_FILE
    else
        sed -i "s/User=pi/User=$CURRENT_USER/g" $SERVICE_FILE
        sed -i "s|/home/pi|/home/$CURRENT_USER|g" $SERVICE_FILE
    fi
    echo "Updated $SERVICE_FILE with the current user."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v poetry >/dev/null 2>&1; then
            echo "Enable service using systemctl..."
            sudo cp meshtastic-bbs.service /etc/systemd/system/
            sudo systemctl enable meshtastic-bbs.service

            echo "Starting service..."
            sudo systemctl start meshtastic-bbs.service
        fi
    else
        echo "Skipping the service  file setup on Mac OS"
    fi
fi

echo "Setup completed successfully!"
