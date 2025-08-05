#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running LongRun Flask API Tests...${NC}"

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -r requirements.txt

# Test MongoDB connection first
echo -e "${GREEN}Testing MongoDB connection...${NC}"
python test_mongo_connection.py
if [ $? -ne 0 ]; then
    echo -e "${RED}MongoDB connection failed. Please check your configuration.${NC}"
    echo -e "${YELLOW}You can update MongoDB settings in config.py or set environment variables.${NC}"
    exit 1
fi

# Start the Flask application in the background
echo -e "${GREEN}Starting Flask application with Waitress on port 8888...${NC}"
python app.py > app.log 2>&1 &
APP_PID=$!

# Wait for the application to start
echo -e "${YELLOW}Waiting for the application to start...${NC}"
sleep 3

# Run the API tests
echo -e "${GREEN}Running API tests...${NC}"
python test_api.py
TEST_RESULT=$?

# Stop the Flask application
echo -e "${YELLOW}Stopping Flask application...${NC}"
kill $APP_PID

# Check if tests were successful
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed. Check the output above for details.${NC}"
fi

# Show the application logs
echo -e "${YELLOW}Application logs:${NC}"
cat app.log

# Clean up
rm -f app.log

exit $TEST_RESULT
