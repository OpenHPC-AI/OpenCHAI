#!/bin/bash
ALL_YML="../../automation/ansible/group_vars/all.yml"

echo ">>> Configuring OpenLDAP Variables"

fields=(
  primary_ldap_node_ip
  secondary_ldap_node_ip
  ldap_base_dn
  ldap_version_tag
  ldap_container_img_tar
  openldap_container_image
)

for key in "${fields[@]}"; do
    cur=$(grep "^$key:" "$ALL_YML" | awk '{print $2}')
    read -p "$key [$cur]: " new
    new="${new:-$cur}"
    sed -i "s|^$key:.*|$key: $new|" "$ALL_YML"
done

echo "✔ LDAP Variables Updated."
