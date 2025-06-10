# Centralized Logging

This directory contains centralized logs for all projects in the racing-api monorepo.

## Structure

```
logs/
├── racing-etl/          # ETL pipeline logs
├── trader/              # Trading bot logs
├── betfair-live-prices/ # Live price collection logs
└── README.md           # This file
```

## Log File Naming Convention

All projects use a uniform naming convention:

- **racing-etl**: `execution_YYYY_MM_DD.log`
- **trader**: `execution_YYYY_MM_DD.log`
- **betfair-live-prices**: `execution_YYYY_MM_DD.log`

## How It Works

1. The racing-etl pipeline runs first each day and creates empty log files for all projects
2. Each project's bash script redirects output to the appropriate centralized log file
3. All logs are stored in date-stamped files for easy organization and retrieval

## Log Creation

Log files are automatically created by the `create_centralized_log_files()` function in the racing-etl main.py, which runs at the start of each daily pipeline execution.

## Migration

Historical log files from the old local directories have been migrated to this centralized structure.
