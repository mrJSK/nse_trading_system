# apps/fundamental_analysis/management/commands/scrape_fundamentals.py

import os
import re
import time
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.market_data_service.models import (
    Company, IndustryClassification, ValuationMetrics, 
    ProfitabilityMetrics, GrowthMetrics, QualitativeAnalysis,
    ShareholdingPattern, FinancialStatement, FundamentalScore
)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
]

HTML_STORAGE_PATH = 'data/scraped_html'
BASE_LIST_URL = "https://www.screener.in/screens/515361/largecaptop-100midcap101-250smallcap251/?page={i}"

def get_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def fetch_page(session, url, retries=3, backoff_factor=0.8, referer=None):
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    if referer:
        headers['Referer'] = referer

    for attempt in range(retries):
        try:
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"[{get_timestamp()}] Request to {url} failed: {e}")
            if attempt < retries - 1:
                wait_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
            else:
                print(f"[{get_timestamp()}] Final attempt failed for {url}")
                return None
    return None

def clean_text(text):
    if not text:
        return None
    return text.strip().replace('₹', '').replace(',', '').replace('%', '').replace('Cr.', '').strip()

def parse_number(text):
    if not text:
        return None
    cleaned = clean_text(text)
    if not cleaned:
        return None
    
    # Handle negative numbers and extract numeric part
    match = re.search(r'[-+]?\d*\.?\d+', cleaned)
    if match:
        try:
            return Decimal(str(match.group(0)))
        except (ValueError, TypeError):
            return None
    return None

def extract_company_symbol_from_url(url):
    parts = url.strip('/').split('/')
    if 'company' in parts:
        try:
            symbol_index = parts.index('company') + 1
            return parts[symbol_index]
        except (IndexError, ValueError):
            pass
    return None

def process_industry_path(soup):
    try:
        peers_section = soup.select_one('section#peers')
        if not peers_section:
            return None
        
        path_paragraph = peers_section.select_one('p.sub:not(#benchmarks)')
        if not path_paragraph:
            return None
        
        path_links = path_paragraph.select('a')
        if not path_links:
            return None
        
        path_names = [link.get_text(strip=True).replace('&', 'and') for link in path_links]
        parent_obj = None
        last_classification_obj = None
        
        with transaction.atomic():
            for level, name in enumerate(path_names):
                classification_obj, _ = IndustryClassification.objects.get_or_create(
                    name=name, 
                    defaults={'parent': parent_obj, 'level': level}
                )
                parent_obj = last_classification_obj = classification_obj
        
        return last_classification_obj
    except Exception as e:
        print(f"Error processing industry path: {e}")
        return None

def parse_website_link(soup):
    try:
        company_links_div = soup.select_one('div.company-links')
        if not company_links_div:
            return None
        
        all_links = company_links_div.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            if 'bseindia.com' not in href and 'nseindia.com' not in href:
                return href
        return None
    except Exception as e:
        print(f"Error parsing website link: {e}")
        return None

def extract_ratios_data(soup):
    try:
        ratios_data = {}
        ratios_list = soup.select('#top-ratios li')
        
        for li in ratios_list:
            name_elem = li.select_one('.name')
            value_elem = li.select_one('.value')
            
            if name_elem and value_elem:
                name = name_elem.get_text(strip=True)
                value = value_elem.get_text(strip=True)
                ratios_data[name] = value
        
        return ratios_data
    except Exception as e:
        print(f"Error extracting ratios data: {e}")
        return {}

def extract_pros_cons(soup):
    try:
        pros = [li.get_text(strip=True) for li in soup.select('.pros ul li')]
        cons = [li.get_text(strip=True) for li in soup.select('.cons ul li')]
        return pros, cons
    except Exception as e:
        print(f"Error extracting pros/cons: {e}")
        return [], []

