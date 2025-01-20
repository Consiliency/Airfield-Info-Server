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
                        alias_attr = type_elem.get('alias')
                        iana_attr = type_elem.get('iana')
                        
                        if alias_attr:
                            # Split the alias attribute into list
                            all_names = alias_attr.split(' ')
                            if all_names:
                                # First name is the canonical ID
                                canonical_id = all_names[0]
                                aliases = set(all_names[1:]) if len(all_names) > 1 else set()
                                
                                # Add IANA names if they differ from canonical and aliases
                                if iana_attr:
                                    iana_names = set(iana_attr.split(' '))
                                    aliases.update(iana_names)
                                
                                # Store both ways for lookup
                                timezone_map[canonical_id] = aliases
                                
                                # Also store mapping for IANA canonical name if different
                                if iana_attr and iana_attr != canonical_id:
                                    iana_canonical = iana_attr.split(' ')[0]
                                    timezone_map[iana_canonical] = {canonical_id}.union(aliases - {iana_canonical})

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

        # Now update timezone records
        for timezone in TimeZone.objects.all():
            try:
                if timezone.timezone_id:
                    # Get the aliases directly from the timezone_map
                    aliases = set()
                    
                    # Check if this timezone_id is a canonical ID
                    if timezone.timezone_id in timezone_map:
                        aliases.update(timezone_map[timezone.timezone_id])
                    else:
                        # Check if this timezone_id is an alias
                        for canonical_id, alias_list in timezone_map.items():
                            if timezone.timezone_id in alias_list:
                                # Add the canonical ID and other aliases
                                aliases.update([canonical_id])
                                aliases.update(alias_list)
                                # Remove self from aliases
                                aliases.discard(timezone.timezone_id)
                                break
                    
                    # Store aliases as space-separated string
                    timezone.aliases = ' '.join(sorted(aliases)) if aliases else ''
                    timezone.save()
                    updated_count += 1
                    self.stdout.write(f"Updated {timezone.timezone_id} with aliases: {aliases}")
                else:
                    skipped_count += 1
                    logger.warning("Skipped timezone with no ID")

            except Exception as e:
                skipped_count += 1
                logger.error(f"Error updating timezone {timezone.timezone_id}: {str(e)}")

        return updated_count, skipped_count

    def handle(self, *args, **options):
        # Imports timezone aliases
        # This is typically run once to set up timezone mappings
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