# Racing API Project - Service Management

This directory contains scripts for managing the Racing API project services using tmux and cron.

## Overview

The Racing API project consists of several services that need to be orchestrated:

- **ETL Pipeline** (`run_etl`): Daily data extraction, transformation, and loading
- **API Server** (`run_api`): FastAPI backend service 
- **Web Application** (`run_webapp`): React frontend
- **Trader** (`run_trader`): Trading algorithm service
- **Betfair Live Prices** (`run_betfair_live_prices`): Live price monitoring

## Service Management Scripts

### Daily Automation Scripts

| Script | Purpose | Schedule |
|--------|---------|----------|
| `run_etl_pipeline` | Run daily ETL pipeline | 5:00 AM |
| `start_trader` | Start trader (tmux session) | 6:00 AM |
| `stop_trader` | Stop trader (tmux session) | 11:00 PM |

### Manual Management Scripts

| Script | Purpose |
|--------|---------|
| `status_services` | Check status of all services |
| `setup_cron` | Install cron jobs for automation |

## Quick Start

### 1. Set up cron jobs for automation:
```bash
~/App/racing-api-project/racing-api-project/scripts/setup_cron
```

### 2. Manual service management:
```bash
# Start trader
~/App/racing-api-project/racing-api-project/scripts/start_trader

# Check service status
~/App/racing-api-project/racing-api-project/scripts/status_services

# Stop trader
~/App/racing-api-project/racing-api-project/scripts/stop_trader

# Run ETL pipeline manually
~/App/racing-api-project/racing-api-project/scripts/run_etl_pipeline
```

## Tmux Session Management

Each service runs in its own tmux session:

| Service | Session Name | Port |
|---------|--------------|------|
| API Server | `racing-api` | 8000 |
| Web App | `racing-webapp` | 5173 |
| Trader | `trader` | - |
| Betfair Live Prices | `betfair-live-prices` | - |
| ETL Pipeline | `racing-etl` | - |

### Tmux Commands

```bash
# List all sessions
tmux list-sessions

# Attach to a specific session
tmux attach-session -t racing-api
tmux attach-session -t racing-webapp
tmux attach-session -t trader
tmux attach-session -t betfair-live-prices
tmux attach-session -t racing-etl

# Detach from session (while attached)
Ctrl+B, then D

# Kill a specific session
tmux kill-session -t session-name
```

## Automated Schedule

When cron jobs are installed, the following schedule runs automatically:

```
5:00 AM  - ETL Pipeline runs (processes previous day's data)
6:00 AM  - All services start up
11:00 PM - All services shut down
```

## Log Files

### Service Logs
Each service creates daily logs in:
- `~/App/racing-api-project/racing-api-project/logs/racing-etl/execution_YYYY_MM_DD.log`
- `~/App/racing-api-project/racing-api-project/logs/trader/execution_YYYY_MM_DD.log`
- `~/App/racing-api-project/racing-api-project/logs/betfair-live-prices/execution_YYYY_MM_DD.log`

### Cron Logs
Cron job execution logs:
- `~/App/racing-api-project/racing-api-project/logs/cron_etl.log`
- `~/App/racing-api-project/racing-api-project/logs/cron_startup.log`
- `~/App/racing-api-project/racing-api-project/logs/cron_shutdown.log`

## Monitoring

### Real-time monitoring:
```bash
# Watch service status
watch ~/App/racing-api-project/racing-api-project/scripts/status_services

# Tail service logs
tail -f ~/App/racing-api-project/racing-api-project/logs/*/execution_$(date +%Y_%m_%d).log

# Monitor specific service
tmux attach-session -t racing-api
```

### Check if services are responding:
```bash
# API health check
curl http://localhost:8000/racing-api/docs

# Web app check
curl http://localhost:5173
```

## Troubleshooting

### Services won't start:
1. Check if tmux sessions already exist: `tmux list-sessions`
2. Kill existing sessions: `tmux kill-session -t session-name`
3. Check logs for errors
4. Verify environment setup

### Cron jobs not running:
1. Check crontab: `crontab -l`
2. Check cron logs: `tail -f ~/App/racing-api-project/racing-api-project/logs/cron_*.log`
3. Verify script permissions: `ls -la ~/App/racing-api-project/racing-api-project/scripts/`

### Port conflicts:
1. Check what's using ports: `lsof -i :8000` or `lsof -i :5173`
2. Kill conflicting processes or change ports

## Remote Access

When SSH'd into the server:
```bash
# Check what's running
~/App/racing-api-project/racing-api-project/scripts/status_services

# Attach to any service to monitor
tmux attach-session -t racing-api

# Start services if needed
~/App/racing-api-project/racing-api-project/scripts/start_trader
```

## Development Mode

For development, you may want to run services manually without cron:

```bash
# Stop cron automation temporarily
crontab -r  # BE CAREFUL: This removes ALL cron jobs

# Run services manually as needed
~/App/racing-api-project/racing-api-project/scripts/start_trader
```

To restore automation:
```bash
~/App/racing-api-project/racing-api-project/scripts/setup_cron
```
