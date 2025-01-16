from django.core.management.base import BaseCommand
from django.conf import settings
from airport_info.models import Airfield
import logging
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates timezone information for all airports using Google Maps API'

    def handle(self, *args, **options):
        airports = Airfield.objects.all()
        total = airports.count()
        updated = 0
        failed = 0

        self.stdout.write(f"Updating timezones for {total} airports...")

        for i, airport in enumerate(airports, 1):
            try:
                if airport.update_timezone(settings.GOOGLE_MAPS_API_KEY):
                    updated += 1
                else:
                    failed += 1
                
                # Print progress every 100 airports
                if i % 100 == 0:
                    self.stdout.write(f"Processed {i}/{total} airports...")
                
                # Sleep briefly to avoid hitting API rate limits
                time.sleep(0.1)  # 100ms delay between requests
                
            except Exception as e:
                failed += 1
                logger.error(f"Error updating timezone for {airport}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(
            f"Finished updating timezones. "
            f"Updated: {updated}, Failed: {failed}, Total: {total}"
        )) 