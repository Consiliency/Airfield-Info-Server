from rest_framework import serializers
from .models import Airfield, TimeZone


class TimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeZone
        fields = [
            'timezone_id',
            'timezone_name',
            'raw_offset',
            'dst_offset',
            'total_offset',
            'last_updated'
        ]


class AirfieldSerializer(serializers.ModelSerializer):
    timezone = TimeZoneSerializer(read_only=True)
    
    class Meta:
        model = Airfield
        fields = [
            'id',
            'ident',
            'iata_code',
            'name',
            'type',
            'latitude',
            'longitude',
            'elevation_ft',
            'continent',
            'iso_country',
            'iso_region',
            'municipality',
            'scheduled_service',
            'gps_code',
            'local_code',
            'home_link',
            'wikipedia_link',
            'keywords',
            'timezone',
            'updated'
        ] 