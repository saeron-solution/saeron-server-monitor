#!/usr/bin/env python3
import json
from pathlib import Path

OUT = Path("grafana/dashboards")
OUT.mkdir(parents=True, exist_ok=True)

PROM = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}


def prom_target(expr, ref="A", legend=""):
    return {
        "refId": ref,
        "expr": expr,
        "legendFormat": legend,
    }


def loki_target(expr, ref="A"):
    return {
        "refId": ref,
        "expr": expr,
    }


def field_config(unit=None, min_value=None, max_value=None, decimals=None):
    defaults = {
        "mappings": [],
        "thresholds": {
            "mode": "absolute",
            "steps": [
                {"color": "green", "value": None},
                {"color": "yellow", "value": 70},
                {"color": "red", "value": 90},
            ],
        },
    }
    if unit:
        defaults["unit"] = unit
    if min_value is not None:
        defaults["min"] = min_value
    if max_value is not None:
        defaults["max"] = max_value
    if decimals is not None:
        defaults["decimals"] = decimals

    return {
        "defaults": defaults,
        "overrides": [],
    }


def stat_options():
    return {
        "reduceOptions": {
            "calcs": ["lastNotNull"],
            "fields": "",
            "values": False,
        },
        "orientation": "auto",
        "textMode": "auto",
        "colorMode": "background",
        "graphMode": "area",
        "justifyMode": "auto",
    }


def timeseries_options():
    return {
        "legend": {
            "displayMode": "list",
            "placement": "bottom",
            "calcs": [],
        },
        "tooltip": {
            "mode": "multi",
            "sort": "none",
        },
    }


def panel(
    panel_id,
    title,
    panel_type,
    x,
    y,
    w,
    h,
    targets,
    datasource=PROM,
    unit=None,
    min_value=None,
    max_value=None,
    decimals=None,
    repeat=None,
    repeat_direction=None,
    max_per_row=None,
):
    p = {
        "id": panel_id,
        "type": panel_type,
        "title": title,
        "datasource": datasource,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": field_config(unit, min_value, max_value, decimals),
        "options": stat_options() if panel_type in ("stat", "gauge") else timeseries_options(),
    }

    if repeat:
        p["repeat"] = repeat
        p["repeatDirection"] = repeat_direction or "h"
        p["maxPerRow"] = max_per_row or 5

    return p


def dashboard_base(uid, title, panels, variables=None, time_from="now-1h"):
    return {
        "id": None,
        "uid": uid,
        "title": title,
        "tags": ["server-observability", "prometheus", "loki"],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 1,
        "refresh": "15s",
        "editable": True,
        "graphTooltip": 0,
        "time": {
            "from": time_from,
            "to": "now",
        },
        "timepicker": {},
        "templating": {
            "list": variables or [],
        },
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": {
                        "type": "grafana",
                        "uid": "-- Grafana --",
                    },
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard",
                }
            ]
        },
        "links": [],
        "panels": panels,
    }


host_variable = {
    "name": "host",
    "label": "Host",
    "type": "query",
    "datasource": PROM,
    "query": "label_values(node_uname_info{job=\"node_exporter\"}, host)",
    "definition": "label_values(node_uname_info{job=\"node_exporter\"}, host)",
    "refresh": 1,
    "sort": 1,
    "multi": True,
    "includeAll": True,
    "hide": 0,
    "current": {
        "selected": True,
        "text": "All",
        "value": "$__all",
    },
    "options": [],
}


# ---------------------------------------------------------------------
# Dashboard 1: Fleet Overview
# ---------------------------------------------------------------------