class Command(BaseCommand):
    help = 'Scrape company fundamentals from screener.in'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            choices=['download', 'process', 'all'],
            default='all',
            help='Specify the operation mode'
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            default=3,
            help='Maximum number of pages to scrape'
        )

    def _log(self, message, style=None):
        style = style or self.style.SUCCESS
        self.stdout.write(style(f"[{get_timestamp()}] {message}"))

    def _extract_companies_from_listing_page(self, soup):
        company_urls = []
        
        try:
            # Find the table with company data
            table = soup.select_one('table')
            if not table:
                self._log("No table found on listing page", self.style.WARNING)
                return company_urls
            
            # Get all rows except header
            rows = table.select('tr')[1:]
            
            for row in rows:
                cells = row.select('td')
                if len(cells) >= 2:
                    # Look for company name link in the second column
                    name_cell = cells[1]
                    link = name_cell.select_one('a')
                    
                    if link and link.get('href'):
                        href = link.get('href')
                        if href.startswith('/'):
                            full_url = f"https://www.screener.in{href}"
                            company_urls.append(full_url)
                            company_name = link.get_text(strip=True)
                            self._log(f"Found: {company_name} -> {full_url}", self.style.HTTP_INFO)
            
            return company_urls
            
        except Exception as e:
            self._log(f"Error extracting companies: {e}", self.style.ERROR)
            return company_urls

    def _run_download_phase(self):
        self._log("====== STARTING DOWNLOAD PHASE ======", self.style.HTTP_SUCCESS)
        os.makedirs(HTML_STORAGE_PATH, exist_ok=True)

        summary = {'success': 0, 'skipped': 0, 'failed': 0}
        company_urls_to_scrape = []
        
        with requests.Session() as session:
            max_pages = getattr(self, 'max_pages', 3)
            
            for page_num in range(1, max_pages + 1):
                list_url = BASE_LIST_URL.format(page_num)
                self._log(f"Fetching company list from page {page_num}...", self.style.HTTP_INFO)
                
                response = fetch_page(session, list_url)
                if not response:
                    self._log(f"Could not fetch list page {page_num}", self.style.WARNING)
                    break

                soup = BeautifulSoup(response.content, 'lxml')
                page_companies = self._extract_companies_from_listing_page(soup)
                
                if not page_companies:
                    self._log(f"No companies found on page {page_num}", self.style.SUCCESS)
                    break
                
                company_urls_to_scrape.extend(page_companies)
                self._log(f"Found {len(page_companies)} companies on page {page_num}", self.style.SUCCESS)
                
                time.sleep(random.uniform(2, 4))

            company_urls_to_scrape = list(set(company_urls_to_scrape))
            self._log(f"Found {len(company_urls_to_scrape)} unique company URLs", self.style.SUCCESS)

            if not company_urls_to_scrape:
                self._log("No company URLs found", self.style.ERROR)
                return

            total_urls = len(company_urls_to_scrape)
            for i, url in enumerate(company_urls_to_scrape):
                try:
                    company_symbol = extract_company_symbol_from_url(url)
                    if not company_symbol:
                        company_symbol = url.strip('/').split('/')[-1]
                    
                    filename = f"{company_symbol}.html"
                    filepath = os.path.join(HTML_STORAGE_PATH, filename)
                    progress = f"[{i+1}/{total_urls}]"

                    if os.path.exists(filepath):
                        self._log(f"{progress} SKIP {company_symbol} already exists", self.style.NOTICE)
                        summary['skipped'] += 1
                        continue

                    self._log(f"{progress} Downloading {company_symbol}...", self.style.HTTP_INFO)
                    
                    response = fetch_page(session, url, referer="https://www.screener.in/")
                    if response:
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        self._log(f"{progress} SUCCESS Saved {company_symbol}", self.style.SUCCESS)
                        summary['success'] += 1
                    else:
                        self._log(f"{progress} FAILED {company_symbol}", self.style.ERROR)
                        summary['failed'] += 1

                except Exception as e:
                    self._log(f"{progress} ERROR for {url}: {e}", self.style.ERROR)
                    summary['failed'] += 1
                
                finally:
                    time.sleep(random.uniform(1.5, 3.0))
        
        self._log("====== DOWNLOAD PHASE FINISHED ======", self.style.HTTP_SUCCESS)
        self._log(f"SUCCESS: {summary['success']}, SKIPPED: {summary['skipped']}, FAILED: {summary['failed']}", self.style.SUCCESS)

    def _save_company_data(self, company_symbol, soup):
        try:
            with transaction.atomic():
                # Get basic company info
                company_name_elem = soup.select_one('h1.margin-0')
                company_name = company_name_elem.get_text(strip=True) if company_name_elem else company_symbol
                
                # Get about text
                about_elem = soup.select_one('.company-profile .about p')
                about_text = about_elem.get_text(strip=True) if about_elem else None
                
                # Get industry classification
                industry_classification = process_industry_path(soup)
                
                # Get website
                website = parse_website_link(soup)
                
                # Get exchange codes
                bse_link = soup.select_one('a[href*="bseindia.com"]')
                bse_code = bse_link.get_text(strip=True).replace('BSE:', '').strip() if bse_link else None
                
                nse_link = soup.select_one('a[href*="nseindia.com"]')
                nse_code = nse_link.get_text(strip=True).replace('NSE:', '').strip() if nse_link else None
                
                # Create/Update Company
                company, created = Company.objects.update_or_create(
                    symbol=company_symbol,
                    defaults={
                        'name': company_name,
                        'about': about_text,
                        'website': website,
                        'bse_code': bse_code,
                        'nse_code': nse_code,
                        'industry_classification': industry_classification,
                        'is_active': True,
                        'is_tradeable': True,
                        'last_scraped': timezone.now(),
                    }
                )

                # Get ratios data
                ratios_data = extract_ratios_data(soup)
                
                # Parse high/low 52-week data
                high_low = ratios_data.get('High / Low', '')
                high_52_week, low_52_week = None, None
                if high_low and '/' in high_low:
                    try:
                        parts = high_low.split('/')
                        high_52_week = parse_number(parts[0].strip())
                        low_52_week = parse_number(parts[1].strip())
                    except:
                        pass

                # Create/Update ValuationMetrics
                ValuationMetrics.objects.update_or_create(
                    company=company,
                    defaults={
                        'market_cap': parse_number(ratios_data.get('Market Cap')),
                        'current_price': parse_number(ratios_data.get('Current Price')),
                        'high_52_week': high_52_week,
                        'low_52_week': low_52_week,
                        'stock_pe': parse_number(ratios_data.get('Stock P/E')),
                        'book_value': parse_number(ratios_data.get('Book Value')),
                        'dividend_yield': parse_number(ratios_data.get('Dividend Yield')),
                        'face_value': parse_number(ratios_data.get('Face Value')),
                        'data_source': 'screener',
                    }
                )

                # Create/Update ProfitabilityMetrics
                ProfitabilityMetrics.objects.update_or_create(
                    company=company,
                    defaults={
                        'roce': parse_number(ratios_data.get('ROCE')),
                        'roe': parse_number(ratios_data.get('ROE')),
                        'data_source': 'screener',
                    }
                )

                # Create/Update QualitativeAnalysis
                pros, cons = extract_pros_cons(soup)
                QualitativeAnalysis.objects.update_or_create(
                    company=company,
                    defaults={
                        'pros': pros,
                        'cons': cons,
                        'data_source': 'screener',
                    }
                )

                return company, created

        except Exception as e:
            self._log(f"Error saving {company_symbol}: {e}", self.style.ERROR)
            return None, False

    def _run_process_phase(self):
        self._log("====== STARTING PROCESSING PHASE ======", self.style.HTTP_SUCCESS)
        
        if not os.path.exists(HTML_STORAGE_PATH):
            self._log(f"Storage directory '{HTML_STORAGE_PATH}' not found", self.style.ERROR)
            return

        html_files = [f for f in os.listdir(HTML_STORAGE_PATH) if f.endswith('.html')]
        total_files = len(html_files)
        self._log(f"Found {total_files} HTML files to process", self.style.SUCCESS)

        summary = {'created': 0, 'updated': 0, 'failed': 0}

        for i, filename in enumerate(html_files):
            company_symbol = filename.replace('.html', '')
            filepath = os.path.join(HTML_STORAGE_PATH, filename)
            progress = f"[{i+1}/{total_files}]"
            
            try:
                self._log(f"{progress} Processing {company_symbol}...", self.style.HTTP_INFO)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'lxml')

                company, created = self._save_company_data(company_symbol, soup)
                
                if company:
                    action = "CREATED" if created else "UPDATED"
                    summary['created' if created else 'updated'] += 1
                    self._log(f"{progress} SUCCESS {action} {company.name}", self.style.SUCCESS)
                else:
                    summary['failed'] += 1

            except Exception as e:
                self._log(f"{progress} FAILED processing {company_symbol}: {e}", self.style.ERROR)
                summary['failed'] += 1

        self._log("====== PROCESSING PHASE FINISHED ======", self.style.HTTP_SUCCESS)
        self._log(f"CREATED: {summary['created']}, UPDATED: {summary['updated']}, FAILED: {summary['failed']}", self.style.SUCCESS)

    def handle(self, *args, **options):
        start_time = time.time()
        mode = options['mode']
        self.max_pages = options['max_pages']
        
        self._log(f"SCRIPT STARTED in '{mode.upper()}' mode", self.style.SUCCESS)

        if mode in ['download', 'all']:
            self._run_download_phase()

        if mode in ['process', 'all']:
            self._run_process_phase()

        end_time = time.time()
        duration = end_time - start_time
        self._log(f"SCRIPT FINISHED. Total time: {duration:.2f} seconds", self.style.SUCCESS)
