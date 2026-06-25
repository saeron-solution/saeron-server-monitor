# Server Observability Stack (Prometheus + Grafana + Loki)

A production-ready multi-node monitoring stack for GPU clusters and distributed systems.

## Architecture

```
[Edge GPU Nodes]                [Central Monitoring]        [User]
├─ node-exporter :9100  ────┐
├─ ipmi-exporter :9290    ───┼──→ Prometheus :9090  ───┐
├─ nvidia-gpu-exporter :9835  │    Loki :3100         ├──→ Grafana :3000 ──→ Laptop
└─ promtail (logs) ────────────→ (Receives logs)  ───┘
                                   Grafana :3000
```

- **Edge nodes** export metrics (pull model) and push logs (push model)
- **Central server** scrapes metrics and receives logs
- **Grafana** visualizes both metrics and logs from a single location

## Quick Start

### Central Server

```bash
cd /path/to/server-observability
cp .env.example .env
# Edit .env with your Grafana password and central host IP
docker compose -f docker-compose.central.yml up -d
```

Access Grafana at `http://<central-host-ip>:3000`

### Edge GPU Node

```bash
cd /path/to/server-observability
cp .env.example .env
# Edit .env:
#   NODE_NAME=gpu-node-01 (or gpu-node-02, etc.)
#   CENTRAL_HOST=10.0.0.10 (IP of central server)
#   LOKI_URL=http://10.0.0.10:3100/loki/api/v1/push
docker compose -f docker-compose.edge.yml up -d
```

Verify edge node is sending metrics:
```bash
curl localhost:9100/metrics | head -20
curl localhost:9290/metrics | grep -E 'fan|temp' | head -5
curl localhost:9835/metrics | grep -E 'nvidia|gpu' | head -5
```

## Compose Files

| File | Purpose | Runs On |
|------|---------|---------|
| `docker-compose.central.yml` | Prometheus, Loki, Grafana | Central server |
| `docker-compose.edge.yml` | node-exporter, ipmi-exporter, nvidia-gpu-exporter, promtail | Edge GPU nodes |
| `docker-compose.yml` | Original all-in-one (deprecated) | Legacy single-host |

## Adding a New Edge Node

1. **Clone repo on new GPU server**
   ```bash
   git clone <repo-url> server-observability
   cd server-observability
   ```

2. **Configure .env**
   ```bash
   cp .env.example .env
   # Edit NODE_NAME, LOKI_URL, CENTRAL_HOST
   ```

3. **Start edge services**
   ```bash
   docker compose -f docker-compose.edge.yml up -d
   ```

4. **Add node to Prometheus targets on central server**
   
   Edit `prometheus/targets/edge-nodes.yml`:
   ```yaml
   - job_name: node-exporter
     static_configs:
       - targets:
           - gpu-node-01:9100
           - gpu-node-02:9100      # Add new node
           - gpu-node-03:9100      # Add new node
   ```

5. **Reload Prometheus (from central server)**
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```

   Or restart Prometheus:
   ```bash
   docker compose -f docker-compose.central.yml restart prometheus
   ```

## Configuration

### .env Variables

```bash
NODE_NAME              # Node identifier (e.g., gpu-node-01)
CENTRAL_HOST           # IP/hostname of central server (reachable from edges)
LOKI_URL              # Loki endpoint for log push (e.g., http://10.0.0.10:3100/loki/api/v1/push)
GF_SECURITY_ADMIN_USER    # Grafana admin username
GF_SECURITY_ADMIN_PASSWORD # Grafana admin password
NODE_EXPORTER_PORT    # node-exporter port (default 9100)
IPMI_EXPORTER_PORT    # ipmi-exporter port (default 9290)
NVIDIA_GPU_EXPORTER_PORT  # nvidia-gpu-exporter port (default 9835)
```

### Prometheus Targets

Edit `prometheus/targets/edge-nodes.yml` to add/remove edge nodes:

```yaml
- job_name: node-exporter
  static_configs:
    - targets:
        - gpu-node-01:9100      # DNS hostname
        - 10.0.0.21:9100        # Or IP address
      labels:
        host: gpu-node-01
```

### Promtail Logs

Logs are collected from `/var/log/**/*.log` on each edge node and pushed to central Loki.

Label format:
```
job: varlogs
node: gpu-node-01 (from NODE_NAME)
```

Query in Grafana: `{job="varlogs", node="gpu-node-01"}`

## Validation Commands

### On Edge Node
```bash
# Check exporters are running and responding
curl localhost:9100/metrics | head
curl localhost:9290/metrics | grep -E 'fan|temp' | head
curl localhost:9835/metrics | grep -E 'nvidia|gpu' | head
```

### On Central Server
```bash
# Check Prometheus is scraping all targets
curl localhost:9090/api/v1/targets

