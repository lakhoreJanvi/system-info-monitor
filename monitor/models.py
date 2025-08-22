from django.db import models
from django.utils import timezone
import secrets

class Host(models.Model):
    hostname = models.CharField(max_length=255, unique=True)
    api_key = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def create_with_key(hostname: str):
        key = secrets.token_urlsafe(32)
        return Host.objects.create(hostname=hostname, api_key = key)
    
    def __str__(self):
        return self.hostname

class Snapshot(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='snapshots')
    collected_at = models.DateTimeField(default=timezone.now, db_index=True)
    system_name = models.CharField(max_length=200, blank=True, null=True)
    os = models.CharField(max_length=200, blank=True, null=True)
    processor = models.CharField(max_length=200, blank=True, null=True)
    cores = models.IntegerField(null=True, blank=True)
    threads = models.IntegerField(null=True, blank=True)
    ram_total = models.FloatField(null=True, blank=True)
    ram_used = models.FloatField(null=True, blank=True)
    ram_available = models.FloatField(null=True, blank=True)
    storage_total = models.FloatField(null=True, blank=True)
    storage_used = models.FloatField(null=True, blank=True)
    storage_free = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.host.hostname} @ {self.collected_at.isoformat()}"
    
class Process(models.Model):
    snapshot = models.ForeignKey(Snapshot, on_delete=models.CASCADE, related_name='processes')
    pid = models.IntegerField(db_index=True)
    name = models.CharField(max_length=300)
    cpu_percent = models.FloatField(default=0.0)
    memory_percent = models.FloatField(default=0.0)
    parent_pid = models.IntegerField(null=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')

    class Meta:
        indexes = [models.Index(fields=['snapshot', 'pid'])]

    def __str__(self):
        return f"{self.name} ({self.pid})"
