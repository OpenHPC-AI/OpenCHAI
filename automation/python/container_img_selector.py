#!/usr/bin/env python3
"""
Script Name : container_img_selector.py
Purpose     : Browse the OpenCHAI vault registry, interactively select
              HPC-AI container images, and download them to the local
              registry with resume support, retries, and live progress.

              Can be called directly by configure_openchai_manager.py
              (credentials forwarded via run()) or run standalone via
              __main__ with optional CLI arguments.

Author      : Satish Gupta
"""

from __future__ import annotations

import base64
import getpass
import logging
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

# ─────────────────────────────────────────────
# Dependency bootstrap  (mirrors main script)
# ─────────────────────────────────────────────
def _ensure_rich() -> None:
    try:
        import rich  # noqa: F401
    except ImportError:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "rich", "--quiet"]
        )

_ensure_rich()

from rich.console import Console
from rich import box
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console()

# ─────────────────────────────────────────────
# Logging  (appends to same log as main script)
# ─────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).resolve().parent
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
log = logging.getLogger("openchai.container")


def log_info(msg: str)   -> None:
    log.info(msg)
    console.print(f"[cyan]ℹ  {msg}[/cyan]")

def log_notice(msg: str) -> None:
    log.info("NOTICE: %s", msg)
    console.print(f"[bold green]✔  {msg}[/bold green]")

def log_warn(msg: str)   -> None:
    log.warning(msg)
    console.print(f"[yellow]⚠  {msg}[/yellow]")

def log_error(msg: str)  -> None:
    log.error(msg)
    console.print(f"[bold red]❌  {msg}[/bold red]")

def error_exit(msg: str) -> None:
    log_error(msg)
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# !! CONFIGURABLE NETWORK CONSTANTS !!
#
# These are the ONLY values you need to change for your environment.
#
# VAULT_PORT
#   80   → http://host/path         (plain HTTP, standard port, no TLS)
#   443  → https://host/path        (HTTPS, standard port)
#   other→ http://host:<port>/path  (non-standard port, plain HTTP)
#
# SSL_VERIFY_CERT
#   True  → Verify the server's SSL certificate (secure, use in production)
#   False → Skip SSL verification (use when server has a self-signed cert)
#           Equivalent to curl -k / wget --no-check-certificate
# ─────────────────────────────────────────────────────────────────────────────
VAULT_HOST       = "hpcsangrah-test.pune.cdac.in"
VAULT_PORT       = 443        # ← change port here (80, 443, 8080, …)
VAULT_PATH       = "/vault/OpenCHAI/hpcsuite_registry/container_img_reg"
SSL_VERIFY_CERT  = False      # ← set True once a valid certificate is installed

# Download tuning
DOWNLOAD_TIMEOUT_S = 300    # seconds before a stalled download is abandoned
CONNECT_TIMEOUT_S  = 15     # seconds for initial HTTP connection
MAX_RETRIES        = 3      # retry attempts per file before giving up
CHUNK_SIZE         = 1 << 20  # 1 MiB read chunks


def _build_vault_url(host: str, port: int, path: str) -> str:
    if port == 443:
        scheme, portstr = "https", ""
    elif port == 80:
        scheme, portstr = "http", ""
    else:
        scheme, portstr = "http", f":{port}"
    return f"{scheme}://{host}{portstr}{path}"


CONTAINER_REG_BASE_URL: str = _build_vault_url(VAULT_HOST, VAULT_PORT, VAULT_PATH)

# Derived no_cert flag — passed to every HTTP call.
# Flip SSL_VERIFY_CERT above; do not edit this line.
_NO_CERT: bool = not SSL_VERIFY_CERT

# ─────────────────────────────────────────────
# Local registry root
# Overwritten by configure_openchai_manager.py
# via _sed_replace when called from it.
# ─────────────────────────────────────────────
LOCAL_DIR = "/opt/OpenCHAI/hpcsuite_registry/container_img_reg"

# ─────────────────────────────────────────────
# Tools served in the container registry
# ─────────────────────────────────────────────
TOOLS: List[str] = [
    "chakshu-front_reg",
    "ganglia_reg",
    "ldap_reg",
    "nagios_reg",
    "osticket_reg",
    "xCAT_reg",
]

# File extensions recognised as container image archives
VALID_EXTENSIONS: Tuple[str, ...] = (
    ".tar", ".img", ".gz", ".xz", ".bz2", ".tgz",
)


# ─────────────────────────────────────────────
# Credentials dataclass
# Mirrors VaultCredentials in main script so
# the object can be passed in directly without
# re-prompting the user.
# ─────────────────────────────────────────────
@dataclass
class VaultCredentials:
    username: str
    password: str

    def auth_header(self) -> str:
        """RFC 7617 HTTP Basic-Auth Authorization header value."""
        token = base64.b64encode(
            f"{self.username}:{self.password}".encode("utf-8")
        ).decode("ascii")
        return f"Basic {token}"


