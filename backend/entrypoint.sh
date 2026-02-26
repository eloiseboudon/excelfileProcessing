#!/bin/sh
# Fix permissions on the logs volume (mounted as root by Docker)
# then drop to appuser to run the application.
chown -R appuser:appuser /app/logs 2>/dev/null || true

exec gosu appuser "$@"
