#!/bin/bash

base_dir="/OpenCHAI"
ALL_YML="$base_dir/automation/ansible/group_vars/all.yml"


echo ">>> Configuring OpenLDAP Variables"

fields=(
  ldap_base_dn
  ldap_version_tag
)

for key in "${fields[@]}"; do
    cur=$(grep "^$key:" "$ALL_YML" | awk '{print $2}')
    read -p "$key [$cur]: " new
    new="${new:-$cur}"
    sed -i "s|^$key:.*|$key: $new|" "$ALL_YML"
done

echo "✔ LDAP Variables Updated."