# ─────────────────────────────────────────────
# Download job & result
# ─────────────────────────────────────────────
@dataclass
class _DownloadJob:
    tool:       str
    version:    str
    img_path:   str          # relative path under <base>/<os>/<tool>/<version>/
    url:        str
    dest:       Path
    size_bytes: Optional[int] = field(default=None)   # None = unknown


@dataclass
class _DownloadResult:
    job:     _DownloadJob
    success: bool
    skipped: bool = False    # file already complete — not re-downloaded
    error:   str  = ""


# ─────────────────────────────────────────────
# HTML href parser  (no regex fragility)
# ─────────────────────────────────────────────
class _HrefParser(HTMLParser):
    # hrefs that are never real registry entries
    _SKIP = {"#", "/", "../", "./", "?C=N;O=D", "?C=M;O=A", "?C=S;O=A", "?C=D;O=A"}

    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "a":
            for name, val in attrs:
                if (
                    name == "href"
                    and val
                    and val not in self._SKIP
                    and not val.startswith("?")
                ):
                    self.links.append(val)


# ─────────────────────────────────────────────
# Low-level HTTP helpers  (stdlib only)
# ─────────────────────────────────────────────
def _make_ssl_ctx(no_cert: bool) -> ssl.SSLContext:
    """
    Build an SSLContext.
    When no_cert=True (SSL_VERIFY_CERT=False) certificate verification and
    hostname checking are both disabled — equivalent to curl -k.
    A one-time advisory is printed so the operator is always aware.
    """
    ctx = ssl.create_default_context()
    if no_cert:
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
    return ctx


def _build_request(
    url: str,
    creds: Optional[VaultCredentials],
    extra_headers: Optional[Dict[str, str]] = None,
) -> urllib.request.Request:
    headers: Dict[str, str] = {"User-Agent": "openchai-container-selector/1.0"}
    if creds:
        headers["Authorization"] = creds.auth_header()
    if extra_headers:
        headers.update(extra_headers)
    return urllib.request.Request(url, headers=headers)


def _http_hint(code: int, url: str) -> str:
    """Human-readable hint for common HTTP error codes."""
    _HINTS: Dict[int, str] = {
        401: "Invalid credentials — check username and password.",
        403: "Access denied — your account may not have permission for this path.",
        404: "Resource not found — the registry path may have changed.",
        407: "Proxy authentication required — check proxy settings.",
        500: "Server error — the vault may be temporarily unavailable.",
        503: "Service unavailable — try again in a few minutes.",
    }
    return _HINTS.get(code, f"HTTP {code}. Verify {url} in a browser.")


def _fetch_html(
    url: str,
    no_cert: bool,
    creds: Optional[VaultCredentials],
    timeout: int = CONNECT_TIMEOUT_S,
) -> Optional[str]:
    """
    GET *url* and return the response body as a UTF-8 string.
    Returns None on any network or HTTP error; caller decides how to handle.
    """
    try:
        req = _build_request(url, creds)
        with urllib.request.urlopen(
            req, context=_make_ssl_ctx(no_cert), timeout=timeout
        ) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        log_error(f"HTTP {exc.code} fetching {url} — {_http_hint(exc.code, url)}")
    except urllib.error.URLError as exc:
        log_warn(f"Network error fetching {url}: {exc.reason}")
    except OSError as exc:
        log_warn(f"Connection timed out fetching {url}: {exc}")
    except Exception as exc:
        log_warn(f"Unexpected error fetching {url}: {exc}")
    return None


def _list_hrefs(
    url: str,
    no_cert: bool,
    creds: Optional[VaultCredentials],
) -> List[str]:
    """Return all non-trivial hrefs from an Apache / Nginx directory listing."""
    html = _fetch_html(url, no_cert, creds)
    if html is None:
        return []
    parser = _HrefParser()
    parser.feed(html)
    return parser.links


def _probe_head(
    url: str,
    no_cert: bool,
    creds: Optional[VaultCredentials],
) -> Optional[int]:
    """
    HEAD request → Content-Length as int, or None.
    Used to show file sizes before the user confirms the download queue.
    """
    try:
        req = _build_request(url, creds)
        req.get_method = lambda: "HEAD"   # type: ignore[method-assign]
        with urllib.request.urlopen(
            req, context=_make_ssl_ctx(no_cert), timeout=CONNECT_TIMEOUT_S
        ) as resp:
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl and cl.isdigit() else None
    except Exception:
        return None


def _fmt_bytes(n: Optional[int]) -> str:
    """Human-readable byte size, or '?' if unknown."""
    if n is None:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n //= 1024
    return f"{n:.1f} PB"


