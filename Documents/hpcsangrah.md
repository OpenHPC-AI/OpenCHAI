**To install Openchai Packages**

```bash
# Multiple OS versions supports (Like: alma8.9, rocky9.4, rocky9.6) are available for download.
# Browse available options here:
# https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/hpcsuite_registry/hostmachine_reg/

# Multiple openchai version (openchai_ha_full_v1.24.0.tgz, openchai_ha_base_v1.24.0.tgz, openchai_ha_full_v1.25.0.tgz, openchai_ha_base_v1.25.0.tgz) are available for download

#Select the operating system version (AlmaLinux or Rocky Linux) according to your environment.

#Example: The following steps demonstrate downloading OpenCHAI packages for AlmaLinux 8.9 / RockyLinux 9.6 . The same procedure can be followed for Rocky Linux 9.4 or Rocky Linux 9.6.
```

**For AlmaLinux8.9:**

```bash
mkdir ./hpcsuite_registry/hostmachine_reg/alma8.9

wget -qO- \
https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/hpcsuite_registry/hostmachine_reg/alma8.9/openchai_ha_full_v1.25.0.tgz \
| tar -xzvf  -C "./hpcsuite_registry/hostmachine_reg/alma8.9"

#Make sure the openchai stack is pulled at  ../OpenCHAI/hpcsuite_registry/hostmachine_reg/alma8.9/ !

ls -lh ../OpenCHAI/hpcsuite_registry/hostmachine_reg/alma8.9/
```

**For RockyLinux9.6:**
```bash
mkdir ./hpcsuite_registry/hostmachine_reg/rocky9.6

wget -qO- \
https://hpcsangrah-test.pune.cdac.in:8008/vault/OpenCHAI/hpcsuite_registry/hostmachine_reg/rocky9.6/openchai_ha_full_v1.25.0.tgz \
| tar -xzvf  -C "./hpcsuite_registry/hostmachine_reg/rocky9.6"

#Make sure the openchai stack is pulled at  ../OpenCHAI/hpcsuite_registry/hostmachine_reg/rocky9.6/ !

ls -lh ../OpenCHAI/hpcsuite_registry/hostmachine_reg/rocky9.6/
```
