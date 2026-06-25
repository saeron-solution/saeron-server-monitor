# Server Observability Stack

Multi-node monitoring stack using Prometheus, Grafana, Loki, Node Exporter, IPMI Exporter, NVIDIA GPU Exporter, and Promtail.

This repository supports two deployment roles:

* **Central server**: runs Prometheus, Loki, and Grafana.
* **Edge node**: runs exporters and Promtail.

A central server may also run the edge stack if you want to monitor the central machine itself.

---

## Architecture

```text
192.168.0.34 / Edge Node
  ├─ node-exporter         :9100  ← scraped by Prometheus
  ├─ ipmi-exporter         :9290  ← scraped by Prometheus
  ├─ nvidia-gpu-exporter   :9835  ← scraped by Prometheus
  └─ promtail                     → pushes logs to Loki

192.168.0.73 / Central Server
  ├─ Prometheus            :19090 host → :9090 container
  ├─ Loki                  :13100 host → :3100 container
  ├─ Grafana               :13000 host → :3000 container
  ├─ node-exporter         :9100  optional, if central also monitored
  ├─ ipmi-exporter         :9290  optional, if central also monitored
  ├─ nvidia-gpu-exporter   :9835  optional, if central also monitored
  └─ promtail                     optional, if central also monitored
```

Metrics are **pull-based**:

```text
Prometheus on central → scrapes edge exporters
```

Logs are **push-based**:

```text
Promtail on edge → pushes logs to central Loki
```

Grafana does not directly collect metrics. Grafana queries Prometheus and Loki.

---

## Compose Files

| File                         | Purpose                                                     | Run On                                   |
| ---------------------------- | ----------------------------------------------------------- | ---------------------------------------- |
| `docker-compose.central.yml` | Prometheus, Loki, Grafana                                   | Central server                           |
| `docker-compose.edge.yml`    | node-exporter, ipmi-exporter, nvidia-gpu-exporter, promtail | Edge nodes and optionally central server |

---

## Quick Start: Central Server

Example central server:

```text
192.168.0.73
```

Clone repo:

```bash
git clone git@github.com:saeron-solution/saeron-server-monitor.git
cd saeron-server-monitor
```

Create `.env`:

```bash
cat > .env <<'EOF'
NODE_NAME=gpu-73
CENTRAL_HOST=192.168.0.73

PROMETHEUS_PORT=19090
LOKI_PORT=13100
GRAFANA_PORT=13000

GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=change-this-password

LOKI_URL=http://192.168.0.73:13100/loki/api/v1/push

NODE_EXPORTER_PORT=9100
IPMI_EXPORTER_PORT=9290
NVIDIA_GPU_EXPORTER_PORT=9835
EOF
```

Start central stack:

```bash
./scripts/central-up.sh
```

Or:

```bash
./scripts/up.sh central
```

Access:

```text
Grafana:    http://192.168.0.73:13000
Prometheus: http://192.168.0.73:19090
Loki:       http://192.168.0.73:13100
```

Stop central stack:

```bash
./scripts/central-down.sh
```

Or:

```bash
./scripts/down.sh central
```

---

## Quick Start: Edge Node

Example edge node:

```text
192.168.0.34
```

Clone repo:

```bash
git clone git@github.com:saeron-solution/saeron-server-monitor.git
cd saeron-server-monitor
```

Create `.env`:

```bash
cat > .env <<'EOF'
NODE_NAME=gpu-34
CENTRAL_HOST=192.168.0.73

LOKI_URL=http://192.168.0.73:13100/loki/api/v1/push

NODE_EXPORTER_PORT=9100
IPMI_EXPORTER_PORT=9290
NVIDIA_GPU_EXPORTER_PORT=9835
EOF
```

Start edge stack:

```bash
./scripts/edge-up.sh
```

Or:

```bash
./scripts/up.sh edge
```

Stop edge stack:

```bash
./scripts/edge-down.sh
```

Or:

```bash
./scripts/down.sh edge
```

---

## Monitor the Central Server Itself

If the central server should also appear as a monitored node, run both stacks on central:

```bash
./scripts/central-up.sh
./scripts/edge-up.sh
```

This means the central machine runs:

* Prometheus
* Loki
* Grafana
* node-exporter
* ipmi-exporter
* nvidia-gpu-exporter
* promtail

---

## Prometheus Target Configuration

Prometheus target files are located under:

```text
prometheus/targets/
```

Recommended structure:

```text
prometheus/targets/
├── node-exporter.yml
├── ipmi-exporter.yml
└── nvidia-gpu-exporter.yml
```

### `prometheus/targets/node-exporter.yml`

```yaml
- targets:
    - 192.168.0.34:9100
  labels:
    host: gpu-34
    role: edge

- targets:
    - 192.168.0.73:9100
  labels:
    host: gpu-73
    role: central
```

### `prometheus/targets/ipmi-exporter.yml`

```yaml
- targets:
    - 192.168.0.34:9290
  labels:
    host: gpu-34
    role: edge

- targets:
    - 192.168.0.73:9290
  labels:
    host: gpu-73
    role: central
```

### `prometheus/targets/nvidia-gpu-exporter.yml`

```yaml
- targets:
    - 192.168.0.34:9835
  labels:
    host: gpu-34
    role: edge

- targets:
    - 192.168.0.73:9835
  labels:
    host: gpu-73
    role: central
```

Important: these target files are used by Prometheus `file_sd_configs`.

They must use this format:

```yaml
- targets:
    - host:port
  labels:
    key: value
```

