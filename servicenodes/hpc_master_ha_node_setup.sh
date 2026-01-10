#!/bin/bash
set -e

base_dir="/OpenCHAI"

PYTHON_CLI="$base_dir/automation/python/run_ha_master_cli.py"
PLAYBOOK="$base_dir/automation/ansible/playbook_library/provision/ha_master.yml"

LIMIT_NODE="${1:-}"

chmod +x "$PYTHON_CLI"

cmd=(python3 "$PYTHON_CLI"
     --playbook "$PLAYBOOK")

if [[ -n "$LIMIT_NODE" ]]; then
  cmd+=(--limit "$LIMIT_NODE")
fi

echo "[INFO] Running: ${cmd[*]}"
"${cmd[@]}"
