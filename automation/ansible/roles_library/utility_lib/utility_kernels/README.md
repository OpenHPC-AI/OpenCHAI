# README

This directory contains automation tasks related to kernel package handling and high-availability setup on Linux systems (RHEL/Rocky).

## Purpose

These tasks help ensure the system has the correct kernel-related RPMs installed, can handle downgrades when required, and sets up tools needed for DRBD and cluster high availability.
- Detects OS platform and major version.
- Supports downloading kernel RPMs from:
  - Local directory (pre-downloaded RPMs).
  - Remote repositories (e.g. Oracle, Rocky, AlmaLinux, RHEL).
- Dynamically imports the correct GPG key for the target OS.
- Verifies all expected kernel RPMs are downloaded and valid.
- Installs and validates kernel version on target hosts.



## 📦 Required Kernel RPMs

The following packages are expected for a complete kernel installation:

- `kernel`
- `kernel-core`
- `kernel-devel`
- `kernel-headers`
- `kernel-modules`
- `kernel-modules-extra`
- `kernel-tools`
- `kernel-tools-libs`

Each is verified after download.

---

### `tasks/download_kernel_package.yml`
Downloads kernel RPMs from Oracle Linux's repositories. Falls back to a secondary URL if a package isn't found at the default location.

### `tasks/drbd_pcs_packages.yml`
Sets up DRBD and cluster tools:
- Installs DRBD kernel modules and user tools
- Enables required system repositories
- Installs `pcs`, `pacemaker`, and related HA packages

### `tasks/kernel_packages1.yml`
Validates whether all required kernel RPMs matching the system's kernel version are installed:
- Warns and prompts before downgrading if a higher version is present
- Ensures consistency across kernel modules

### `tasks/main.yml`
Entry file that calls the above tasks in sequence.

---

### `vars/main.yml`
## ⚙️ Role Variables

| Variable               | Default                                       | Description                                       |
|------------------------|-----------------------------------------------|---------------------------------------------------|
| `default_kernel_version` | `"5.14.0-427.13.1.el9_4"`                    | Kernel version to be installed                    |
| `kernel_rpm_dir`         | `"/home/CHAI_Sk/automation/ansible/rpm-stack/kernel_rpms"` | Path to store or read RPMs from                   |
| `rpm_base_urls`          | List of URLs (BaseOS, AppStream, third fallback) | Used for online fetch when local RPMs are absent  |

Defines:
- The currently running kernel version
- The exact list of kernel RPMs that must be installed for compatibility
- Repository URLs used for RPM fetching

---

## Need

This setup is required when:
- You are preparing a system with strict kernel version dependencies (e.g., for OFED, DRBD)
- Downgrade or reinstall of specific kernel packages is needed
- High Availability (HA) stack needs to be set up cleanly and repeatably across systems
