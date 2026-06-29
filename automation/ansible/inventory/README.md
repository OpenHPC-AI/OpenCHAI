# Ansible Inventory & Vault Manager

Production-grade unified utility for dynamic Ansible inventory generation,
Ansible Vault password management, validation, backup/restore, and full host
lifecycle operations for enterprise and HPC environments.

---

## Architecture Decision: Unified Application (Option 1)

A **single `inventory.py`** application was chosen over separate utilities because:

| Concern | Unified | Separate |
|---|---|---|
| Secret isolation | One boundary to audit | Secrets cross process boundaries |
| Atomic host+vault ops | Trivially consistent | Requires orchestration |
| Locking | One lock file | Lock per utility (deadlock risk) |
| Error handling | Shared exception hierarchy | Duplicate handling code |
| Testing | One test suite | Multiple suites, integration gaps |
| Deployment | One file to ship | Multiple scripts to sync |

The internal design is still **modular**: `VaultManager`, `InventoryManager`,
validators, and the CLI are cleanly separated and independently testable.

---

## Directory Layout

```
.
├── inventory.py                    ← Main application (single entry point)
├── bootstrap_import.py             ← One-time migration from 7-field files
├── ansible.cfg
├── .vault_pass                     ← Vault encryption key (chmod 600, gitignored)
├── inventory/
│   ├── inventory.sh                ← Thin wrapper for ansible.cfg compatibility
│   ├── inventory_def.txt           ← 6-field host records (NO passwords)
│   ├── group_vars/
│   │   └── all/
│   │       ├── vars.yml            ← Non-secret group defaults
│   │       └── vault.yml           ← Encrypted passwords (ansible-vault)
│   └── host_vars/
│       ├── master01.yml            ← Per-host stub, references vault
│       └── ...
├── backups/                        ← Timestamped backup archives
├── logs/
│   └── inventory.log               ← Rotating log (10 MB × 5)
└── tests/
    └── test_inventory.py
```

---

## Quick Start

### 1. Prerequisites

```bash
pip install ansible-core          # provides ansible-vault
python3 --version                 # requires 3.11+
```

### 2. Create vault password file

```bash
echo "MyVaultEncryptionKey" > .vault_pass
chmod 600 .vault_pass
echo ".vault_pass" >> .gitignore
```

### 3. Bootstrap from existing 7-field definition file

If you have an existing file with passwords in the 7th column:

```bash
# Space-separated
python3 bootstrap_import.py nodes.txt

# The script:
#  - writes inventory/inventory_def.txt  (6 fields, no passwords)
#  - encrypts all passwords into vault.yml
#  - writes host_vars/ stubs
#  - DELETES nodes.txt automatically
```

---

## CLI Reference

### Ansible Dynamic Inventory (called by Ansible)

```bash
# Full inventory JSON
inventory.py --list

# Single host variables
inventory.py --host master01
```

### Host Management

```bash
# Interactive add (prompts for all fields, password not echoed)
inventory.py --add-host

# Delete host from inventory + vault
inventory.py --delete-host compute001

# Interactive update (blank = keep current value)
inventory.py --update-host gpu001
```

### Vault

```bash
# Sync vault from a 7-field definition file, then delete the file
inventory.py --sync-vault --def-file new_nodes.txt
```

### Validation

```bash
# Check inventory syntax + vault consistency
inventory.py --validate
```

### Backup & Restore

```bash
# Timestamped backup (inventory + vault + host_vars)
inventory.py --backup
# Output: backups/backup_20250601_143022/

# Restore from backup
inventory.py --restore backups/backup_20250601_143022
```

### Export / Import

```bash
# Export safe inventory JSON (no secrets)
inventory.py --export /tmp/inventory_snapshot.json

# Bootstrap import (see Quick Start above)
inventory.py --import nodes.txt           # deletes nodes.txt after import
inventory.py --import nodes.txt --no-delete   # INSECURE: keeps file
```

---

## Inventory File Format (6 fields, no password)

```
# node  ip  user  group  hostname  ssh_port
master01    192.168.10.11  root  hpc_master  master01  22
compute001  192.168.10.101 root  compute     cn001     22
gpu001      192.168.20.10  root  gpu         gpu001    4411
```

| Field | Description |
|---|---|
| node | Ansible inventory hostname |
| ip | IPv4 address (validated) |
| user | SSH login user |
| group | Ansible group (any name, HPC-aware) |
| hostname | Linux hostname |
| ssh_port | SSH port (1–65535) |

**Never add a password column.** Use `--sync-vault` or `--add-host`.

---

## Vault Structure (decrypted view)

```yaml
vault_passwords:
  master01:   "SuperSecure01"
  compute001: "ComputePass"
  gpu001:     "GpuPass"
```

Each host's `host_vars/<node>.yml` stub references the vault:

```yaml
ansible_user: root
ansible_host: 192.168.10.11
ansible_port: 22
ansible_password: "{{ vault_passwords[inventory_hostname] }}"
ansible_become_pass: "{{ vault_passwords[inventory_hostname] }}"
```

---

