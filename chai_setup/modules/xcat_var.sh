#!/bin/bash
ALL_YML="../../automation/ansible/group_vars/all.yml"

echo ">>> Configuring xCAT Variables (Module 5)"

fields=(
  xcat_version_tag
  xcat_container_img_tar
  xcat_docker_img
)

for key in "${fields[@]}"; do
    cur=$(grep "^$key:" "$ALL_YML" | awk '{print $2}')
    read -p "$key [$cur]: " new
    new="${new:-$cur}"
    sed -i "s|^$key:.*|$key: $new|" "$ALL_YML"
done

echo "✔ xCAT Variables Updated."
