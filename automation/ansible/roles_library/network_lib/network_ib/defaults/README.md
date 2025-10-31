# README - network_ib

## Purpose

The `network_ib` task set is designed to configure and enable InfiniBand (IB) networking on systems that use high-performance interconnects, typically found in HPC or clustered environments.


ansible-playbook setup_mellanox.yml \
  --extra-vars "base_dir=/opt/my_dir install_mellanox=false"


## Need

This is required when:
- Setting up systems that rely on InfiniBand for low-latency, high-throughput communication.
- Ensuring IB interfaces (e.g., `ib0`, `mlx5_0`) are correctly detected, named, and brought up.
- Automating the installation of necessary IB tools and drivers to avoid manual configuration errors.

## What it does

- Installs essential InfiniBand packages (e.g., `infiniband-diags`, `rdma-core`, `ibutils`, `perftest`).
- Detects and configures IB interfaces on the node.
- Brings up the interfaces and optionally assigns IP addresses.
- Enables persistent naming or renaming if required for consistency across reboots.
- Verifies link status and basic IB connectivity (optional diagnostics).

> These tasks ensure that InfiniBand networking is properly initialized and available for high-performance workloads.
