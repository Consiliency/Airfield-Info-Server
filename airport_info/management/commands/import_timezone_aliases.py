import requests
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from django.utils import timezone
from airport_info.models import TimeZone, DataSource
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import timezone aliases from Unicode CLDR data'
    
    TIMEZONE_URL = 'https://raw.githubusercontent.com/unicode-org/cldr/main/common/bcp47/timezone.xml'
    UPDATE_INTERVAL = 14  # days

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if the file was recently downloaded'
        )

    def download_timezone_data(self):
        """Download the timezone XML file and return its content."""
        # Get or create data source record
        data_source, _ = DataSource.objects.get_or_create(
            url=self.TIMEZONE_URL,
            defaults={'last_download': timezone.now() - timezone.timedelta(days=self.UPDATE_INTERVAL + 1)}
        )

        # Make the request without using cached headers for this run
        try:
            response = requests.get(self.TIMEZONE_URL)
            if response.status_code != 200:
                raise Exception(f'Failed to download timezone data: {response.status_code}')

            # Save the new ETag and Last-Modified headers
            data_source.last_etag = response.headers.get('ETag')
            data_source.last_modified = response.headers.get('Last-Modified')
            data_source.last_download = timezone.now()
            data_source.save()

            return response.text

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error downloading timezone data: {str(e)}')
            )
            return None

    def parse_timezone_aliases(self, xml_content):
        """Parse the XML content and extract timezone aliases."""
        try:
            root = ET.fromstring(xml_content)
            timezone_map = {}

            # Find the timezone keyword
            for keyword in root.findall(".//key"):
                if keyword.get('name') == 'tz':
                    # Process each timezone type
                    for type_elem in keyword.findall('.//type'):
                        alias = type_elem.get('alias')
                        if alias:
                            # The alias attribute contains the canonical timezone ID and aliases
                            all_names = alias.split(' ')
                            if all_names:
                                # Get the canonical ID (first name) and any additional aliases
                                canonical_id = all_names[0]
                                aliases = all_names[1:] if len(all_names) > 1 else []
                                
                                # Add any IANA preferred names
                                iana = type_elem.get('iana')
                                if iana:
                                    aliases.extend([a for a in iana.split(' ') if a not in aliases])
                                
                                # Store in map
                                timezone_map[canonical_id] = aliases

            return timezone_map

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error parsing timezone XML: {str(e)}')
            )
            return None

    def update_timezone_aliases(self, timezone_map):
        """Update timezone records with alias information."""
        updated_count = 0
        skipped_count = 0

        # First, create a reverse lookup from aliases to canonical IDs
        reverse_map = {}
        canonical_aliases = {}  # Store all aliases for each canonical ID
        for canonical_id, aliases in timezone_map.items():
            reverse_map[canonical_id] = canonical_id  # Map canonical to itself
            canonical_aliases[canonical_id] = set([canonical_id])  # Include canonical ID in its own aliases
            for alias in aliases:
                reverse_map[alias] = canonical_id
                canonical_aliases[canonical_id].add(alias)

        # Now update timezone records
        for timezone in TimeZone.objects.all():
            try:
                if timezone.timezone_id:
                    # Try to find the canonical ID for this timezone
                    canonical_id = reverse_map.get(timezone.timezone_id)
                    if canonical_id:
                        # Get all aliases for the canonical ID
                        aliases = canonical_aliases.get(canonical_id, set())
                        # Remove the current timezone_id from aliases to avoid redundancy
                        aliases.discard(timezone.timezone_id)
                        # Store aliases as space-separated string
                        timezone.aliases = ' '.join(sorted(aliases)) if aliases else ''
                        timezone.save()
                        updated_count += 1
                        self.stdout.write(f"Updated {timezone.timezone_id} with aliases: {aliases}")
                    else:
                        skipped_count += 1
                        logger.warning(f"No canonical ID found for timezone: {timezone.timezone_id}")
                else:
                    skipped_count += 1
                    logger.warning("Skipped timezone with no ID")

            except Exception as e:
                skipped_count += 1
                logger.error(f"Error updating timezone {timezone.timezone_id}: {str(e)}")

        return updated_count, skipped_count

    def handle(self, *args, **options):
        self.force = options['force']
        
        # Download the timezone data
        xml_content = self.download_timezone_data()
        if not xml_content:
            return

        # Parse the timezone aliases
        timezone_map = self.parse_timezone_aliases(xml_content)
        if not timezone_map:
            return

        # Update the timezone records
        updated_count, skipped_count = self.update_timezone_aliases(timezone_map)

        self.stdout.write(
            self.style.SUCCESS(
                f'Timezone update completed: {updated_count} updated, '
                f'{skipped_count} skipped'
            )
        ) 