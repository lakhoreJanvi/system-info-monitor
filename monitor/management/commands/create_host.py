# monitor/management/commands/create_host.py
from django.core.management.base import BaseCommand
from monitor.models import Host

class Command(BaseCommand):
    help = "Create a host and print its API key"

    def add_arguments(self, parser):
        parser.add_argument('--hostname', required=True)

    def handle(self, *args, **opts):
        hostname = opts['hostname']
        host = Host.create_with_key(hostname)
        self.stdout.write(self.style.SUCCESS(f"Hostname: {host.hostname}"))
        self.stdout.write(self.style.SUCCESS(f"API Key:  {host.api_key}"))
