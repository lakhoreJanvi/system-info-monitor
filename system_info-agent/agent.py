import json
import os
import time
import socket
import platform
import psutil
import requests
from pathlib import Path

def load_config():
    cfg_path = Path(__file__).with_name("config.json")
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Fallback: env vars
    return {
        "backend_url": os.getenv("BACKEND_URL", "http://127.0.0.1:8000"),
        "api_key": os.getenv("API_KEY", ""),
        "hostname": os.getenv("HOSTNAME", ""),
    }

def get_hostname(cfg):
    return cfg.get("hostname") or socket.gethostname() or platform.node()

def collect_processes():
    # Warm-up CPU counters so next read isn't 0.0
    for p in psutil.process_iter(['pid']):
        try:
            p.cpu_percent(None)
        except Exception:
            pass
    time.sleep(0.2)

    procs = []
    for p in psutil.process_iter(['pid','ppid','name','cpu_percent','memory_percent']):
        try:
            info = p.info
            procs.append({
                "pid": int(info.get('pid', 0)),
                "ppid": int(info.get('ppid', 0)) if info.get('ppid') is not None else None,
                "name": str(info.get('name') or ''),
                "cpu_percent": float(info.get('cpu_percent') or 0.0),
                "memory_percent": float(info.get('memory_percent') or 0.0),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue
    return procs

def collect_system_info():
    du = psutil.disk_usage("/")
    return {
        "system_name": platform.node(),
        "hostname": platform.node(),
        "os": platform.system() + " " + platform.release(),
        "processor": platform.processor(),
        "cores": psutil.cpu_count(logical=False),
        "threads": psutil.cpu_count(logical=True),
        "ram_total": round(psutil.virtual_memory().total / (1024**3), 2),
        "ram_used": round(psutil.virtual_memory().used / (1024**3), 2),
        "ram_available": round(psutil.virtual_memory().available / (1024**3), 2),
        "storage_total": round(du.total / (1024**3), 2),  
        "storage_used": round(du.used / (1024**3), 2),
        "storage_free": round(du.free / (1024**3), 2)
    }

def post_payload(backend_url, api_key, hostname, processes):
    url = backend_url.rstrip("/") + "/api/v1/ingest/"
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}
    payload = {"hostname": hostname, "system_info": collect_system_info(), "processes": processes}
    print("DEBUG PAYLOAD >>>")
    print(json.dumps(payload, indent=2)) 
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def main():
    cfg = load_config()
    backend_url = cfg["backend_url"]
    api_key = cfg["api_key"]
    hostname = get_hostname(cfg)
    if not api_key:
        print("ERROR: Missing API key. Set in config.json or API_KEY env.")
        return 1
    processes = collect_processes()
    try:
        resp = post_payload(backend_url, api_key, hostname, processes)
        print("Ingest OK:", resp)
    except Exception as e:
        print("Ingest failed:", e)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
