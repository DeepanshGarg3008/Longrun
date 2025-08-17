import requests
import time
import os
from urllib.parse import urlparse
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class NSEDownloader:
    def __init__(self):
        self.session = requests.Session()
        # Add headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def method1_requests_with_retry(self, url, filename, max_retries=3, chunk_size=8192):
        """Method 1: Robust requests with retry logic and chunked download"""
        print(f"📥 Method 1: Downloading {filename} with retry...")
        
        for attempt in range(max_retries):
            try:
                # Use longer timeout and stream download
                response = self.session.get(
                    url, 
                    stream=True, 
                    timeout=(30, 120),  # (connection timeout, read timeout)
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # Download in chunks
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                
                print(f"✅ Downloaded: {filename} ({os.path.getsize(filename)} bytes)")
                return True
                
            except requests.exceptions.Timeout:
                print(f"⏰ Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Request error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        print(f"❌ Failed to download {filename} after {max_retries} attempts")
        return False
    
    def method2_curl_subprocess(self, url, filename):
        """Method 2: Use curl subprocess (more reliable for large files)"""
        print(f"📥 Method 2: Downloading {filename} with curl...")
        
        try:
            # curl command with options for reliability
            curl_cmd = [
                'curl',
                '-L',  # Follow redirects
                '-o', filename,  # Output file
                '--connect-timeout', '30',  # Connection timeout
                '--max-time', '300',  # Max total time (5 minutes)
                '--retry', '3',  # Retry attempts
                '--retry-delay', '2',  # Delay between retries
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                url
            ]
            
            # Run curl
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=360)
            
            if result.returncode == 0 and os.path.exists(filename):
                print(f"✅ Downloaded: {filename} ({os.path.getsize(filename)} bytes)")
                return True
            else:
                print(f"❌ Curl failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Curl command timed out")
            return False
        except FileNotFoundError:
            print("❌ Curl not found. Install curl or use other methods.")
            return False
        except Exception as e:
            print(f"❌ Curl error: {e}")
            return False
    
    def method3_wget_subprocess(self, url, filename):
        """Method 3: Use wget subprocess"""
        print(f"📥 Method 3: Downloading {filename} with wget...")
        
        try:
            wget_cmd = [
                'wget',
                '-O', filename,  # Output file
                '--timeout=30',  # Timeout
                '--tries=3',  # Retry attempts
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                url
            ]
            
            result = subprocess.run(wget_cmd, capture_output=True, text=True, timeout=360)
            
            if result.returncode == 0 and os.path.exists(filename):
                print(f"✅ Downloaded: {filename} ({os.path.getsize(filename)} bytes)")
                return True
            else:
                print(f"❌ Wget failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Wget command timed out")
            return False
        except FileNotFoundError:
            print("❌ Wget not found. Install wget or use other methods.")
            return False
        except Exception as e:
            print(f"❌ Wget error: {e}")
            return False
    
    def method4_threaded_download(self, url, filename, num_threads=4):
        """Method 4: Multi-threaded download (for large files)"""
        print(f"📥 Method 4: Multi-threaded download of {filename}...")
        
        try:
            # Get file size first
            head_response = self.session.head(url, timeout=30)
            if 'content-length' not in head_response.headers:
                print("❌ Cannot determine file size, falling back to single-threaded")
                return self.method1_requests_with_retry(url, filename)
            
            file_size = int(head_response.headers['content-length'])
            print(f"📊 File size: {file_size} bytes")
            
            # Calculate chunk size per thread
            chunk_size = file_size // num_threads
            
            def download_chunk(start, end, chunk_filename):
                headers = {'Range': f'bytes={start}-{end}'}
                response = self.session.get(url, headers=headers, timeout=120)
                with open(chunk_filename, 'wb') as f:
                    f.write(response.content)
                return chunk_filename
            
            # Download chunks in parallel
            chunk_files = []
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = []
                
                for i in range(num_threads):
                    start = i * chunk_size
                    end = start + chunk_size - 1 if i < num_threads - 1 else file_size - 1
                    chunk_filename = f"{filename}.part{i}"
                    chunk_files.append(chunk_filename)
                    
                    future = executor.submit(download_chunk, start, end, chunk_filename)
                    futures.append(future)
                
                # Wait for all chunks to complete
                for future in as_completed(futures):
                    future.result()
            
            # Combine chunks
            with open(filename, 'wb') as outfile:
                for chunk_file in chunk_files:
                    with open(chunk_file, 'rb') as infile:
                        outfile.write(infile.read())
                    os.remove(chunk_file)  # Clean up
            
            print(f"✅ Downloaded: {filename} ({os.path.getsize(filename)} bytes)")
            return True
            
        except Exception as e:
            print(f"❌ Multi-threaded download failed: {e}")
            return False
    
    def method5_browser_automation(self, url, filename):
        """Method 5: Use selenium to download via browser (requires selenium)"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            import time
            
            print(f"📥 Method 5: Browser automation download of {filename}...")
            
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in background
            chrome_options.add_experimental_option("prefs", {
                "download.default_directory": os.path.abspath(os.path.dirname(filename)),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            })
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            time.sleep(10)  # Wait for download
            driver.quit()
            
            if os.path.exists(filename):
                print(f"✅ Downloaded: {filename} ({os.path.getsize(filename)} bytes)")
                return True
            else:
                print("❌ Browser download failed")
                return False
                
        except ImportError:
            print("❌ Selenium not installed. Run: pip install selenium")
            return False
        except Exception as e:
            print(f"❌ Browser automation failed: {e}")
            return False
    
    def smart_download(self, url, filename, methods=None):
        """Smart download: Try multiple methods until one succeeds"""
        if methods is None:
            methods = ['requests', 'curl', 'wget', 'threaded']
        
        print(f"🤖 Smart download: Trying multiple methods for {filename}")
        
        for method in methods:
            print(f"\n🔄 Trying method: {method}")
            
            success = False
            if method == 'requests':
                success = self.method1_requests_with_retry(url, filename)
            elif method == 'curl':
                success = self.method2_curl_subprocess(url, filename)
            elif method == 'wget':
                success = self.method3_wget_subprocess(url, filename)
            elif method == 'threaded':
                success = self.method4_threaded_download(url, filename)
            elif method == 'browser':
                success = self.method5_browser_automation(url, filename)
            
            if success:
                return True
            else:
                # Clean up partial file
                if os.path.exists(filename):
                    os.remove(filename)
        
        print(f"❌ All download methods failed for {filename}")
        return False

# Usage examples
def main():
    downloader = NSEDownloader()
    
    # Example URL (replace with actual NSE PDF URL)
    test_url = "https://nsearchives.nseindia.com/corporate/ARISINFRA_08082025143129_ArisInfraLetterSub.pdf"
    filename = "test_download.pdf"
    
    print("Testing different download methods:\n")
    
    # Method 1: Try single method
    # downloader.method1_requests_with_retry(test_url, filename)
    
    # Method 2: Smart download (tries multiple methods)
    downloader.smart_download(test_url, filename)
    
    # Method 3: Try specific method
    # downloader.method2_curl_subprocess(test_url, filename)

if __name__ == "__main__":
    main()

# Integration with your existing NSE monitor
class EnhancedNSEMonitor:
    def __init__(self, check_interval=300):
        self.rss_url = "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
        self.check_interval = check_interval
        self.seen_items = set()
        self.downloader = NSEDownloader()
    
    def download_pdf_robust(self, pdf_url, filename):
        """Enhanced PDF download with multiple fallback methods"""
        print(f"📥 Downloading: {filename}")
        
        # Try smart download with multiple methods
        success = self.downloader.smart_download(
            pdf_url, 
            filename, 
            methods=['requests', 'curl', 'wget']  # Try these in order
        )
        
        if success:
            print(f"✅ Successfully downloaded: {filename}")
        else:
            print(f"❌ Failed to download: {filename}")
            # Log the failed download for manual retry later
            with open("failed_downloads.log", "a") as f:
                f.write(f"{pdf_url},{filename}\n")
        
        return success