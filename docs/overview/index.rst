Overview
============

The **CHAI Cluster Manager Tool** is a unified, modular automation framework designed to simplify and accelerate the deployment, configuration, and management of **HPC and AI clusters**. It integrates provisioning, orchestration, workload scheduling, and monitoring using industry-standard tools like **xCAT**, **Ansible**, **SLURM**, **OpenLDAP** and **Kubernetes** etc.

The framework currently supports:

- **x86_64** architecture and multi OS-based environments
- Multiple software stack versions with version control
- Bare Metal and Virtual Machine
- Both **bare-metal** and **containerized software stack** of **HPC-AI infrastructure**
- **Multi-tenant Kubernetes control planes** for AI user(Team) isolation

# HPC Cluster Management and Service Nodes*

To efficiently manage the cluster, dedicated **service nodes** handle installation, deployment, and administrative tasks. These include:

- **Head Node -** A head node which is CHAI Manger tool. To configure all the service nodes. (It can be temporary or permanent.)
- **Master Nodes** – Manage compute nodes using **xCAT** for provisioning and **SLURM** for workload scheduling and ldap for central user authentication.
- **Management Nodes** – Handle monitoring, logging, and ticketing systems.
- **Login Nodes** – Provide user access to the cluster.
- **BMC (Baseboard Management Controller) Nodes** – Oversee hardware health and remote management.
- **Firewall Node** – Ensures network security
