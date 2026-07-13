# CHAI CLI

Command-line client for the **OpenCHAI GUI backend API**. It talks to the
same FastAPI backend as the web GUI (`chai_gui/backend`), so anything you
do with `chai` is immediately visible in the GUI, and vice versa — there
is exactly one source of truth (the backend), with two clients.

No changes to `chai_gui/backend` were required — every command below
wraps an existing endpoint.

---

## 1. Requirements

- Python 3.8+
- The OpenCHAI GUI backend already running somewhere reachable (default
  assumed: `http://127.0.0.1:8000`, i.e. running on the same host)

## 2. Install

From the repo root:

```bash
cd chai_cli
pip install -e .
```

This installs a `chai` command on your `$PATH` (via `console_scripts`).

To also enable **live log streaming** (`chai logs follow`, `chai logs
tail`, `--watch` on execute/deploy commands), install the optional extra:

```bash
pip install -e ".[live]"
```

Without it, every other command works fine — you'll only get a clear
error message if you try to use a live-streaming command.

If you'd rather not install anything system-wide, use a venv:

```bash
cd chai_cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[live]"
```

### Alternative: run without installing

```bash
cd chai_cli
pip install -r requirements.txt   # click + requests only
python -m chai --help
```

## 3. Quick start

```bash
# Point the CLI at your backend (only needed once; defaults to
# http://127.0.0.1:8000 if you skip this and the backend runs locally)
chai config set --base-url http://<gui-host>:8000

# Log in with the same Linux/PAM credentials + admin-group membership
# the web GUI requires. The session token is cached in
# ~/.config/chai/config.json (0600 permissions) so you don't need to
# log in again until it expires (default 8h).
chai auth login -u myuser

# Confirm you're in
chai auth whoami

# Explore
chai info paths
chai playbooks categories
chai playbooks list provision
chai inventory list
```

Every command supports `-o json` for machine-readable output, e.g.:

```bash
chai -o json nodes list | jq '.[] | select(.role=="gpu")'
```

## 4. Command reference

| Group | Commands | Backend endpoint(s) |
|---|---|---|
| `chai auth` | `login`, `logout`, `whoami`, `status` | `/auth/*` |
| `chai config` | `show`, `set` | *(local only — no backend call)* |
| `chai cluster` | `create`, `get`, `preview`, `state`, `reset`, `schema` | `/cluster/*` |
| `chai nodes` | `list`, `get`, `add`, `update`, `delete`, `bulk-import` | `/nodes/*` |
| `chai inventory` | `list`, `add`, `update`, `delete`, `bulk-import`, `raw`, `ssh-test` | `/inventory-def/*` |
| `chai health` | `all`, `node` | `/nodes/health/*` |
| `chai playbooks` | `categories`, `list`, `tree`, `groups`, `detail`, `execute` | `/playbooks/*` |
| `chai deploy` | `start`, `generate`, `jobs`, `job` | `/deploy/*` |
| `chai logs` | `jobs`, `stream`, `follow`, `tail` | `/logs/*`, `/logtail/*` |
| `chai backup` | `list`, `read`, `restore`, `delete` | `/backup/*` |
| `chai audit` | `list`, `clear` | `/audit` |
| `chai info` | `paths`, `tree`, `ansible` | `/info/*` |

Run `chai --help`, or `chai <group> --help` / `chai <group> <command>
--help` for full flag documentation — every command is self-documenting.

### `chai nodes` vs `chai inventory` — which one do I use?

The backend has two distinct node stores, and the CLI mirrors that:

- **`chai nodes`** manages the in-memory cluster-state model used by the
  setup wizard (`ClusterConfig` + `Node` list) — the same thing the GUI's
  "Cluster Setup" flow builds up before generating an inventory.
- **`chai inventory`** manages `automation/ansible/inventory/inventory_def.txt`
  directly (plus vault-encrypted `host_vars/`) — the file Ansible actually
  reads when playbooks run.

