from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from licensing.models import Service


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """API health check endpoint"""
    return Response({
        'status': 'healthy',
        'version': '1.0.0',
        'message': 'MetaTask API is running'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def services_list(request):
    """List available services"""
    services = Service.objects.filter(is_active=True).order_by('sort_order', 'name')
    return Response([
        {
            'id': service.id,
            'name': service.name,
            'slug': service.slug,
            'description': service.description,
            'version': service.version,
            'icon': service.icon,
            'color': service.color,
        }
        for service in services
    ])
