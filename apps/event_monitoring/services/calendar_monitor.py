# apps/event_monitoring/services/calendar_monitor.py
import os
import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from django.utils import timezone
from core.interfaces.scraping_interfaces import EventMonitorInterface

logger = logging.getLogger(__name__)

class NSEEventCalendarMonitor(EventMonitorInterface):
    """Single responsibility: Monitor NSE event calendar for result dates"""
    
    def __init__(self):
        self.nse_base_url = "https://www.nseindia.com"
        self.calendar_url = f"{self.nse_base_url}/companies-listing/corporate-filings-event-calendar"
        self.download_dir = "data/event_calendar_downloads"
        self.driver = None
        
        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
        
        self._setup_driver()
    
    def _setup_driver(self):
        """Setup Selenium WebDriver with download preferences"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Set download preferences
            prefs = {
                "download.default_directory": os.path.abspath(self.download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            self.driver = None
    
    def get_upcoming_events(self, days_ahead: int = 30) -> Dict[str, List[str]]:
        """Get upcoming corporate events"""
        try:
            if not self.driver:
                return {}
            
            # Download both equity and SME event calendars
            equity_events = self._download_equity_calendar()
            sme_events = self._download_sme_calendar()
            
            # Parse and filter events
            cutoff_date = datetime.now() + timedelta(days=days_ahead)
            
            upcoming_events = {
                'equity_companies': [],
                'sme_companies': [],
                'all_events': []
            }
            
            # Process equity events
            for event in equity_events:
                event_date = self._parse_event_date(event.get('event_date', ''))
                if event_date and event_date <= cutoff_date:
                    company_symbol = event.get('symbol', '').strip()
                    if company_symbol:
                        upcoming_events['equity_companies'].append(company_symbol)
                        upcoming_events['all_events'].append({
                            'symbol': company_symbol,
                            'event_date': event_date,
                            'event_type': event.get('event_type', ''),
                            'category': 'equity'
                        })
            
            # Process SME events
            for event in sme_events:
                event_date = self._parse_event_date(event.get('event_date', ''))
                if event_date and event_date <= cutoff_date:
                    company_symbol = event.get('symbol', '').strip()
                    if company_symbol:
                        upcoming_events['sme_companies'].append(company_symbol)
                        upcoming_events['all_events'].append({
                            'symbol': company_symbol,
                            'event_date': event_date,
                            'event_type': event.get('event_type', ''),
                            'category': 'sme'
                        })
            
            # Remove duplicates
            upcoming_events['equity_companies'] = list(set(upcoming_events['equity_companies']))
            upcoming_events['sme_companies'] = list(set(upcoming_events['sme_companies']))
            
            return upcoming_events
            
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return {}
    
    def get_recent_announcements(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get recent corporate announcements"""
        try:
            # This would integrate with the RSS feed monitoring
            from .announcement_monitor import OrderAnnouncementMonitor
            
            announcement_monitor = OrderAnnouncementMonitor()
            return announcement_monitor.get_recent_order_announcements(hours_back)
            
        except Exception as e:
            logger.error(f"Error getting recent announcements: {e}")
            return []
    
    def get_companies_announcing_today(self) -> List[str]:
        """Get companies announcing results today"""
        try:
            today = datetime.now().date()
            upcoming = self.get_upcoming_events(days_ahead=1)
            
            companies_today = []
            
            for event in upcoming.get('all_events', []):
                event_date = event.get('event_date')
                if event_date and event_date.date() == today:
                    companies_today.append(event['symbol'])
            
            return list(set(companies_today))
            
        except Exception as e:
            logger.error(f"Error getting companies announcing today: {e}")
            return []
    
    def _download_equity_calendar(self) -> List[Dict[str, Any]]:
        """Download equity event calendar from NSE"""
        try:
            logger.info("Downloading equity event calendar")
            
            # Navigate to calendar page
            self.driver.get(self.calendar_url)
            time.sleep(3)
            
            # Look for equity calendar download button/link
            equity_download = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Equity') or contains(@href, 'equity')]"))
            )
            
            # Click download
            equity_download.click()
            time.sleep(5)  # Wait for download
            
            # Find and parse the downloaded CSV file
            return self._parse_downloaded_csv('equity')
            
        except Exception as e:
            logger.error(f"Error downloading equity calendar: {e}")
            return []
    
    def _download_sme_calendar(self) -> List[Dict[str, Any]]:
        """Download SME event calendar from NSE"""
        try:
            logger.info("Downloading SME event calendar")
            
            # Look for SME calendar download button/link
            sme_download = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'SME') or contains(@href, 'sme')]"))
            )
            
            # Click download
            sme_download.click()
            time.sleep(5)  # Wait for download
            
            # Find and parse the downloaded CSV file
            return self._parse_downloaded_csv('sme')
            
        except Exception as e:
            logger.error(f"Error downloading SME calendar: {e}")
            return []
    
    def _parse_downloaded_csv(self, calendar_type: str) -> List[Dict[str, Any]]:
        """Parse downloaded CSV file"""
        try:
            # Find the most recently downloaded CSV file
            csv_files = [f for f in os.listdir(self.download_dir) if f.endswith('.csv')]
            
            if not csv_files:
                logger.warning(f"No CSV files found for {calendar_type} calendar")
                return []
            
            # Get the most recent file
            csv_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.download_dir, x)), reverse=True)
            latest_csv = os.path.join(self.download_dir, csv_files[0])
            
            events = []
            
            with open(latest_csv, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                for row in csv_reader:
                    # Map CSV columns to our event structure
                    event = {
                        'symbol': row.get('Symbol', row.get('Company Symbol', '')).strip(),
                        'company_name': row.get('Company Name', row.get('Name', '')).strip(),
                        'event_type': row.get('Event Type', row.get('Purpose', '')).strip(),
                        'event_date': row.get('Event Date', row.get('Date', '')).strip(),
                        'calendar_type': calendar_type
                    }
                    
                    # Only include events with valid symbols and dates
                    if event['symbol'] and event['event_date']:
                        events.append(event)
            
            logger.info(f"Parsed {len(events)} events from {calendar_type} calendar")
            return events
            
        except Exception as e:
            logger.error(f"Error parsing CSV for {calendar_type}: {e}")
            return []
    
    def _parse_event_date(self, date_str: str) -> Optional[datetime]:
        """Parse event date string to datetime"""
        try:
            if not date_str:
                return None
            
            # Try different date formats commonly used by NSE
            formats = [
                '%d-%m-%Y',
                '%d/%m/%Y',
                '%Y-%m-%d',
                '%d %b %Y',
                '%d %B %Y',
                '%d-%b-%Y',
                '%d-%B-%Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            
            logger.warning(f"Could not parse date: {date_str}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing event date {date_str}: {e}")
            return None
    
    def __del__(self):
        """Cleanup WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