## Security Model

| Risk | Mitigation |
|---|---|
| Passwords in stdout | `HostRecord` never stores password; `--list`/`--host` output is password-free |
| Passwords in logs | Log messages scrub any `password=` matches with `[REDACTED]` |
| Passwords in inventory file | Parser **rejects** 7-field lines with `ParseError` |
| Passwords on disk unencrypted | `VaultManager` writes to temp → `ansible-vault encrypt` → atomic rename |
| Passwords in temp files | Temp files are always unlinked in `finally` blocks |
| Concurrent modifications | `FileLock` (fcntl exclusive) with 30s timeout |
| Partial writes | All writes go through `atomic_write()` (tempfile + `os.replace`) |
| Loose vault pass perms | Warning logged if `.vault_pass` is world/group readable |
| Source file with plaintext | `--import` deletes the file by default; `--sync-vault` prints a reminder |

---

## Error Handling Strategy

All errors map to the custom exception hierarchy:

```
InventoryError
├── ParseError          — malformed/missing inventory file
├── ValidationError     — bad IP / duplicate host / invalid port
├── VaultError          — ansible-vault failures / missing vault pass
├── LockError           — concurrent modification timeout
├── BackupError         — backup/restore filesystem errors
└── HostNotFoundError   — --delete-host / --update-host on unknown host
```

No uncaught exceptions reach the user. The `main()` function catches all
`InventoryError` subclasses and exits with code 1 + human-readable message.

---

## Logging Strategy

- **Dual sink**: rotating file (`logs/inventory.log`, 10 MB × 5) + stderr console
- **File level**: DEBUG (full detail including lock events)
- **Console level**: INFO and above (never DEBUG to avoid accidental secret exposure in terminals)
- **Secret scrubbing**: `VaultError` messages run through a regex that replaces `password=<value>` with `[REDACTED]`

```bash
inventory.py --validate --debug     # enable DEBUG on both sinks
```

---

## Validation Strategy

`inventory.py --validate` checks:

1. **File existence** — raises `ParseError` if missing
2. **Field count** — 6 required; 7 (with password) rejected
3. **IPv4 validity** — `ipaddress.IPv4Address` strict parse
4. **Port range** — 1–65535
5. **Name characters** — `[a-zA-Z0-9_\-\.]` only for node/group/hostname
6. **Duplicate nodes** — first occurrence wins, rest warned
7. **Duplicate IPs** — same policy
8. **Vault consistency** — cross-checks inventory nodes vs. vault entries
   - Missing vault entries (hosts without passwords) → warning
   - Orphan vault entries (deleted hosts still in vault) → info

---

## Scalability (10,000+ nodes)

- **Parser**: line-by-line streaming — O(n) memory, handles arbitrarily large files
- **Vault**: single encrypted YAML file; `ansible-vault` handles the crypto
- **Inventory caching**: `ansible.cfg` enables `cache_plugin = jsonfile` with 120s TTL
- **Lock timeout**: configurable; 30s default is safe for batch imports
- **Backup**: `shutil.copy2` per file (not full tar); fast for typical host_vars counts

For clusters > 50,000 nodes, consider splitting the vault by group
(one vault file per HPC group) — the `VaultManager` class is easily subclassed
to support that pattern.

---

## Backup & Recovery

```bash
# Create backup before any bulk operation
inventory.py --backup
# → backups/backup_YYYYMMDD_HHMMSS/
#      manifest.json
#      inventory/inventory_def.txt
#      inventory/group_vars/all/vault.yml
#      inventory/host_vars/*.yml

# List available backups
ls -lt backups/

# Restore
inventory.py --restore backups/backup_20250601_143022
```

The `manifest.json` records the timestamp, file list, and host count —
useful for audit trails.

---

## Migration from Old Scripts

### Old approach

```bash
# Old: shell loop calling ansible_vault.sh per host
tail -n +2 nodes.csv | while IFS=',' read -r NODE IP USER GROUP HOSTNAME SSH_PORT PASSWORD; do
    ./ansible_vault.sh "$NODE" "$IP" ...
done
```

### New approach (one command)

```bash
python3 bootstrap_import.py nodes.txt
# or, using the main CLI:
python3 inventory.py --import nodes.txt
```

The old `ansible_vault.sh` can be retired. `inventory.sh` remains as a
thin shim so `ansible.cfg`'s `inventory =` line needs no change.

---

## Running Tests

```bash
pip install pytest
python3 -m pytest tests/ -v
```

---

## Extending the Solution

| Feature | Extension point |
|---|---|
| LDAP/AD group sync | Subclass `InventoryManager.load()` |
| Per-group vault files | Subclass `VaultManager` with group routing |
| REST API | Wrap `InventoryManager` methods in FastAPI routes |
| Terraform integration | Parse Terraform state JSON in a custom `parse_inventory_file()` |
| Netbox source of truth | Add `--netbox-sync` command that calls Netbox API and calls `add_host()` |
| SSH key auth (passwordless) | Skip vault entries for key-based hosts; `VaultManager.sync()` already handles missing passwords gracefully |
