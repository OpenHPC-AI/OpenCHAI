📘 Infrastructure Automation Playbook Library
(Ansible • HPC • Docker Swarm • xCAT • DRBD • Linux Automation)

This repository contains a well-structured playbook library designed for automating HPC and cloud infrastructure components such as:

xCAT (Cluster Administration Toolkit)

Docker Swarm HA

DRBD storage replication

Networking and security configuration

Cluster provisioning and monitoring

Storage, services, and application stack deployment

The library is organized into multiple functional parent directories, allowing administrators and developers to quickly locate the correct automation module.

🗂️ Directory Overview

Below is the explanation of each parent directory and what type of playbooks belong there.

🥾 bootstrap/ – Initial System Preparation

This directory contains playbooks that must run before any installation or configuration.

📌 Use it for:

OS validation

Package installation (dnf/yum)

Firewall/SELinux initial state

Enabling required repositories

Preparing DRBD mount

Installing Docker Engine/Swarm prerequisites

Initial SSH setup

📄 Example:
bootstrap/
 ├── pre-requisite.yml
 ├── verify_os.yml
 └── setup_basic_packages.yml

🧩 install/ – Software Installation

Contains playbooks to install infrastructure components.

📌 Use it for:

Installing xCAT

Installing SLURM, LDAP, MariaDB

Installing monitoring agents

Installing InfiniBand drivers (OFED)

📄 Example:
install/
 ├── install_xcat.yml
 ├── install_mariadb.yml
 └── install_slurm.yml

⚙️ configure/ – Post-Installation Configuration

These playbooks configure the software installed in the previous stage.

📌 Use it for:

xCAT site table setup

DHCP/DNS configuration

NTP/Chrony setup

Sysctl and kernel tuning

Slurm configs

LDAP attributes

📄 Example:
configure/
 ├── configure_xcat.yml
 ├── configure_dhcp.yml
 └── configure_slurm_settings.yml

📦 container/ – Docker/Podman/Swarm Automation

Playbooks to deploy or manage containers and container stacks.

📌 Use it for:

Building xCAT container images

docker-compose generation

Docker swarm initialization

Swarm stack deploy/update/rollback

Container health checks

📄 Example:
container/
 ├── build_xcat_image.yml
 ├── deploy_xcat_stack.yml
 └── create_xcat_containers.yml

🏗️ provision/ – Provisioning Nodes & Cluster Resources

Playbooks that add nodes, build OS images, or allocate resources.

📌 Use it for:

Adding compute/GPU/login nodes

Generating OS images for xCAT

Creating provisioning profiles

IP assignment automation

Node discovery

📄 Example:
provision/
 ├── add_compute_nodes.yml
 ├── generate_osimage.yml
 └── provision_xcat_nodes.yml

🖧 network/ – Network Configuration & Validation

Everything required to bring up or verify cluster networking.

📌 Use it for:

Interface/bonding/VLAN configuration

DNS/DHCP/NIS

Routing rules

InfiniBand subnet manager (opensmd)

NTP synchronization

📄 Example:
network/
 ├── configure_bonding.yml
 ├── setup_dns.yml
 └── verify_network.yml

🛡️ security/ – Hardening & Access Control

Playbooks for implementing security best practices.

📌 Use it for:

SELinux management

Firewall policies

SSL/TLS certificate deployment

LDAP authentication

SSH hardening

📄 Example:
security/
 ├── configure_selinux.yml
 ├── setup_firewall.yml
 └── secure_ssh.yml

🔧 services/ – Service Management

Handles Linux services and daemon operations.

📌 Use it for:

Starting/stopping/enabling services

Reloading configurations

Validating service health

Managing MariaDB, DHCP, xCAT, Docker daemons

📄 Example:
services/
 ├── restart_xcat.yml
 ├── manage_mariadb.yml
 └── validate_services.yml

🗄️ storage/ – Storage, DRBD, LVM, RAID

Automation related to local or distributed storage setups.

📌 Use it for:

DRBD replication setup

RAID configuration

LVM provisioning

NFS exports and mounts

Container persistent storage

📄 Example:
storage/
 ├── configure_drbd.yml
 ├── setup_lvm.yml
 └── mount_storage.yml

📊 monitoring/ – Observability & Metrics

Playbooks for monitoring stack deployment and log management.

📌 Use it for:

Prometheus/Nagios installation

Node exporter configuration

Log rotation

Application health checks

Monitoring container status

📄 Example:
monitoring/
 ├── install_prometheus.yml
 ├── configure_rsyslog.yml
 └── healthcheck_containers.yml

🧰 utility/ – Helper Tools (General Purpose)

Utility playbooks are non-critical helpers used by developers and admins.

📌 Use it for:

Cleanup tasks

Debugging information

File sync or backup

Reusable helper functions

Temporary scripts used during maintenance

📄 Example:
utility/
 ├── cleanup_logs.yml
 ├── backup_xcatdata.yml
 └── collect_debug_info.yml

🤖 ai_stack/ – AI/ML/HPC Stack Deployment

Playbooks specifically for GPU, AI, and HPC application installation.

📌 Use it for:

HPL/HPCG benchmark installation

NCCL test setup

CUDA toolkit validation

AI/ML framework installs (TensorFlow/PyTorch)

📄 Example:
ai_stack/
 ├── install_nccl.yml
 ├── run_hpl.yml
 └── deploy_ai_containers.yml
