import os
import time
import requests
import csv
import sys

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "nse_downloads")
UPLOADED_LOG = os.path.join(os.path.dirname(__file__), "uploaded_files.csv")
BASE_URL = "http://18.207.201.219:1234"  # Base URL for all API endpoints
UPLOAD_URL = f"{BASE_URL}/upload"
STATUS_URL = f"{BASE_URL}/status"  # Will append /{doc_id}
QUERY_URL = f"{BASE_URL}/query"  # Will use query parameters
DELETE_URL = f"{BASE_URL}/delete"  # Will append /{doc_id}
SLEEP_INTERVAL = 5  # seconds to wait between status checks

def get_uploaded_files():
    uploaded = {}
    if not os.path.exists(UPLOADED_LOG):
        return uploaded
    with open(UPLOADED_LOG, "r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) == 2:
                filename, doc_id = row
                uploaded[filename] = doc_id
    return uploaded

def log_uploaded_file(filename, doc_id):
    with open(UPLOADED_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([filename, doc_id])

def upload_file(filepath):
    """Upload a file and return the document ID"""
    filename = os.path.basename(filepath)
    print(f"Uploading {filename}...")
    
    with open(filepath, "rb") as f:
        files = {"file": (filename, f)}
        # Add headers or authentication as needed
        response = requests.post(UPLOAD_URL, files=files)
    
    if response.status_code == 200:
        try:
            data = response.json()
            doc_id = data.get("doc_id")
            if doc_id:
                print(f"Uploaded {filename} successfully. doc_id: {doc_id}")
                return doc_id
        except Exception as e:
            print(f"Error parsing response for {filename}: {e}")
    else:
        print(f"Failed to upload {filename}. Status code: {response.status_code}")
    
    return None

def check_status(doc_id):
    """Check the processing status of a document"""
    print(f"Checking status for doc_id: {doc_id}...")
    
    url = f"{STATUS_URL}/{doc_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        try:
            data = response.json()
            status = data.get("status")
            print(f"Status: {status}")
            return status == "success"
        except Exception as e:
            print(f"Error parsing status response: {e}")
    else:
        print(f"Failed to check status. Status code: {response.status_code}")
    
    return False

def query_document(doc_id, query_text):
    """Query the document with the given text"""
    print(f"Querying document {doc_id} with: '{query_text}'")
    
    params = {
        "query": query_text,
        "doc_id": doc_id
    }
    
    response = requests.get(QUERY_URL, params=params)
    
    if response.status_code == 200:
        try:
            data = response.json()
            return data
        except Exception as e:
            print(f"Error parsing query response: {e}")
    else:
        print(f"Failed to query document. Status code: {response.status_code}")
    
    return None

def delete_document(doc_id):
    """Delete the document from the server"""
    print(f"Deleting document {doc_id}...")
    
    url = f"{DELETE_URL}/{doc_id}"
    response = requests.delete(url)
    
    if response.status_code == 200:
        print(f"Document {doc_id} deleted successfully.")
        return True
    else:
        print(f"Failed to delete document. Status code: {response.status_code}")
        return False

def process_document(filepath, query_text=None):
    """Process a document through the complete workflow"""
    # Step 1: Upload the document
    doc_id = upload_file(filepath)
    if not doc_id:
        print("Upload failed. Aborting process.")
        return False
    
    # Step 2: Check status until success or timeout
    max_attempts = 12  # 1 minute with 5-second intervals
    attempt = 0
    success = False
    
    while attempt < max_attempts:
        success = check_status(doc_id)
        if success:
            break
        
        print(f"Processing not complete. Waiting {SLEEP_INTERVAL} seconds...")
        time.sleep(SLEEP_INTERVAL)
        attempt += 1
    
    if not success:
        print("Document processing timed out or failed.")
        return False
    
    # Step 3: Query the document if query text is provided
    if query_text:
        result = query_document(doc_id, query_text)
        if result:
            print("\nQuery Result:")
            print(result)
        else:
            print("Query failed.")
    
    # Step 4: Delete the document
    delete_document(doc_id)
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_to_ai.py <filepath> [query_text]")
        return
    
    filepath = sys.argv[1]
    query_text = sys.argv[2] if len(sys.argv) > 2 else "Summarize this document"
    
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    
    process_document(filepath, query_text)

def batch_process():
    """Process all new files in the downloads directory"""
    print("Starting batch processing...")
    uploaded_files = get_uploaded_files()
    all_files = [
        f for f in os.listdir(DOWNLOADS_DIR)
        if os.path.isfile(os.path.join(DOWNLOADS_DIR, f))
    ]
    new_files = [f for f in all_files if f not in uploaded_files]

    for filename in new_files:
        filepath = os.path.join(DOWNLOADS_DIR, filename)
        try:
            doc_id = upload_file(filepath)
            if doc_id:
                log_uploaded_file(filename, doc_id)
                
                # Process the document
                if check_status(doc_id):
                    # Use a default query
                    result = query_document(doc_id, "Summarize this document")
                    if result:
                        print(f"Query result for {filename}:")
                        print(result)
                    
                    # Delete the document
                    delete_document(doc_id)
            else:
                print(f"Failed to upload {filename} or missing doc_id.")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    main()
