# Multi-Node Monitoring Stack Deployment Guide

## Overview

This guide covers deploying a production-ready multi-node monitoring architecture where:
- **Edge nodes** (GPU servers) export metrics and push logs
- **Central server** aggregates metrics and logs, runs Grafana
- **Laptop/client** connects to Grafana remotely

## Prerequisites

All machines (central + edges):
- Docker 20.10+
- Docker Compose v2+
- `.env` file in the repo directory

Central server additionally:
- Network connectivity to all edge nodes (direct or via VPN)

Edge nodes additionally:
- NVIDIA Container Toolkit (if running GPU exporter)
- IPMI device support (if running IPMI exporter)

## Deployment Steps

### 1. Central Server Setup

On the central monitoring machine:

```bash
# Clone the repository
git clone <repo-url> server-observability
cd server-observability

# Copy and configure .env
cp .env.example .env

# Edit .env with your values:
# - CENTRAL_HOST: IP/hostname of this central server
# - GF_SECURITY_ADMIN_PASSWORD: Strong Grafana password
nano .env
```

Start the central stack:

```bash
docker compose -f docker-compose.central.yml up -d
docker compose -f docker-compose.central.yml ps
```

Verify services are running:

```bash
# Prometheus (metrics)
curl http://localhost:9090/-/ready
curl http://localhost:9090/api/v1/targets

# Loki (logs)
curl http://localhost:3100/ready

# Grafana
curl -s http://localhost:3000/api/health | jq '.database'
```

Access Grafana: `http://<central-server-ip>:3000`

### 2. Edge Node Setup (First Node)

On the first GPU server:

```bash
# Clone the same repository
git clone <repo-url> server-observability
cd server-observability

# Copy and configure .env
cp .env.example .env

# Edit .env values:
# - NODE_NAME=gpu-node-01
# - CENTRAL_HOST=<IP-of-central-server>
# - LOKI_URL=http://<IP-of-central-server>:3100/loki/api/v1/push
nano .env
```

Start the edge stack:

```bash
docker compose -f docker-compose.edge.yml up -d
docker compose -f docker-compose.edge.yml ps
```

Verify edge node exporters:

```bash
# Host metrics
curl http://localhost:9100/metrics | head -20

# Hardware metrics (if IPMI available)
curl http://localhost:9290/metrics | grep -E 'temperature|fan' | head

# GPU metrics (if NVIDIA GPU)
curl http://localhost:9835/metrics | grep -E 'nvidia|gpu' | head
```

### 3. Register Edge Node with Central Prometheus

On the central server, edit the Prometheus targets file:

```bash
nano prometheus/targets/edge-nodes.yml
```

Add the new node:

```yaml
# For existing jobs, add the new node's IP/hostname:

- job_name: node-exporter
  static_configs:
    - targets:
        - gpu-node-01:9100
        # ^ First node (added automatically as example)
```

If using IP addresses instead of DNS:

```yaml
- job_name: node-exporter
  static_configs:
    - targets:
        - 10.0.0.21:9100
        - 10.0.0.22:9100
```

Reload Prometheus to apply:

```bash
curl -X POST http://localhost:9090/-/reload
```

Or restart Prometheus:

```bash
docker compose -f docker-compose.central.yml restart prometheus
```

Verify in Prometheus: `http://localhost:9090/graph` → search for `up` metric

### 4. Add More Edge Nodes (Repeat)

For each additional GPU server, repeat steps 2–3:
1. Clone repo and configure `.env` with unique `NODE_NAME`
2. Start edge stack
3. Add to `prometheus/targets/edge-nodes.yml` on central
4. Reload Prometheus

### 5. Accessing Grafana Remotely

From your laptop:

#### Option A: Private Network (No VPN needed)
```bash
# If your laptop is on the same LAN as central server
open http://<central-server-ip>:3000
```

#### Option B: SSH Tunnel (Most Secure)
```bash
# Create SSH tunnel to central server
ssh -L 3000:localhost:3000 user@central-server-ip

# Open Grafana
open http://localhost:3000
```

#### Option C: Reverse Proxy (Production)
Set up nginx/Traefik with HTTPS on central server to expose Grafana safely.

#### Option D: VPN (Best for Scale)
Connect to company VPN (WireGuard, Tailscale) and access central server's private IP.

## Validation Commands

### On Each Edge Node

```bash
# Check all exporters are responding
curl -s localhost:9100/metrics | wc -l
curl -s localhost:9290/metrics | wc -l
curl -s localhost:9835/metrics | wc -l

# Check promtail is pushing logs
docker compose -f docker-compose.edge.yml logs promtail | tail -20
```

### On Central Server

