from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.market_data_service.models import Company
import random

class Command(BaseCommand):
    help = 'Collect market data from Fyers API'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting market data collection...'))
        
        companies = Company.objects.filter(is_active=True, is_tradeable=True)[:5]
        
        for company in companies:
            self.stdout.write(f'Collecting data for {company.symbol}')
            
            # Simulate data collection (replace with actual Fyers API calls)
            mock_price = random.uniform(100, 5000)
            mock_volume = random.randint(1000, 100000)
            
            self.stdout.write(f'  Price: ₹{mock_price:.2f}, Volume: {mock_volume}')
            
            # Update company data
            company.last_updated = timezone.now()
            company.save()
        
        self.stdout.write(self.style.SUCCESS('Market data collection completed!'))
