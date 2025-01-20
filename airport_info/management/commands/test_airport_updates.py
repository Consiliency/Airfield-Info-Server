from django.core.management.base import BaseCommand
from django.conf import settings
from airport_info.models import Airfield
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test airport updates on a few specific airports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--airports',
            nargs='+',
            type=str,
            default=['LAX', 'JFK', 'ORD'],
            help='IATA codes of airports to test (default: LAX, JFK, ORD)'
        )

    def handle(self, *args, **options):
        airport_codes = options['airports']
        self.stdout.write(f"Testing updates for airports: {', '.join(airport_codes)}")

        for code in airport_codes:
            try:
                airport = Airfield.objects.get(iata_code=code)
                self.stdout.write(f"\nTesting {airport.name} ({code}):")
                
                # Print current state
                self.stdout.write(f"  Current timezone: {airport.timezone}")
                self.stdout.write(f"  Last timezone update: {airport.timezone_last_updated}")
                
                # Force timezone update
                self.stdout.write("  Updating timezone...")
                result = airport.update_timezone_if_needed(settings.GOOGLE_MAPS_API_KEY)
                
                # Print results
                airport.refresh_from_db()
                self.stdout.write(
                    self.style.SUCCESS("  ✓ Update successful")
                    if result else
                    self.style.WARNING("  ⚠ No update needed")
                )
                self.stdout.write(f"  New timezone: {airport.timezone}")
                self.stdout.write(f"  New last update: {airport.timezone_last_updated}")
                
            except Airfield.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"\n✗ Airport with code {code} not found")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"\n✗ Error updating {code}: {str(e)}")
                ) 