#!/bin/bash

cd /app

## TODO: Make optional by adding a default
## TODO: Consider using environment variables instead of command line arguments

# requirements.txt
wget -O requirements.txt "${1}"
pip3 install --break-system-packages -r requirements.txt

# python script
wget "${2}"

# command to launch the script
echo $3
eval "$3"