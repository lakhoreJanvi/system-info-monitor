from django.contrib import admin
from .models import Host, Snapshot, Process

@admin.register(Host)
class HostAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'api_key', 'created_at')

@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ('host', 'collected_at')

@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('snapshot', 'pid', 'name', 'parent_pid', 'cpu_percent', 'memory_percent')
