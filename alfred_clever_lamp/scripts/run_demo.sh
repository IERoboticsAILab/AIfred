#!/usr/bin/env bash
# Run demo.launch against the remote ROS master (which hosts natnet/optitrack).
#
#   ./run_demo.sh [roslaunch args...]          # e.g. ./run_demo.sh use_sim:=true
#   ROS_MASTER_HOST=1.2.3.4 ./run_demo.sh      # use another master
#   source run_demo.sh --env-only              # only set ROS_MASTER_URI/ROS_IP in this shell
#
# ROS_IP is detected as the local IP of the interface that routes to the master,
# so it keeps working when the IP or the network interface changes.

ROS_MASTER_HOST="${ROS_MASTER_HOST:-10.205.10.254}"
ROS_MASTER_PORT="${ROS_MASTER_PORT:-11311}"

# Detect the local IP used to reach the master
_detect_ip() {
    local ip
    ip=$(ip -4 route get "$ROS_MASTER_HOST" 2>/dev/null | grep -oP 'src \K[0-9.]+' | head -n1)
    [ -z "$ip" ] && ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    echo "$ip"
}

export ROS_MASTER_URI="http://${ROS_MASTER_HOST}:${ROS_MASTER_PORT}"
export ROS_IP="$(_detect_ip)"
unset ROS_HOSTNAME  # ROS_HOSTNAME takes precedence over ROS_IP

if [ -z "$ROS_IP" ]; then
    echo "[run_demo] ERROR: could not determine local IP to reach $ROS_MASTER_HOST" >&2
    return 1 2>/dev/null || exit 1
fi

echo "[run_demo] ROS_MASTER_URI=$ROS_MASTER_URI"
echo "[run_demo] ROS_IP=$ROS_IP"

# When sourced with --env-only, just set the variables in the current shell
if [ "${1:-}" = "--env-only" ]; then
    return 0 2>/dev/null || exit 0
fi

set -e

# Source ROS + workspace if not already done (workspace = 3 levels above this script's package)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
if ! command -v roslaunch >/dev/null 2>&1; then
    for f in /opt/ros/*/setup.bash; do [ -f "$f" ] && source "$f" && break; done
fi
if ! rospack find alfred_clever_lamp >/dev/null 2>&1 && [ -f "$WS_DIR/devel/setup.bash" ]; then
    source "$WS_DIR/devel/setup.bash"
fi

# Activate the project's Python venv (AIfred/.venv)
VENV_ACTIVATE="$SCRIPT_DIR/../../.venv/bin/activate"
if [ -f "$VENV_ACTIVATE" ]; then
    source "$VENV_ACTIVATE"
else
    echo "[run_demo] WARNING: venv not found at $VENV_ACTIVATE" >&2
fi

# Check the master is reachable before launching (otherwise roslaunch starts a local roscore)
if ! timeout 3 bash -c "</dev/tcp/$ROS_MASTER_HOST/$ROS_MASTER_PORT" 2>/dev/null; then
    echo "[run_demo] ERROR: ROS master $ROS_MASTER_URI is not reachable" >&2
    exit 1
fi

exec roslaunch --wait alfred_clever_lamp demo.launch "$@"
