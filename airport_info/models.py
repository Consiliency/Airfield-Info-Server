from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta


class DataSource(models.Model):
    url = models.URLField(max_length=500)
    last_download = models.DateTimeField(auto_now=True)
    last_etag = models.CharField(max_length=100, null=True, blank=True)
    last_modified = models.CharField(max_length=100, null=True, blank=True)

    @property
    def needs_update(self):
        return self.last_download < timezone.now() - timedelta(days=7)

    def __str__(self):
        return f"Airport data source (last updated: {self.last_download})"


class TimeZone(models.Model):
    name = models.CharField(max_length=100)
    raw_offset = models.IntegerField(
        validators=[MinValueValidator(-43200), MaxValueValidator(43200)],  # Seconds from UTC
        help_text="Raw offset from UTC in seconds",
        null=True,
        blank=True
    )
    dst_offset = models.IntegerField(
        validators=[MinValueValidator(-43200), MaxValueValidator(43200)],  # Seconds from UTC
        help_text="DST offset from UTC in seconds",
        null=True,
        blank=True
    )
    timezone_id = models.CharField(max_length=100, null=True, blank=True)  # e.g., "America/Los_Angeles"
    timezone_name = models.CharField(max_length=100, null=True, blank=True)  # e.g., "Pacific Daylight Time"
    last_updated = models.DateTimeField(null=True, blank=True)

    @property
    def needs_update(self):
        if not self.last_updated:
            return True
        return self.last_updated < timezone.now() - timedelta(days=90)  # 3 months

    @property
    def total_offset(self):
        """Total offset in hours including DST if applicable."""
        if self.raw_offset is None:
            return 0
        total_seconds = self.raw_offset + (self.dst_offset or 0)
        return total_seconds / 3600

    def __str__(self):
        if self.timezone_id:
            return f"{self.timezone_id} (UTC{'+' if self.total_offset >= 0 else ''}{self.total_offset})"
        return f"UTC{'+' if self.total_offset >= 0 else ''}{self.total_offset}"

    class Meta:
        ordering = ['name']


class Airfield(models.Model):
    AIRPORT_TYPES = [
        ('balloonport', 'Balloon Port'),
        ('closed', 'Closed'),
        ('heliport', 'Heliport'),
        ('large_airport', 'Large Airport'),
        ('medium_airport', 'Medium Airport'),
        ('seaplane_base', 'Seaplane Base'),
        ('small_airport', 'Small Airport'),
    ]

    # Existing fields that match CSV columns
    id = models.CharField(max_length=50, primary_key=True)  # matches 'id'
    iata_code = models.CharField(max_length=3, unique=True, null=True, blank=True)  # renamed from iata_id
    name = models.CharField(max_length=200)  # matches 'name'
    latitude = models.DecimalField(  # matches 'latitude_deg'
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.DecimalField(  # matches 'longitude_deg'
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    municipality = models.CharField(max_length=100, null=True, blank=True)  # renamed from city
    iso_country = models.CharField(max_length=2)  # matches 'iso_country'

    # New fields from CSV
    ident = models.CharField(max_length=10, default='')
    type = models.CharField(max_length=20, choices=AIRPORT_TYPES, default='small_airport')
    elevation_ft = models.FloatField(null=True, blank=True)
    continent = models.CharField(max_length=2, null=True, blank=True)
    iso_region = models.CharField(max_length=10, null=True, blank=True)
    scheduled_service = models.BooleanField(default=False)
    gps_code = models.CharField(max_length=10, null=True, blank=True)
    local_code = models.CharField(max_length=10, null=True, blank=True)
    home_link = models.URLField(max_length=500, null=True, blank=True)
    wikipedia_link = models.URLField(max_length=500, null=True, blank=True)
    keywords = models.TextField(null=True, blank=True)

    # Existing fields we want to keep
    timezone = models.ForeignKey(
        TimeZone,
        on_delete=models.PROTECT,
        related_name='airfields',
        null=True,
        blank=True
    )
    updated = models.DateTimeField(auto_now=True)

    def update_timezone(self, api_key):
        """Update timezone information using Google Maps API if needed."""
        if self.timezone and not self.timezone.needs_update:
            return self.timezone

        import requests
        import time

        timestamp = int(time.time())
        url = (
            f"https://maps.googleapis.com/maps/api/timezone/json"
            f"?location={self.latitude},{self.longitude}"
            f"&timestamp={timestamp}"
            f"&key={api_key}"
        )

        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK':
                    timezone_obj, created = TimeZone.objects.get_or_create(
                        timezone_id=data['timeZoneId'],
                        defaults={
                            'name': data['timeZoneId'],
                            'raw_offset': data['rawOffset'],
                            'dst_offset': data['dstOffset'],
                            'timezone_name': data['timeZoneName'],
                            'last_updated': timezone.now()
                        }
                    )
                    if not created:
                        timezone_obj.raw_offset = data['rawOffset']
                        timezone_obj.dst_offset = data['dstOffset']
                        timezone_obj.timezone_name = data['timeZoneName']
                        timezone_obj.last_updated = timezone.now()
                        timezone_obj.save()
                    
                    self.timezone = timezone_obj
                    self.save()
                    return timezone_obj
        except Exception as e:
            print(f"Error updating timezone for {self}: {str(e)}")
        
        return None

    def __str__(self):
        return f"{self.name} ({self.iata_code or self.ident})"

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['iata_code']),
            models.Index(fields=['ident']),
            models.Index(fields=['municipality']),
            models.Index(fields=['iso_country']),
            models.Index(fields=['iso_region']),
            models.Index(fields=['type']),
            models.Index(fields=['updated']),
        ]