from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def health_check(request):
    """
    GET /health/
    Returns 200 OK — used by Render health probes.
    """
    return Response({'status': 'ok'})
