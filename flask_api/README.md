# LongRun Flask API

A Flask API with login and registration functionality using MongoDB for authentication, served with Waitress. The API also includes tools for monitoring NSE (National Stock Exchange) announcements and processing documents with AI.

## Features

- User registration and login API endpoints
- MongoDB integration for user data storage
- Password hashing for security
- CORS support for frontend integration
- Served using Waitress for production-ready deployment
- NSE announcement monitoring with multiple methods
- Robust file downloading with fallback mechanisms
- Document processing workflow with AI integration

## Setup Instructions

### 1. Install Dependencies

```bash
cd flask_api
pip install -r requirements.txt
```

### 2. Configure MongoDB

You can configure the MongoDB connection in one of two ways:

#### Option 1: Using a .env file (recommended)

Copy the example environment file and update it with your MongoDB details:

```bash
cp .env.example .env
```

Then edit the `.env` file with your MongoDB connection details:

```
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USERNAME=your_username
MONGO_PASSWORD=your_password
MONGO_DB=longrun
```

#### Option 2: Using environment variables

Set the following environment variables:

```bash
export MONGO_HOST=localhost
export MONGO_PORT=27017
export MONGO_USERNAME=your_username
export MONGO_PASSWORD=your_password
export MONGO_DB=longrun
```

### 3. Run the Application

You can start the application using the provided start script:

```bash
./start.sh
```

Or manually:

```bash
python app.py
```

The API will be available at `http://localhost:8888`.

### 4. Testing the Application

#### Test MongoDB Connection

To test your MongoDB connection:

```bash
python test_mongo_connection.py
```

#### Test API Endpoints

To test all API endpoints (this will start the server, run tests, and then stop the server):

```bash
./run_tests.sh
```

Or to test against an already running server:

```bash
python test_api.py
```

## API Endpoints

### Health Check

```
GET /api/health
```

Returns the health status of the API.

### Register User

```
POST /api/register
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

Registers a new user in the system.

### Login User

```
POST /api/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

Authenticates a user and returns user information.

## NSE Monitoring Tools

The project includes several tools for monitoring NSE (National Stock Exchange) announcements:

### NSE Downloader (`nse_downloader.py`)

A robust downloader for NSE files with multiple download methods and fallbacks.

```bash
python nse_downloader.py
```

Features:

- Multiple download methods (requests, curl, wget, threaded, browser automation)
- Smart fallback mechanism
- Robust error handling and retry logic

### NSE Monitor (`nse_monitor.py`)

A monitor for NSE announcements with incremental checking and caching.

```bash
python nse_monitor.py
```

Features:

- Incremental monitoring with caching
- Multiple methods for processing RSS feeds
- Smart PDF download with fallback mechanisms
- Time-based filtering

### Simple NSE Monitor (`simple_nse_monitor.py`)

A simpler version of the NSE monitor that uses curl to bypass Python request blocking.

```bash
python simple_nse_monitor.py
```

Features:

- Curl-based RSS fetching
- Manual XML parsing
- PDF downloading with curl

### Stock Webhook (`stock_webhook.py`)

A complete NSE webhook monitor that combines curl-based RSS fetching with smart PDF/XML downloads.

```bash
python stock_webhook.py
```

Features:

- Complete monitoring solution
- Smart file downloading for both PDF and XML files
- Company search functionality
- Download statistics

## Document Processing with AI

The project includes a document processing workflow that integrates with an AI service. This functionality is implemented in `upload_to_ai.py`.

### Usage

```bash
python upload_to_ai.py <filepath> [query_text]
```

Where:

- `filepath`: Path to the document to be processed
- `query_text`: (Optional) The query to run against the document (defaults to "Summarize this document")

### Workflow

1. The document is uploaded to the AI service, which returns a document ID
2. The script checks the processing status until it's successful
3. Once processing is complete, the script queries the document with the provided query text
4. The query result is displayed
5. The document is deleted from the AI service

### Batch Processing

The script also supports batch processing of multiple documents in the `nse_downloads` directory. This functionality can be accessed by calling the `batch_process()` function.

## Integration with Frontend

The API includes CORS support, allowing it to be easily integrated with a frontend application. The frontend can make requests to the API endpoints to register users, authenticate them, and access protected resources.
