#!/bin/bash
pg_dump -h server -U tomwattley -s -n live_betting -f "/Users/tomwattley/App/racing-api-project/racing-api-project/apps/trader/live_betting_schema.sql" racing-api
