#!/bin/bash

base_dir="/OpenCHAI"
ALL_YML="$base_dir/automation/ansible/group_vars/all.yml"

echo ">>> Configuring DRBD / HA Variables"

fields=(
  private_interface
  xcat_vip_ip
  xcat_vip_interface
  xcat_vip_subnet_prefix
  xcat_vip_resource_name
  drbd_resource_name
  drbd_clone_name
  drbd_fs_resource_name
  drbd_device
  drbd_mount_dir
  drbd_fstype
  pcs_primary_master_node_hostname
  pcs_secondary_master_node_hostname
  pcs_cluster_password
  pcs_cluster_name
)

for key in "${fields[@]}"; do
    cur=$(grep "^$key:" "$ALL_YML" | awk '{print $2}')
    read -p "$key [$cur]: " new
    new="${new:-$cur}"
    sed -i "s|^$key:.*|$key: $new|" "$ALL_YML"
done

echo "✔ DRBD/HA Variables Updated."
