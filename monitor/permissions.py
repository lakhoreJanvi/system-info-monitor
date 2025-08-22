# monitor/permissions.py
from rest_framework.permissions import BasePermission
from .models import Host

class HasValidAgentKey(BasePermission):
    """
    For POST /ingest/: require X-API-Key and a hostname in the payload.
    """
    def has_permission(self, request, view):
        if request.method != 'POST':
            return True
        api_key = request.headers.get('X-API-Key')
        hostname = (request.data or {}).get('hostname')
        if not api_key or not hostname:
            return False
        try:
            host = Host.objects.get(hostname=hostname, api_key=api_key)
        except Host.DoesNotExist:
            return False
        # Stash host for the view (so we don’t re-query)
        request._ingest_host = host
        return True
