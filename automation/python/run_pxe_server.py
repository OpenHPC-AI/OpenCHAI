#!/usr/bin/env python3

import argparse
import subprocess
import sys
import yaml
from pathlib import Path

TEMP_VARS_FILE = "/tmp/pxe_dhcp_clients.yml"


# ---------------------------------------------------------
# DHCP CLIENT FILE PARSER
# ---------------------------------------------------------
def parse_dhcp_file(file_path):
    clients = []

    with open(file_path, "r") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split(",")]

            if len(parts) != 3:
                print(f"[ERROR] Invalid format at line {lineno}: {line}")
                print("Expected: name,mac,ip")
                sys.exit(1)

            clients.append({
                "name": parts[0],
                "mac": parts[1],
                "ip": parts[2]
            })

    if not clients:
        print("[ERROR] No valid DHCP clients found in input file")
        sys.exit(1)

    return clients


# ---------------------------------------------------------
# DISPLAY CLIENTS
# ---------------------------------------------------------
def display_clients(clients):
    print("\nConfigured DHCP Clients")
    print("-" * 65)
    print(f"{'NAME':20} {'MAC':20} {'IP'}")
    print("-" * 65)

    for c in clients:
        print(f"{c['name']:20} {c['mac']:20} {c['ip']}")

    print("-" * 65)


# ---------------------------------------------------------
# INTERACTIVE UPDATE
# ---------------------------------------------------------
def update_clients(clients):
    while True:
        ans = input("\nUpdate any DHCP client? (yes/no): ").strip().lower()
        if ans not in ("yes", "no"):
            continue

        if ans == "no":
            return clients

        name = input("Enter node name to update: ").strip()
        client = next((c for c in clients if c["name"] == name), None)

        if not client:
            print("[WARN] Node not found")
            continue

        print(f"Current MAC: {client['mac']}")
        print(f"Current IP : {client['ip']}")

        new_mac = input("New MAC (Enter to keep): ").strip()
        new_ip = input("New IP  (Enter to keep): ").strip()

        if new_mac:
            client["mac"] = new_mac
        if new_ip:
            client["ip"] = new_ip

        print("[INFO] Client updated")
        display_clients(clients)


# ---------------------------------------------------------
# CONFIRMATION
# ---------------------------------------------------------
def confirm_execution():
    ans = input("\nProceed with PXE configuration? (yes/no): ").strip().lower()
    if ans != "yes":
        print("[INFO] Operation cancelled")
        sys.exit(0)


# ---------------------------------------------------------
# WRITE TEMP VARS FILE
# ---------------------------------------------------------
def write_vars_file(clients):
    data = {"dhcp_clients": clients}
    with open(TEMP_VARS_FILE, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False)

    print(f"[INFO] Generated vars file: {TEMP_VARS_FILE}")


# ---------------------------------------------------------
# RUN ANSIBLE
# ---------------------------------------------------------
def run_ansible(playbook, limit):
    cmd = [
        "ansible-playbook",
        playbook,
        "-e", f"@{TEMP_VARS_FILE}"
    ]

    if limit:
        cmd.extend(["-l", limit])

    print("\n[INFO] Executing Ansible command:")
    print(" ".join(cmd))

    subprocess.run(cmd, check=True)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Enterprise PXE Server Provisioning CLI"
    )

    parser.add_argument(
        "--playbook",
        required=True,
        help="PXE server playbook path"
    )

    parser.add_argument(
        "--dhcp-file",
        required=True,
        help="DHCP client input file (name,mac,ip)"
    )

    parser.add_argument(
        "--limit",
        required=False,
        help="Limit execution to a specific host or group (-l)"
    )

    args = parser.parse_args()

    dhcp_file = Path(args.dhcp_file)
    playbook = Path(args.playbook)

    if not dhcp_file.exists():
        print(f"[ERROR] DHCP file not found: {dhcp_file}")
        sys.exit(1)

    if not playbook.exists():
        print(f"[ERROR] Playbook not found: {playbook}")
        sys.exit(1)

    clients = parse_dhcp_file(dhcp_file)
    display_clients(clients)
    update_clients(clients)
    confirm_execution()
    write_vars_file(clients)
    run_ansible(str(playbook), args.limit)


if __name__ == "__main__":
    main()
