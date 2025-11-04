#!/usr/bin/env python3
import json
import sys
import argparse

def parse_input_file(filename):
    """
    Parse a simple text file where each line is:
    ansible_hostname ip ansible_user ansible_password group hostname
    Example:
    hpc-master01 192.168.1.10 root mypass hpc_master master01
    hpc-mgmt01   192.168.1.20 admin secret hpc_management mgmt01
    """
    groups = {}
    hostvars = {}

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            try:
                hostname, ip, user, password, group = line.split()
            except ValueError:
                print(f"Invalid line in inventory file: {line}", file=sys.stderr)
                continue

            if group not in groups:
                groups[group] = {"hosts": [], "vars": {}}
            groups[group]["hosts"].append(hostname)

            hostvars[hostname] = {
                "ansible_host": ip,
                "ansible_user": user,
                "ansible_password": password
            }

    return groups, hostvars


def generate_inventory(input_file):
    groups, hostvars = parse_input_file(input_file)

    inventory = {
        "_meta": {
            "hostvars": hostvars
        }
    }

    inventory.update(groups)
    return inventory


def main():
    parser = argparse.ArgumentParser(description="Flexible Dynamic Inventory")
    parser.add_argument("--list", action="store_true", help="Output full inventory")
    parser.add_argument("--host", help="Output details for a specific host")
    parser.add_argument("--input-file", default="inventory.txt",
                        help="Path to user input file (default: inventory.txt)")

    args = parser.parse_args()

    if args.list:
        inventory = generate_inventory(args.input_file)
        print(json.dumps(inventory, indent=2))

    elif args.host:
        groups, hostvars = parse_input_file(args.input_file)
        host_data = hostvars.get(args.host, {})
        print(json.dumps(host_data, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
