🧰 **xCAT Container HA Deployment**

***(Docker Swarm + DRBD + Ansible)***

This repository contains an automated framework to deploy xCAT (Extreme Cloud Administration Toolkit) in a High-Availability (HA) configuration using:

Docker Swarm (for cluster-managed container orchestration)

DRBD (for synchronous disk replication between master nodes)

Ansible (for automated provisioning and failover control)

The system ensures reliable xCAT operation, persistent shared storage, and smooth failover between two master nodes.

```
🏗️ Architecture Overview
Docker Swarm Manager Nodes
        ┌───────────────┐          ┌───────────────┐
        │  headnode01   │          │  headnode02   │
        │ (Primary)     │          │ (Secondary)   │
        └───────────────┘          └───────────────┘
                 │                          │
                 ▼                          ▼
           /drbd mounted           /drbd not mounted
             (active)                 (standby)

📦 Shared DRBD Volume Layout

The following directories are replicated between both nodes via DRBD and mounted inside the xCAT container:

/xcatdata
/var/log/xcat
/var/lib/mysql

```

This ensures xCAT configuration, logs, and database remain consistent across failovers.



---

## ⚙️ Key Features

* 🐳 **Dockerized xCAT** — Portable and version-controlled
* 🧩 **Ansible Automated Deployment** — Consistent & repeatable
* 🔁 **High Availability with DRBD** — Data mirrored between masters
* 🕹️ **Swarm Label Control** — Containers only run on labeled manager nodes
* 🧾 **Dynamic Image Fetch** — Automatically uses the locally available xCAT image

---

## 📂 Directory Structure

```
roles/xcat_container_lib/tasks/
├── main.yml
├── assign_docker_swarm_labels.yml
├── create_xcat_drbd_dirs.yml
├── load_xcat_image.yml
├── xcat_dev_env.yml
├── deploy_xcat_docker_compose.yml
└── create_xcat_containers.yml
```

---

## 🧩 Files Overview

| File                                    | Purpose                                                    |
| --------------------------------------- | ---------------------------------------------------------- |
| **main.yml**                            | Master orchestrator that calls all subtasks                |
| **assign_docker_swarm_labels.yml**      | Adds labels to Swarm manager nodes                         |
| **create_xcat_drbd_dirs.yml**           | Creates DRBD-backed persistent directories                 |
| **load_xcat_image.yml**                 | Pulls or loads xCAT Docker image locally                   |
| **xcat_dev_env.yml**                    | Generates `.env` file aligned with host parameters         |
| **deploy_xcat_docker_compose.yml**      | Generates docker-compose (Jinja2 template)                 |
| **create_xcat_containers.yml**          | Creates and starts the xCAT container (active master only) |

---

## 📋 Prerequisites

| Component         | Minimum Version                               | Notes                                      |
| ----------------- | --------------------------------------------- | ------------------------------------------ |
| **Docker Engine** | ≥ 20.10                                       | Installed and configured on both masters   |
| **Docker Swarm**  | Initialized and both nodes joined as managers |                                            |
| **DRBD**          | Configured and synced between both nodes      |                                            |
| **Ansible**       | ≥ 2.14                                        | Used for orchestration                     |
| **xCAT Image**    | 2.17.0 (based on AlmaLinux 8.9)               | Can be customized in `xcat_image` variable |
| **SSH Access**    | Password-less between both master nodes 
                      (Not Compulsory)                             | For Better Experience                      |

---

## 🧾 Variables (from `xcat_ha_setup.yml`)

| Variable                  | Description                               | Example                            |
| ------------------------- | ----------------------------------------- | ---------------------------------- |
| `primary_swarm_manager`   | Hostname of primary Swarm master          | `hpc-master01`                     |
| `secondary_swarm_manager` | Hostname of secondary Swarm master        | `hpc-master02`                     |
| `swarm_label_key`         | Swarm label used to identify xCAT masters | `xcat_master`                      |
| `swarm_label_value`       | Value of Swarm label                      | `true`                             |
| `xcat_version`            | xCAT container version                    | `2.17.0`                           |
| `xcat_image`              | xCAT container image                      | `cdac_xcat/alma8.9:2.17.0`         |
| `xCAT_reg_path`           | Registry path containing xCAT image       | `/hpctool_stack/xcat_repo/`        |

---

## 🚀 How to Deploy

### 1️⃣  Prepare the Environment

```bash
# On both nodes
sudo systemctl enable docker --now
sudo docker swarm init --advertise-addr <primary_ip>
sudo docker swarm join-token manager  # run this on secondary
```

### 2️⃣  Ensure DRBD is Configured

Verify `/drbd` is mounted on one node and secondary is in sync:

```bash
mount | grep drbd
cat /proc/drbd
```

### 3️⃣  Run the Ansible Playbook

```bash
ansible-playbook OpenCHAI/automation/ansible/playbook_library/provision/xcat-container/xcat-management/configure_xcat_ha_cluster.yml -i inventory/hosts
```

### 4️⃣  Verify the Deployment

```bash
docker service ls
docker ps | grep xcat
docker exec -it xcat /bin/bash
```

### 5️⃣  Test Failover

Unmount `/drbd` on the active node and promote it on the standby to confirm automatic xCAT container re-deployment.

---

## 🧩 Generated docker-compose (Template Example)

```yaml
services:
  xcat:
    image: {{ xcat_image }}
    env_file:
      - .env
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:ro
      - /drbd/xcatdata:/xcatdata
      - /drbd/var_log_xcat:/var/log/xcat
      - /drbd/xcat_mysqldata:/var/lib/mysql
      - /drbd/xcatcont_sshkey/.ssh/:/root/.ssh/
    deploy:
      replicas: 1
      restart_policy:
        condition: any
      placement:
        constraints:
          - node.labels.xcat_master == true
    networks:
      - host

networks:
  host:
    external: true
```

---

## 🔍 Validation Commands

```bash
docker images | grep xcat
ansible -m ping all
docker node ls
```

---

## 🧱 Troubleshooting

| Issue                       | Possible Cause                     | Resolution                                       |
| --------------------------- | ---------------------------------- | ------------------------------------------------ |
| xCAT container not starting | `/drbd` not mounted on active node | Mount DRBD volume before running playbook        |
| “No label found” error      | Swarm label missing                | Run role `docker_swarm_label.yml` manually       |
| Image not found             | Registry path incorrect            | Update `xCAT_reg_path` or ensure image is loaded |

---
