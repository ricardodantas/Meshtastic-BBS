#!/bin/bash

# Clone the repository
git clone https://github.com/ricardodantas/meshtastic-bbs.git

cd meshtastic-bbs || exit

# Check if pyenv is already installed
if command -v pyenv >/dev/null 2>&1; then
    echo "pyenv is already installed."
else
    # Determine the operating system and install pyenv accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://pyenv.run | bash

        echo "Detected Linux OS. Installing pyenv..."
        echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
        echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
        echo 'eval "$(pyenv init - bash)"' >> ~/.bashrc

        echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.profile
        echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.profile
        echo 'eval "$(pyenv init - bash)"' >> ~/.profile

        exec "$SHELL"

        pyenv install 3.12
        pyenv local 3.12
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Detected macOS. Installing pyenv..."
        brew update
        brew install pyenv
        pyenv install 3.12
        pyenv local 3.12
    else
        echo "Unsupported OS: $OSTYPE"
        exit 1
    fi
fi


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
