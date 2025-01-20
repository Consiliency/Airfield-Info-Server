from django.core.management.base import BaseCommand
from django.conf import settings
from airport_info.models import Airfield
import logging
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates timezone information for specific airports using Google Maps API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'airport_ids',
            nargs='+',
            type=int,
            help='IDs of airports to update'
        )

    def handle(self, *args, **options):
        airports = Airfield.objects.filter(id__in=options['airport_ids'])
        
        for airport in airports:
            if airport.needs_timezone_update():
                try:
                    if airport.update_timezone(settings.GOOGLE_MAPS_API_KEY):
                        self.stdout.write(f"Updated timezone for {airport}")
                except Exception as e:
                    logger.error(f"Error updating timezone for {airport}: {str(e)}") 