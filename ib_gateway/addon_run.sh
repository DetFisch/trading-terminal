#!/usr/bin/env bash
# Add-on options -> the environment variables the ib-gateway image expects, then start it.
set -euo pipefail
OPTS=/data/options.json
opt() { jq -r --arg k "$1" '.[$k] // empty' "$OPTS"; }

if [ -z "$(opt ib_username)" ] || [ -z "$(opt ib_password)" ]; then
    echo "[ib_gateway] Set ib_username and ib_password on the Configuration tab, then restart." >&2
    exit 1
fi

export TWS_USERID="$(opt ib_username)"
export TWS_PASSWORD="$(opt ib_password)"
export TRADING_MODE="$(opt trading_mode)"
export READ_ONLY_API="$([ "$(opt read_only_api)" = "true" ] && echo yes || echo no)"
export TWOFA_TIMEOUT_ACTION="$(opt twofa_timeout_action)"
export AUTO_RESTART_TIME="$(opt auto_restart_time)"
export TIME_ZONE="$(opt time_zone)"
export TZ="$TIME_ZONE"
export HOME=/home/ibgateway

echo "[ib_gateway] Starting IB Gateway (${TRADING_MODE}). API: port 4004 paper / 4003 live."
exec setpriv --reuid=1000 --regid=1000 --init-groups /home/ibgateway/scripts/run.sh
