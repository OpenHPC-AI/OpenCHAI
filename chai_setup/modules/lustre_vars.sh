#!/bin/bash
ALL_YML="../../automation/ansible/group_vars/all.yml"

echo ">>> Configuring Lustre Variables"

fields=(
  storage_vm_server_ip_one
  storage_vm_server_ha_ip_one
  storage_vm_server_ip_two
  storage_vm_server_ha_ip_two
  lnet_networks
  lnet_networks_ha
  lustre_mounts_dest_primary_path
  lustre_mounts_src_primary_path
  lustre_mounts_dest_secondary_path
  lustre_mounts_src_secondary_path
)

for key in "${fields[@]}"; do
    cur=$(grep "^$key:" "$ALL_YML" | awk '{print $2}')
    read -p "$key [$cur]: " new
    new="${new:-$cur}"
    sed -i "s|^$key:.*|$key: $new|" "$ALL_YML"
done

echo "✔ Lustre Variables Updated."
