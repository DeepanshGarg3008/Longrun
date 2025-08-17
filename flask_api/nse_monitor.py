import feedparser
import requests
import time
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import json
import os
from io import StringIO

class IncrementalNSEMonitor:
    def __init__(self, check_interval=300, max_items_to_process=20, download_pdfs=False):
        self.rss_url = "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
        self.check_interval = check_interval
        self.max_items_to_process = max_items_to_process  # Only process latest N items
        self.download_pdfs = download_pdfs  # Whether to download PDFs
        self.last_check_time = None
        self.seen_items = set()
        self.cache_file = "nse_incremental_cache.json"
        self.load_cache()
    
    def load_cache(self):
        """Load cache with last check time"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self.seen_items = set(cache_data.get('seen_items', []))
                    
                    # Load last check time
                    if cache_data.get('last_check_time'):
                        self.last_check_time = datetime.fromisoformat(cache_data['last_check_time'])
                    
                print(f"📂 Loaded cache: {len(self.seen_items)} items, last check: {self.last_check_time}")
        except Exception as e:
            print(f"❌ Error loading cache: {e}")
    
    def save_cache(self):
        """Save cache with current time"""
        try:
            cache_data = {
                'seen_items': list(self.seen_items),
                'last_check_time': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving cache: {e}")
    
    def method1_process_only_latest_items(self):
        """Method 1: Download full RSS but only process first N items"""
        print(f"📡 Method 1: Processing only latest {self.max_items_to_process} items...")
        
        try:
            response = requests.get(self.rss_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Parse RSS but limit processing
            feed = feedparser.parse(response.content)
            
            # Get file size info
            content_length = response.headers.get('content-length', 'unknown')
            print(f"📊 RSS feed size: {content_length} bytes")
            
            if not feed.entries:
                print("❌ No entries found")
                return
            
            print(f"📈 Total entries in feed: {len(feed.entries)}")
            print(f"🎯 Processing only latest {self.max_items_to_process} entries")
            
            # Process only the latest items (RSS is typically ordered newest first)
            latest_entries = feed.entries[:self.max_items_to_process]
            
            new_count = 0
            for entry in latest_entries:
                item_id = self.generate_item_id(entry)
                
                if item_id not in self.seen_items:
                    self.seen_items.add(item_id)
                    new_count += 1
                    self.print_announcement(entry, is_new=True, download_pdf=self.download_pdfs)
            
            print(f"✅ Processed {len(latest_entries)} latest items, found {new_count} new")
            
        except Exception as e:
            print(f"❌ Error in method 1: {e}")
    
    def method2_streaming_xml_parser(self):
        """Method 2: Stream XML and stop after processing N items"""
        print(f"📡 Method 2: Streaming XML parser (stop after {self.max_items_to_process} items)...")
        
        try:
            response = requests.get(self.rss_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Stream and parse XML incrementally
            items_processed = 0
            new_count = 0
            current_item = {}
            in_item = False
            current_tag = None
            content = ""
            
            print("🔄 Streaming XML content...")
            
            # Read content in chunks
            xml_content = ""
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                xml_content += chunk
                
                # Process XML as we get it
                while '<item>' in xml_content and items_processed < self.max_items_to_process:
                    # Extract one complete item
                    start = xml_content.find('<item>')
                    end = xml_content.find('</item>') + 7
                    
                    if start != -1 and end != -1 and end > start:
                        item_xml = xml_content[start:end]
                        xml_content = xml_content[end:]  # Remove processed item
                        
                        # Parse this item
                        try:
                            root = ET.fromstring(item_xml)
                            item_data = {}
                            
                            for child in root:
                                item_data[child.tag] = child.text or ""
                            
                            # Check if new
                            item_id = f"{item_data.get('title', '')}-{item_data.get('pubDate', '')}"
                            
                            if item_id not in self.seen_items:
                                self.seen_items.add(item_id)
                                new_count += 1
                                self.print_announcement_from_dict(item_data, is_new=True)
                            
                            items_processed += 1
                            
                        except ET.ParseError as e:
                            print(f"⚠️ XML parse error for item: {e}")
                    else:
                        break  # Need more content
                
                # Stop if we've processed enough items
                if items_processed >= self.max_items_to_process:
                    print(f"🛑 Stopping after processing {items_processed} items")
                    break
            
            print(f"✅ Streamed processing: {items_processed} items, {new_count} new")
            
        except Exception as e:
            print(f"❌ Error in method 2: {e}")
    
    def method3_time_based_filtering(self):
        """Method 3: Process items only from last check time"""
        print("📡 Method 3: Time-based filtering...")
        
        if self.last_check_time is None:
            print("⚠️ No last check time, processing latest 10 items")
            self.max_items_to_process = 10
            return self.method1_process_only_latest_items()
        
        try:
            feed = feedparser.parse(self.rss_url)
            
            if not feed.entries:
                print("❌ No entries found")
                return
            
            print(f"📈 Total entries: {len(feed.entries)}")
            print(f"🕐 Last check: {self.last_check_time}")
            
            # Filter items newer than last check
            new_items = []
            for entry in feed.entries:
                try:
                    # Parse publication date
                    pub_date_str = entry.get('published', '')
                    if pub_date_str:
                        # NSE format: "08-Aug-2025 14:31:29"
                        pub_date = datetime.strptime(pub_date_str, "%d-%b-%Y %H:%M:%S")
                        
                        if pub_date > self.last_check_time:
                            new_items.append(entry)
                        else:
                            # Since RSS is chronological, we can stop here
                            break
                            
                except ValueError as e:
                    print(f"⚠️ Date parse error: {pub_date_str} - {e}")
                    # Include item if we can't parse date
                    new_items.append(entry)
            
            print(f"📊 Found {len(new_items)} items newer than last check")
            
            # Process new items
            new_count = 0
            for entry in new_items:
                item_id = self.generate_item_id(entry)
                
                if item_id not in self.seen_items:
                    self.seen_items.add(item_id)
                    new_count += 1
                    self.print_announcement(entry, is_new=True)
            
            self.last_check_time = datetime.now()
            print(f"✅ Time-based filter: {len(new_items)} candidates, {new_count} truly new")
            
        except Exception as e:
            print(f"❌ Error in method 3: {e}")
    
    def method4_http_range_requests(self):
        """Method 4: Use HTTP Range to get only start of file"""
        print("📡 Method 4: HTTP Range request (first 50KB only)...")
        
        try:
            # Request only first 50KB of the file
            headers = {'Range': 'bytes=0-51200'}  # First 50KB
            response = requests.get(self.rss_url, headers=headers, timeout=30)
            
            if response.status_code == 206:  # Partial Content
                print("✅ Got partial content (first 50KB)")
                partial_xml = response.text
                
                # Try to make it valid XML by adding closing tags if needed
                if '</rss>' not in partial_xml:
                    # Find last complete item
                    last_complete_item = partial_xml.rfind('</item>')
                    if last_complete_item != -1:
                        partial_xml = partial_xml[:last_complete_item + 7] + '\n</channel>\n</rss>'
                
                # Parse partial XML
                try:
                    feed = feedparser.parse(partial_xml)
                    
                    if feed.entries:
                        print(f"📊 Parsed {len(feed.entries)} items from partial content")
                        
                        new_count = 0
                        for entry in feed.entries:
                            item_id = self.generate_item_id(entry)
                            
                            if item_id not in self.seen_items:
                                self.seen_items.add(item_id)
                                new_count += 1
                                self.print_announcement(entry, is_new=True)
                        
                        print(f"✅ Range request: {len(feed.entries)} items, {new_count} new")
                    else:
                        print("⚠️ No complete items in partial content")
                        
                except Exception as parse_error:
                    print(f"❌ Failed to parse partial XML: {parse_error}")
                    # Fallback to method 1
                    return self.method1_process_only_latest_items()
            else:
                print("⚠️ Server doesn't support range requests, falling back...")
                return self.method1_process_only_latest_items()
            
        except Exception as e:
            print(f"❌ Error in method 4: {e}")
    
    def smart_incremental_check(self):
        """Smart method selection - now with RSS fetch fallbacks"""
        print(f"\n🔍 Incremental check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Skip the HEAD request entirely - just try processing
        print("🎯 Using latest items method with smart RSS fetching")
        
        try:
            self.method1_process_only_latest_items()
            self.save_cache()
            
        except Exception as e:
            print(f"❌ Smart check failed: {e}")
            print("🔄 RSS feed may be temporarily unavailable")
    
    def generate_item_id(self, entry):
        """Generate unique ID for RSS entry"""
        return f"{entry.get('title', '')}-{entry.get('published', '')}-{entry.get('link', '')}"
    
    def download_pdf_with_smart_fallback(self, pdf_url, filename):
        """Smart PDF download with multiple fallback methods"""
        if not pdf_url or not pdf_url.endswith('.pdf'):
            print(f"⚠️ Skipping non-PDF link: {pdf_url}")
            return False
        
        # Create downloads directory
        downloads_dir = "nse_downloads"
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
        
        filepath = os.path.join(downloads_dir, filename)
        
        # Skip if already exists
        if os.path.exists(filepath):
            print(f"📄 Already exists: {filename}")
            return True
        
        print(f"📥 Smart downloading: {filename}")
        
        # Method 1: Enhanced requests with retry
        if self._download_method_requests(pdf_url, filepath):
            return True
        
        # Method 2: Try curl subprocess
        if self._download_method_curl(pdf_url, filepath):
            return True
        
        # Method 3: Try wget subprocess  
        if self._download_method_wget(pdf_url, filepath):
            return True
        
        # All methods failed
        print(f"❌ All download methods failed for: {filename}")
        return False
    
    def _download_method_requests(self, pdf_url, filepath):
        """Method 1: Enhanced requests with better error handling"""
        print("🔄 Trying enhanced requests method...")
        
        for attempt in range(3):
            try:
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive'
                })
                
                response = session.get(
                    pdf_url, 
                    timeout=(30, 300),  # 30s connection, 300s read
                    stream=True,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # Download in chunks
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = os.path.getsize(filepath)
                print(f"✅ Requests method success: {os.path.basename(filepath)} ({file_size:,} bytes)")
                
                # Log successful download
                with open("download_log.txt", "a") as log:
                    log.write(f"{datetime.now()}: {os.path.basename(filepath)} - {file_size} bytes - requests\n")
                
                return True
                
            except requests.exceptions.Timeout:
                print(f"⏰ Requests timeout (attempt {attempt + 1}/3)")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Requests error (attempt {attempt + 1}/3): {e}")
                if attempt < 2:
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ Unexpected requests error: {e}")
                break
                
        return False
    
    def _download_method_curl(self, pdf_url, filepath):
        """Method 2: Use curl subprocess"""
        print("🔄 Trying curl method...")
        
        try:
            import subprocess
            
            curl_cmd = [
                'curl',
                '-L',  # Follow redirects
                '-o', filepath,
                '--connect-timeout', '30',
                '--max-time', '300',
                '--retry', '3',
                '--retry-delay', '2',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--silent',  # Reduce output
                pdf_url
            ]
            
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=360)
            
            if result.returncode == 0 and os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"✅ Curl method success: {os.path.basename(filepath)} ({file_size:,} bytes)")
                
                with open("download_log.txt", "a") as log:
                    log.write(f"{datetime.now()}: {os.path.basename(filepath)} - {file_size} bytes - curl\n")
                
                return True
            else:
                if os.path.exists(filepath):
                    os.remove(filepath)  # Clean up partial file
                print(f"❌ Curl failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Curl command timed out")
            return False
        except FileNotFoundError:
            print("❌ Curl not found - install curl or skip this method")
            return False
        except Exception as e:
            print(f"❌ Curl error: {e}")
            return False
    
    def _download_method_wget(self, pdf_url, filepath):
        """Method 3: Use wget subprocess"""
        print("🔄 Trying wget method...")
        
        try:
            import subprocess
            
            wget_cmd = [
                'wget',
                '-O', filepath,
                '--timeout=30',
                '--tries=3',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--quiet',  # Reduce output
                pdf_url
            ]
            
            result = subprocess.run(wget_cmd, capture_output=True, text=True, timeout=360)
            
            if result.returncode == 0 and os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"✅ Wget method success: {os.path.basename(filepath)} ({file_size:,} bytes)")
                
                with open("download_log.txt", "a") as log:
                    log.write(f"{datetime.now()}: {os.path.basename(filepath)} - {file_size} bytes - wget\n")
                
                return True
            else:
                if os.path.exists(filepath):
                    os.remove(filepath)  # Clean up partial file
                print(f"❌ Wget failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Wget command timed out")
            return False
        except FileNotFoundError:
            print("❌ Wget not found - install wget or skip this method")
            return False
        except Exception as e:
            print(f"❌ Wget error: {e}")
            return False
    
    def print_announcement(self, entry, is_new=False, download_pdf=False):
        """Print RSS entry announcement"""
        print(f"\n🆕 {'-'*70}")
        print(f"🏢 COMPANY: {entry.get('title', 'Unknown')}")
        print(f"📅 DATE: {entry.get('published', 'No Date')}")
        
        pdf_link = entry.get('link', 'No Link')
        print(f"🔗 DOCUMENT: {pdf_link}")
        
        description = entry.get('description', '')
        if '|SUBJECT:' in description:
            main_desc, subject = description.split('|SUBJECT:', 1)
            print(f"📋 DESCRIPTION: {main_desc.strip()}")
            print(f"🏷️  SUBJECT: {subject.strip()}")
        else:
            print(f"📋 DESCRIPTION: {description}")
        
        # Optional PDF download for new announcements
        if download_pdf and is_new and pdf_link != 'No Link':
            # Clean filename
            company_name = entry.get('title', 'Unknown').replace(' ', '_').replace('/', '_').replace('\\', '_')
            pub_date = entry.get('published', '').replace('-', '').replace(' ', '_').replace(':', '').replace(',', '')
            
            # Create safe filename
            safe_filename = f"{company_name}_{pub_date}.pdf"
            # Remove any remaining unsafe characters
            safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in '._-')
            
            print(f"🎯 New announcement detected - attempting smart PDF download...")
            success = self.download_pdf_with_smart_fallback(pdf_link, safe_filename)
            
            if not success:
                # Store failed download for retry later
                failed_item = {
                    'url': pdf_link,
                    'filename': safe_filename,
                    'company': entry.get('title', ''),
                    'date': entry.get('published', ''),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Save to retry queue
                retry_file = "retry_downloads.json"
                retry_queue = []
                if os.path.exists(retry_file):
                    try:
                        with open(retry_file, 'r') as f:
                            retry_queue = json.load(f)
                    except:
                        pass
                
                retry_queue.append(failed_item)
                with open(retry_file, 'w') as f:
                    json.dump(retry_queue, f, indent=2)
                
                print(f"💾 Added to retry queue: {safe_filename}")
        
        print("-" * 80)
    
    def print_announcement_from_dict(self, item_data, is_new=False):
        """Print announcement from dictionary data"""
        print(f"\n🆕 {'-'*70}")
        print(f"🏢 COMPANY: {item_data.get('title', 'Unknown')}")
        print(f"📅 DATE: {item_data.get('pubDate', 'No Date')}")
        print(f"🔗 DOCUMENT: {item_data.get('link', 'No Link')}")
        
        description = item_data.get('description', '')
        if '|SUBJECT:' in description:
            main_desc, subject = description.split('|SUBJECT:', 1)
            print(f"📋 DESCRIPTION: {main_desc.strip()}")
            print(f"🏷️  SUBJECT: {subject.strip()}")
        else:
            print(f"📋 DESCRIPTION: {description}")
        print("-" * 80)
    
    def retry_failed_downloads(self):
        """Retry previously failed downloads"""
        retry_file = "retry_downloads.json"
        
        if not os.path.exists(retry_file):
            print("📋 No failed downloads to retry")
            return
        
        try:
            with open(retry_file, 'r') as f:
                retry_queue = json.load(f)
            
            if not retry_queue:
                print("📋 Retry queue is empty")
                return
            
            print(f"🔄 Retrying {len(retry_queue)} failed downloads...")
            
            successful_retries = []
            remaining_failures = []
            
            for item in retry_queue:
                print(f"\n🔄 Retrying: {item['company']}")
                success = self.download_pdf(item['url'], item['filename'])
                
                if success:
                    successful_retries.append(item)
                else:
                    remaining_failures.append(item)
                
                # Small delay between retries
                time.sleep(2)
            
            # Update retry queue (remove successful ones)
            with open(retry_file, 'w') as f:
                json.dump(remaining_failures, f, indent=2)
            
            print(f"\n✅ Retry results: {len(successful_retries)} successful, {len(remaining_failures)} still failed")
            
        except Exception as e:
            print(f"❌ Error in retry process: {e}")
    
    def test_rss_fetching(self):
        """Test RSS fetching methods individually"""
        print("🧪 Testing RSS fetching methods...\n")
        
        # Test the smart fetching
        content = self.fetch_rss_with_fallbacks()
        
        if content:
            print(f"✅ RSS fetch successful! Content length: {len(content)}")
            
            # Try parsing
            feed = feedparser.parse(content)
            print(f"📊 Parsed {len(feed.entries)} entries")
            
            if feed.entries:
                latest = feed.entries[0]
                print(f"📄 Latest: {latest.get('title', 'No title')}")
                print(f"📅 Date: {latest.get('published', 'No date')}")
            
            return True
        else:
            print("❌ All RSS fetching methods failed")
            return False
        """Show download statistics"""
        downloads_dir = "nse_downloads"
        
        if not os.path.exists(downloads_dir):
            print("📊 No downloads directory found")
            return
        
        pdf_files = [f for f in os.listdir(downloads_dir) if f.endswith('.pdf')]
        
        if not pdf_files:
            print("📊 No PDFs downloaded yet")
            return
        
        total_size = sum(os.path.getsize(os.path.join(downloads_dir, f)) for f in pdf_files)
        
        print(f"\n📊 DOWNLOAD STATISTICS:")
        print(f"📄 Total PDFs: {len(pdf_files)}")
        print(f"💾 Total size: {total_size / (1024*1024):.1f} MB")
        print(f"📁 Location: ./{downloads_dir}/")
        
        # Show recent downloads
        recent_files = sorted(pdf_files, key=lambda x: os.path.getmtime(os.path.join(downloads_dir, x)), reverse=True)[:5]
        print(f"\n📋 Recent downloads:")
        for f in recent_files:
            file_path = os.path.join(downloads_dir, f)
            size_kb = os.path.getsize(file_path) / 1024
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            print(f"   • {f} ({size_kb:.0f} KB) - {mtime.strftime('%Y-%m-%d %H:%M')}")
    
    def run_incremental_monitoring(self):
        """Run incremental monitoring"""
        print("🚀 Starting Incremental NSE Monitor")
        print("⚡ Optimized for large RSS feeds")
        print(f"🎯 Max items per check: {self.max_items_to_process}")
        print(f"📥 Download PDFs: {'Yes - ALL new announcements' if self.download_pdfs else 'No'}")
        
        if self.download_pdfs:
            print("📁 PDFs will be saved to: ./nse_downloads/")
            print("📝 Download logs: download_log.txt, failed_downloads.txt")
        
        print(f"⏱️  Check interval: {self.check_interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        # Show current stats
        if self.download_pdfs:
            self.get_download_stats()
        
        while True:
            try:
                self.smart_incremental_check()
                print(f"💤 Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                print("\n👋 Monitor stopped")
                self.save_cache()
                
                if self.download_pdfs:
                    self.get_download_stats()
                    
                    # Ask if user wants to retry failed downloads
                    retry_file = "retry_downloads.json"
                    if os.path.exists(retry_file):
                        try:
                            with open(retry_file, 'r') as f:
                                retry_queue = json.load(f)
                            if retry_queue:
                                print(f"\n🔄 There are {len(retry_queue)} failed downloads.")
                                print("Run monitor.retry_failed_downloads() to retry them.")
                        except:
                            pass
                
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(60)

# Performance comparison tool
def compare_methods():
    print("📊 PERFORMANCE COMPARISON FOR LARGE RSS FEEDS:\n")
    
    file_size_mb = 5.9
    total_items = 500  # Estimated
    
    print(f"📁 File size: {file_size_mb} MB")
    print(f"📄 Estimated total items: {total_items}")
    print(f"🎯 Interested in: Latest 20 items\n")
    
    methods = {
        "Full Download + Process All": {
            "download_mb": file_size_mb,
            "items_processed": total_items,
            "time_estimate": "30-60 seconds"
        },
        "Full Download + Process Latest 20": {
            "download_mb": file_size_mb,
            "items_processed": 20,
            "time_estimate": "15-30 seconds"
        },
        "HTTP Range (First 50KB)": {
            "download_mb": 0.05,
            "items_processed": 20,
            "time_estimate": "2-5 seconds"
        },
        "Time-based Filtering": {
            "download_mb": file_size_mb,
            "items_processed": 5,  # Only recent items
            "time_estimate": "10-20 seconds"
        }
    }
    
    for method, stats in methods.items():
        print(f"🔧 {method}:")
        print(f"   📥 Download: {stats['download_mb']} MB")
        print(f"   ⚙️  Process: {stats['items_processed']} items")
        print(f"   ⏱️  Time: {stats['time_estimate']}")
        print()

# Usage
if __name__ == "__main__":
    # Show performance comparison
    compare_methods()
    
    print("=" * 60 + "\n")
    
    def test_rss_fetching(self):
        """Test RSS fetching methods individually"""
        print("🧪 Testing RSS fetching methods...\n")
        
        # Test the smart fetching
        content = self.fetch_rss_with_fallbacks()
        
        if content:
            print(f"✅ RSS fetch successful! Content length: {len(content)}")
            
            # Try parsing
            feed = feedparser.parse(content)
            print(f"📊 Parsed {len(feed.entries)} entries")
            
            if feed.entries:
                latest = feed.entries[0]
                print(f"📄 Latest: {latest.get('title', 'No title')}")
                print(f"📅 Date: {latest.get('published', 'No date')}")
            
            return True
        else:
            print("❌ All RSS fetching methods failed")
            return False