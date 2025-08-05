# LongRun Flask API

A Flask API with login and registration functionality using MongoDB for authentication, served with Waitress.

## Features

- User registration and login API endpoints
- MongoDB integration for user data storage
- Password hashing for security
- CORS support for frontend integration
- Served using Waitress for production-ready deployment

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

## Integration with Frontend

The API includes CORS support, allowing it to be easily integrated with a frontend application. The frontend can make requests to the API endpoints to register users, authenticate them, and access protected resources.
