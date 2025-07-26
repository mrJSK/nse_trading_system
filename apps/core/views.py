from django.http import JsonResponse

def health_check_view(request):
    """
    A simple health check endpoint for monitoring.
    Returns a JSON response indicating the service is healthy.
    """
    return JsonResponse({'status': 'healthy'})