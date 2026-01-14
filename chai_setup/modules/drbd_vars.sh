#!/usr/bin/env bash
set -euo pipefail

############################################
# DRBD / HA Variable Update Module
############################################

base_dir="/OpenCHAI"
ALL_YML="$base_dir/automation/ansible/group_vars/all.yml"

if [[ ! -f "$ALL_YML" ]]; then
  echo "❌ ERROR: $ALL_YML not found"
  exit 1
fi

echo "=============================================="
echo " DRBD / HA Variable Configuration"
echo " File: $ALL_YML"
echo "=============================================="

############################################
# Generic YAML updater (SAFE)
############################################
update_var() {
  local key="$1"
  local prompt="$2"

  # Read current value (entire RHS, safe for spaces)
  local current
  current=$(grep -E "^${key}:" "$ALL_YML" | head -n1 | sed "s/^${key}:[[:space:]]*//")

  read -rp "${prompt} [${current}]: " input
  input="${input:-$current}"

  # Escape sed replacement-sensitive characters
  local safe_value
  safe_value=$(printf '%s\n' "$input" | sed 's/[\/&|\\]/\\&/g')

  if grep -qE "^${key}:" "$ALL_YML"; then
    sed -i "s|^${key}:.*|${key}: ${safe_value}|" "$ALL_YML"
  else
    echo "${key}: ${safe_value}" >> "$ALL_YML"
  fi
}

############################################
# DRBD / PCS / VIP Variables
############################################
update_var private_interface              "Private interface (e.g. ib0 / ens192), default:"
update_var xcat_vip_ip                    "xCAT Virtual IP, default:"
update_var xcat_vip_interface             "VIP interface, default:"
update_var xcat_vip_subnet_prefix         "VIP subnet prefix (e.g. 24), default:"
update_var xcat_vip_resource_name         "PCS VIP resource name, default:"

drbd_primary_master_node_ip               "DRBD primary master node ip" 
drbd_secondary_master_node_ip             "DRBD secondary master node ip"
drbd_primary_master_node_hostname         "DRBD primary master node hostname"
drbd_secondary_master_node_hostname       "DRBD secondary master node hostname"

update_var drbd_resource_name             "DRBD resource name, default:"
update_var drbd_clone_name                "DRBD clone name, default:"
update_var drbd_fs_resource_name          "DRBD filesystem resource name, default:"
update_var drbd_device                    "DRBD device (e.g. /dev/drbd0), default:"
update_var drbd_mount_dir                 "DRBD mount directory, default:"
update_var drbd_fstype                    "DRBD filesystem type (xfs/ext4), default:"
update_var drbd_primitive_name            "DRBD primitive resource name, default:"
update_var drbd_sync_delay                "DRBD sync delay (seconds), default:"

update_var pcs_primary_master_node_hostname   "PCS primary master hostname, default:"
update_var pcs_secondary_master_node_hostname "PCS secondary master hostname, default:"
update_var pcs_cluster_password               "PCS cluster password, default:"
update_var pcs_cluster_name                   "PCS cluster name, default:"

echo
echo "✅ DRBD / HA variables updated successfully."
echo "=============================================="
