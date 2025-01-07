from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.shortcuts import get_object_or_404
from .models import Airfield
from .serializers import AirfieldSerializer
import logging

logger = logging.getLogger(__name__)


class AirfieldViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for retrieving airport information.
    Supports lookup by IATA code or ICAO code (ident).
    """
    queryset = Airfield.objects.all()
    serializer_class = AirfieldSerializer
    lookup_field = 'id'

    @action(detail=False, methods=['get'])
    def by_iata(self, request):
        """Get airport by IATA code."""
        iata = request.query_params.get('code', '').upper()
        logger.info(f"Searching for IATA code: {iata}")
        
        if not iata:
            return Response(
                {'error': 'IATA code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            airport = get_object_or_404(Airfield, iata_code=iata)
            logger.info(f"Found airport: {airport}")
            
            # Update timezone if requested
            if request.query_params.get('include_timezone', '').lower() == 'true':
                logger.info("Updating timezone information")
                airport.update_timezone(settings.GOOGLE_MAPS_API_KEY)
                # Refresh from database to get updated timezone
                airport.refresh_from_db()
            
            serializer = self.get_serializer(airport)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def by_icao(self, request):
        """Get airport by ICAO code (ident)."""
        icao = request.query_params.get('code', '').upper()
        logger.info(f"Searching for ICAO code: {icao}")
        
        if not icao:
            return Response(
                {'error': 'ICAO code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            airport = get_object_or_404(Airfield, ident=icao)
            logger.info(f"Found airport: {airport}")
            
            # Update timezone if requested
            if request.query_params.get('include_timezone', '').lower() == 'true':
                logger.info("Updating timezone information")
                airport.update_timezone(settings.GOOGLE_MAPS_API_KEY)
                # Refresh from database to get updated timezone
                airport.refresh_from_db()
            
            serializer = self.get_serializer(airport)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
