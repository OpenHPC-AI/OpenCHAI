#!/bin/bash

base_dir="/OpenCHAI"
ALL_YML="$base_dir/automation/ansible/group_vars/all.yml"

echo ">>> Configuring Third Docker Swarm Variables, Give ansible-inventory-hostname "


fields=(
  tertiary_swarm_manager
)

for key in "${fields[@]}"; do
    cur=$(grep "^$key:" "$ALL_YML" | awk '{print $2}')
    read -p "$key [$cur]: " new
    new="${new:-$cur}"
    sed -i "s|^$key:.*|$key: $new|" "$ALL_YML"
done

echo "✔ Docker Swarm Variables Updated."
