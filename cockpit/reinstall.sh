#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "${SCRIPT_DIR}/venv/bin/activate" ]; then
        echo -e "${YELLOW}Activating venv (local)...${RESET}"
        source "${SCRIPT_DIR}/venv/bin/activate"
    elif [ -f "${SCRIPT_DIR}/.venv/bin/activate" ]; then
        echo -e "${YELLOW}Activating .venv (local)...${RESET}"
        source "${SCRIPT_DIR}/.venv/bin/activate"
    elif [ -f "${SCRIPT_DIR}/../venv/bin/activate" ]; then
        echo -e "${YELLOW}Activating venv (parent)...${RESET}"
        source "${SCRIPT_DIR}/../venv/bin/activate"
    elif [ -f "${SCRIPT_DIR}/../.venv/bin/activate" ]; then
        echo -e "${YELLOW}Activating .venv (parent)...${RESET}"
        source "${SCRIPT_DIR}/../.venv/bin/activate"
    else
        echo -e "${RED}Warning: No virtual environment found (venv or .venv).${RESET}"
        echo -e "${YELLOW}Attempting to use system pip...${RESET}"
    fi
fi

if ! command -v pip &> /dev/null; then
    echo -e "${RED}Error: pip command not found.${RESET}"
    echo -e "Please ensure python and pip are installed and you are in a virtual environment."
    exit 1
fi

echo -e "${YELLOW}Cleaning up previous installation...${RESET}"

pip uninstall -y cockpit

echo -e "${YELLOW}Removing build artifacts...${RESET}"
rm -rf "${SCRIPT_DIR}/build"
rm -rf "${SCRIPT_DIR}/dist"
rm -rf "${SCRIPT_DIR}/src/cockpit.egg-info"
rm -rf "${SCRIPT_DIR}/src/cockpit/__pycache__"

echo -e "${YELLOW}Reinstalling in editable mode...${RESET}"
pip install -e "${SCRIPT_DIR}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully reinstalled cockpit!${RESET}"
else
    echo -e "${RED}✗ Installation failed.${RESET}"
    exit 1
fi
