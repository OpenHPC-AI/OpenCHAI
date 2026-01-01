#!/bin/bash
set -euo pipefail

############################################
# PXE / Kickstart Variable Update Module
############################################

BASE_DIR="/OpenCHAI"
ALL_YML="$BASE_DIR/automation/ansible/group_vars/all.yml"

if [[ ! -f "$ALL_YML" ]]; then
  echo "❌ ERROR: $ALL_YML not found"
  exit 1
fi

echo "=============================================="
echo " PXE Server & Kickstart Variable Configuration "
echo "=============================================="

update_var() {
  local key="$1"
  local prompt="$2"

  local current
  current=$(grep -E "^${key}:" "$ALL_YML" | head -n1 | sed "s/^${key}:[[:space:]]*//")

  read -rp "$prompt [$current]: " input
  input="${input:-$current}"

  local safe_value
  safe_value=$(printf '%s\n' "$input" | sed 's/[\/&]/\\&/g')

  if grep -qE "^${key}:" "$ALL_YML"; then
    sed -i "s|^${key}:.*|${key}: ${safe_value}|" "$ALL_YML"
  else
    echo "${key}: ${safe_value}" >> "$ALL_YML"
  fi
}

############################################
# PXE Server Configuration
############################################
update_var pxe_boot_iso "PXE boot ISO filename"
update_var pxe_server_ip "PXE server IP"
update_var pxe_server_dhcp_range_start "PXE DHCP range start"
update_var pxe_server_dhcp_range_end "PXE DHCP range end"
update_var pxe_server_dns "PXE DNS server"

############################################
# Partition Sizes (MB)
############################################
update_var part_efi_size "EFI partition size (MB)"
update_var part_boot_size "BOOT partition size (MB)"
update_var part_swap_size "SWAP partition size (MB)"
update_var part_var_size "VAR partition size (MB)"

############################################
# LVM Configuration
############################################
update_var lvm_vg_name "LVM volume group name"
update_var lvm_pe_size "LVM PE size (MB)"
update_var lvm_swap_size "LVM swap size (MB)"
update_var lvm_var_size "LVM var size (MB)"

############################################
# Kickstart Configuration
############################################
update_var ks_timezone "Kickstart timezone"
update_var ks_bootproto "Kickstart boot protocol (dhcp/static)"
update_var ks_root_password "Kickstart root password"
update_var ks_type "Kickstart type (standard/lvm)"

echo
echo "✅ PXE & Kickstart variables updated successfully."
echo "📄 File: $ALL_YML"
echo "=============================================="
