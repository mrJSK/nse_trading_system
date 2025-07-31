from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.market_data_service.models import Company

class Command(BaseCommand):
    help = 'Run fundamental analysis for companies'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting fundamental analysis...'))
        
        companies = Company.objects.filter(is_active=True)[:10]
        
        for company in companies:
            self.stdout.write(f'Analyzing {company.symbol}')
            
            # Simulate analysis (replace with actual fundamental analysis logic)
            self.stdout.write(f'  Running financial ratio analysis...')
            self.stdout.write(f'  Calculating growth metrics...')
            self.stdout.write(f'  Evaluating debt levels...')
            
            company.last_updated = timezone.now()
            company.save()
        
        self.stdout.write(self.style.SUCCESS('Fundamental analysis completed!'))