fleet_panels = [
    panel(
        1,
        "CPU Usage by Host",
        "timeseries",
        0,
        0,
        12,
        8,
        [
            prom_target(
                '100 * (1 - avg by (host) (rate(node_cpu_seconds_total{job="node_exporter",mode="idle",host=~"$host"}[$__rate_interval])))',
                legend="{{host}}",
            )
        ],
        unit="percent",
        min_value=0,
        max_value=100,
        decimals=1,
    ),
    panel(
        2,
        "Memory Usage by Host",
        "timeseries",
        12,
        0,
        12,
        8,
        [
            prom_target(
                '100 * (1 - avg by (host) (node_memory_MemAvailable_bytes{job="node_exporter",host=~"$host"} / node_memory_MemTotal_bytes{job="node_exporter",host=~"$host"}))',
                legend="{{host}}",
            )
        ],
        unit="percent",
        min_value=0,
        max_value=100,
        decimals=1,
    ),
    panel(
        3,
        "Host Up",
        "stat",
        0,
        8,
        6,
        5,
        [
            prom_target(
                'up{job="node_exporter",host=~"$host"}',
                legend="{{host}}",
            )
        ],
        unit="short",
        min_value=0,
        max_value=1,
        decimals=0,
    ),
    panel(
        4,
        "Load 1m by Host",
        "timeseries",
        6,
        8,
        9,
        5,
        [
            prom_target(
                'node_load1{job="node_exporter",host=~"$host"}',
                legend="{{host}}",
            )
        ],
        unit="short",
        decimals=2,
    ),
    panel(
        5,
        "Root Disk Usage by Host",
        "timeseries",
        15,
        8,
        9,
        5,
        [
            prom_target(
                '100 * (1 - (node_filesystem_avail_bytes{job="node_exporter",host=~"$host",mountpoint="/",fstype!~"tmpfs|overlay|squashfs|fuse.lxcfs"} / node_filesystem_size_bytes{job="node_exporter",host=~"$host",mountpoint="/",fstype!~"tmpfs|overlay|squashfs|fuse.lxcfs"}))',
                legend="{{host}} /",
            )
        ],
        unit="percent",
        min_value=0,
        max_value=100,
        decimals=1,
    ),
    panel(
        6,
        "CPU Card - $host",
        "stat",
        0,
        13,
        5,
        5,
        [
            prom_target(
                '100 * (1 - avg(rate(node_cpu_seconds_total{job="node_exporter",mode="idle",host="$host"}[$__rate_interval])))',
                legend="CPU",
            )
        ],
        unit="percent",
        min_value=0,
        max_value=100,
        decimals=1,
        repeat="host",
        repeat_direction="h",
        max_per_row=5,
    ),
    panel(
        7,
        "Memory Card - $host",
        "stat",
        0,
        18,
        5,
        5,
        [
            prom_target(
                '100 * (1 - avg(node_memory_MemAvailable_bytes{job="node_exporter",host="$host"} / node_memory_MemTotal_bytes{job="node_exporter",host="$host"}))',
                legend="Memory",
            )
        ],
        unit="percent",
        min_value=0,
        max_value=100,
        decimals=1,
        repeat="host",
        repeat_direction="h",
        max_per_row=5,
    ),
    panel(
        8,
        "GPU Utilization by Host/GPU",
        "timeseries",
        0,
        23,
        12,
        8,
        [
            prom_target(
                'nvidia_smi_utilization_gpu_ratio{job="nvidia_gpu_exporter",host=~"$host"} * 100',
                legend="{{host}} GPU {{gpu}}",
            )
        ],
        unit="percent",
        min_value=0,
        max_value=100,
        decimals=1,
    ),
    panel(
        9,
        "GPU Temperature by Host/GPU",
        "timeseries",
        12,
        23,
        12,
        8,
        [
            prom_target(
                'nvidia_smi_temperature_gpu{job="nvidia_gpu_exporter",host=~"$host"}',
                legend="{{host}} GPU {{gpu}}",
            )
        ],
        unit="celsius",
        decimals=1,
    ),
    panel(
        10,
        "Recent Logs by Host",
        "logs",
        0,
        31,
        24,
        8,
        [
            loki_target(
                '{host=~"$host"}'
            )
        ],
        datasource=LOKI,
    ),
]

fleet_dashboard = dashboard_base(
    "fleet-overview",
    "Fleet Overview",
    fleet_panels,
    variables=[host_variable],
    time_from="now-1h",
)


# ---------------------------------------------------------------------
# Dashboard 2: Host Detail
# ---------------------------------------------------------------------