# ─────────────────────────────────────────────
# Connection test
# ─────────────────────────────────────────────
def _test_connection(
    no_cert: bool,
    creds: Optional[VaultCredentials],
) -> bool:
    """
    HEAD (fallback GET) against the registry root to verify reachability
    and credentials before the user spends time selecting images.
    Returns True on success.
    """
    url = CONTAINER_REG_BASE_URL + "/"
    console.print(f"[dim]  Connecting to {VAULT_HOST}:{VAULT_PORT} …[/dim]")
    try:
        req = _build_request(url, creds)
        req.get_method = lambda: "HEAD"   # type: ignore[method-assign]
        with urllib.request.urlopen(
            req, context=_make_ssl_ctx(no_cert), timeout=CONNECT_TIMEOUT_S
        ) as resp:
            if resp.status < 400:
                log_notice(f"Registry reachable (HTTP {resp.status}).")
                return True
            log_error(f"Registry returned HTTP {resp.status}.")
            return False

    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            log_error("HTTP 401 Unauthorized — credentials rejected.")
        elif exc.code == 405:
            # Server does not support HEAD — fall back to GET
            html = _fetch_html(url, no_cert, creds)
            if html is not None:
                log_notice("Registry reachable (HEAD unsupported, GET succeeded).")
                return True
            return False
        else:
            log_error(f"HTTP {exc.code} — {_http_hint(exc.code, url)}")
        return False

    except urllib.error.URLError as exc:
        reason = str(exc.reason)
        if "CERTIFICATE_VERIFY_FAILED" in reason or "SSL" in reason.upper():
            log_error(
                f"SSL certificate verification failed for {VAULT_HOST}:{VAULT_PORT}.\n"
                f"  The server is using a self-signed or untrusted certificate.\n"
                f"  To disable verification, set  SSL_VERIFY_CERT = False  "
                f"at the top of this script.\n"
                f"  To enable  verification, install a valid certificate on the "
                f"server and set  SSL_VERIFY_CERT = True."
            )
        else:
            log_error(
                f"Cannot reach {VAULT_HOST}:{VAULT_PORT} — {exc.reason}\n"
                "  Verify network connectivity and VAULT_HOST / VAULT_PORT constants."
            )
        return False
    except Exception as exc:
        log_error(f"Connection test failed: {exc}")
        return False


# ─────────────────────────────────────────────
# Credential collection
# ─────────────────────────────────────────────
def collect_credentials() -> Optional[VaultCredentials]:
    """
    Interactively prompt for vault credentials.

    When called from configure_openchai_manager.py the VaultCredentials
    object is passed directly into run() — this function is only invoked
    when running standalone or when the caller passes creds=None.
    """
    console.print(Rule("[bold]Vault Registry Authentication[/bold]"))
    ssl_status = (
        "[green]Enabled (verified)[/green]"
        if SSL_VERIFY_CERT else
        "[yellow]Disabled (self-signed / set SSL_VERIFY_CERT=True when cert is ready)[/yellow]"
    )
    console.print(
        f"[cyan]Registry URL :[/cyan] [white]{CONTAINER_REG_BASE_URL}[/white]\n"
        f"[cyan]Host         :[/cyan] [white]{VAULT_HOST}[/white]\n"
        f"[cyan]Port         :[/cyan] [white]{VAULT_PORT}[/white]\n"
        f"[cyan]SSL verify   :[/cyan] {ssl_status}\n"
    )

    if not Confirm.ask(
        "Does the registry server require authentication?", default=True
    ):
        log_notice("Skipping authentication — anonymous access assumed.")
        return None

    # Username — visible input
    username = ""
    while not username:
        username = Prompt.ask("  Vault username").strip()
        if not username:
            console.print("[red]  Username cannot be empty. Try again.[/red]")

    # Password — hidden via getpass (reliable across SSH / sudo / CI terminals)
    password = ""
    while not password:
        sys.stdout.write("  Vault password: ")
        sys.stdout.flush()
        try:
            password = getpass.getpass(prompt="")
        except Exception:
            # Fallback for IDE-embedded terminals where getpass may fail
            password = Prompt.ask("  Vault password", password=True)
        if not password:
            console.print("[red]  Password cannot be empty. Try again.[/red]")

    creds = VaultCredentials(username=username, password=password)
    log.info("Container-selector credentials collected for user: %s", username)
    log_notice(f"Credentials accepted for '{username}' (password not logged).")
    return creds


def _re_prompt_credentials(reason: str) -> Optional[VaultCredentials]:
    """
    Offer the user a chance to re-enter credentials after an auth failure.
    Returns fresh VaultCredentials, or None if the user declines.
    """
    console.print()
    log_error(f"Authentication failure: {reason}")
    if not Confirm.ask(
        "Re-enter credentials and retry?", default=True
    ):
        return None
    return collect_credentials()