```bash
# Verify all targets are UP
curl -s http://localhost:9090/api/v1/targets | grep '"health"'

# Check Loki received logs
curl -s http://localhost:3100/loki/api/v1/label/node/values

# Verify Grafana datasources
curl -s http://localhost:3000/api/datasources | jq '.[] | {name, type}'
```

### In Grafana UI

1. Log in at `http://localhost:3000`
2. Go to **Dashboards** → **Server Overview**
3. Verify all nodes appear in dropdowns
4. Check metrics appear in panels (may take 1-2 minutes)

## Troubleshooting

### "Failed to connect to edge node" in Prometheus

**Cause:** Central server can't reach edge node IP/port

**Solution:**
1. Verify edge node is running: `docker ps` on edge
2. Test connectivity: `curl <edge-ip>:9100/metrics` from central
3. Check firewall: `sudo ufw status` on edge
4. Verify correct IP in `prometheus/targets/edge-nodes.yml`

### "No Data" in Grafana panels

**Cause:** Prometheus hasn't scraped yet or targets are unhealthy

**Solution:**
1. Check Prometheus targets: `http://central:9090/targets`
2. Ensure target state is "UP" (not "DOWN")
3. Wait 15–30 seconds (default scrape interval)
4. Query metrics manually: `http://central:9090/graph?expr=up`

### IPMI exporter shows no temperature/fan data

**Cause:** IPMI device not accessible or kernel module not loaded

**Solution on edge:**
```bash
# Load kernel modules
sudo modprobe ipmi_devintf ipmi_si

# Verify device exists
ls -l /dev/ipmi0

# Restart exporter
docker compose -f docker-compose.edge.yml restart ipmi-exporter
```

### GPU metrics are empty

**Cause:** NVIDIA Container Toolkit not configured

**Solution on edge:**
```bash
# Install toolkit
sudo apt-get install nvidia-container-toolkit

# Configure Docker
sudo nvidia-ctk runtime configure --runtime=docker

# Restart Docker daemon
sudo systemctl restart docker

# Restart edge services
docker compose -f docker-compose.edge.yml up -d
```

### Logs not appearing in Grafana

**Cause:** Promtail can't reach Loki or misconfigured

**Solution:**
1. Check Loki is accessible: `curl <central-ip>:3100/ready` on edge
2. Verify LOKI_URL in `.env` is correct
3. Check promtail logs: `docker compose -f docker-compose.edge.yml logs promtail`
4. Ensure `/var/log/**/*.log` files exist on edge

## Security Best Practices

### 1. Network Segmentation
- Run monitoring stack on **private network only**
- Use VPN or firewall to isolate

### 2. Credentials
- Change default Grafana password in `.env`
- Restrict Prometheus/Loki access (no internet exposure)

### 3. Log Levels
- Set appropriate log levels for production
- Mask sensitive information in logs

### 4. Authentication
- Add Reverse Proxy with HTTPS for remote access
- Consider OAuth2/LDAP for centralized auth

### 5. Backup
- Backup Prometheus TSDB: `prometheus_data/`
- Backup Grafana dashboards: `grafana/dashboards/`
- Backup Loki data: `loki_data/`

```bash
# Backup script
tar -czf monitoring-backup-$(date +%Y%m%d).tar.gz \
  prometheus_data/ \
  loki_data/ \
  grafana_data/ \
  grafana/dashboards/ \
  prometheus/targets/
```

## Scaling Considerations

### Adding 50+ Edge Nodes
1. Separate Prometheus instances (federated scraping)
2. Use remote storage (Cortex, Thanos)
3. Add alertmanager
4. Increase central server resources

### Long-term Data Retention
- Prometheus default: 15 days
- Configure `--storage.tsdb.retention.time` in compose
- Add remote storage backend

### HA Setup
- Run Prometheus in HA mode (dual instances)
- Use shared storage (NFS) for `prometheus_data/`
- Add HAProxy or nginx load balancer

## Maintenance

### Regular Tasks

**Weekly:**
```bash
# Check disk usage
df -h prometheus_data/ loki_data/ grafana_data/

# Verify all targets UP
curl http://localhost:9090/api/v1/targets
```

**Monthly:**
```bash
# Backup data
tar -czf monitoring-backup-$(date +%Y%m%d).tar.gz prometheus_data/ loki_data/ grafana_data/

# Update images
docker compose pull
docker compose -f docker-compose.central.yml up -d
```

**Quarterly:**
- Review and update alert rules
- Audit user access
- Test disaster recovery (restore from backup)

## Next Steps

1. **Add alertmanager** for notifications (email, Slack, PagerDuty)
2. **Custom dashboards** for your GPU workloads
3. **Alerting rules** for SLA compliance
4. **Authentication** (OAuth2, LDAP)
5. **Long-term storage** (Cortex, Thanos) for compliance/audit
