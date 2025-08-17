#!/usr/bin/env python3
"""
Complete NSE Webhook Monitor - FIXED VERSION
Combines curl-based RSS fetching with smart PDF/XML downloads
"""

import subprocess
import json
import os
import time
import requests
from datetime import datetime
import xml.etree.ElementTree as ET
import re

class CompleteNSEMonitor:
    def __init__(self, check_interval=300, max_items=20, download_pdfs=True):
        self.rss_url = "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
        self.check_interval = check_interval
        self.max_items = max_items
        self.download_pdfs = download_pdfs
        self.cache_file = "nse_complete_cache.json"
        self.seen_items = set()
        self.load_cache()
        
        # Create downloads directory
        if download_pdfs:
            os.makedirs("nse_downloads", exist_ok=True)
    
    def load_cache(self):
        """Load seen items from cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    self.seen_items = set(cache.get('seen_items', []))
                print(f"📂 Loaded {len(self.seen_items)} cached items")
        except Exception as e:
            print(f"❌ Cache load error: {e}")
    
    def save_cache(self):
        """Save seen items to cache"""
        try:
            cache = {
                'seen_items': list(self.seen_items),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            print(f"❌ Cache save error: {e}")
    
    def fetch_rss_with_curl(self):
        """Fetch RSS using curl - bypasses Python request blocking"""
        print("📡 Fetching RSS with curl...")
        
        try:
            curl_cmd = [
                'curl',
                '-s',  # Silent
                '-L',  # Follow redirects
                '--connect-timeout', '30',
                '--max-time', '120',
                '--retry', '2',
                '--retry-delay', '3',
                '--user-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                '--header', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                '--header', 'Accept-Language: en-US,en;q=0.9',
                '--compressed',
                self.rss_url
            ]
            
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=150)
            
            if result.returncode == 0 and result.stdout.strip():
                content = result.stdout.strip()
                print(f"✅ RSS fetched! Content length: {len(content):,} chars")
                
                if '<rss' in content and '</rss>' in content:
                    return content
                else:
                    print("⚠️ Invalid RSS content received")
                    return None
            else:
                print(f"❌ Curl failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("⏰ Curl timed out")
            return None
        except Exception as e:
            print(f"❌ Curl error: {e}")
            return None
    
    def parse_rss_manually(self, xml_content):
        """Parse RSS manually"""
        try:
            print("🔄 Parsing RSS content...")
            
            # Remove encoding declarations
            xml_content = re.sub(r'<\?xml[^>]*\?>', '', xml_content)
            
            # Parse with ElementTree
            root = ET.fromstring(xml_content)
            
            # Find all item elements
            items = []
            for item in root.findall('.//item'):
                item_data = {}
                
                # Extract basic fields
                for child in item:
                    if child.tag in ['title', 'link', 'description', 'pubDate']:
                        item_data[child.tag] = (child.text or '').strip()
                
                if item_data.get('title'):
                    items.append(item_data)
            
            print(f"📊 Parsed {len(items)} items from RSS")
            return items
            
        except ET.ParseError as e:
            print(f"❌ XML parse error: {e}")
            return []
        except Exception as e:
            print(f"❌ RSS parse error: {e}")
            return []
    
    def create_safe_filename(self, company, pub_date, file_url):
        """Create a safe filename from company name and date"""
        try:
            # Clean company name - keep only alphanumeric and spaces
            company_clean = re.sub(r'[^a-zA-Z0-9\s]', '', company)
            company_clean = re.sub(r'\s+', '_', company_clean.strip())
            
            # Clean date - format: "09-Aug-2025 20:27:19" -> "09Aug2025_202719"
            if pub_date:
                # Extract just the date and time parts
                date_parts = pub_date.replace('-', '').replace(':', '').replace(' ', '_')
                # Remove any remaining non-alphanumeric except underscore
                date_clean = re.sub(r'[^a-zA-Z0-9_]', '', date_parts)
            else:
                date_clean = datetime.now().strftime('%d%b%Y_%H%M%S')
            
            # Determine file extension
            if file_url.endswith('.pdf'):
                file_ext = '.pdf'
            elif file_url.endswith('.xml'):
                file_ext = '.xml'
            else:
                file_ext = '.pdf'  # Default fallback
            
            # Combine parts
            filename = f"{company_clean}_{date_clean}{file_ext}"
            
            # Final cleanup
            filename = re.sub(r'_{2,}', '_', filename)  # Remove multiple underscores
            filename = re.sub(r'^_+|_+$', '', filename)  # Remove leading/trailing underscores
            
            # Ensure we have a valid filename
            if not filename or filename == file_ext or len(filename) < 5:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"NSE_Announcement_{timestamp}{file_ext}"
            
            # Limit filename length (filesystem limits)
            if len(filename) > 200:
                base_name = filename[:190]
                filename = base_name + file_ext
            
            return filename
            
        except Exception as e:
            print(f"❌ Error creating filename: {e}")
            # Fallback filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = '.pdf' if file_url.endswith('.pdf') else '.xml' if file_url.endswith('.xml') else '.pdf'
            return f"NSE_Announcement_{timestamp}{ext}"
    
    def smart_download_file(self, file_url, filename):
        """Smart file download for both PDF and XML files"""
        if not (file_url.endswith('.pdf') or file_url.endswith('.xml')):
            print(f"⚠️ Skipping unsupported file type: {file_url}")
            return False
        
        filepath = os.path.join("nse_downloads", filename)
        
        # Skip if exists
        if os.path.exists(filepath):
            print(f"📄 Already exists: {filename}")
            return True
        
        print(f"📥 Smart downloading: {filename}")
        
        # Method 1: Try requests first
        success = self._download_with_requests(file_url, filepath, filename)
        if success:
            return True
        
        # Method 2: Try curl
        success = self._download_with_curl(file_url, filepath, filename)
        if success:
            return True
        
        # Method 3: Try wget
        success = self._download_with_wget(file_url, filepath, filename)
        if success:
            return True
        
        print(f"❌ All download methods failed: {filename}")
        
        # Log failed download
        with open("failed_downloads.txt", "a") as log:
            log.write(f"{datetime.now()}: FAILED - {file_url} -> {filename}\\n")
        
        return False
    
    def _download_with_requests(self, file_url, filepath, filename):
        """Method 1: Enhanced requests for any file type"""
        try:
            print("🔄 Trying requests method...")
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/pdf,application/xml,text/xml,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9'
            })
            
            response = session.get(file_url, timeout=(30, 300), stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(filepath)
            print(f"✅ Requests success: {filename} ({file_size:,} bytes)")
            
            # Log success
            with open("download_log.txt", "a") as log:
                log.write(f"{datetime.now()}: {filename} - {file_size} bytes - requests\\n")
            
            return True
            
        except Exception as e:
            print(f"❌ Requests failed: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
    
    def _download_with_curl(self, file_url, filepath, filename):
        """Method 2: Curl download for any file type"""
        try:
            print("🔄 Trying curl method...")
            
            curl_cmd = [
                'curl',
                '-L',  # Follow redirects
                '-o', filepath,
                '--connect-timeout', '30',
                '--max-time', '300',
                '--retry', '2',
                '--user-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                '--silent',
                file_url
            ]
            
            result = subprocess.run(curl_cmd, timeout=360)
            
            if result.returncode == 0 and os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                if file_size > 0:
                    print(f"✅ Curl success: {filename} ({file_size:,} bytes)")
                    
                    # Log success
                    with open("download_log.txt", "a") as log:
                        log.write(f"{datetime.now()}: {filename} - {file_size} bytes - curl\\n")
                    
                    return True
                else:
                    os.remove(filepath)
            
            return False
            
        except Exception as e:
            print(f"❌ Curl failed: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
    
    def _download_with_wget(self, file_url, filepath, filename):
        """Method 3: Wget download for any file type"""
        try:
            print("🔄 Trying wget method...")
            
            wget_cmd = [
                'wget',
                '-O', filepath,
                '--timeout=30',
                '--tries=2',
                '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                '--quiet',
                file_url
            ]
            
            result = subprocess.run(wget_cmd, timeout=360)
            
            if result.returncode == 0 and os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                if file_size > 0:
                    print(f"✅ Wget success: {filename} ({file_size:,} bytes)")
                    
                    # Log success
                    with open("download_log.txt", "a") as log:
                        log.write(f"{datetime.now()}: {filename} - {file_size} bytes - wget\\n")
                    
                    return True
                else:
                    os.remove(filepath)
            
            return False
            
        except Exception as e:
            print(f"❌ Wget failed: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
    
    def process_announcement(self, item, is_new=False):
        """Process a single announcement"""
        print(f"\\n{'🆕' if is_new else '👁️'} {'-'*70}")
        print(f"🏢 COMPANY: {item.get('title', 'Unknown')}")
        print(f"📅 DATE: {item.get('pubDate', 'No Date')}")
        
        file_link = item.get('link', '')
        print(f"🔗 DOCUMENT: {file_link}")
        
        # Parse description
        description = item.get('description', '')
        if '|SUBJECT:' in description:
            main_desc, subject = description.split('|SUBJECT:', 1)
            print(f"📋 DESCRIPTION: {main_desc.strip()}")
            print(f"🏷️ SUBJECT: {subject.strip()}")
        else:
            print(f"📋 DESCRIPTION: {description}")
        
        # Download files if requested and new (both PDF and XML)
        if self.download_pdfs and is_new:
            if file_link.endswith('.pdf') or file_link.endswith('.xml'):
                # Create safe filename using the new method
                filename = self.create_safe_filename(
                    item.get('title', 'Unknown'),
                    item.get('pubDate', ''),
                    file_link
                )
                
                file_type = "PDF Document" if file_link.endswith('.pdf') else "XML Data"
                print(f"🎯 New announcement - attempting {file_type} download...")
                print(f"📝 Filename: {filename}")
                
                self.smart_download_file(file_link, filename)
            else:
                print(f"⚠️ Skipping unsupported file type: {file_link}")
        
        print("-" * 80)
    
    def check_announcements(self):
        """Check for new announcements"""
        print(f"\\n🔍 Checking NSE announcements at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Fetch RSS with curl
        rss_content = self.fetch_rss_with_curl()
        if not rss_content:
            print("❌ Could not fetch RSS content")
            return
        
        # Parse RSS
        items = self.parse_rss_manually(rss_content)
        if not items:
            print("❌ Could not parse any items from RSS")
            return
        
        print(f"📈 Total items in RSS: {len(items)}")
        print(f"🎯 Processing latest {min(self.max_items, len(items))} items")
        
        # Process latest items only
        latest_items = items[:self.max_items]
        new_count = 0
        
        for item in latest_items:
            # Create unique ID
            item_id = f"{item.get('title', '')}-{item.get('pubDate', '')}"
            
            if item_id not in self.seen_items:
                self.seen_items.add(item_id)
                new_count += 1
                self.process_announcement(item, is_new=True)
            # Uncomment below to show all items
            # else:
            #     self.process_announcement(item, is_new=False)
        
        print(f"\\n📊 SUMMARY: {new_count} new announcements, {len(latest_items) - new_count} previously seen")
        
        if new_count > 0:
            print(f"🔔 {new_count} NEW CORPORATE ANNOUNCEMENTS!")
            self.save_cache()
        else:
            print("😴 No new announcements")
    
    def get_download_stats(self):
        """Show download statistics for both PDF and XML files"""
        downloads_dir = "nse_downloads"
        
        if not os.path.exists(downloads_dir):
            print("📊 No downloads directory found")
            return
        
        # Get both PDF and XML files
        pdf_files = [f for f in os.listdir(downloads_dir) if f.endswith('.pdf')]
        xml_files = [f for f in os.listdir(downloads_dir) if f.endswith('.xml')]
        all_files = pdf_files + xml_files
        
        if not all_files:
            print("📊 No files downloaded yet")
            return
        
        total_size = sum(os.path.getsize(os.path.join(downloads_dir, f)) for f in all_files)
        
        print(f"\\n📊 DOWNLOAD STATISTICS:")
        print(f"📄 PDF files: {len(pdf_files)}")
        print(f"📋 XML files: {len(xml_files)}")
        print(f"📁 Total files: {len(all_files)}")
        print(f"💾 Total size: {total_size / (1024*1024):.1f} MB")
        print(f"📂 Location: ./{downloads_dir}/")
        
        # Show recent downloads
        if all_files:
            recent_files = sorted(all_files, key=lambda x: os.path.getmtime(os.path.join(downloads_dir, x)), reverse=True)[:5]
            print(f"\\n📋 Recent downloads:")
            for f in recent_files:
                file_path = os.path.join(downloads_dir, f)
                size_kb = os.path.getsize(file_path) / 1024
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                file_type = "📄 PDF" if f.endswith('.pdf') else "📋 XML"
                print(f"   • {file_type}: {f} ({size_kb:.0f} KB) - {mtime.strftime('%Y-%m-%d %H:%M')}")
    
    def test_filename_generation(self):
        """Test filename generation with sample data"""
        test_cases = [
            {'title': 'EPL Limited', 'pubDate': '08-Aug-2025 21:14:22', 'url': 'test.pdf'},
            {'title': 'Yatra Online Limited', 'pubDate': '08-Aug-2025 21:07:56', 'url': 'test.pdf'},
            {'title': 'Concord Enviro Systems Limited', 'pubDate': '08-Aug-2025 21:07:40', 'url': 'test.xml'},
            {'title': 'The Grob Tea Company Limited', 'pubDate': '09-Aug-2025 20:13:41', 'url': 'test.pdf'},
            {'title': 'KEC International Limited', 'pubDate': '09-Aug-2025 20:22:59', 'url': 'test.xml'}
        ]
        
        print("🧪 Testing filename generation:")
        print("-" * 80)
        
        for case in test_cases:
            filename = self.create_safe_filename(case['title'], case['pubDate'], case['url'])
            print(f"Company: {case['title']}")
            print(f"Date: {case['pubDate']}")
            print(f"Type: {case['url']}")
            print(f"Generated: {filename}")
            print("-" * 40)
    
    def search_company(self, company_name):
        """Search for specific company announcements"""
        print(f"🔍 Searching for '{company_name}' announcements...")
        
        # Fetch and parse RSS
        rss_content = self.fetch_rss_with_curl()
        if not rss_content:
            print("❌ Could not fetch RSS")
            return
        
        items = self.parse_rss_manually(rss_content)
        if not items:
            print("❌ Could not parse RSS")
            return
        
        # Filter by company name
        matching_items = []
        for item in items:
            if company_name.lower() in item.get('title', '').lower():
                matching_items.append(item)
        
        if matching_items:
            print(f"🏢 Found {len(matching_items)} announcements for '{company_name}':")
            for item in matching_items:
                self.process_announcement(item, is_new=True)
        else:
            print(f"❌ No announcements found for '{company_name}'")
    
    def run_once(self):
        """Run a single check"""
        print("🔍 Running single check...")
        self.check_announcements()
        if self.download_pdfs:
            self.get_download_stats()
    
    def run_continuous(self):
        """Run continuous monitoring"""
        print("🚀 Starting Complete NSE Monitor")
        print(f"📡 RSS URL: {self.rss_url}")
        print(f"🎯 Max items per check: {self.max_items}")
        print(f"📥 Download files: {'Yes - PDFs and XMLs' if self.download_pdfs else 'No'}")
        
        if self.download_pdfs:
            print("📁 Files will be saved to: ./nse_downloads/")
            print("📝 Logs: download_log.txt, failed_downloads.txt")
        
        print(f"⏱️  Check interval: {self.check_interval} seconds")
        print("Press Ctrl+C to stop\\n")
        
        # Show current stats
        if self.download_pdfs:
            self.get_download_stats()
        
        while True:
            try:
                self.check_announcements()
                print(f"💤 Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                print("\\n👋 Monitor stopped")
                if self.download_pdfs:
                    self.get_download_stats()
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                print("🔄 Retrying in 60 seconds...")
                time.sleep(60)

def main():
    print("🚀 Complete NSE Announcement Monitor - FIXED VERSION")
    print("=" * 60)
    
    # Configuration
    monitor = CompleteNSEMonitor(
        check_interval=300,    # Check every 5 minutes
        max_items=20,         # Process latest 20 items only
        download_pdfs=True    # Download all files for new announcements
    )
    
    # Choose what to do
    choice = input("""
Choose an option:
1. Run once (test)
2. Run continuous monitoring  
3. Search for specific company
4. Show download stats only
5. Test filename generation

Enter choice (1-5): """).strip()
    
    if choice == '1':
        monitor.run_once()
    elif choice == '2':
        monitor.run_continuous()
    elif choice == '3':
        company = input("Enter company name: ").strip()
        if company:
            monitor.search_company(company)
    elif choice == '4':
        monitor.get_download_stats()
    elif choice == '5':
        monitor.test_filename_generation()
    else:
        print("Invalid choice. Running once...")
        monitor.run_once()

if __name__ == "__main__":
    main()