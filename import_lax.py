import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from airport_info.models import Airfield, TimeZone

# Delete existing LAX airport if it exists
Airfield.objects.filter(iata_code="LAX").delete()

# Create LAX airport timezone
timezone = TimeZone.objects.create(
    raw_offset=-28800,  # -8 hours in seconds
    dst_offset=3600,    # 1 hour in seconds
    timezone_id="America/Los_Angeles",
    timezone_name="Pacific Time",
    aliases="PT PST PDT"
)

# Create new LAX airport
lax = Airfield.objects.create(
    id="KLAX",
    ident="KLAX",
    iata_code="LAX", 
    name="Los Angeles International Airport",
    latitude=33.9425,
    longitude=-118.408056,
    elevation_ft=125,
    type="large_airport",
    municipality="Los Angeles",
    iso_region="US-CA",
    iso_country="US",
    timezone=timezone
)

print(f"Created {lax.name} ({lax.iata_code})") 