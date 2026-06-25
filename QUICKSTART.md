# Quick Start Guide - Multi-Node Monitoring

## Deploy Central Monitoring Server (5 minutes)

```bash
# 1. Clone and navigate
git clone <repo> server_observability
cd server_observability

# 2. Configure central server
cp .env.example .env
# Edit .env - set:
#   GF_SECURITY_ADMIN_PASSWORD=your_secure_password
#   CENTRAL_HOST=central-server-ip-or-dns

# 3. Start central stack
docker compose -f docker-compose.central.yml up -d

# 4. Verify services running
docker compose -f docker-compose.central.yml ps

# 5. Access Grafana
# http://CENTRAL_HOST:3000
# Username: admin
# Password: <your GF_SECURITY_ADMIN_PASSWORD>
```

## Deploy Edge Node (2 minutes per node)

```bash
# On each GPU server:

# 1. Copy repository
cd /opt  # or your preferred location
cp -r server_observability server_observability_edge

# 2. Configure this edge node
cd server_observability_edge
cp .env.example .env
# Edit .env - set:
#   NODE_NAME=gpu-node-01
#   CENTRAL_HOST=central-server-ip
#   LOKI_URL=http://central-server-ip:3100/loki/api/v1/push
#   NODE_EXPORTER_PORT=9100
#   IPMI_EXPORTER_PORT=9290
#   NVIDIA_GPU_EXPORTER_PORT=9835

# 3. Start edge services
docker compose -f docker-compose.edge.yml up -d

# 4. Verify exporters running
curl http://localhost:9100/metrics | head -20  # node exporter
curl http://localhost:9290/metrics | head -20  # IPMI exporter
curl http://localhost:9835/metrics | head -20  # GPU exporter
```

## Register Edge Node with Prometheus (1 minute)

```bash
# On central server:
# 1. Edit Prometheus targets
nano prometheus/targets/edge-nodes.yml

# 2. Add new node (copy template):
#   - targets: ['gpu-node-01:9100']
#   - targets: ['gpu-node-01:9290']
#   - targets: ['gpu-node-01:9835']

# 3. Reload Prometheus (no restart needed)
docker exec server_observability-prometheus-1 kill -HUP 1

# Or use curl:
curl -X POST http://localhost:9090/-/reload

# 4. Verify targets in Prometheus UI
# http://central-host:9090/targets
# All should show "UP" within 30 seconds
```

## Verify Everything Works

```bash
# ✓ Prometheus scraping edge node
curl -s 'http://localhost:9090/api/v1/targets' | jq '.data.activeTargets[] | {labels, state}'

# ✓ Grafana datasources connected
curl -s http://localhost:3000/api/datasources \
  -H "Authorization: Bearer $(curl -s -X POST http://localhost:3000/api/auth/login \
    -d '{\"user\":\"admin\",\"password\":\"your_password\"}' | jq -r '.token')" \
  | jq '.[] | {name, type, isDefault}'

# ✓ Logs being collected
curl -s 'http://localhost:3100/loki/api/v1/label/node/values' | jq '.data'
```

## Troubleshooting Quick Reference

| Issue | Check | Solution |
|-------|-------|----------|
| Edge metrics not appearing | CENTRAL_HOST in .env correct? | Verify DNS/IP resolves from edge node |
| No IPMI data | Is /dev/ipmi0 present? | `ls -l /dev/ipmi0` on edge server |
| No GPU data | GPU drivers installed? | `nvidia-smi` on edge server must work |
| Logs not in Loki | LOKI_URL correct? | `curl http://LOKI_URL` from edge node |
| Grafana dashboards empty | Prometheus job added? | Check Prometheus targets UI for "UP" status |

## File Structure Reference

```
server_observability/
├── docker-compose.central.yml  ← Start here on central server
├── docker-compose.edge.yml     ← Use on each GPU node
├── .env.example               ← Copy to .env before deploying
├── README.md                  ← Full documentation
├── DEPLOYMENT.md              ← Step-by-step guide
├── QUICKSTART.md              ← You are here
├── prometheus/
│   ├── prometheus.yml         ← Uses file_sd_configs
│   └── targets/
│       └── edge-nodes.yml     ← Edit this to add nodes
├── promtail/
│   └── config.yml             ← Uses ${LOKI_URL} env var
└── grafana/
    ├── dashboards/
    │   └── server-overview.json
    └── provisioning/
        └── datasources/
```

## Common Tasks

### Add a New GPU Node
```bash
# 1. Deploy edge on new server (see "Deploy Edge Node" above)
# 2. On central server, edit targets:
nano prometheus/targets/edge-nodes.yml
# 3. Add three lines for new node:
#   - targets: ['gpu-node-02:9100']
#   - targets: ['gpu-node-02:9290']
#   - targets: ['gpu-node-02:9835']
# 4. Reload Prometheus:
curl -X POST http://localhost:9090/-/reload
# Done! Metrics appear within 30 seconds
```

### Scale to Multiple Central Servers
```bash
# Edit .env.example to create per-region .env files:
# .env.us-west (CENTRAL_HOST=west-prometheus)
# .env.us-east (CENTRAL_HOST=east-prometheus)

# Each edge node can push to multiple central servers
# by running docker compose multiple times with different .env files
```

### Enable Authentication
```bash
# In .env on central server:
GF_SECURITY_ADMIN_PASSWORD=strong_password_123
GF_AUTH_BASIC_ENABLED=true

# In .env on edge nodes (optional):
# PROMETHEUS_SCRAPE_USERNAME=admin
# PROMETHEUS_SCRAPE_PASSWORD=secret
# (requires prometheus.yml updates)
```

## Next Steps

1. **Read Full Docs**: See `README.md` for architecture, security, scaling
2. **Read Deployment Guide**: See `DEPLOYMENT.md` for production best practices
3. **Set Up Alerting**: Add Alertmanager to `docker-compose.central.yml`
4. **Configure Backups**: Set up Prometheus/Grafana volume backups
5. **Enable VPN**: Use WireGuard/OpenVPN for secure remote access (see README.md)

## Support

- **Logs**: `docker compose logs -f service-name`
- **Debug**: `docker compose exec service-name sh`
- **Metrics endpoint**: `curl http://node:9100/metrics`
- **Loki queries**: http://central:3000 → Explore → Logs

---

**Status**: ✅ Multi-node monitoring stack ready for production
**Deploy Time**: ~10 minutes for first central + edge setup
**Scale Time**: ~2 minutes per additional edge node
