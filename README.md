# OpenCHAI
The OpenCHAI Manager Tool is a unified, modular automation framework designed to simplify and accelerate the deployment, configuration, and management of HPC and AI clusters. It integrates provisioning, orchestration, workload scheduling, and monitoring using industry-standard tools like xCAT, Ansible, SLURM, and Kubernetes.

# OpenCHAI Deployment and Quickstart Guide
The Quickstart is intended for deployment on **dedicated nodes or virtual machines (VMs)** running an **RPM-based Linux distribution** with an **x86_64 architecture**.

A **minimum high-availability (HA) master node configuration** requires **three stateful nodes** — two permanent and one temporary (which can also be made permanent if desired) — along with at least **one stateful compute node** and an **optional stateful GPU node**.

Both master nodes must include a **25 GB `/drbd` partition** to support data replication and synchronization between them.


# OpenCHAI Manager Tool Setup
#Install the git package 

```python
yum install git
```

#Clone the repository

```python
git clone https://github.com/OpenHPC-AI/OpenCHAI.git
```

#Run configuration script to setup the manager tool

```python
$ cd ./OpenCHAI

#Update the inventory file with all service node details for your cluster, based on your environment configuration.

$ vim chai_setup/inventory_def.txt

#Once the inventory definition file is updated, set up the Chai Manager tool on the head node to deploy and configure the HPC-AI cluster

$ bash ./configure.sh

```