# ─────────────────────────────────────────────
# OS-version discovery
# ─────────────────────────────────────────────
def select_os_version(
    no_cert: bool,
    creds: Optional[VaultCredentials],
) -> Optional[str]:
    """
    Discover OS-version sub-directories on the registry (alma9, rocky9 …)
    and let the user select one.  Returns the chosen version string or None.
    """
    console.print(Rule("[bold]OS Version Selection[/bold]"))
    log_info(f"Fetching OS version list from: {CONTAINER_REG_BASE_URL}/")

    hrefs = _list_hrefs(CONTAINER_REG_BASE_URL + "/", no_cert, creds)

    os_versions = sorted({
        h.rstrip("/") for h in hrefs
        if h.endswith("/")
        and re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*/$", h)
        and h not in ("../", "./")
    })

    if not os_versions:
        log_warn("No OS-version directories found at the registry root.")
        return None

    table = Table(
        box=box.SIMPLE_HEAVY, show_header=True,
        header_style="bold magenta", padding=(0, 2),
    )
    table.add_column("#",          style="bold cyan", no_wrap=True, justify="right")
    table.add_column("OS Version", style="white")
    for i, v in enumerate(os_versions, 1):
        table.add_row(str(i), v)
    console.print(table)

    while True:
        raw = Prompt.ask("Select OS version number").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(os_versions):
            selected = os_versions[int(raw) - 1]
            break
        console.print("[red]  Invalid choice — enter a number from the table.[/red]")

    log_notice(f"OS version selected: {selected}")
    return selected


# ─────────────────────────────────────────────
# Local directory structure
# ─────────────────────────────────────────────
def create_local_directories() -> None:
    """Ensure LOCAL_DIR and one sub-folder per tool exist on disk."""
    root = Path(LOCAL_DIR)
    root.mkdir(parents=True, exist_ok=True)
    for tool in TOOLS:
        (root / tool).mkdir(exist_ok=True)
    log_notice(f"Local directory structure ready: {LOCAL_DIR}")


# ─────────────────────────────────────────────
# Registry browsing helpers
# ─────────────────────────────────────────────
def _is_image(name: str) -> bool:
    """Return True if *name* looks like a container image file."""
    clean = name.rstrip("/")
    return (
        any(clean.endswith(ext) for ext in VALID_EXTENSIONS)
        or "cdac_" in clean
        or (":" in clean and not clean.endswith("/"))
    )


def _list_versions(
    tool_name: str,
    os_version: str,
    no_cert: bool,
    creds: Optional[VaultCredentials],
) -> List[str]:
    """
    Return sorted version sub-directory names under
    <registry>/<os_version>/<tool_name>/.
    Accepts any alphanumeric folder name (v1.2.3, rocky9.6, beta_01 …).
    """
    url   = f"{CONTAINER_REG_BASE_URL}/{os_version}/{tool_name}/"
    hrefs = _list_hrefs(url, no_cert, creds)
    return sorted({
        h.rstrip("/") for h in hrefs
        if h.endswith("/")
        and re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*/$", h)
        and h not in ("../", "./")
    })


def _safe_join_url(base: str, href: str) -> str:
    """
    Safely join URLs regardless of whether href is:
      • relative path
      • absolute path
      • full URL
      • contains duplicate slashes

    Prevents malformed URLs like:
      .../version//vault/OpenCHAI/...

    Examples:
        base = https://server/path/version/
        href = image.tar
            -> https://server/path/version/image.tar

        href = /vault/path/image.tar
            -> https://server/vault/path/image.tar

        href = https://other/path/image.tar
            -> https://other/path/image.tar
    """
    if not href:
        return base

    href = href.strip()

    # Already a full URL
    if href.startswith(("http://", "https://")):
        return href

    # urljoin automatically handles:
    #   relative paths
    #   leading slashes
    #   duplicate slashes
    return urljoin(base, href)


def _list_images(
    tool_name: str,
    os_version: str,
    version: str,
    no_cert: bool,
    creds: Optional[VaultCredentials],
) -> List[str]:
    """
    Recursively collect container image filenames under
    <registry>/<os_version>/<tool_name>/<version>/.

    Handles:
      • relative hrefs
      • absolute hrefs
      • full URLs
      • nested directories
      • duplicate slash issues

    Returns image paths relative to the version directory.
    """

    base_url = (
        f"{CONTAINER_REG_BASE_URL}/"
        f"{os_version}/{tool_name}/{version}/"
    )

    hrefs = _list_hrefs(base_url, no_cert, creds)

    images: List[str] = []
    seen: set = set()

    for item in hrefs:

        if item in ("../", "./", "/") or item.startswith("?"):
            continue

        item = item.strip()

        # ─────────────────────────────────────────────
        # DIRECTORY HANDLING
        # ─────────────────────────────────────────────
        if item.endswith("/"):

            dir_url = _safe_join_url(base_url, item)

            sub_hrefs = _list_hrefs(dir_url, no_cert, creds)

            for sub in sub_hrefs:

                if sub in ("../", "./", "/") or sub.startswith("?"):
                    continue

                sub = sub.strip()

                if _is_image(sub):

                    # Convert to clean relative path
                    sub_name = Path(
                        urlparse(sub).path
                    ).name

                    dir_name = Path(
                        urlparse(item).path
                    ).name

                    relative_path = f"{dir_name}/{sub_name}"

                    if relative_path not in seen:
                        images.append(relative_path)
                        seen.add(relative_path)

        # ─────────────────────────────────────────────
        # DIRECT IMAGE FILE
        # ─────────────────────────────────────────────
        elif _is_image(item):

            clean_name = Path(
                urlparse(item).path
            ).name

            if clean_name not in seen:
                images.append(clean_name)
                seen.add(clean_name)

    return sorted(images)

