#!/usr/bin/env python3
"""
Simple NSE RSS Monitor with curl fallback
Works around NSE blocking Python requests
"""

import subprocess
import json
import os
import time
from datetime import datetime
import xml.etree.ElementTree as ET
import re

class SimpleNSECurlMonitor:
    def __init__(self, check_interval=300, download_pdfs=True):
        self.rss_url = "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
        self.check_interval = check_interval
        self.download_pdfs = download_pdfs
        self.cache_file = "nse_simple_cache.json"
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
            # Check if curl is available
            result = subprocess.run(['curl', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Curl not found. Install with: sudo apt install curl")
                return None
            
            # Curl command with browser-like headers
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
            
            print("🔄 Running curl command...")
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=150)
            
            if result.returncode == 0 and result.stdout.strip():
                content = result.stdout.strip()
                print(f"✅ Curl success! Content length: {len(content):,} chars")
                
                # Basic validation
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
        except FileNotFoundError:
            print("❌ Curl not found. Install with: sudo apt install curl")
            return None
        except Exception as e:
            print(f"❌ Curl error: {e}")
            return None
    
    def parse_rss_manually(self, xml_content):
        """Parse RSS manually since feedparser might have issues"""
        try:
            print("🔄 Parsing RSS content...")
            
            # Remove any encoding declarations that might cause issues
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
    
    def download_pdf_with_curl(self, pdf_url, filename):
        """Download PDF using curl"""
        if not pdf_url.endswith('.pdf'):
            return False
        
        filepath = os.path.join("nse_downloads", filename)
        
        # Skip if exists
        if os.path.exists(filepath):
            print(f"📄 Already exists: {filename}")
            return True
        
        print(f"📥 Downloading: {filename}")
        
        try:
            curl_cmd = [
                'curl',
                '-L',  # Follow redirects
                '-o', filepath,
                '--connect-timeout', '30',
                '--max-time', '300',  # 5 minutes for large PDFs
                '--retry', '2',
                '--user-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                '--silent',
                pdf_url
            ]
            
            result = subprocess.run(curl_cmd, timeout=360)
            
            if result.returncode == 0 and os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                if file_size > 0:
                    print(f"✅ Downloaded: {filename} ({file_size:,} bytes)")
                    
                    # Log success
                    with open("download_log.txt", "a") as log:
                        log.write(f"{datetime.now()}: {filename} - {file_size} bytes\n")
                    
                    return True
                else:
                    os.remove(filepath)  # Remove empty file
            
            print(f"❌ Download failed: {filename}")
            return False
            
        except subprocess.TimeoutExpired:
            print(f"⏰ Download timed out: {filename}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False
    
    def process_announcement(self, item, is_new=False):
        """Process a single announcement"""
        print(f"\n{'🆕' if is_new else '👁️'} {'-'*70}")
        print(f"🏢 COMPANY: {item.get('title', 'Unknown')}")
        print(f"📅 DATE: {item.get('pubDate', 'No Date')}")
        
        pdf_link = item.get('link', '')
        print(f"🔗 DOCUMENT: {pdf_link}")
        
        # Parse description
        description = item.get('description', '')
        if '|SUBJECT:' in description:
            main_desc, subject = description.split('|SUBJECT:', 1)
            print(f"📋 DESCRIPTION: {main_desc.strip()}")
            print(f"🏷️ SUBJECT: {subject.strip()}")
        else:
            print(f"📋 DESCRIPTION: {description}")
        
        # Download PDF if requested and new
        if self.download_pdfs and is_new and pdf_link.endswith('.pdf'):
            # Create safe filename
            company = item.get('title', 'Unknown').replace(' ', '_').replace('/', '_')
            pub_date = item.get('pubDate', '').replace('-', '').replace(' ', '_').replace(':', '')
            filename = f"{company}_{pub_date}.pdf"
            
            # Clean filename
            filename = re.sub(r'[^\w\-_.]', '', filename)
            
            self.download_pdf_with_curl(pdf_link, filename)
        
        print("-" * 80)
    
    def check_announcements(self, max_items=20):
        """Check for new announcements"""
        print(f"\n🔍 Checking NSE announcements at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
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
        print(f"🎯 Processing latest {min(max_items, len(items))} items")
        
        # Process latest items only
        latest_items = items[:max_items]
        new_count = 0
        
        for item in latest_items:
            # Create unique ID
            item_id = f"{item.get('title', '')}-{item.get('pubDate', '')}"
            
            if item_id not in self.seen_items:
                self.seen_items.add(item_id)
                new_count += 1
                self.process_announcement(item, is_new=True)
            else:
                # Uncomment below to show all items, not just new ones
                # self.process_announcement(item, is_new=False)
                pass
        
        print(f"\n📊 SUMMARY: {new_count} new announcements, {len(latest_items) - new_count} previously seen")
        
        if new_count > 0:
            print(f"🔔 {new_count} NEW CORPORATE ANNOUNCEMENTS!")
            self.save_cache()
        else:
            print("😴 No new announcements")
    
    def run_monitoring(self):
        """Run continuous monitoring"""
        print("🚀 Starting Simple NSE Monitor (Curl-based)")
        print(f"📡 RSS URL: {self.rss_url}")
        print(f"📥 Download PDFs: {'Yes' if self.download_pdfs else 'No'}")
        print(f"⏱️ Check interval: {self.check_interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                self.check_announcements()
                print(f"💤 Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                print("\n👋 Monitor stopped")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                print("🔄 Retrying in 60 seconds...")
                time.sleep(60)

def main():
    print("🧪 NSE RSS Monitor - Simple Curl Version")
    print("=" * 50)
    
    # Create monitor
    monitor = SimpleNSECurlMonitor(
        check_interval=300,  # 5 minutes
        download_pdfs=True   # Download all PDFs for new announcements
    )
    
    # Test single run first
    print("\n🔍 Testing single check...")
    monitor.check_announcements(max_items=10)
    
    print("\n" + "=" * 50)
    response = input("Single check completed. Start continuous monitoring? (y/n): ")
    
    if response.lower() == 'y':
        monitor.run_monitoring()
    else:
        print("👋 Exiting...")

if __name__ == "__main__":
    main()