If you're driving a deployment end-to-end from the CLI the same way the
GUI wizard does, use `chai cluster create` + `chai nodes add` + `chai
deploy start`. If you just need to add/fix a host in the real inventory
(the way `chai_gui`'s "Inventory Management" page does), use `chai
inventory add/update/delete`.

## 5. Common workflows

### Run a playbook and watch it live

```bash
chai playbooks categories
chai playbooks list provision
chai playbooks execute provision/master.yml \
    --var cluster_name=demo \
    --limit headnode \
    --tags network,storage \
    --watch
```

`--watch` streams output over WebSocket until the job finishes (requires
the `[live]` extra). Without `--watch`, poll it later:

```bash
chai logs stream <job_id> --lines 200
```

### Build a cluster config + deploy from scratch

```bash
chai cluster schema > my-cluster.json   # edit as needed
chai cluster create --file my-cluster.json
chai nodes add --hostname cn01 --ip 192.168.1.101 --role compute --cpu 64 --ram-gb 256
chai nodes add --hostname gn01 --ip 192.168.1.102 --role gpu --gpu-count 4 --gpu-model A100
chai deploy start --playbook provision/cluster.yml --dry-run   # check mode first
chai deploy start --playbook provision/cluster.yml --watch     # then for real
```

### Manage the real Ansible inventory directly

```bash
chai inventory add --hostname cn01 --ip 192.168.1.101 --group compute --password 'secret'
chai inventory ssh-test --ip 192.168.1.101 --user root
chai inventory list
```

### Tail backend logs live

```bash
chai logs tail app --lines 100
chai logs tail audit
```

## 6. Configuration & authentication details

- Config file: `~/.config/chai/config.json` (override the directory with
  `CHAI_CONFIG_DIR`). Contains `base_url`, `verify_ssl`, and the saved
  session token — written with `0600` permissions.
- Resolution order for backend URL and token (highest priority first):
  1. `--base-url` / `--token` CLI flags
  2. `CHAI_API_URL` / `CHAI_TOKEN` environment variables
  3. Saved values from `chai config set` / `chai auth login`
  4. Default `http://127.0.0.1:8000`
- `chai auth login` calls the same PAM-backed `/auth/login` endpoint the
  GUI uses — you need Linux credentials on the backend host **and**
  membership in an admin group (`OPENCHAI_ADMIN_GROUPS`, default
  `openchai-admins`), exactly like GUI login.
- Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (backend default: 8
  hours). When a token expires, any command fails with a clear "Token
  invalid or expired" message and a hint to re-run `chai auth login`.
- Self-signed/internal TLS certs: pass `--no-verify-ssl` or run `chai
  config set --no-verify-ssl` once to persist it.

## 7. Output formats & scripting

Every command accepts `-o table` (default, human-readable) or `-o json`
(for piping into `jq` or other tooling). Errors always go to stderr with
a non-zero exit code, so `chai ... || echo "failed"` and CI usage work as
expected.

## 8. Package layout

```
chai_cli/
├── setup.py                 # pip install -e .  →  `chai` on PATH
├── requirements.txt         # click + requests (websockets optional, for live streaming)
├── README.md                 # this file
└── chai/
    ├── __init__.py
    ├── __main__.py            # `python -m chai`
    ├── cli.py                 # top-level command group + global options
    ├── client.py               # requests-based HTTP client + error types
    ├── config.py                # ~/.config/chai/config.json handling
    ├── output.py                 # table/json rendering + unified error handling
    └── commands/
        ├── auth.py, config_cmd.py, cluster.py, nodes.py, inventory.py,
        ├── health.py, playbooks.py, deploy.py, logs.py, backup.py,
        └── audit.py, info.py
```

Each `commands/*.py` module maps 1:1 to one backend router (see the table
in §4), matching the existing project convention of one Python module per
domain.

## 9. Extending the CLI

To wrap a new backend endpoint (e.g. once `chai-release` or
`cluster-setup` gain CLI coverage), add a command function to the
relevant module in `chai/commands/` (or a new module + `main.add_command`
in `chai/cli.py`), following the existing pattern:

```python
@some_group.command("my-command")
@click.option("--flag", default=None)
@click.pass_context
def my_command(ctx, flag):
    """One-line help text."""
    data = call(ctx.obj.client.get, "/some/endpoint", params={"flag": flag})
    render(data, ctx.obj.output)
```

`call()` and `render()` (from `chai.output`) give you consistent error
handling and table/JSON output for free — no need to reimplement either.
