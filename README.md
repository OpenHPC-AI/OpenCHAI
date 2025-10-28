# OpenCHAI
The OpenCHAI Manager Tool is a unified, modular automation framework designed to simplify and accelerate the deployment, configuration, and management of HPC and AI clusters. It integrates provisioning, orchestration, workload scheduling, and monitoring using industry-standard tools like xCAT, Ansible, SLURM, and Kubernetes.

# OpenCHAI Deployment and Quickstart Guide
The Quickstart is intended for deployment on **dedicated nodes or virtual machines (VMs)** running an **RPM-based Linux distribution** with an **x86_64 architecture**.

A **minimum high-availability (HA) master node configuration** requires **three stateful nodes** — two permanent and one temporary (which can also be made permanent if desired) — along with at least **one stateful compute node** and an **optional stateful GPU node**.

Both master nodes must include a **25 GB `/drbd` partition** to support data replication and synchronization between them.
