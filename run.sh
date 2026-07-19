#!/usr/bin/with-contenv bashio

bashio::log.info "Starting Forewarned..."

# Get configuration
export CHECK_INTERVAL=$(bashio::config 'check_interval')
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"

# Start the application
cd /app
python3 main.py