# ─────────────────────────────────────────────
# Per-tool interactive selection
# ─────────────────────────────────────────────
def _select_tool_version(
    tool: str,
    os_version: str,
    no_cert: bool,
    creds: Optional[VaultCredentials],
) -> Optional[str]:
    """
    Show available versions for *tool* and let the user pick one.
    Returns the chosen version string, or None to skip this tool.
    """
    versions = _list_versions(tool, os_version, no_cert, creds)

    if not versions:
        log_warn(f"No versions found for '{tool}' — skipping.")
        return None

    table = Table(box=box.SIMPLE_HEAVY, show_header=False, padding=(0, 2))
    table.add_column("#",       style="bold cyan", no_wrap=True, justify="right")
    table.add_column("Version", style="white")
    for i, v in enumerate(versions, 1):
        table.add_row(str(i), v)
    console.print(table)

    raw = Prompt.ask(
        f"  Version for [cyan]{tool}[/cyan]  "
        "[dim](number to select · Enter to skip)[/dim]",
        default="",
    ).strip()

    if not raw:
        log_info(f"Skipping {tool}.")
        return None

    if raw.isdigit() and 1 <= int(raw) <= len(versions):
        chosen = versions[int(raw) - 1]
        log_info(f"{tool} — version selected: {chosen}")
        return chosen

    log_warn(f"Invalid input '{raw}' — skipping {tool}.")
    return None


def _select_images(
    tool: str,
    os_version: str,
    version: str,
    no_cert: bool,
    creds: Optional[VaultCredentials],
) -> List[str]:
    """
    Show all image files available for *tool/version* and let the user
    select one, several (comma-separated), or all.
    Returns a de-duplicated list of relative image paths.
    """
    images = _list_images(tool, os_version, version, no_cert, creds)

    if not images:
        log_warn(f"No image files found under {tool}/{version}.")
        return []

    table = Table(
        box=box.SIMPLE_HEAVY, show_header=True,
        header_style="bold magenta", padding=(0, 2),
    )
    table.add_column("#",          style="bold cyan", no_wrap=True, justify="right")
    table.add_column("Image file", style="white")
    for i, img in enumerate(images, 1):
        table.add_row(str(i), img)
    console.print(table)

    console.print(
        "  [dim]Enter number(s) separated by commas · "
        "[bold white]a[/bold white] = all · Enter = skip[/dim]"
    )
    raw = Prompt.ask(
        f"  Image(s) for [cyan]{tool}[/cyan]",
        default="",
    ).strip().lower()

    if not raw:
        log_info(f"No images selected for {tool}.")
        return []

    if raw == "a":
        log_notice(f"All {len(images)} image(s) selected for {tool}.")
        return images

    selected: List[str] = []
    seen: set = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if token.isdigit():
            idx = int(token)
            if 1 <= idx <= len(images):
                img = images[idx - 1]
                if img not in seen:
                    selected.append(img)
                    seen.add(img)
            else:
                log_warn(f"  Index {idx} is out of range — ignored.")
        else:
            log_warn(f"  Non-numeric entry '{token}' — ignored.")

    return selected