host_panels = [
    panel(
        1,
        "CPU Usage - $host",
        "timeseries",
        0,
        0,
        12,
        8,
        [
            prom_target(
                '100 * (1 - avg by (host) (rate(node_cpu_seconds_total{job="node_exporter",mode="idle",host=~"$host"}[$__rate_interval])))',
                legend="{{host}}",
            )
        ],
        unit="percent",
        min_value=0,
        max_value=100,
        decimals=1,
    ),
    panel(
        2,
        "Memory Usage - $host",
        "timeseries",
        12,
        0,
        12,
        8,
        [
            prom_target(
                '100 * (1 - (node_memory_MemAvailable_bytes{job="node_exporter",host=~"$host"} / node_memory_MemTotal_bytes{job="node_exporter",host=~"$host"}))',
                legend="{{host}}",
            )
        ],
        unit="percent",
        min_value=0,
        max_value=100,
        decimals=1,
    ),
    panel(
        3,
        "Load Average - $host",
        "timeseries",
        0,
        8,
        12,
        8,
        [
            prom_target('node_load1{job="node_exporter",host=~"$host"}', "A", "1m {{host}}"),
            prom_target('node_load5{job="node_exporter",host=~"$host"}', "B", "5m {{host}}"),
            prom_target('node_load15{job="node_exporter",host=~"$host"}', "C", "15m {{host}}"),
        ],
        decimals=2,
    ),
    panel(
        4,
        "Disk Usage by Mountpoint - $host",
        "timeseries",
        12,
        8,
        12,
        8,
        [
            prom_target(
                '100 * (1 - (node_filesystem_avail_bytes{job="node_exporter",host=~"$host",fstype!~"tmpfs|overlay|squashfs|fuse.lxcfs"} / node_filesystem_size_bytes{job="node_exporter",host=~"$host",fstype!~"tmpfs|overlay|squashfs|fuse.lxcfs"}))',
                legend="{{host}} {{mountpoint}}",
            )
        ],
        unit="percent",
        min_value=0,
        max_value=100,
        decimals=1,
    ),
    panel(
        5,
        "GPU Utilization - $host",
        "timeseries",
        0,
        16,
        12,
        8,
        [
            prom_target(
                'nvidia_smi_utilization_gpu_ratio{job="nvidia_gpu_exporter",host=~"$host"} * 100',
                legend="GPU {{gpu}}",
            )
        ],
        unit="percent",
        min_value=0,
        max_value=100,
        decimals=1,
    ),
    panel(
        6,
        "GPU Memory Used - $host",
        "timeseries",
        12,
        16,
        12,
        8,
        [
            prom_target(
                'nvidia_smi_memory_used_bytes{job="nvidia_gpu_exporter",host=~"$host"}',
                legend="GPU {{gpu}} used",
            ),
            prom_target(
                'nvidia_smi_memory_total_bytes{job="nvidia_gpu_exporter",host=~"$host"}',
                ref="B",
                legend="GPU {{gpu}} total",
            ),
        ],
        unit="bytes",
        decimals=1,
    ),
    panel(
        7,
        "IPMI Temperature Sensors - $host",
        "timeseries",
        0,
        24,
        12,
        8,
        [
            prom_target(
                'ipmi_temperature_celsius{job="ipmi_exporter",host=~"$host"}',
                legend="{{name}}",
            )
        ],
        unit="celsius",
        decimals=1,
    ),
    panel(
        8,
        "IPMI Fan Speed - $host",
        "timeseries",
        12,
        24,
        12,
        8,
        [
            prom_target(
                'ipmi_fan_speed_rpm{job="ipmi_exporter",host=~"$host"}',
                legend="{{name}}",
            )
        ],
        unit="rpm",
        decimals=0,
    ),
    panel(
        9,
        "System Logs - $host",
        "logs",
        0,
        32,
        24,
        10,
        [
            loki_target('{host=~"$host"}')
        ],
        datasource=LOKI,
    ),
]

host_detail_dashboard = dashboard_base(
    "host-detail",
    "Host Detail",
    host_panels,
    variables=[host_variable],
    time_from="now-6h",
)

(OUT / "00-fleet-overview.json").write_text(json.dumps(fleet_dashboard, indent=2))
(OUT / "10-host-detail.json").write_text(json.dumps(host_detail_dashboard, indent=2))

print("Wrote:")
print(" - grafana/dashboards/00-fleet-overview.json")
print(" - grafana/dashboards/10-host-detail.json")