Do **not** put `job_name` or `static_configs` inside these files.

---

## Reload Prometheus

If Prometheus was started with `--web.enable-lifecycle`, reload without restart:

```bash
curl -X POST http://localhost:19090/-/reload
```

Or restart Prometheus:

```bash
docker compose -f docker-compose.central.yml restart prometheus
```

---

## Validation Commands

### Validate Compose Files

```bash
docker compose -f docker-compose.central.yml config -q
docker compose -f docker-compose.edge.yml config -q
```

### Validate Prometheus Config

```bash
docker run --rm \
  -v "$PWD/prometheus:/etc/prometheus:ro" \
  prom/prometheus:v2.54.1 \
  promtool check config /etc/prometheus/prometheus.yml
```

### Validate Central Services

Run on central server:

```bash
curl http://localhost:19090/-/ready
curl http://localhost:13100/ready
curl http://localhost:13000/api/health
```

### Validate Edge Exporters

Run on each edge node:

```bash
curl http://localhost:9100/metrics | head
curl http://localhost:9290/metrics | head
curl http://localhost:9835/metrics | head
```

### Validate Central Can Reach Edge

Run on central server:

```bash
curl http://192.168.0.34:9100/metrics | head
curl http://192.168.0.34:9290/metrics | head
curl http://192.168.0.34:9835/metrics | head
```

### Check Prometheus Targets

Open:

```text
http://192.168.0.73:19090/targets
```

Or query API:

```bash
curl -s http://localhost:19090/api/v1/targets | python -m json.tool
```

---

## Ports

| Service             | Container Port | Recommended Host Port | Runs On |
| ------------------- | -------------: | --------------------: | ------- |
| Prometheus          |           9090 |                 19090 | Central |
| Grafana             |           3000 |                 13000 | Central |
| Loki                |           3100 |                 13100 | Central |
| node-exporter       |           9100 |                  9100 | Edge    |
| ipmi-exporter       |           9290 |                  9290 | Edge    |
| nvidia-gpu-exporter |           9835 |                  9835 | Edge    |
| promtail            |           9080 |           not exposed | Edge    |

The host ports for Prometheus, Grafana, and Loki are intentionally shifted away from common defaults to avoid conflicts on shared servers.

---

## Scripts

### Easy Commands

```bash
./scripts/central-up.sh
./scripts/central-down.sh
./scripts/edge-up.sh
./scripts/edge-down.sh
```

### Generic Commands

```bash
./scripts/up.sh central
./scripts/down.sh central

./scripts/up.sh edge
./scripts/down.sh edge
```

### Start One Service

```bash
./scripts/up.sh central prometheus
./scripts/up.sh edge node-exporter
```

---

## Troubleshooting

### Prometheus Cannot See Edge Metrics

Check from central:

```bash
curl http://192.168.0.34:9100/metrics | head
```

If this fails:

* edge container may not be running
* firewall may block the port
* wrong edge IP in target file
* exporter port may be different from target file

Check containers:

```bash
docker ps
```

Check Prometheus target page:

```text
http://192.168.0.73:19090/targets
```

### Loki Logs Not Appearing

Check Promtail logs on edge:

```bash
docker compose -f docker-compose.edge.yml logs --tail=100 promtail
```

Check Loki from edge:

```bash
curl http://192.168.0.73:13100/ready
```

Check `.env`:

```bash
cat .env | grep LOKI_URL
```

Expected:

```text
LOKI_URL=http://192.168.0.73:13100/loki/api/v1/push
```

### IPMI Exporter Fails

Check device:

```bash
ls -l /dev/ipmi0
```

Try loading modules:

```bash
sudo modprobe ipmi_devintf ipmi_si
```

Restart edge stack:

```bash
./scripts/edge-up.sh
```

If the machine does not support IPMI, remove its IPMI target from `prometheus/targets/ipmi-exporter.yml`.

### NVIDIA GPU Exporter Fails

Check driver:

```bash
nvidia-smi
```

Check Docker NVIDIA runtime/toolkit:

```bash
docker info | grep -i nvidia
```

Restart Docker if needed:

```bash
sudo systemctl restart docker
./scripts/edge-up.sh
```

### Port Conflict

Check used ports:

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"
sudo ss -tulpn | grep -E ':19090|:13000|:13100|:9100|:9290|:9835'
```

Change `.env` if needed.

---

## Security Notes

Do not expose Prometheus, Loki, Grafana, or exporter ports directly to the public internet.

Recommended access patterns:

* private LAN only
* VPN such as WireGuard or Tailscale
* SSH tunnel
* reverse proxy with HTTPS and authentication
* firewall rules limiting access to trusted IPs

Example SSH tunnel for Grafana:

```bash
ssh -L 13000:localhost:13000 user@192.168.0.73
```

Then open:

```text
http://localhost:13000
```

---

## File Structure

```text
server-observability/
├── docker-compose.central.yml
├── docker-compose.edge.yml
├── .env.example
├── README.md
├── scripts/
│   ├── central-up.sh
│   ├── central-down.sh
│   ├── edge-up.sh
│   ├── edge-down.sh
│   ├── up.sh
│   └── down.sh
├── prometheus/
│   ├── prometheus.yml
│   └── targets/
│       ├── node-exporter.yml
│       ├── ipmi-exporter.yml
│       └── nvidia-gpu-exporter.yml
├── loki/
│   └── config.yml
├── promtail/
│   └── config.yml
├── ipmi_exporter/
│   └── ipmi_local.yml
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   └── dashboards/
    └── dashboards/
        └── server-overview.json
```
