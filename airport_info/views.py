from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from .models import Airfield
from .serializers import AirfieldSerializer
import logging

logger = logging.getLogger(__name__)

CACHE_TTL = 60 * 60 * 24  # 24 hours

class AirfieldViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for retrieving airport information.
    Supports lookup by IATA code or ICAO code (ident).
    """
    queryset = Airfield.objects.all()
    serializer_class = AirfieldSerializer
    lookup_field = 'id'

    def _log_request_info(self, request, code_type, code):
        """Log detailed request information."""
        info = {
            'remote_addr': request.META.get('REMOTE_ADDR'),
            'origin': request.META.get('HTTP_ORIGIN', 'Unknown'),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
            'code_type': code_type,
            'code': code,
            'method': request.method,
            'path': request.path,
        }
        logger.info(
            f"API Request - {code_type}: {code} | "
            f"Origin: {info['origin']} | "
            f"IP: {info['remote_addr']} | "
            f"Agent: {info['user_agent']}"
        )

    def _update_timezone_if_needed(self, airport, include_timezone):
        """Helper method to update timezone data if needed."""
        if include_timezone:
            should_update = (
                airport.timezone is None or  # No timezone data exists
                airport.timezone.needs_update  # Timezone data is outdated
            )
            if should_update:
                logger.info("Updating timezone information")
                airport.update_timezone(settings.GOOGLE_MAPS_API_KEY)
                airport.refresh_from_db()

    @action(detail=False, methods=['get'])
    def by_iata(self, request):
        """Get airport by IATA code."""
        iata = request.query_params.get('code', '').upper()
        include_timezone = request.query_params.get('include_timezone', '').lower() == 'true'
        
        self._log_request_info(request, 'IATA', iata)
        
        if not iata:
            return Response(
                {'error': 'IATA code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Try to get from cache first
        cache_key = f'airport_iata_{iata}_{include_timezone}'
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for IATA: {iata}")
            return Response(cached_data)

        try:
            airport = get_object_or_404(Airfield, iata_code=iata)
            logger.info(f"Found airport: {airport}")
            
            # Update timezone if needed
            self._update_timezone_if_needed(airport, include_timezone)
            
            serializer = self.get_serializer(airport)
            cache.set(cache_key, serializer.data, CACHE_TTL)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error processing IATA request: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def by_icao(self, request):
        """Get airport by ICAO code (ident)."""
        icao = request.query_params.get('code', '').upper()
        include_timezone = request.query_params.get('include_timezone', '').lower() == 'true'
        
        self._log_request_info(request, 'ICAO', icao)
        
        if not icao:
            return Response(
                {'error': 'ICAO code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Try to get from cache first
        cache_key = f'airport_icao_{icao}_{include_timezone}'
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for ICAO: {icao}")
            return Response(cached_data)

        try:
            airport = get_object_or_404(Airfield, ident=icao)
            logger.info(f"Found airport: {airport}")
            
            # Update timezone if needed
            self._update_timezone_if_needed(airport, include_timezone)
            
            serializer = self.get_serializer(airport)
            cache.set(cache_key, serializer.data, CACHE_TTL)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error processing ICAO request: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
