#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting LongRun Flask API...${NC}"

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}No virtual environment found. Consider creating one:${NC}"
    echo -e "python -m venv venv"
    echo -e "source venv/bin/activate"
fi

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -r requirements.txt

# Test MongoDB connection
echo -e "${GREEN}Testing MongoDB connection...${NC}"
python test_mongo_connection.py
if [ $? -ne 0 ]; then
    echo -e "${RED}MongoDB connection failed. Please check your configuration.${NC}"
    echo -e "${YELLOW}You can update MongoDB settings in config.py or set environment variables.${NC}"
    exit 1
fi

# Start the application
echo -e "${GREEN}Starting Flask application with Waitress on port 8888...${NC}"
python app.py

# This line will only execute if the application crashes or is stopped
echo -e "${RED}Application stopped.${NC}"
