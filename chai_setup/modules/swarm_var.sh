#!/bin/bash
ALL_YML="../../automation/ansible/group_vars/all.yml"

echo ">>> Configuring Docker Swarm Variables (Module 4)"

fields=(
  primary_swarm_manager_ip
  primary_swarm_manager
  secondary_swarm_manager
  tertiary_swarm_manager
)

for key in "${fields[@]}"; do
    cur=$(grep "^$key:" "$ALL_YML" | awk '{print $2}')
    read -p "$key [$cur]: " new
    new="${new:-$cur}"
    sed -i "s|^$key:.*|$key: $new|" "$ALL_YML"
done

echo "✔ Docker Swarm Variables Updated."
