#!/bin/bash
set -e

base_dir="/OpenCHAI"

pxe_server_script="$base_dir/automation/python/run_pxe_server.py"
pxe_server_playbook="$base_dir/automation/ansible/playbook_library/provision/pxe_server.yml"
dhcp_file="$PWD/dhcp_clients_mac.txt"

# Optional limit (host or group)
LIMIT_NODE="${1:-}"

chmod +x "$pxe_server_script"

cmd=(python3 "$pxe_server_script"
     --playbook "$pxe_server_playbook"
     --dhcp-file "$dhcp_file")

if [[ -n "$LIMIT_NODE" ]]; then
  cmd+=(--limit "$LIMIT_NODE")
fi

echo "[INFO] Running: ${cmd[*]}"
"${cmd[@]}"
