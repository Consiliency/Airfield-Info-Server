from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.shortcuts import get_object_or_404
from .models import Airfield
from .serializers import AirfieldSerializer
import logging
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

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
        logger.info(f"Checking if timezone update needed for {airport}")
        logger.info(f"include_timezone parameter: {include_timezone}")
        
        if not include_timezone:
            logger.debug("Timezone update skipped - include_timezone=false")
            return
            
        needs_update = False
        reason = ""
        
        if airport.timezone is None:
            needs_update = True
            reason = "no timezone data exists"
        elif (airport.timezone.timezone_id == "UTC" or 
              airport.timezone.timezone_name == "Coordinated Universal Time"):
            needs_update = True
            reason = f"timezone is UTC (id: {airport.timezone.timezone_id}, name: {airport.timezone.timezone_name})"
        elif (airport.timezone.raw_offset is None or
              airport.timezone.dst_offset is None or
              airport.timezone.timezone_id is None or
              airport.timezone.timezone_name is None):
            needs_update = True
            reason = "incomplete timezone data"
        elif (airport.timezone.last_updated is None or
              airport.timezone.last_updated < timezone.now() - timedelta(days=90)):
            needs_update = True
            reason = f"timezone data is old (last_updated: {airport.timezone.last_updated})"
        
        logger.info(f"Needs update: {needs_update}, Reason: {reason}")
        
        if needs_update:
            logger.info(f"Updating timezone for {airport} - Reason: {reason}")
            logger.info(f"Current timezone data: {airport.timezone.__dict__ if airport.timezone else None}")
            
            result = airport.update_timezone(settings.GOOGLE_MAPS_API_KEY)
            logger.info(f"Update timezone result: {result.__dict__ if result else 'Failed'}")
            
            airport.refresh_from_db()
            logger.info(f"After refresh - timezone data: {airport.timezone.__dict__ if airport.timezone else None}")
        else:
            logger.info(f"No timezone update needed for {airport}")

    @action(detail=False, methods=['get'])
    def by_iata(self, request):
        """Get airport by IATA code."""
        iata = request.query_params.get('code', '').upper()
        include_timezone = request.query_params.get('include_timezone', '').lower() == 'true'
        logger.info(f"Request params - code: {iata}, include_timezone: {include_timezone}")
        
        self._log_request_info(request, 'IATA', iata)
        
        if not iata:
            return Response(
                {'error': 'IATA code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            airport = get_object_or_404(Airfield, iata_code=iata)
            logger.info(f"Found airport: {airport}")
            
            # Update timezone if requested
            if include_timezone:
                logger.info(f"Updating timezone for {airport}")
                if airport.timezone:
                    logger.info(f"Current timezone data: {airport.timezone.timezone_id}, {airport.timezone.timezone_name}")
                self._update_timezone_if_needed(airport, include_timezone)
                logger.info(f"After update - timezone data: {airport.timezone.timezone_id if airport.timezone else 'None'}")
            
            serializer = self.get_serializer(airport)
            response_data = serializer.data
            logger.info(f"Response data for {iata}: {response_data.get('timezone', {})}")
            
            return Response(response_data)
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

        try:
            airport = get_object_or_404(Airfield, ident=icao)
            logger.info(f"Found airport: {airport}")
            
            # Update timezone if needed
            if include_timezone:
                logger.info(f"Updating timezone for {airport}")
                if airport.timezone:
                    logger.info(f"Current timezone data: {airport.timezone.timezone_id}, {airport.timezone.timezone_name}")
                self._update_timezone_if_needed(airport, include_timezone)
                logger.info(f"After update - timezone data: {airport.timezone.timezone_id if airport.timezone else 'None'}")
            
            serializer = self.get_serializer(airport)
            response_data = serializer.data
            logger.info(f"Response data for {icao}: {response_data.get('timezone', {})}")
            
            return Response(response_data)
        except Exception as e:
            logger.error(f"Error processing ICAO request: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
