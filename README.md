# LongRun Project

A web application with a Flask API backend and Next.js frontend.

## Project Structure

- **flask_api/**: Backend API with user authentication using Flask, MongoDB, and Waitress
- **frontend/longrun/**: Frontend application using Next.js (to be implemented)

## Backend (Flask API)

The backend provides a RESTful API with user authentication endpoints:

- User registration
- User login
- Health check

### Features

- MongoDB integration for user data storage
- Password hashing for security
- CORS support for frontend integration
- Served using Waitress on port 8888

### Setup and Usage

See the [Flask API README](flask_api/README.md) for detailed setup and usage instructions.

## Frontend (Next.js)

The frontend will be implemented using Next.js to provide a user interface for the application.

## Getting Started

1. Set up the Flask API backend:

   ```bash
   cd flask_api
   pip install -r requirements.txt
   # Configure MongoDB connection in .env file
   ./start.sh
   ```

2. Set up the Next.js frontend (to be implemented)

## Development

### Git Workflow

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd longrun
   ```

2. Make changes to the codebase

3. Commit your changes:

   ```bash
   git add .
   git commit -m "Your commit message"
   ```

4. Push to the remote repository:
   ```bash
   git push origin main
   ```

## License

[MIT License](LICENSE)
