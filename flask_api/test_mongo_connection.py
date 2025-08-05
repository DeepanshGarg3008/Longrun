from pymongo import MongoClient
import sys
import os
from config import MONGO_HOST, MONGO_PORT, MONGO_USERNAME, MONGO_PASSWORD, MONGO_DB

def test_connection():
    """Test the MongoDB connection using the configured settings."""
    print(f"Testing MongoDB connection to {MONGO_HOST}:{MONGO_PORT}...")
    
    try:
        # Create a MongoDB client
        client = MongoClient(
            host=MONGO_HOST,
            port=MONGO_PORT,
            username=MONGO_USERNAME if MONGO_USERNAME else None,
            password=MONGO_PASSWORD if MONGO_PASSWORD else None,
            serverSelectionTimeoutMS=5000  # 5 second timeout
        )
        
        # Force a connection to verify
        client.server_info()
        
        # Try to access the database
        db = client[MONGO_DB]
        collections = db.list_collection_names()
        
        print("✅ Connection successful!")
        print(f"Available collections in '{MONGO_DB}' database: {collections}")
        
        # Check if users collection exists, create it if not
        if 'users' not in collections:
            print("Creating 'users' collection...")
            db.create_collection('users')
            print("✅ 'users' collection created successfully.")
        else:
            print("✅ 'users' collection already exists.")
            user_count = db.users.count_documents({})
            print(f"Number of users in database: {user_count}")
        
        return True
    
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nPlease check your MongoDB connection settings in config.py or environment variables.")
        print("Make sure MongoDB is running and accessible.")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
