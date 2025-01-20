from django.core.management.base import BaseCommand
from django.test import Client, override_settings
from airport_info.models import Airfield
import json

class Command(BaseCommand):
    help = 'Test timezone update for an airport that has never been requested'

    def add_arguments(self, parser):
        parser.add_argument(
            '--code',
            type=str,
            default='YYZ',
            help='IATA code of airport to test (default: YYZ)'
        )

    @override_settings(ALLOWED_HOSTS=['testserver'])
    def handle(self, *args, **options):
        code = options['code']
        client = Client()
        
        # Show initial state
        try:
            airport = Airfield.objects.get(iata_code=code)
            self.stdout.write(f"\nInitial state for {airport.name} ({code}):")
            self.stdout.write("-" * 40)
            self.stdout.write(f"Current timezone: {airport.timezone}")
            self.stdout.write(f"Last timezone update: {airport.timezone_last_updated}")
        except Airfield.DoesNotExist:
            self.stdout.write(f"\nAirport {code} not found in database")
            return
        
        # Make the API request
        self.stdout.write(f"\nMaking API request for {code}...")
        response = client.get('/api/airports/by_iata/', {
            'code': code, 
            'include_timezone': 'true'
        })
        
        # Show final state
        airport.refresh_from_db()
        self.stdout.write(f"\nFinal state for {airport.name} ({code}):")
        self.stdout.write("-" * 40)
        self.stdout.write(f"Current timezone: {airport.timezone}")
        self.stdout.write(f"Last timezone update: {airport.timezone_last_updated}")
        
        # Show full API response
        self.stdout.write("\nAPI Response:")
        self.stdout.write("-" * 40)
        try:
            content = response.json()
        except ValueError:
            content = response.content.decode('utf-8')
        self.stdout.write(
            json.dumps(content, indent=2) 
            if isinstance(content, (dict, list)) 
            else content
        ) 