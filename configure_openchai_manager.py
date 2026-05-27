#!/usr/bin/env python3
"""
Script Name : configure_openchai_manager.py
Purpose     : Configure OpenCHAI manager tool for cluster setup
Author      : Satish Gupta
Python Port : Optimized CLI version with rich UX
"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
import re
import logging
import platform
import urllib.request
import urllib.error
import urllib.parse
import base64
import getpass
import ssl
import tarfile
from dataclasses import dataclass
from pathlib import Path
from html.parser import HTMLParser
from typing import Dict, List, Optional, Set, Tuple

# ─────────────────────────────────────────────
# Dependency bootstrap (rich for UX)
# ─────────────────────────────────────────────
def _ensure_rich():
    try:
        import rich  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "--quiet"])

_ensure_rich()

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.text import Text
from rich.rule import Rule
from rich.syntax import Syntax

console = Console()

# ─────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LOG = Path("/var/log/openchai_config.log")

def _get_log_path() -> Path:
    if DEFAULT_LOG.parent.exists() and os.access(DEFAULT_LOG.parent, os.W_OK):
        return DEFAULT_LOG
    return SCRIPT_DIR / "openchai_config.log"

LOG_PATH = _get_log_path()

logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("openchai")


def log_info(msg: str):
    log.info(msg)
    console.print(f"[cyan]ℹ  {msg}[/cyan]")

def log_notice(msg: str):
    log.info(f"NOTICE: {msg}")
    console.print(f"[bold green]✔  {msg}[/bold green]")

def log_warn(msg: str):
    log.warning(msg)
    console.print(f"[yellow]⚠  {msg}[/yellow]")

def log_error(msg: str):
    log.error(msg)
    console.print(f"[bold red]❌  {msg}[/bold red]")

def error_exit(msg: str):
    log_error(msg)
    sys.exit(1)


# ─────────────────────────────────────────────
# !! CONFIGURABLE NETWORK CONSTANTS !!
# Change VAULT_PORT here to redirect all network
# access to a different port without editing
# any other part of the script.
# ─────────────────────────────────────────────
VAULT_HOST     = "hpcsangrah-test.pune.cdac.in"
VAULT_PORT     = 443          # ← change port here (e.g. 443 for HTTPS, 8080, etc.)
VAULT_PATH     = "/vault/OpenCHAI/hpcsuite_registry/"

# Derive the full base URL from the components above.
# Port 80  → http://…   (no explicit port in URL for cleanliness)
# Port 443 → https://…  (no explicit port in URL for cleanliness)
# Any other port → http://…:<port>  (explicit port always shown)
def _build_vault_url(host: str, port: int, path: str) -> str:
    if port == 443:
        scheme  = "https"
        portstr = ""
    elif port == 80:
        scheme  = "http"
        portstr = ""
    else:
        scheme  = "http"
        portstr = f":{port}"
    return f"{scheme}://{host}{portstr}{path}"

OPENCHAI_VAULT_URL: str = _build_vault_url(VAULT_HOST, VAULT_PORT, VAULT_PATH)


# ─────────────────────────────────────────────
# Vault credentials dataclass
# ─────────────────────────────────────────────
@dataclass
class VaultCredentials:
    username: str
    password: str

    def auth_header(self) -> str:
        """Return a Basic-Auth Authorization header value."""
        token = base64.b64encode(
            f"{self.username}:{self.password}".encode("utf-8")
        ).decode("ascii")
        return f"Basic {token}"


@dataclass
class DownloadTask:
    tool: str
    version: str
    filename: str
    size: str
    url: str
    destination: Path
    status: str = "PENDING"
    detail: str = ""
# ─────────────────────────────────────────────
# HTML href parser (replaces grep/sed pipeline)
# ─────────────────────────────────────────────
class _HrefParser(HTMLParser):
    ARCHIVE_EXT = (".tar.gz", ".tgz", ".tar.xz", ".tar", ".img")

    def __init__(self):
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, val in attrs:
                if name == "href" and val and any(val.endswith(e) for e in self.ARCHIVE_EXT):
                    self.links.append(val)


def _fetch_url(
    url: str,
    no_cert: bool = False,
    creds: Optional[VaultCredentials] = None,
) -> bytes:
    ctx = ssl.create_default_context()
    if no_cert:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    headers = {"User-Agent": "openchai-setup/1.0"}
    if creds:
        headers["Authorization"] = creds.auth_header()
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return resp.read()


def _list_remote_archives(
    url: str,
    no_cert: bool,
    creds: Optional[VaultCredentials] = None,
) -> List[str]:
    try:
        html = _fetch_url(url, no_cert, creds).decode("utf-8", errors="replace")
        parser = _HrefParser()
        parser.feed(html)
        return parser.links
    except Exception as exc:
        log_warn(f"Could not fetch archive list from {url}: {exc}")
        return []


# ─────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────
def strip_tar_ext(filename: str) -> str:
    for ext in (".tar.gz", ".tgz", ".tar.xz", ".tar"):
        if filename.endswith(ext):
            return filename[: -len(ext)]
    return filename


def _run(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    log.debug("RUN: %s", " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True)


def _get_available_gb(path: Path) -> Optional[int]:
    try:
        stat = shutil.disk_usage(path)
        return int(stat.free / (1024 ** 3))
    except Exception:
        return None


def _detect_pkg_manager() -> Optional[str]:
    for mgr in ("dnf", "yum"):
        if shutil.which(mgr):
            return mgr
    return None


def _ensure_ansible():
    if shutil.which("ansible"):
        log_notice("Ansible is already installed.")
        return
    log_warn("Ansible not found. Installing...")
    mgr = _detect_pkg_manager()
    if not mgr:
        error_exit("No supported package manager (dnf/yum) found.")
    try:
        _run(["sudo", mgr, "-y", "install", "epel-release"], check=False)
        _run(["sudo", mgr, "-y", "install", "ansible-core", "ansible"])
        log_notice("Ansible installed successfully.")
    except subprocess.CalledProcessError:
        error_exit("Failed to install Ansible.")


# ─────────────────────────────────────────────
# OS Detection
# ─────────────────────────────────────────────
def detect_os() -> Tuple[str, str, str]:
    """Returns (os_name, version_id, detected_label)."""
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        error_exit("/etc/os-release missing. Cannot detect OS.")

    name, ver = "Unknown", "Unknown"
    for line in os_release.read_text().splitlines():
        if line.startswith("NAME="):
            name = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("VERSION_ID="):
            ver = line.split("=", 1)[1].strip().strip('"')

    label_map = {
        "AlmaLinux": f"alma{ver}",
        "Rocky":     f"rocky{ver}",
        "CentOS":    f"centos{ver}",
        "Red Hat":   f"rhel{ver}",
    }
    label = next((v for k, v in label_map.items() if k.lower() in name.lower()), "unknown")
    return name, ver, label


# ─────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────
def print_banner():
    console.print()
    console.print(Panel.fit(
        Text.from_markup(
            "[bold cyan]OpenCHAI Manager – Cluster Configuration Wizard[/bold cyan]\n"
            "[dim]HPC-AI Suite  |  CDAC Pune[/dim]"
        ),
        box=box.DOUBLE_EDGE,
        border_style="cyan",
        padding=(1, 4),
    ))
    console.print()


# ─────────────────────────────────────────────
# Section 1 – License
# ─────────────────────────────────────────────
def check_license():
    console.print(Rule("[bold]License Agreement[/bold]"))
    console.print(
        "[yellow]You must read and accept the OpenCHAI Software License Agreement "
        "before proceeding.[/yellow]\n"
    )
    accepted = Confirm.ask("Have you read and accepted the Software License Agreement?", default=False)
    if not accepted:
        console.print("[red]Installation aborted. License Agreement must be accepted.[/red]")
        sys.exit(1)
    log.info("License accepted by user.")


# ─────────────────────────────────────────────
# Section 2 – Base Directory
# ─────────────────────────────────────────────
def select_base_dir() -> Path:
    console.print(Rule("[bold]Base Directory Selection[/bold]"))
    default = SCRIPT_DIR
    log_info(f"Default base directory: {default}")

    avail_gb = _get_available_gb(default)

    if avail_gb is None:
        log_warn("Unable to detect disk space. Proceeding with manual entry.")
        return _prompt_base_dir()

    if avail_gb >= 50:
        log_info(f"✅ {default} has sufficient free space ({avail_gb} GB available).")
        if Confirm.ask(f"Use default base directory [cyan]{default}[/cyan]?", default=True):
            return default
        return _prompt_base_dir()
    else:
        log_warn(f"{default} has insufficient space ({avail_gb} GB < 50 GB required).")
        _show_mount_points()
        return _prompt_base_dir()


def _show_mount_points():
    console.print("\n[cyan]Mount points with ≥ 50 GB free:[/cyan]")
    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    table.add_column("Path", style="white")
    table.add_column("Available", style="green", justify="right")
    try:
        result = subprocess.run(
            ["df", "-h", "--output=target,avail"], capture_output=True, text=True
        )
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                size_str = parts[1].rstrip("G")
                try:
                    if float(size_str) >= 50:
                        table.add_row(parts[0], parts[1])
                except ValueError:
                    pass
    except Exception:
        pass
    console.print(table)
    console.print()


def _prompt_base_dir() -> Path:
    while True:
        raw = Prompt.ask("Enter absolute path for OpenCHAI installation").strip()
        p = Path(raw)
        if not p.is_absolute():
            console.print("[red]Please enter an absolute path.[/red]")
            continue
        if not p.exists():
            if Confirm.ask(f"Directory [cyan]{p}[/cyan] does not exist. Create it?", default=True):
                p.mkdir(parents=True, exist_ok=True)
                return p
        else:
            return p


# ─────────────────────────────────────────────
# Section 3 – OS / Arch Parameters
# ─────────────────────────────────────────────
def collect_system_params(detected_os_label: str) -> dict:
    console.print(Rule("[bold]System Parameters[/bold]"))
    console.print("[dim]Press ENTER to accept detected defaults.[/dim]\n")

    os_release = Path("/etc/os-release")
    ver_num = ""
    for line in os_release.read_text().splitlines():
        if line.startswith("VERSION_ID="):
            ver_num = line.split("=", 1)[1].strip().strip('"').split(".")[0]
            break

    defaults = {
        "os_arch":    platform.machine(),
        "os_version": detected_os_label,
        "rhel_label": f"rh{ver_num}",
        "el_label":   f"el{ver_num}",
        "kernel":     platform.release(),
    }

    params = {}
    fields = [
        ("os_arch",    "OS Architecture"),
        ("os_version", "OS Version"),
        ("rhel_label", "RHEL Label"),
        ("el_label",   "Enterprise EL Label"),
        ("kernel",     "Kernel Version"),
    ]

    for key, label in fields:
        val = Prompt.ask(f"  {label}", default=defaults[key]).strip() or defaults[key]
        params[key] = val

    # Strip last segment from kernel (e.g. .x86_64)
    params["kernel"] = ".".join(params["kernel"].split(".")[:-1]) if "." in params["kernel"] else params["kernel"]

    console.print()
    return params


# ─────────────────────────────────────────────
# Section 4 – SSL Check Option
# ─────────────────────────────────────────────
def ask_ssl_option() -> bool:
    console.print(Rule("[bold]SSL / Host Key Checking[/bold]"))
    no_cert = Confirm.ask(
        "Disable SSL/host-key checking for downloads? (not recommended for production)",
        default=False,
    )
    if no_cert:
        log_warn("SSL/host-key checking disabled for this session.")
    return no_cert


# ─────────────────────────────────────────────
# Section 4b – Vault Authentication Credentials
# ─────────────────────────────────────────────
def collect_vault_credentials() -> Optional[VaultCredentials]:
    """
    Prompt the user for HTTP Basic-Auth credentials needed to access
    the OpenCHAI vault at VAULT_HOST:VAULT_PORT.

    Returns a VaultCredentials instance, or None if the user opts out
    (e.g. the server does not require authentication).
    """
    console.print(Rule("[bold]Vault Registry Authentication[/bold]"))

    console.print(
        f"[cyan]Registry URL :[/cyan] [white]{OPENCHAI_VAULT_URL}[/white]\n"
        f"[cyan]Host         :[/cyan] [white]{VAULT_HOST}[/white]\n"
        f"[cyan]Port         :[/cyan] [white]{VAULT_PORT}[/white]\n"
    )

    needs_auth = Confirm.ask(
        "Does the registry server require authentication?",
        default=True,
    )

    if not needs_auth:
        log_notice("Skipping authentication – anonymous access assumed.")
        return None

    username = ""

    while not username:
        username = Prompt.ask("  Vault username").strip()

        if not username:
            console.print("[red]Username cannot be empty.[/red]")

    console.print("  Vault password: ", end="")

    password = ""

    while not password:

        try:
            password = getpass.getpass(prompt="")

        except Exception:
            password = Prompt.ask(
                "  Vault password",
                password=True
            )

        if not password:
            console.print(
                "[red]Password cannot be empty. Try again.[/red]"
            )
            console.print("  Vault password: ", end="")

    creds = VaultCredentials(
        username=username,
        password=password
    )

    log.info(
        "Vault credentials collected for user: %s",
        username
    )

    log_notice(
        f"Credentials stored for user '{username}' "
        f"(password redacted from log)."
    )

    return creds


# ─────────────────────────────────────────────
# Registry Tar Handling
# ─────────────────────────────────────────────

TAR_EXTS = (".tar.gz", ".tgz", ".tar.xz", ".tar")


def _find_local_tars(directory: Path) -> List[Path]:

    if not directory.exists():
        return []

    return [
        f for f in directory.iterdir()
        if f.is_file()
        and any(f.name.endswith(e) for e in TAR_EXTS)
    ]


def _safe_extract_tar(tf: tarfile.TarFile, path: Path):
    """
    Secure tar extraction preventing path traversal attacks.
    """

    abs_path = path.resolve()

    for member in tf.getmembers():

        member_path = (path / member.name).resolve()

        if not str(member_path).startswith(str(abs_path)):
            raise Exception(
                f"Blocked suspicious tar path: {member.name}"
            )

    tf.extractall(path)

def _extract_tar(
    src,
    dest_dir: Path,
    is_stream: bool = False
) -> bool:
    """Extract tar from file path or file-like stream into dest_dir."""

    dest_dir.mkdir(parents=True, exist_ok=True)

    try:

        with Progress(
            SpinnerColumn(),
            TextColumn(
                "[progress.description]{task.description}"
            ),
            console=console,
        ) as progress:

            task = progress.add_task(
                "Extracting archive…",
                total=None
            )

            if is_stream:

                with tarfile.open(
                    fileobj=src,
                    mode="r|*"
                ) as tf:

                    _safe_extract_tar(tf, dest_dir)

            else:

                with tarfile.open(
                    src,
                    mode="r:*"
                ) as tf:

                    _safe_extract_tar(tf, dest_dir)

            progress.update(task, completed=True)

        return True

    except Exception as exc:

        log_warn(f"Extraction failed: {exc}")

        return False

def _show_download_queue(tasks: List[DownloadTask]):

    console.print(
        Rule("[bold]Download Queue[/bold]")
    )

    table = Table(
        box=box.ROUNDED,
        header_style="bold cyan"
    )

    table.add_column("#", justify="center")
    table.add_column("Tool")
    table.add_column("Version")
    table.add_column("Image")
    table.add_column("Size", justify="right")
    table.add_column("Destination")

    for idx, task in enumerate(tasks, 1):

        table.add_row(
            str(idx),
            task.tool,
            task.version,
            task.filename,
            task.size,
            str(task.destination)
        )

    console.print(table)

    console.print(
        f"\n[bold]{len(tasks)}[/bold] image(s) queued"
    )

def _show_download_report(tasks: List[DownloadTask]):

    console.print(
        Rule("[bold]Download Report[/bold]")
    )

    table = Table(
        box=box.SIMPLE_HEAVY
    )

    table.add_column("Status")
    table.add_column("Tool")
    table.add_column("Image")
    table.add_column("Detail")

    for task in tasks:

        status_icon = {
            "DONE": "✔",
            "SKIP": "⏭",
            "FAILED": "❌"
        }.get(task.status, "?")

        table.add_row(
            status_icon,
            task.tool,
            task.filename,
            task.detail
        )

    console.print(table)

def _download_and_extract(
    task: DownloadTask,
    no_cert: bool,
    creds: Optional[VaultCredentials] = None,
) -> bool:

    ctx = ssl.create_default_context()

    if no_cert:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "User-Agent": "openchai-setup/1.0"
    }

    if creds:
        headers["Authorization"] = creds.auth_header()

    tmp_tar = (
        task.destination.parent /
        f"{task.filename}.download"
    )

    try:

        req = urllib.request.Request(
            task.url,
            headers=headers
        )

        with urllib.request.urlopen(
            req,
            context=ctx,
            timeout=300
        ) as resp:

            total = int(
                resp.headers.get(
                    "Content-Length",
                    0
                )
            )

            with Progress(
                SpinnerColumn(),
                TextColumn(
                    "[progress.description]{task.description}"
                ),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:

                dl_task = progress.add_task(
                    f"Downloading {task.filename}",
                    total=total
                )

                with open(tmp_tar, "wb") as out:

                    while True:

                        chunk = resp.read(1024 * 1024)

                        if not chunk:
                            break

                        out.write(chunk)

                        progress.update(
                            dl_task,
                            advance=len(chunk)
                        )

        log_notice(
            f"Download completed: "
            f"{task.filename}"
        )

        if not _extract_tar(
            str(tmp_tar),
            task.destination.parent
        ):

            task.status = "FAILED"
            task.detail = "Extraction failed"

            return False

        task.status = "DONE"
        task.detail = "Downloaded & extracted"

        return True

    except Exception as exc:

        task.status = "FAILED"
        task.detail = str(exc)

        log_warn(
            f"Download failed: {exc}"
        )

        return False

    finally:

        try:

            if tmp_tar.exists():
                tmp_tar.unlink()

        except Exception:
            pass

# ─────────────────────────────────────────────
# Main Registry Handler
# ─────────────────────────────────────────────
def handle_registry_tar(
    base_dir: Path,
    arch: str,
    os_version: str,
    no_cert: bool,
    creds: Optional[VaultCredentials] = None,
) -> str:

    console.print(
        Rule("[bold]Host Machine Registry (Tar)[/bold]")
    )

    registry_dir = (
        base_dir /
        "hpcsuite_registry" /
        "hostmachine_reg" /
        arch
    )

    version_dir = registry_dir / os_version

    version_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    network_url = (
        f"{OPENCHAI_VAULT_URL}"
        f"hostmachine_reg/"
        f"{arch}/"
        f"{os_version}/"
    )

    local_tars = _find_local_tars(version_dir)

    # ─────────────────────────────────────────
    # LOCAL TAR FILES
    # ─────────────────────────────────────────
    if local_tars:

        log_info(
            f"Found {len(local_tars)} local tar file(s)"
        )

        table = Table(
            box=box.ROUNDED,
            header_style="bold cyan"
        )

        table.add_column("#", justify="center")
        table.add_column("Tarball")
        table.add_column("Location")

        for idx, tar in enumerate(local_tars, 1):

            table.add_row(
                str(idx),
                tar.name,
                str(tar.parent)
            )

        console.print(table)

        raw = Prompt.ask(
            "Select local tarball",
            default="1"
        )

        try:
            idx = int(raw) - 1
        except Exception:
            log_warn("Invalid selection")
            return "__SET_LATER__"

        if idx < 0 or idx >= len(local_tars):

            log_warn("Invalid selection")

            return "__SET_LATER__"

        chosen = local_tars[idx]

        openchai_version = strip_tar_ext(
            chosen.name
        )

        extracted_dir = (
            version_dir / openchai_version
        )

        # Already extracted
        if extracted_dir.exists() and any(extracted_dir.iterdir()):

            log_notice(
                f"Already complete, skipping: "
                f"{openchai_version}"
            )

            return openchai_version

        log_info(
            f"Extracting {chosen.name}"
        )

        if _extract_tar(
            str(chosen),
            version_dir
        ):

            log_notice(
                f"Registry extracted successfully: "
                f"{openchai_version}"
            )

            return openchai_version

        log_warn(
            "Extraction failed."
        )

        return "__SET_LATER__"

    # ─────────────────────────────────────────
    # NO LOCAL TARS
    # ─────────────────────────────────────────
    log_warn(
        f"No tar files found in {version_dir}"
    )

    console.print("\n  [bold]Options:[/bold]")
    console.print("  [cyan]1[/cyan]  Download from network")
    console.print("  [cyan]2[/cyan]  Install manually later")
    console.print("  [cyan]3[/cyan]  Skip")

    choice = Prompt.ask(
        "Select option",
        choices=["1", "2", "3"],
        default="3"
    )

    if choice == "2":

        log_warn(
            f"Place registry tar later in:\n"
            f"  → {version_dir}"
        )

        return "__SET_MANUALLY__"

    if choice == "3":

        return "__SET_LATER__"

    # ─────────────────────────────────────────
    # FETCH REMOTE FILES
    # ─────────────────────────────────────────
    log_info(
        f"Fetching tar list from {network_url} …"
    )

    remote_files = _list_remote_archives(
        network_url,
        no_cert,
        creds
    )

    if not remote_files:

        log_warn(
            "No archives found on network."
        )

        return "__SET_LATER__"

    # ─────────────────────────────────────────
    # REMOTE TABLE
    # ─────────────────────────────────────────
    table = Table(
        title="Available OpenCHAI Packages",
        box=box.ROUNDED,
        header_style="bold cyan"
    )

    table.add_column("#", justify="center")
    table.add_column("Package")
    table.add_column("Version")
    table.add_column("Tarball")

    for idx, file in enumerate(remote_files, 1):

        version = strip_tar_ext(file)

        table.add_row(
            str(idx),
            "openchai",
            version,
            file
        )

    console.print(table)

    raw = Prompt.ask(
        "Select file to download",
        default="1"
    )

    try:
        idx = int(raw) - 1
    except Exception:
        log_warn("Invalid selection")
        return "__SET_LATER__"

    if idx < 0 or idx >= len(remote_files):

        log_warn("Invalid selection")

        return "__SET_LATER__"

    selected = remote_files[idx]

    openchai_version = strip_tar_ext(
        Path(selected).name
    )

    extracted_dir = (
        version_dir / openchai_version
    )

    # ─────────────────────────────────────────
    # DOWNLOAD TASK
    # ─────────────────────────────────────────
    task = DownloadTask(
        tool="openchai",
        version=openchai_version,
        filename=selected,
        size="Unknown",
        url=network_url + selected,
        destination=extracted_dir,
    )

    # ─────────────────────────────────────────
    # SHOW QUEUE
    # ─────────────────────────────────────────
    _show_download_queue([task])

    if not Confirm.ask(
        f"Proceed to download 1 package(s)?",
        default=True
    ):

        return "__SET_LATER__"

    # ─────────────────────────────────────────
    # ALREADY EXISTS
    # ─────────────────────────────────────────
    if extracted_dir.exists() and any(extracted_dir.iterdir()):

        task.status = "SKIP"
        task.detail = "Already downloaded"

        log_notice(
            f"Already complete, skipping: "
            f"{openchai_version}"
        )

        _show_download_report([task])

        return openchai_version

    # ─────────────────────────────────────────
    # DOWNLOAD & EXTRACT
    # ─────────────────────────────────────────
    console.print(
        Rule("[bold]Downloading[/bold]")
    )

    if _download_and_extract(
        task,
        no_cert,
        creds
    ):

        log_notice(
            f"Registry extracted: "
            f"{openchai_version}"
        )

    else:

        log_warn(
            f"Failed downloading: "
            f"{openchai_version}"
        )

        return "__SET_LATER__"

    # ─────────────────────────────────────────
    # REPORT
    # ─────────────────────────────────────────
    _show_download_report([task])

    return openchai_version

# ─────────────────────────────────────────────
# Section 6 – Registry version validation
# ─────────────────────────────────────────────
def validate_registry(
    base_dir: Path,
    arch: str,
    os_version: str,
    openchai_version: str
):

    console.print(
        Rule("[bold]Registry Validation[/bold]")
    )

    registry_path = (
        base_dir
        / "hpcsuite_registry"
        / "hostmachine_reg"
        / arch
        / os_version
        / openchai_version
    )

    if registry_path.exists() and any(registry_path.iterdir()):

        log_notice(
            f"Version '{openchai_version}' found at: "
            f"{registry_path}"
        )

    else:

        log_warn(
            f"Version directory not found: {registry_path}\n"
            "Update 'openchai_version' later in group_vars/all.yml"
        )


# ─────────────────────────────────────────────
# Section 7 – Inventory confirmation & copy
# ─────────────────────────────────────────────
def handle_inventory(base_dir: Path):
    console.print(Rule("[bold]Inventory File[/bold]"))
    inventory_def    = base_dir / "chai_setup" / "inventory_def.txt"
    inventory_target = base_dir / "automation" / "ansible" / "inventory" / "inventory_def.txt"

    confirmed = Confirm.ask(
        f"Have you updated the inventory file [cyan]{inventory_def}[/cyan] for your environment?",
        default=False,
    )
    if not confirmed:
        error_exit("Please update the inventory file before continuing.")

    if not inventory_def.exists():
        error_exit(f"Inventory definition file not found: {inventory_def}")

    inventory_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(inventory_def, inventory_target)
    log_notice(f"Copied: {inventory_def} → {inventory_target}")


# ─────────────────────────────────────────────
# Section 8 – Print summary table
# ─────────────────────────────────────────────
def print_summary(
    params: dict,
    base_dir: Path,
    openchai_version: str,
    creds: Optional[VaultCredentials] = None,
):
    console.print()
    console.print(Rule("[bold]Configuration Summary[/bold]"))
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    table.add_column("Variable", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white")

    rows = [
        ("OS Architecture",      params["os_arch"]),
        ("OS Version",           params["os_version"]),
        ("RHEL Label",           params["rhel_label"]),
        ("Enterprise EL Label",  params["el_label"]),
        ("Kernel Version",       params["kernel"]),
        ("Base Directory",       str(base_dir)),
        ("OpenCHAI Version",     openchai_version),
        ("Vault Host",           VAULT_HOST),
        ("Vault Port",           str(VAULT_PORT)),
        ("Vault URL",            OPENCHAI_VAULT_URL),
        ("Vault User",           creds.username if creds else "[dim]anonymous[/dim]"),
    ]
    for k, v in rows:
        table.add_row(k, v)

    console.print(table)
    console.print()


# ─────────────────────────────────────────────
# Section 9 – Update config files
# ─────────────────────────────────────────────
def _sed_replace(filepath: Path, pattern: str, replacement: str):
    """In-place regex substitution on a single line."""
    if not filepath.exists():
        return
    text = filepath.read_text()
    new_text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
    filepath.write_text(new_text)


def update_all_yml(base_dir: Path, params: dict, openchai_version: str):
    all_yml = base_dir / "automation" / "ansible" / "group_vars" / "all.yml"
    if not all_yml.exists():
        log_warn(f"group_vars/all.yml not found at: {all_yml} (skipping)")
        return

    replacements = {
        r"^openchai_version:.*":        f"openchai_version: {openchai_version}",
        r"^base_dir:.*":                f"base_dir: {base_dir}",
        r"^os_version:.*":              f"os_version: {params['os_version']}",
        r"^os_arch:.*":                 f"os_arch: {params['os_arch']}",
        r"^rhel_linux_label:.*":        f"rhel_linux_label: {params['rhel_label']}",
        r"^enterprise_linux_label:.*":  f"enterprise_linux_label: {params['el_label']}",
        r"^default_kernel_version:.*":  f'default_kernel_version: "{params["kernel"]}"',
    }
    for pat, repl in replacements.items():
        _sed_replace(all_yml, pat, repl)

    log_notice(f"Updated: {all_yml}")


def update_script_base_dirs(base_dir: Path):
    candidates = []
    for glob_pat in [
        "chai_setup/update_group_var_all.sh",
        "chai_setup/update_inventory_def.sh",
        "chai_setup/modules/*.sh",
        "servicenodes/*.sh",
    ]:
        candidates.extend(base_dir.glob(glob_pat))

    for f in candidates:
        if f.is_file():
            _sed_replace(f, r"^base_dir\s*=\s*.*", f'base_dir="{base_dir}"')
            log.debug("Updated base_dir in %s", f)


def update_ansible_cfg(base_dir: Path):
    ansible_cfg     = base_dir / "automation" / "ansible" / "ansible.cfg"
    system_cfg      = Path("/etc/ansible/ansible.cfg")
    inventory_sh    = base_dir / "automation" / "ansible" / "inventory" / "inventory.sh"
    inventory_line  = f"inventory = {inventory_sh}"
    all_yml         = base_dir / "automation" / "ansible" / "group_vars" / "all.yml"

    # Local ansible.cfg
    if ansible_cfg.exists():
        _sed_replace(ansible_cfg, r"inventory\s*=\s*.*inventory\.sh", inventory_line)
        log_notice(f"Updated: {ansible_cfg}")
    else:
        log_warn(f"Not found: {ansible_cfg}")

    # inventory.sh
    if inventory_sh.exists():
        _sed_replace(inventory_sh, r"^base_dir=.*", f'base_dir="{base_dir}"')
        inventory_sh.chmod(inventory_sh.stat().st_mode | 0o111)
        log_notice(f"Updated: {inventory_sh}")
    else:
        log_warn(f"Not found: {inventory_sh}")

    # System /etc/ansible/ansible.cfg
    if system_cfg.exists():
        text = system_cfg.read_text()
        if re.search(r"^\s*inventory\s*=", text, re.MULTILINE):
            text = re.sub(r"^\s*inventory\s*=.*", inventory_line, text, flags=re.MULTILINE)
        elif "[defaults]" in text:
            text = text.replace("[defaults]", f"[defaults]\n{inventory_line}", 1)
        else:
            text = f"[defaults]\n{inventory_line}\n" + text

        if "host_key_checking = False" not in text:
            text += "\nhost_key_checking = False\n"

        try:
            system_cfg.write_text(text)
            log_notice(f"Updated system Ansible config: {system_cfg}")
        except PermissionError:
            log_warn(f"No write permission to {system_cfg}. Run as root to update it.")

        # Make inventory.sh executable
        try:
            if inventory_sh.exists():
                inventory_sh.chmod(inventory_sh.stat().st_mode | 0o111)
        except Exception:
            pass

        # Copy group_vars to /etc/ansible/
        gv_src = base_dir / "automation" / "ansible" / "group_vars"
        gv_dst = Path("/etc/ansible/group_vars")
        try:
            if gv_src.exists():
                shutil.copytree(str(gv_src), str(gv_dst), dirs_exist_ok=True)
                log_notice(f"Copied group_vars → {gv_dst}")
        except Exception as exc:
            log_warn(f"Could not copy group_vars: {exc}")
    else:
        log_warn(f"System Ansible config not found at {system_cfg} (skipping)")


# ─────────────────────────────────────────────
# Section 10 – Container Image Registry
# ─────────────────────────────────────────────
IMG_EXTS = (".img", ".tar", ".tar.gz", ".tgz")


def _find_app_dirs(container_reg_path: Path) -> List[Path]:
    if not container_reg_path.exists():
        return []
    return [d for d in container_reg_path.iterdir() if d.is_dir()]


def _collect_local_images(app_dirs: List[Path]) -> Tuple[Dict[int, Path], Set[str]]:
    img_map: Dict[int, Path] = {}
    local_names: Set[str] = set()
    idx = 1

    for app_dir in app_dirs:
        imgs = [
            f for f in app_dir.rglob("*")
            if f.is_file() and any(f.name.endswith(e) for e in IMG_EXTS)
        ]
        if not imgs:
            log_warn(f"No images found in {app_dir.name}")
            continue
        console.print(f"\n[bold cyan]🧩 [{app_dir.name}][/bold cyan] {len(imgs)} image(s):")
        for img in imgs:
            console.print(f"   [dim][{idx}][/dim] {img.name}")
            img_map[idx] = img
            local_names.add(img.name)
            idx += 1

    return img_map, local_names


def _run_python_selector(selector: Path):
    if not selector.exists():
        log_warn(f"Python selector not found: {selector}")
        return
    if not shutil.which("python3"):
        log_warn("python3 not available; cannot run image selector.")
        return
    try:
        subprocess.run([sys.executable, str(selector)], check=False)
    except Exception as exc:
        log_warn(f"Python selector failed: {exc}")


def _fetch_network_images(
    container_reg_path: Path,
    container_url: str,
    local_names: Set[str],
    no_cert: bool,
    creds: Optional[VaultCredentials] = None,
):
    log_info(f"Fetching image list from {container_url} …")
    net_imgs = _list_remote_archives(container_url, no_cert, creds)

    if not net_imgs:
        log_warn("No images found on network.")
        return

    log_info(f"Found {len(net_imgs)} image(s) on network.")
    for net_img in net_imgs:
        base = Path(net_img).name
        if base in local_names:
            log_notice(f"⏭  Skipping {base} (already local)")
            continue

        dest = container_reg_path / base
        url  = container_url + net_img
        log_info(f"⬇  Downloading {base} …")

        ctx = ssl.create_default_context()
        if no_cert:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        headers = {"User-Agent": "openchai-setup/1.0"}
        if creds:
            headers["Authorization"] = creds.auth_header()

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                DownloadColumn(),
                TransferSpeedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(f"Downloading {base}", total=None)
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, context=ctx, timeout=300) as resp, open(dest, "wb") as out:
                    while True:
                            chunk = resp.read(1 << 20)
                            if not chunk:
                                break
                            out.write(chunk)
                progress.update(task, completed=True)
            log_notice(f"✅ Downloaded: {base}")
        except Exception as exc:
            log_warn(f"Failed to download {base}: {exc}")
            if dest.exists():
                dest.unlink()

    log_notice("Network image synchronisation complete.")


def handle_container_images(
    base_dir: Path,
    os_version: str,
    no_cert: bool,
    creds: Optional[VaultCredentials] = None,
):
    console.print(Rule("[bold]Container Image Registry[/bold]"))

    container_reg_path = base_dir / "hpcsuite_registry" / "container_img_reg"
    container_reg_path.mkdir(parents=True, exist_ok=True)

    python_selector = base_dir / "automation" / "python" / "container_img_selector.py"
    container_url   = f"{OPENCHAI_VAULT_URL}container_img_reg/{os_version}/"

    # Patch Python selector path if present
    if python_selector.exists():
        _sed_replace(
            python_selector,
            r'^LOCAL_DIR\s*=.*',
            f'LOCAL_DIR = "{container_reg_path}"',
        )

    log_info(f"Scanning container image registry: {container_reg_path}")
    app_dirs = _find_app_dirs(container_reg_path)

    if not app_dirs:
        log_warn(f"No application directories found in {container_reg_path}")
        if Confirm.ask("Fetch container images from network?", default=False):
            log_info("Launching Python container image selector…")
            _run_python_selector(python_selector)
        else:
            log_notice(f"Skipping. Add images later under:\n  {container_reg_path}")
        return

    img_map, local_names = _collect_local_images(app_dirs)

    if not img_map:
        log_warn("No local container images found.")
        if Confirm.ask("Fetch missing images from the network?", default=False):
            if shutil.which("python3"):
                _run_python_selector(python_selector)
            else:
                _fetch_network_images(container_reg_path, container_url, local_names, no_cert, creds)
        return

    if Confirm.ask("Fetch any missing images from the network?", default=False):
        if not shutil.which("curl") and not shutil.which("python3"):
            log_warn("Neither curl nor python3 available. Cannot fetch network images.")
        else:
            _fetch_network_images(container_reg_path, container_url, local_names, no_cert, creds)
    else:
        log_notice("Network image fetch skipped.")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():

    print_banner()

    log.info(
        "Script started by user=%s",
        os.getenv("USER", "unknown")
    )

    # ─────────────────────────────────────────
    # 1 ─ License
    # ─────────────────────────────────────────
    check_license()

    # ─────────────────────────────────────────
    # 2 ─ Ansible
    # ─────────────────────────────────────────
    console.print(
        Rule("[bold]Ansible Check[/bold]")
    )

    _ensure_ansible()

    # ─────────────────────────────────────────
    # 3 ─ Base directory
    # ─────────────────────────────────────────
    base_dir = select_base_dir()

    (
        base_dir /
        "hpcsuite_registry" /
        "hostmachine_reg"
    ).mkdir(
        parents=True,
        exist_ok=True
    )

    (
        base_dir /
        "hpcsuite_registry" /
        "container_img_reg"
    ).mkdir(
        parents=True,
        exist_ok=True
    )

    log.info("BASE_DIR=%s", base_dir)

    # ─────────────────────────────────────────
    # 4 ─ OS Detection
    # ─────────────────────────────────────────
    console.print(
        Rule("[bold]OS Detection[/bold]")
    )

    os_name, os_ver_id, detected_label = detect_os()

    log_info(
        f"Detected OS: {os_name} {os_ver_id}"
    )

    log_info(
        f"Suggested label: {detected_label}"
    )

    log_notice(
        f"Default OS label from Headnode: "
        f"{detected_label}"
    )

    console.print(
        "[dim]You can override the OS version "
        "for HPC-AI Master Nodes in the next "
        "step.[/dim]\n"
    )

    # ─────────────────────────────────────────
    # 5 ─ System parameters
    # ─────────────────────────────────────────
    params = collect_system_params(
        detected_label
    )

    #
    # Backward compatibility handling
    #
    # If arch not returned by older function,
    # auto-detect from machine architecture.
    #
    if "arch" not in params:

        detected_arch = platform.machine().strip()

        #
        # Normalize common arch names
        #
        arch_map = {
            "x86_64": "x86_64",
            "amd64": "x86_64",
            "aarch64": "aarch64",
            "arm64": "aarch64",
        }

        detected_arch = arch_map.get(
            detected_arch.lower(),
            detected_arch
        )

        params["arch"] = detected_arch

        log_warn(
            "Architecture not found in "
            "collect_system_params(). "
            f"Auto-detected arch: "
            f"{detected_arch}"
        )

    log_notice(
        f"Selected architecture: "
        f"{params['arch']}"
    )

    # ─────────────────────────────────────────
    # 6 ─ SSL option
    # ─────────────────────────────────────────
    no_cert = ask_ssl_option()

    # ─────────────────────────────────────────
    # 6b ─ Vault credentials
    # ─────────────────────────────────────────
    creds = collect_vault_credentials()

    # ─────────────────────────────────────────
    # 7 ─ Registry tar
    # ─────────────────────────────────────────
    openchai_version = handle_registry_tar(
        base_dir,
        params["arch"],
        params["os_version"],
        no_cert,
        creds
    )

    # ─────────────────────────────────────────
    # 8 ─ Validate Registry
    # ─────────────────────────────────────────
    if openchai_version not in (
        "__SET_LATER__",
        "__SET_MANUALLY__"
    ):

        validate_registry(
            base_dir,
            params["arch"],
            params["os_version"],
            openchai_version
        )

    else:

        log_warn(
            "OpenCHAI version not yet set. "
            "Update 'openchai_version' in "
            "group_vars/all.yml when ready."
        )

    # ─────────────────────────────────────────
    # 9 ─ Inventory
    # ─────────────────────────────────────────
    handle_inventory(base_dir)

    # ─────────────────────────────────────────
    # 10 ─ Summary
    # ─────────────────────────────────────────
    print_summary(
        params,
        base_dir,
        openchai_version,
        creds
    )

    # ─────────────────────────────────────────
    # 11 ─ Update config files
    # ─────────────────────────────────────────
    console.print(
        Rule("[bold]Updating Configuration Files[/bold]")
    )

    update_all_yml(
        base_dir,
        params,
        openchai_version
    )

    update_script_base_dirs(base_dir)

    update_ansible_cfg(base_dir)

    # ─────────────────────────────────────────
    # 12 ─ Container images
    # ─────────────────────────────────────────
    handle_container_images(
        base_dir,
        params["os_version"],
        no_cert,
        creds
    )

    # ─────────────────────────────────────────
    # Done
    # ─────────────────────────────────────────
    console.print()

    console.print(
        Panel.fit(
            (
                "[bold green]✅  OpenCHAI "
                "Manager configuration "
                "completed![/bold green]\n"
                f"[dim]Log file: "
                f"{LOG_PATH}[/dim]"
            ),
            border_style="green",
            padding=(1, 4),
        )
    )

    log.info(
        "Script finished successfully."
    )


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        console.print(
            "\n[yellow]Aborted by user.[/yellow]"
        )

        sys.exit(130)
