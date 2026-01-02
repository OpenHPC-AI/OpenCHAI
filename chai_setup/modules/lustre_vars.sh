#!/usr/bin/env bash
set -euo pipefail

############################################
# Lustre Variable Update Module
############################################

base_dir="/OpenCHAI"
ALL_YML="$base_dir/automation/ansible/group_vars/all.yml"

if [[ ! -f "$ALL_YML" ]]; then
  echo "❌ ERROR: $ALL_YML not found"
  exit 1
fi

echo "=============================================="
echo " Lustre Variable Configuration"
echo " File: $ALL_YML"
echo "=============================================="

############################################
# Generic YAML updater (SAFE)
############################################
update_var() {
  local key="$1"
  local prompt="$2"

  # Read full RHS safely (supports spaces)
  local current
  current=$(grep -E "^${key}:" "$ALL_YML" | head -n1 | sed "s/^${key}:[[:space:]]*//")

  read -rp "${prompt} (default: ${current}): " input
  input="${input:-$current}"

  # Escape sed-sensitive characters
  local safe_value
  safe_value=$(printf '%s\n' "$input" | sed 's/[\/&|\\]/\\&/g')

  if grep -qE "^${key}:" "$ALL_YML"; then
    sed -i "s|^${key}:.*|${key}: ${safe_value}|" "$ALL_YML"
  else
    echo "${key}: ${safe_value}" >> "$ALL_YML"
  fi
}

############################################
# Lustre Variables
############################################
update_var storage_vm_server_ip_one               "Storage VM Server Primary IP"
update_var storage_vm_server_ha_ip_one            "Storage VM Server HA Primary IP"
update_var storage_vm_server_ip_two               "Storage VM Server Secondary IP"
update_var storage_vm_server_ha_ip_two            "Storage VM Server HA Secondary IP"
update_var lnet_networks                          "LNet primary networks"
update_var lnet_networks_ha                       "LNet HA networks"
update_var lustre_mounts_dest_primary_path        "Lustre primary mount destination path"
update_var lustre_mounts_src_primary_path         "Lustre primary mount source path"
update_var lustre_mounts_dest_secondary_path      "Lustre secondary mount destination path"
update_var lustre_mounts_src_secondary_path       "Lustre secondary mount source path"

echo
echo "✅ Lustre variables updated successfully."
echo "=============================================="