# Check Loki is ready for logs
curl localhost:3100/ready

# Access Grafana
curl localhost:3000
```

## Security Notes

⚠️ **Do not expose Prometheus, Loki, or exporter ports to the internet.**

Recommended approaches:
- **Private LAN only** (isolated network segment)
- **VPN** (WireGuard, OpenVPN, Tailscale)
- **SSH tunnel** (for remote Grafana access)
- **Reverse proxy with HTTPS** (nginx, Traefik)
- **Firewall rules** (iptables, ufw)

Example SSH tunnel for Grafana access:
```bash
ssh -L 3000:localhost:3000 central-server-user@central-server-ip
# Open http://localhost:3000 on your laptop
```

## Troubleshooting

### Edge node metrics not showing in Prometheus
1. Check edge node is running: `docker ps`
2. Check Prometheus can reach edge node: `curl <edge-ip>:9100/metrics`
3. Check `prometheus/targets/edge-nodes.yml` has the correct IP/hostname
4. Reload Prometheus: `curl -X POST http://central:9090/-/reload`

### Logs not appearing in Loki
1. Check `promtail` is running on edge: `docker ps`
2. Check Loki is accessible: `curl <central-ip>:3100/ready`
3. Verify `LOKI_URL` in `.env` is correct
4. Check `promtail/config.yml` is reading `/var/log/**/*.log`

### IPMI metrics are empty
1. Check `/dev/ipmi0` exists on edge node: `ls -l /dev/ipmi0`
2. Load kernel modules: `sudo modprobe ipmi_devintf ipmi_si`
3. Restart ipmi-exporter: `docker compose -f docker-compose.edge.yml restart ipmi-exporter`

### NVIDIA GPU metrics not appearing
1. Check NVIDIA driver: `nvidia-smi`
2. Check NVIDIA Container Toolkit: `docker info | grep nvidia`
3. Install if missing: `sudo apt-get install nvidia-container-toolkit`
4. Restart Docker: `sudo systemctl restart docker`
5. Restart edge services: `docker compose -f docker-compose.edge.yml up -d`

## Services Included

**Central Server:**
- `prometheus` (metrics storage, 15s scrape interval)
- `loki` (log aggregation)
- `grafana` (dashboard UI, auto-provisioned)

**Edge Node:**
- `node-exporter` (host CPU, memory, disk, load)
- `ipmi-exporter` (hardware sensors, fans, temperature)
- `nvidia-gpu-exporter` (GPU utilization, memory, temperature)
- `promtail` (log collection and push)

## Grafana Dashboards

Pre-configured dashboards auto-load from `grafana/dashboards/`:
- **Server Overview** (CPU, Memory, Load, GPU)
- More can be added as JSON files in the directory

Datasources auto-configured:
- Prometheus (metrics)
- Loki (logs)

## Default Ports

| Service | Port | Host |
|---------|------|------|
| Prometheus | 9090 | Central |
| Grafana | 3000 | Central |
| Loki | 3100 | Central |
| node-exporter | 9100 | Edge |
| ipmi-exporter | 9290 | Edge |
| nvidia-gpu-exporter | 9835 | Edge |

## File Structure

```
server-observability/
├── docker-compose.central.yml    # Central server stack
├── docker-compose.edge.yml       # Edge node stack
├── docker-compose.yml            # Legacy all-in-one
├── .env.example                  # Configuration template
├── README.md                      # This file
├── prometheus/
│   ├── prometheus.yml            # Prometheus config
│   └── targets/
│       └── edge-nodes.yml        # Edge node targets (to be edited)
├── loki/
│   └── config.yml                # Loki config
├── promtail/
│   └── config.yml                # Promtail config (uses env vars)
├── ipmi_exporter/
│   └── ipmi_local.yml            # IPMI exporter config
└── grafana/
    ├── provisioning/
    │   ├── datasources/          # Prometheus, Loki datasources
    │   └── dashboards/           # Dashboard provisioning
    └── dashboards/
        └── server-overview.json  # Pre-built dashboard
```

## Notes

- Prometheus uses **pull-based** metrics collection (scrapes edge nodes)
- Promtail uses **push-based** log collection (sends to central Loki)
- Both metrics and logs are labeled with node name for easy querying
- No persistent data is lost if a single edge node goes down
- Central Prometheus can be scaled with remote storage (e.g., Cortex, Thanos)
- Edge nodes are stateless and can be easily replaced