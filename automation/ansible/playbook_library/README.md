# 📘 Infrastructure Automation Playbook Library

### *Ansible • HPC • Docker Swarm • xCAT • DRBD • Linux Automation*

This repository contains a well-structured **Ansible playbook library** for automating High-Performance Computing (HPC) and cloud infrastructure components, including:

* xCAT (Cluster Administration Toolkit)
* Docker Swarm HA
* DRBD replicated storage
* System provisioning
* Configuration management
* Monitoring
* Security and networking automation

The library is divided into modular **parent directories**, each dedicated to a specific area of automation.
This structure makes it easy for System Administrators, DevOps Engineers, SREs, and Developers to find the correct playbooks quickly.



# 🗂️ Directory Overview

Below is a complete explanation of each parent directory and the type of playbooks it should contain.

---

## 🥾 `bootstrap/` — Initial System Preparation

Contains playbooks that must run **before installation or configuration** begins.

### Use it for:

* OS validation
* Installing base packages (dnf/yum)
* Setting SELinux/firewall defaults
* Enabling required repositories
* Preparing DRBD mount
* Installing Docker Engine prerequisites
* Initial SSH setup

```
bootstrap/
 ├── pre-requisite.yml
 ├── verify_os.yml
 └── setup_basic_packages.yml
```

---

## 🧩 `install/` — Software Installation

Responsible for installing major system components.

### Use it for:

* xCAT installation
* SLURM/MariaDB/LDAP install
* Monitoring tools
* OFED/InfiniBand driver setup

```
install/
 ├── install_xcat.yml
 ├── install_mariadb.yml
 └── install_slurm.yml
```

---

## ⚙️ `configure/` — Post-Installation Configuration

Configures services **after installation**.

### Use it for:

* xCAT site table setup
* DHCP/DNS configuration
* NTP / Chrony
* Kernel and sysctl tuning
* SLURM configuration
* LDAP attribute tuning

```
configure/
 ├── configure_xcat.yml
 ├── configure_dhcp.yml
 └── configure_slurm_settings.yml
```

---

## 📦 `container/` — Docker/Podman/Swarm Automation

Playbooks for building, deploying, and managing containers.

### Use it for:

* Building xCAT container image
* docker-compose generation
* Docker Swarm initialization
* Stack deploy/update/rollback
* Container health checks

```
container/
 ├── build_xcat_image.yml
 ├── deploy_xcat_stack.yml
 └── create_xcat_containers.yml
```

---

## 🏗️ `provision/` — Node & Cluster Resource Provisioning

Playbooks related to bringing new nodes into the cluster.

### Use it for:

* Adding compute/GPU/login nodes
* Generating OS images
* Creating provisioning profiles
* IP address automation
* Node discovery workflows

```
provision/
 ├── add_compute_nodes.yml
 ├── generate_osimage.yml
 └── provision_xcat_nodes.yml
```

---

## 🖧 `network/` — Networking Configuration

Handles everything related to network automation.

### Use it for:

* Interface / bonding / VLAN setup
* DNS / DHCP / NIS
* Routing tables
* InfiniBand opensmd subnet manager
* NTP sync configuration

```
network/
 ├── configure_bonding.yml
 ├── setup_dns.yml
 └── verify_network.yml
```

---

## 🛡️ `security/` — Security & Hardening

Security-focused automation.

### Use it for:

* SELinux setup
* Firewall rules
* SSL/TLS certificate management
* SSH hardening
* LDAP authentication

```
security/
 ├── configure_selinux.yml
 ├── setup_firewall.yml
 └── secure_ssh.yml
```

---

## 🔧 `services/` — Service Management

General service lifecycle operations.

### Use it for:

* Start/stop/reload services
* Validating daemon health
* Managing MariaDB / DHCP / xCAT / Docker

```
services/
 ├── restart_xcat.yml
 ├── manage_mariadb.yml
 └── validate_services.yml
```

---

## 🗄️ `storage/` — DRBD / LVM / RAID / Persistent Storage

Everything related to storage configuration.

### Use it for:

* DRBD cluster setup
* RAID creation
* LVM provisioning
* NFS exports/mounts
* Persistent volumes for containers

```
storage/
 ├── configure_drbd.yml
 ├── setup_lvm.yml
 └── mount_storage.yml
```

---

## 📊 `monitoring/` — Observability & Metrics

Handle monitoring and log analysis.

### Use it for:

* Prometheus/Nagios/Grafana deployment
* Node exporter setup
* Log rotation
* Health checks for containers or services

```
monitoring/
 ├── install_prometheus.yml
 ├── configure_rsyslog.yml
 └── healthcheck_containers.yml
```

---

## 🧰 `utility/` — Helper Tools & Maintenance Tasks

Reusable helper scripts and utilities.

### Use it for:

* Cleanup tasks
* Backup scripts
* File sync helpers
* Debug information collectors

```
utility/
 ├── cleanup_logs.yml
 ├── backup_xcatdata.yml
 └── collect_debug_info.yml
```

---

## 🤖 `ai_stack/` — AI / ML / GPU Workloads

Specialized playbooks for HPC/AI stack deployment.

### Use it for:

* HPL/HPCG benchmarks
* NCCL tests
* CUDA validation
* Deploying AI/ML containers

```
ai_stack/
 ├── install_nccl.yml
 ├── run_hpl.yml
 └── deploy_ai_containers.yml
```

---

---