# ─────────────────────────────────────────────
# Pre-download size probe
# ─────────────────────────────────────────────
def _probe_queue_sizes(
    queue: List[_DownloadJob],
    no_cert: bool,
    creds: Optional[VaultCredentials],
) -> None:
    """
    HEAD-request every job in *queue* to populate size_bytes.
    Runs sequentially with a spinner; skipped gracefully on any error.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[dim]Probing file sizes … {task.description}[/dim]"),
        console=console,
        transient=True,
    ) as p:
        t = p.add_task("", total=len(queue))
        for job in queue:
            p.update(t, description=Path(job.img_path).name)
            job.size_bytes = _probe_head(job.url, no_cert, creds)
            p.advance(t)


# ─────────────────────────────────────────────
# Download engine
# ─────────────────────────────────────────────
def _download_file(
    job: _DownloadJob,
    no_cert: bool,
    creds: Optional[VaultCredentials],
    progress: Progress,
    overall_task: TaskID,
) -> _DownloadResult:
    """
    Stream-download job.url → job.dest with:
      • Atomic write via a .part temp file
      • Resume support   (Range header if .part already exists)
      • Up to MAX_RETRIES attempts with exponential back-off
      • Per-file progress bar inside the shared *progress* context
      • Credential re-prompt on HTTP 401

    Returns a _DownloadResult.
    """
    job.dest.parent.mkdir(parents=True, exist_ok=True)
    tmp      = job.dest.with_suffix(job.dest.suffix + ".part")
    filename = Path(job.img_path).name

    # ── Already fully downloaded? ─────────────────────────────────────────
    if job.dest.exists() and job.dest.stat().st_size > 0:
        if job.size_bytes and job.dest.stat().st_size == job.size_bytes:
            log_notice(f"Already complete, skipping: {filename}")
            progress.update(overall_task, advance=1)
            return _DownloadResult(job=job, success=True, skipped=True)
        # Size mismatch — re-download
        job.dest.unlink()

    file_task = progress.add_task(
        f"[cyan]{job.tool}[/cyan] [dim]/[/dim] [white]{filename}[/white]",
        total=job.size_bytes,
    )

    for attempt in range(1, MAX_RETRIES + 1):
        resumed_at      = tmp.stat().st_size if tmp.exists() else 0
        extra_headers: Dict[str, str] = {}

        if resumed_at > 0:
            extra_headers["Range"] = f"bytes={resumed_at}-"
            progress.update(file_task, completed=resumed_at)
            log_info(
                f"Resuming {filename} from byte {resumed_at:,} "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )
        elif attempt > 1:
            log_info(f"Retrying {filename} (attempt {attempt}/{MAX_RETRIES})")

        ctx = _make_ssl_ctx(no_cert)
        req = _build_request(job.url, creds, extra_headers)

        try:
            with urllib.request.urlopen(
                req, context=ctx, timeout=DOWNLOAD_TIMEOUT_S
            ) as resp:
                # Update progress bar total from server response
                cl = resp.headers.get("Content-Length")
                if cl and cl.isdigit():
                    server_len = int(cl)
                    # 206 Partial Content → total is resumed_at + remaining
                    new_total = (resumed_at + server_len) if resp.status == 206 else server_len
                    progress.update(file_task, total=new_total)

                mode = "ab" if (resumed_at > 0 and resp.status == 206) else "wb"
                with open(tmp, mode) as fh:
                    while True:
                        chunk = resp.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        fh.write(chunk)
                        progress.update(file_task, advance=len(chunk))

            tmp.rename(job.dest)
            progress.update(
                file_task,
                completed=progress.tasks[file_task].total or 0,
            )
            progress.update(overall_task, advance=1)
            log.info("Downloaded %s → %s", job.url, job.dest)
            return _DownloadResult(job=job, success=True)

        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                # Offer credential re-entry once per file
                new_creds = _re_prompt_credentials(
                    "HTTP 401 — credentials rejected by server"
                )
                if new_creds is None:
                    progress.remove_task(file_task)
                    if tmp.exists():
                        tmp.unlink()
                    return _DownloadResult(
                        job=job, success=False,
                        error="Aborted after authentication failure",
                    )
                creds = new_creds
                continue   # retry with refreshed creds

            if exc.code == 416:
                # Range Not Satisfiable — stale .part file; start over
                if tmp.exists():
                    tmp.unlink()
                resumed_at = 0
                progress.update(file_task, completed=0)
                continue

            err = _http_hint(exc.code, job.url)
            log_error(f"HTTP {exc.code} downloading {filename}: {err}")
            progress.remove_task(file_task)
            if tmp.exists():
                tmp.unlink()
            return _DownloadResult(job=job, success=False, error=err)

        except (urllib.error.URLError, OSError) as exc:
            log_warn(
                f"Transient error on attempt {attempt}/{MAX_RETRIES} "
                f"for {filename}: {exc}"
            )
            if attempt < MAX_RETRIES:
                wait = 2 ** attempt   # 2 s · 4 s · 8 s
                log_info(f"Waiting {wait} s before retry …")
                time.sleep(wait)

        except Exception as exc:
            log_error(f"Unexpected error downloading {filename}: {exc}")
            break

    # All attempts exhausted
    progress.remove_task(file_task)
    if tmp.exists():
        tmp.unlink()
    err_msg = f"Failed after {MAX_RETRIES} attempt(s)"
    return _DownloadResult(job=job, success=False, error=err_msg)


# ─────────────────────────────────────────────
# Main workflow
# ─────────────────────────────────────────────
def run(
    no_cert: bool = _NO_CERT,
    creds: Optional[VaultCredentials] = None,
    os_version: Optional[str] = None,
) -> None:
    """
    Primary entry-point — called by configure_openchai_manager.py with
    pre-collected arguments, or via __main__ for standalone usage.

    Parameters
    ----------
    no_cert    : Skip SSL certificate verification when True.
                 Defaults to (not SSL_VERIFY_CERT) from the constants block.
    creds      : VaultCredentials from the parent script, or None to prompt.
    os_version : Pre-selected OS label (e.g. "alma9.3"), or None to prompt.
    """
    # ── Banner ────────────────────────────────────────────────────────────
    console.print()
    console.print(Panel.fit(
        Text.from_markup(
            "[bold cyan]HPCSuite Container Image Registry Selector[/bold cyan]\n"
            "[dim]OpenCHAI  |  CDAC Pune[/dim]"
        ),
        box=box.DOUBLE_EDGE,
        border_style="cyan",
        padding=(1, 4),
    ))

    # SSL advisory — shown once so the operator always knows the TLS state
    if no_cert:
        console.print(
            "[yellow]⚠  SSL certificate verification is DISABLED "
            "(SSL_VERIFY_CERT = False).\n"
            "   Set SSL_VERIFY_CERT = True at the top of this script "
            "once a valid certificate is installed.[/yellow]"
        )
    else:
        console.print("[green]🔒 SSL certificate verification is enabled.[/green]")
    console.print()

    # ── Credentials ───────────────────────────────────────────────────────
    if creds is None:
        creds = collect_credentials()

    # ── Connection test ───────────────────────────────────────────────────
    console.print(Rule("[bold]Registry Connection[/bold]"))
    console.print(
        f"[cyan]Host :[/cyan] [white]{VAULT_HOST}[/white]   "
        f"[cyan]Port :[/cyan] [white]{VAULT_PORT}[/white]   "
        f"[cyan]SSL verify :[/cyan] "
        + ("[green]on[/green]" if not no_cert else "[yellow]off (self-signed)[/yellow]")
    )
    if not _test_connection(no_cert, creds):
        # Give the user one chance to fix credentials before aborting
        creds = _re_prompt_credentials("Initial connection / authentication failed")
        if creds is None:
            error_exit("Connection aborted by user.")
        if not _test_connection(no_cert, creds):
            error_exit(
                "Still cannot reach the registry. "
                "Check VAULT_HOST, VAULT_PORT, and your credentials."
            )

    # ── OS version ────────────────────────────────────────────────────────
    if os_version is None:
        os_version = select_os_version(no_cert, creds)
        if os_version is None:
            error_exit("No OS version selected. Aborting.")
    else:
        log_info(f"Using pre-selected OS version: {os_version}")

    log_info(f"Registry path: {CONTAINER_REG_BASE_URL}/{os_version}/")

    # ── Local directories ─────────────────────────────────────────────────
    create_local_directories()

    # ── Tool / version / image selection ─────────────────────────────────
    console.print()
    console.print(Rule("[bold]Tool & Image Selection[/bold]"))
    console.print(
        "[dim]For each tool: select a version then choose which images to download.\n"
        "Press Enter at any prompt to skip that tool.[/dim]\n"
    )

    download_queue: List[_DownloadJob] = []

    for tool in TOOLS:
        console.print(f"[bold yellow]╔══ {tool} ══[/bold yellow]")

        version = _select_tool_version(tool, os_version, no_cert, creds)
        if version is None:
            console.print()
            continue

        selected_imgs = _select_images(tool, os_version, version, no_cert, creds)
        if not selected_imgs:
            console.print()
            continue

        for img_path in selected_imgs:
            img_url = (
                f"{CONTAINER_REG_BASE_URL}/{os_version}"
                f"/{tool}/{version}/{img_path}"
            )
            dest = Path(LOCAL_DIR) / tool / Path(img_path).name
            download_queue.append(_DownloadJob(
                tool     = tool,
                version  = version,
                img_path = img_path,
                url      = img_url,
                dest     = dest,
            ))
        console.print()

    # ── Nothing selected ─────────────────────────────────────────────────
    if not download_queue:
        log_warn("No images selected. Nothing to download.")
        return

    # ── Probe file sizes ──────────────────────────────────────────────────
    _probe_queue_sizes(download_queue, no_cert, creds)

    # ── Download queue summary ────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold]Download Queue[/bold]"))

    total_known   = sum(j.size_bytes for j in download_queue if j.size_bytes)
    unknown_count = sum(1 for j in download_queue if j.size_bytes is None)

    summary = Table(
        box=box.ROUNDED, show_header=True,
        header_style="bold magenta", padding=(0, 2),
    )
    summary.add_column("#",           style="bold cyan",  no_wrap=True, justify="right")
    summary.add_column("Tool",        style="cyan",       no_wrap=True)
    summary.add_column("Version",     style="white",      no_wrap=True)
    summary.add_column("Image",       style="white")
    summary.add_column("Size",        style="green",      no_wrap=True, justify="right")
    summary.add_column("Destination", style="dim")

    for i, job in enumerate(download_queue, 1):
        already    = job.dest.exists() and job.dest.stat().st_size > 0
        dest_label = str(job.dest)
        if already:
            dest_label += " [green][exists][/green]"
        summary.add_row(
            str(i),
            job.tool,
            job.version,
            Path(job.img_path).name,
            _fmt_bytes(job.size_bytes),
            dest_label,
        )

    console.print(summary)
    console.print()

    size_line = f"[bold]{_fmt_bytes(total_known)}[/bold] known"
    if unknown_count:
        size_line += f"  +  {unknown_count} file(s) with unknown size"
    console.print(
        f"  [cyan]{len(download_queue)}[/cyan] image(s) queued  |  "
        f"Estimated total: {size_line}"
    )
    console.print()

    if not Confirm.ask(
        f"Proceed to download [bold cyan]{len(download_queue)}[/bold cyan] image(s)?",
        default=True,
    ):
        log_warn("Download cancelled by user.")
        return

    # ── Execute downloads ─────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold]Downloading[/bold]"))
    console.print()

    results: List[_DownloadResult] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        overall = progress.add_task(
            f"[bold]Overall  (0 / {len(download_queue)})[/bold]",
            total=len(download_queue),
        )
        for idx, job in enumerate(download_queue, 1):
            progress.update(
                overall,
                description=(
                    f"[bold]Overall  "
                    f"({idx - 1} / {len(download_queue)})[/bold]"
                ),
            )
            result = _download_file(job, no_cert, creds, progress, overall)
            results.append(result)

        progress.update(
            overall,
            description=(
                f"[bold]Overall  "
                f"({len(download_queue)} / {len(download_queue)})[/bold]"
            ),
        )

    # ── Final report ──────────────────────────────────────────────────────
    succeeded = [r for r in results if r.success and not r.skipped]
    skipped   = [r for r in results if r.skipped]
    failed    = [r for r in results if not r.success]

    console.print()
    console.print(Rule("[bold]Download Report[/bold]"))

    report = Table(
        box=box.SIMPLE_HEAVY, show_header=True,
        header_style="bold", padding=(0, 2),
    )
    report.add_column("Status", no_wrap=True, justify="center")
    report.add_column("Tool",   style="cyan",  no_wrap=True)
    report.add_column("Image",  style="white")
    report.add_column("Detail", style="dim")

    for r in succeeded:
        report.add_row(
            "[bold green]✔  OK[/bold green]",
            r.job.tool,
            Path(r.job.img_path).name,
            str(r.job.dest),
        )
    for r in skipped:
        report.add_row(
            "[bold blue]⏭  SKIP[/bold blue]",
            r.job.tool,
            Path(r.job.img_path).name,
            "Already downloaded",
        )
    for r in failed:
        report.add_row(
            "[bold red]✘  FAIL[/bold red]",
            r.job.tool,
            Path(r.job.img_path).name,
            r.error or "Unknown error",
        )

    console.print(report)
    console.print()

    if not failed:
        console.print(Panel.fit(
            f"[bold green]✅  All {len(succeeded) + len(skipped)} image(s) ready[/bold green]  "
            f"({len(succeeded)} downloaded · {len(skipped)} already present)\n"
            f"[dim]Saved under: {LOCAL_DIR}[/dim]",
            border_style="green",
            padding=(1, 4),
        ))
    else:
        console.print(Panel.fit(
            f"[bold yellow]⚠  {len(succeeded)} downloaded  ·  "
            f"{len(skipped)} skipped  ·  "
            f"[bold red]{len(failed)} failed[/bold red][/bold yellow]\n"
            f"[dim]Review errors above · Log: {LOG_PATH}[/dim]",
            border_style="yellow",
            padding=(1, 4),
        ))

    log.info(
        "Container image selector finished: %d downloaded, %d skipped, %d failed.",
        len(succeeded), len(skipped), len(failed),
    )


# ─────────────────────────────────────────────
# Standalone entry-point
# ─────────────────────────────────────────────
def main() -> None:
    """Run the selector as a standalone script."""
    global LOCAL_DIR   # declared here so the f-string default and the override both work
    import argparse

    parser = argparse.ArgumentParser(
        description="OpenCHAI HPCSuite — container image selector",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--no-cert", action="store_true", default=_NO_CERT,
        help=(
            "Disable SSL certificate verification. "
            f"Current default from SSL_VERIFY_CERT constant: "
            f"{'enabled' if SSL_VERIFY_CERT else 'DISABLED (self-signed cert mode)'}."
        ),
    )
    parser.add_argument(
        "--verify-cert", action="store_true", default=False,
        help=(
            "Force SSL certificate verification ON regardless of the "
            "SSL_VERIFY_CERT constant. Use when you have a valid cert "
            "and want to verify without editing the script."
        ),
    )
    parser.add_argument(
        "--os-version", default=None, metavar="VERSION",
        help="OS version label (e.g. alma9.3). Prompts interactively if omitted.",
    )
    parser.add_argument(
        "--local-dir", default=None, metavar="PATH",
        help=f"Override local registry root (default: {LOCAL_DIR})",
    )
    parser.add_argument(
        "--username", default=None, metavar="USER",
        help="Vault username — password is prompted securely at startup.",
    )
    args = parser.parse_args()

    # Apply local-dir override before anything else reads LOCAL_DIR
    if args.local_dir:
        LOCAL_DIR = args.local_dir

    # Build credentials from CLI username if supplied
    creds: Optional[VaultCredentials] = None
    if args.username:
        sys.stdout.write(f"  Vault password for {args.username}: ")
        sys.stdout.flush()
        try:
            pwd = getpass.getpass(prompt="")
        except Exception:
            pwd = Prompt.ask("  Password", password=True)
        if pwd:
            creds = VaultCredentials(username=args.username, password=pwd)
        else:
            console.print("[red]No password supplied — will prompt interactively.[/red]")

    # --verify-cert overrides --no-cert and the constant
    no_cert_final = False if args.verify_cert else args.no_cert

    try:
        run(no_cert=no_cert_final, creds=creds, os_version=args.os_version)
    except KeyboardInterrupt:
        console.print("\n[yellow]Aborted by user.[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
