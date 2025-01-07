import csv
import requests
import tempfile
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from airport_info.models import Airfield, TimeZone, DataSource


class Command(BaseCommand):
    help = 'Import airports from the OurAirports CSV file'
    
    DEFAULT_URL = 'https://davidmegginson.github.io/ourairports-data/airports.csv'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='URL of the CSV file (default: OurAirports data)',
            default=self.DEFAULT_URL
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if the file was recently downloaded'
        )

    def download_file(self, url):
        """Download the CSV file and return its path."""
        # Get or create data source record
        data_source, _ = DataSource.objects.get_or_create(
            url=url,
            defaults={'last_download': timezone.now()}
        )

        # Check if we need to update
        if not data_source.needs_update and not self.force:
            self.stdout.write(
                self.style.WARNING(
                    'Data was updated less than 7 days ago. Use --force to override.'
                )
            )
            return None

        # Make the request with existing headers if available
        headers = {}
        if data_source.last_etag:
            headers['If-None-Match'] = data_source.last_etag
        if data_source.last_modified:
            headers['If-Modified-Since'] = data_source.last_modified

        response = requests.get(url, headers=headers, stream=True)

        # Check if the file has been modified
        if response.status_code == 304:  # Not Modified
            self.stdout.write(self.style.SUCCESS('Data is up to date'))
            return None

        if response.status_code != 200:
            raise Exception(f'Failed to download file: {response.status_code}')

        # Save the new ETag and Last-Modified headers
        data_source.last_etag = response.headers.get('ETag')
        data_source.last_modified = response.headers.get('Last-Modified')
        data_source.save()

        # Save the file to a temporary location
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        temp_file.close()

        return temp_file.name

    def handle(self, *args, **options):
        self.force = options['force']
        url = options['url']
        
        try:
            # Download the file
            csv_file = self.download_file(url)
            if not csv_file:
                return

            # Get or create a default timezone (UTC)
            default_timezone, _ = TimeZone.objects.get_or_create(
                name='UTC',
                defaults={'offset': 0, 'uses_dst': False}
            )

            created_count = 0
            updated_count = 0
            skipped_count = 0
            
            try:
                with open(csv_file, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    
                    with transaction.atomic():
                        for row in reader:
                            # Convert 'yes'/'no' to boolean
                            scheduled_service = row['scheduled_service'].lower() == 'yes'
                            
                            # Prepare the airport data
                            airport_data = {
                                'ident': row['ident'],
                                'type': row['type'],
                                'name': row['name'],
                                'latitude': float(row['latitude_deg'] or 0),
                                'longitude': float(row['longitude_deg'] or 0),
                                'elevation_ft': float(row['elevation_ft'] or 0) if row['elevation_ft'] else None,
                                'continent': row['continent'] or None,
                                'iso_country': row['iso_country'],
                                'iso_region': row['iso_region'] or None,
                                'municipality': row['municipality'] or None,
                                'scheduled_service': scheduled_service,
                                'gps_code': row['gps_code'] or None,
                                'iata_code': row['iata_code'] or None,
                                'local_code': row['local_code'] or None,
                                'home_link': row['home_link'] or None,
                                'wikipedia_link': row['wikipedia_link'] or None,
                                'keywords': row['keywords'] or None,
                                'timezone': default_timezone,
                            }

                            try:
                                airport, created = Airfield.objects.update_or_create(
                                    id=row['id'],
                                    defaults=airport_data
                                )
                                
                                if created:
                                    created_count += 1
                                else:
                                    updated_count += 1
                                    
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f'Error processing airport {row["id"]}: {str(e)}'
                                    )
                                )
                                skipped_count += 1
                                continue

            finally:
                # Clean up the temporary file
                Path(csv_file).unlink()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'Import completed: {created_count} created, '
                f'{updated_count} updated, {skipped_count} skipped'
            )
        ) 