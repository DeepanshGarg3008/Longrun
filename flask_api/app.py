from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os
from waitress import serve
import json
from bson import ObjectId

# Custom JSON encoder to handle MongoDB ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(JSONEncoder, self).default(obj)

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.json_encoder = JSONEncoder

# Load configuration
app.config.from_pyfile('config.py')

# MongoDB connection
def get_db():
    client = MongoClient(
        host=app.config['MONGO_HOST'],
        port=app.config['MONGO_PORT'],
        username=app.config['MONGO_USERNAME'],
        password=app.config['MONGO_PASSWORD']
    )
    db = client[app.config['MONGO_DB']]
    return db

# API Routes
@app.route('/api/register', methods=['POST'])
def register():
    db = get_db()
    users = db.users
    
    # Get user data from request
    user_data = request.get_json()
    username = user_data.get('username')
    password = user_data.get('password')
    
    # Validate input
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    # Check if username already exists
    if users.find_one({"username": username}):
        return jsonify({"error": "Username already exists"}), 400
    
    # Hash password
    hashed_password = generate_password_hash(password)
    
    # Insert user into database
    user_id = users.insert_one({
        "username": username,
        "password": hashed_password
    }).inserted_id
    
    return jsonify({"message": "User registered successfully", "user_id": str(user_id)}), 201

@app.route('/api/login', methods=['POST'])
def login():
    db = get_db()
    users = db.users
    
    # Get user data from request
    user_data = request.get_json()
    username = user_data.get('username')
    password = user_data.get('password')
    
    # Validate input
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    # Find user in database
    user = users.find_one({"username": username})
    
    # Check if user exists and password is correct
    if user and check_password_hash(user['password'], password):
        return jsonify({
            "message": "Login successful",
            "user_id": str(user['_id']),
            "username": user['username']
        }), 200
    
    return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    print(f"Starting server on port {app.config['PORT']}")
    serve(app, host='0.0.0.0', port=app.config['PORT'])
