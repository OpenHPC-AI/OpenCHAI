#!/usr/bin/env python3
"""
OpenCHAI – HPC Provisioning Control Plane
Phase + Tag level interactive controller
"""

import argparse
import subprocess
import sys

# =============================================================================
# PHASE DEFINITIONS (1-based)
# =============================================================================

PHASES = {
    1: {
        "name": "PHASE 1 – Pre-requisites",
        "tags": [
            "phase1", "security", "firewall", "selinux", "bootstrap",
            "web_repo", "hosts_file", "standard_dir",
            "storage", "nfs", "sshd", "chrony"
        ],
    },
    2: {
        "name": "PHASE 2 – High Availability",
        "tags": [
            "phase2", "ha", "kernel",
            "pcs_drbd_pkg", "drbd_config", "pcs_config"
        ],
    },
    3: {
        "name": "PHASE 3 – Network",
        "tags": [
            "phase3", "network", "mellanox", "ip_config", "nm_service"
        ],
    },
    4: {
        "name": "PHASE 4 – Container Platform",
        "tags": [
            "phase4", "container",
            "docker_engine", "docker_compose", "docker_swarm"
        ],
    },
    5: {
        "name": "PHASE 5 – xCAT Provisioning",
        "tags": [
            "phase5", "provisioning",
            "xcat_container", "xcat_hostmachine",
            "pcs_xcat_resource", "xcat_osimage"
        ],
    },
    6: {
        "name": "PHASE 6 – Authentication",
        "tags": [
            "phase6", "auth",
            "ldap_container", "ldap_hostmachine"
        ],
    },
    7: {
        "name": "PHASE 7 – Workload Management",
        "tags": [
            "phase7", "workload", "slurm_config"
        ],
    },
    8: {
        "name": "PHASE 8 – Utilities & Monitoring",
        "tags": [
            "phase8", "utilities", "lmod",
            "monitoring", "mcelog", "rsyslog"
        ],
    },
}

# =============================================================================
# UI HELPERS
# =============================================================================

def banner(playbook):
    print("=" * 80)
    print(" OpenCHAI – HPC Provisioning Control Plane")
    print("=" * 80)
    print(f" Playbook : {playbook}")
    print(" Control  : Phase + Tag selection")
    print("=" * 80)
    print()

def show_phases():
    print("Available Provisioning Phases")
    print("-" * 80)
    for i in PHASES:
        print(f"[{i}] {PHASES[i]['name']}")
        print(f"    Tags: {', '.join(PHASES[i]['tags'])}")
    print("-" * 80)
    print("Examples:")
    print("  3           → PHASE 3 only")
    print("  1,3,5       → Multiple phases")
    print("  all         → All phases")
    print()

def show_tags(tags):
    print("\nAvailable Tags (from selected phases)")
    print("-" * 80)
    for t in sorted(tags):
        print(f" - {t}")
    print("-" * 80)
    print("Examples:")
    print("  docker_engine")
    print("  docker_engine,docker_swarm")
    print("  all")
    print()

# =============================================================================
# INPUT PARSERS
# =============================================================================

def parse_numeric_selection(prompt, valid_values):
    raw = input(prompt).strip().lower()

    if raw in ("", "none"):
        return set()

    if raw in ("all", "a"):
        return set(valid_values)

    try:
        values = {int(x) for x in raw.split(",")}
    except ValueError:
        sys.exit("[ERROR] Invalid numeric input.")

    invalid = values - set(valid_values)
    if invalid:
        sys.exit(f"[ERROR] Invalid selection: {invalid}")

    return values


def parse_tag_selection(prompt, valid_tags):
    raw = input(prompt).strip().lower()

    if raw in ("", "none"):
        return set()

    if raw in ("all", "a"):
        return set(valid_tags)

    values = {x.strip() for x in raw.split(",")}
    invalid = values - valid_tags

    if invalid:
        sys.exit(f"[ERROR] Invalid tag(s): {invalid}")

    return values

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="OpenCHAI HA Master Provisioning CLI"
    )
    parser.add_argument("--playbook", required=True)
    parser.add_argument("--limit")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--yes", action="store_true")

    args = parser.parse_args()

    banner(args.playbook)
    show_phases()

    run_phases = parse_numeric_selection(
        "Select PHASES to RUN (ENTER = all): ",
        PHASES.keys()
    )

    exclude_phases = parse_numeric_selection(
        "Select PHASES to EXCLUDE (ENTER = none): ",
        PHASES.keys()
    )

    # Resolve phases
    selected_phases = set(run_phases) if run_phases else set(PHASES.keys())
    selected_phases -= exclude_phases

    if not selected_phases:
        sys.exit("[ERROR] No phases selected after exclusion.")

    # Collect tags
    all_tags = {
        tag
        for p in selected_phases
        for tag in PHASES[p]["tags"]
    }

    show_tags(all_tags)

    run_tags = parse_tag_selection(
        "Select TAGS to RUN (ENTER = all): ",
        all_tags
    )

    exclude_tags = parse_tag_selection(
        "Select TAGS to EXCLUDE (ENTER = none): ",
        all_tags
    )

    # Resolve tags
    final_tags = set(run_tags) if run_tags else set(all_tags)
    final_tags -= exclude_tags

    if not final_tags:
        sys.exit("[ERROR] No tags selected after exclusion.")

    # =============================================================================
    # CONFIRMATION
    # =============================================================================

    print("\nExecution Plan")
    print("-" * 80)
    for p in sorted(selected_phases):
        print(f"✔ {PHASES[p]['name']}")
    print("-" * 80)
    print(f"Tags: {', '.join(sorted(final_tags))}")
    print("-" * 80)

    if not args.yes:
        confirm = input("Proceed with execution? (yes/no): ").strip().lower()
        if confirm not in ("yes", "y"):
            print("Execution cancelled.")
            sys.exit(0)

    cmd = [
        "ansible-playbook",
        args.playbook,
        "--tags", ",".join(sorted(final_tags))
    ]

    if args.limit:
        cmd += ["--limit", args.limit]
    if args.check:
        cmd.append("--check")

    print("\n[INFO] Running:")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

# =============================================================================

if __name__ == "__main__":
    main()
