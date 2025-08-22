# monitor/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.shortcuts import render
from django.utils.dateparse import parse_datetime

from .models import Host, Snapshot, Process
from .permissions import HasValidAgentKey

@api_view(['POST'])
@permission_classes([HasValidAgentKey])
def ingest(request):
    data = request.data or {}
    host = getattr(request, '_ingest_host')  # set by permission
    processes = data.get('processes', [])
    system_info = data.get("system_info", {})
    

    # optional client-supplied timestamp; otherwise now()
    # (We store auto_now; this shows how you'd accept a ts)
    # collected_at = parse_datetime(data.get('collected_at')) if data.get('collected_at') else None

    if not isinstance(processes, list):
        return Response({'detail': 'Invalid processes array'}, status=400)

    with transaction.atomic():
        snapshot = Snapshot.objects.create(
            host=host,
            system_name=system_info.get("system_name", ""),
            os=system_info.get("os", ""),
            processor=system_info.get("processor", ""),
            cores=system_info.get("cores"),
            threads=system_info.get("threads"),
            ram_total=system_info.get("ram_total"),
            ram_used=system_info.get("ram_used"),
            ram_available=system_info.get("ram_available"),
            storage_total=system_info.get("storage_total"),
            storage_used=system_info.get("storage_used"),
            storage_free=system_info.get("storage_free"),
        )

        objs = []
        for p in processes:
            try:
                objs.append(Process(
                    snapshot=snapshot,
                    pid=int(p.get('pid')),
                    name=str(p.get('name') or ''),
                    cpu_percent=float(p.get('cpu_percent') or 0.0),
                    memory_percent=float(p.get('memory_percent') or 0.0),
                    parent_pid=int(p.get('ppid')) if p.get('ppid') is not None else None,
                ))
            except Exception:
                # skip malformed entries
                continue
        Process.objects.bulk_create(objs, batch_size=1000)
        # Wire up parent relations (only within this snapshot)
        pid_map = {pr.pid: pr.id for pr in Process.objects.filter(snapshot=snapshot).only('id','pid')}
        updates = []
        for pr in Process.objects.filter(snapshot=snapshot).only('id','parent_pid'):
            if pr.parent_pid in pid_map:
                pr.parent_id = pid_map[pr.parent_pid]
                updates.append(pr)
        if updates:
            Process.objects.bulk_update(updates, ['parent'])

    return Response({'snapshot_id': snapshot.id, 'host': host.hostname, 'collected_at': snapshot.collected_at.isoformat()}, status=201)

@api_view(['GET'])
def hosts(request):
    items = list(Host.objects.order_by('hostname').values_list('hostname', flat=True))
    return Response({'hosts': items})

def _build_tree(snapshot):
    # return nested tree for the latest snapshot
    procs = list(Process.objects.filter(snapshot=snapshot).values('pid','name','cpu_percent','memory_percent','parent_pid'))
    nodes = {p['pid']: {**p, 'children': []} for p in procs}
    roots = []
    for p in procs:
        node = nodes[p['pid']]
        parent_pid = p['parent_pid']
        if parent_pid and parent_pid in nodes:
            nodes[parent_pid]['children'].append(node)
        else:
            roots.append(node)
    return roots

@api_view(['GET'])
def latest_snapshot(request):
    hostname = request.GET.get('hostname')
    if not hostname:
        return Response({'detail': 'hostname query param is required'}, status=400)
    try:
        host = Host.objects.get(hostname=hostname)
    except Host.DoesNotExist:
        return Response({'detail': 'Unknown host'}, status=404)
    snap = host.snapshots.order_by('-collected_at').first()
    if not snap:
        return Response({'detail': 'No snapshots for host'}, status=404)
    tree = _build_tree(snap)
    return Response({
        'hostname': host.hostname,
        'snapshot_id': snap.id,
        'collected_at': snap.collected_at.isoformat(),
        'system_info': {
            "system_name": snap.system_name,
            "os": snap.os,
            "processor": snap.processor,
            "cores": snap.cores,
            "threads": snap.threads,
            "ram_total": snap.ram_total,
            "ram_used": snap.ram_used,
            "ram_available": snap.ram_available,
            "storage_total": snap.storage_total,
            "storage_used": snap.storage_used,
            "storage_free": snap.storage_free,
        },
        'process_tree': tree
    })

# Simple homepage to serve the frontend
def index(request):
    return render(request, 'index.html')
