#!/bin/bash

# Clone the repository
git clone git@github.com:ricardodantas/Meshtastic-BBS.git

# Check if pyenv is already installed
if command -v pyenv >/dev/null 2>&1; then
    echo "pyenv is already installed."
else
    # Determine the operating system and install pyenv accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Detected Linux OS. Installing pyenv..."
        curl -fsSL https://pyenv.run | bash
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Detected macOS. Installing pyenv..."
        brew update
        brew install pyenv
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

echo "Setup completed successfully!"
