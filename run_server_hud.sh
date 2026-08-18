#!/usr/bin/env bash
# ==============================================================================
# U-SIE Sovereign Platform HUD Startup Script
# Co-authored by Fred Laurenzo (Chief Architect)
# Description: Automated setup and launcher for the U-SIE Streamlit HUD.
# ==============================================================================
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${GREEN}   U-SIE Sovereign Platform HUD Startup Utility${NC}"
echo -e "${BLUE}======================================================================${NC}"



# Step 1: Check Python 3 environment
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[Error] Python 3 is required but was not found on this system.${NC}"
    echo "Please install Python 3.9+ and try again."
    exit 1
fi

# Step 2: Establish isolated virtual environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[Info] Creating a local sandboxed Python virtual environment: $VENV_DIR...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# Activate Virtual Environment
echo -e "${YELLOW}[Info] Activating local virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Step 3: Upgrade pip and install core system requirements
echo -e "${YELLOW}[Info] Upgrading pip and installing required visualization/UI libraries...${NC}"
pip install --upgrade pip
pip install streamlit plotly pandas requests pypdf

# Step 4: Verify HUD python script is nearby (Defaulting to v6.1)
HUD_SCRIPT="USIE_SovereignPlatform_HUD_v6.1.py"
if [ ! -f "$HUD_SCRIPT" ]; then
    echo -e "${YELLOW}[Warning] Streamlit launcher script '$HUD_SCRIPT' was not found in current directory.${NC}"
    echo "Searching filesystem..."
    FOUND_HUD=$(find . -maxdepth 3 -name "USIE_SovereignPlatform_HUD_v6.1.py" -print -quit 2>/dev/null || true)
    if [ -n "$FOUND_HUD" ]; then
        HUD_SCRIPT="$FOUND_HUD"
        echo -e "${GREEN}[Info] Found launcher script at: $HUD_SCRIPT${NC}"
    else
        echo -e "${RED}[Error] Could not locate 'USIE_SovereignPlatform_HUD_v6.1.py'.${NC}"
        echo "Please download the v6.1 file from your Studio panel and place it in this folder."
        exit 1
    fi
fi

# Step 5: Launch Streamlit Dashboard
echo -e "${GREEN}[Success] Starting the U-SIE Sovereign Platform HUD on your server...${NC}"
echo -e "${BLUE}----------------------------------------------------------------------${NC}"
streamlit run "$HUD_SCRIPT" --server.enableCORS=false --server.enableXsrfProtection=false
