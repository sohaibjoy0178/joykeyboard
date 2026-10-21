"""Public GitHub stable releases, verified downloads and consented Windows installation."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from core import APP_VERSION

REPOSITORY = "sohaibjoy0178/joykeyboard"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
MAX_INSTALLER_BYTES = 512 * 1024 * 1024
TRUSTED_HOSTS = {"api.github.com", "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}


class UpdateError(RuntimeError):
    pass


class UpdateCancelled(UpdateError):
    pass


def _trusted_url(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in TRUSTED_HOSTS or parts.username or parts.password or parts.port not in (None, 443):
        raise UpdateError("Update link is not a trusted GitHub HTTPS address.")
    return url


class GitHubRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, _trusted_url(newurl))


def _open(url):
    request = Request(_trusted_url(url), headers={
        "User-Agent": f"JoyKeyboard/{APP_VERSION}",
        "Accept": "application/vnd.github+json" if urlsplit(url).hostname == "api.github.com" else "application/octet-stream",
        "X-GitHub-Api-Version": "2026-03-10",
    })
    return build_opener(GitHubRedirects()).open(request, timeout=15)


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"v?[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}", value):
        raise UpdateError("Release version must have three numbers, such as v0.4.10.")
    return tuple(int(part) for part in value.removeprefix("v").split("."))


@dataclass(frozen=True)
class Release:
    version: str
    download_url: str
    size: int
    sha256: str


@dataclass(frozen=True)
class ReadyUpdate:
    release: Release
    installer: Path


def parse_release(payload, current=APP_VERSION):
    if not isinstance(payload, dict):
        raise UpdateError("GitHub returned invalid release information.")
    if payload.get("draft") or payload.get("prerelease"):
        return None
    tag = payload.get("tag_name")
    latest = version_tuple(tag)
    if latest <= version_tuple(current):
        return None
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise UpdateError("Release has no installer assets.")
    installers = [asset for asset in assets if isinstance(asset, dict) and asset.get("name") == "JoyKeyboard-Setup.exe"]
    if len(installers) != 1:
        raise UpdateError("Release needs exactly one JoyKeyboard-Setup.exe asset.")
    asset = installers[0]
    size, digest = asset.get("size"), asset.get("digest")
    if asset.get("state") != "uploaded" or type(size) is not int or not 1024 <= size <= MAX_INSTALLER_BYTES:
        raise UpdateError("Release installer is incomplete or too large.")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise UpdateError("Release installer has no valid GitHub SHA-256 digest.")
    expected = f"https://github.com/{REPOSITORY}/releases/download/{tag}/JoyKeyboard-Setup.exe"
    if asset.get("browser_download_url") != expected:
        raise UpdateError("Release installer does not belong to the configured GitHub release.")
    return Release(".".join(map(str, latest)), expected, size, digest[7:].lower())


def check_latest(current=APP_VERSION):
    try:
        with _open(API_URL) as response:
            body = response.read(1_000_001)
        if len(body) > 1_000_000:
            raise UpdateError("GitHub release response is too large.")
        return parse_release(json.loads(body), current)
    except HTTPError as exc:
        if exc.code == 404:
            raise UpdateError("No public installer release is available yet.") from exc
        if exc.code in (403, 429):
            raise UpdateError("GitHub update limit reached. Try again later.") from exc
        raise UpdateError("GitHub could not check for updates. Try again later.") from exc
    except (OSError, URLError, ValueError) as exc:
        raise UpdateError("Could not check updates. Check internet and try again.") from exc


def _cancelled(cancel):
    if cancel.is_set():
        raise UpdateCancelled("Update download cancelled.")


def verify_installer(path, release, cancel=None):
    path = Path(path)
    if not path.is_file() or path.stat().st_size != release.size:
        raise UpdateError("Update installer is missing or incomplete. Download it again.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            if cancel is not None:
                _cancelled(cancel)
            digest.update(chunk)
    if digest.hexdigest() != release.sha256:
        raise UpdateError("Update installer verification failed. Download it again.")


def download_installer(release, directory, cancel, status=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "JoyKeyboard-Setup.exe"
    partial = directory / "JoyKeyboard-Setup.exe.part"
    _cancelled(cancel)
    try:
        verify_installer(target, release, cancel)
        return target
    except UpdateCancelled:
        raise
    except UpdateError:
        pass
    try:
        digest, received, last_percent = hashlib.sha256(), 0, -1
        with _open(release.download_url) as response, partial.open("wb") as stream:
            while chunk := response.read1(1024 * 1024):
                _cancelled(cancel)
                received += len(chunk)
                if received > release.size:
                    raise UpdateError("Update download is larger than its published size.")
                stream.write(chunk)
                digest.update(chunk)
                percent = received * 100 // release.size
                if status and percent != last_percent:
                    status(f"Downloading {release.version} · {percent}%")
                    last_percent = percent
            stream.flush()
            os.fsync(stream.fileno())
        _cancelled(cancel)
        if received != release.size or digest.hexdigest() != release.sha256:
            raise UpdateError("Update download failed its size/SHA-256 check. Retry the download.")
        partial.replace(target)
        return target
    except UpdateError:
        raise
    except (OSError, URLError) as exc:
        raise UpdateError("Could not download the update. Check internet and free disk space, then retry.") from exc
    finally:
        partial.unlink(missing_ok=True)


def prepare_update(directory, cancel, status=None, current=APP_VERSION):
    _cancelled(cancel)
    release = check_latest(current)
    _cancelled(cancel)
    if release is None:
        return None
    if status:
        status(f"Update {release.version} available · preparing download…")
    return ReadyUpdate(release, download_installer(release, directory, cancel, status))


def installer_script(update, executable, parent_pid, autostart):
    """Only trusted local paths/arguments enter PowerShell; never release-provided commands."""
    executable = Path(executable).resolve()
    installer = Path(update.installer).resolve()
    if type(parent_pid) is not int or parent_pid <= 0:
        raise UpdateError("Invalid application process for update handoff.")
    def quoted(value):
        return "'" + str(value).replace("'", "''") + "'"
    arguments = subprocess.list2cmdline([
        "/SP-", "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOCLOSEAPPLICATIONS", "/NORESTARTAPPLICATIONS",
        f"/DIR={executable.parent}", "/TASKS=autostart" if autostart else "/TASKS=",
    ])
    error_file = installer.parent / "install-error.txt"
    return f"""$ErrorActionPreference = 'Stop'
$app = {quoted(executable)}
$setup = {quoted(installer)}
$errorFile = {quoted(error_file)}
try {{
    $previous = Get-Process -Id {parent_pid} -ErrorAction SilentlyContinue
    if ($previous) {{ $previous | Wait-Process -Timeout 120 -ErrorAction Stop }}
    $hashing = [Security.Cryptography.SHA256]::Create()
    $installerStream = [IO.File]::OpenRead($setup)
    try {{ $actualHash = [BitConverter]::ToString($hashing.ComputeHash($installerStream)).Replace('-', '').ToLowerInvariant() }}
    finally {{ $installerStream.Dispose(); $hashing.Dispose() }}
    if ($actualHash -ne {quoted(update.release.sha256)}) {{ throw 'Installer SHA-256 changed. Update cancelled.' }}
    $result = Start-Process -FilePath $setup -ArgumentList {quoted(arguments)} -PassThru -Wait -WindowStyle Hidden
    if ($result.ExitCode -notin @(0, 3010)) {{ throw "Installer exited with code $($result.ExitCode)." }}
    Remove-Item -LiteralPath $errorFile -ErrorAction SilentlyContinue
}} catch {{
    Set-Content -LiteralPath $errorFile -Value $_.Exception.Message -Encoding UTF8
}}
if (Test-Path -LiteralPath $app) {{ Start-Process -FilePath $app -WorkingDirectory {quoted(executable.parent)} -WindowStyle Hidden }}
"""


def launch_installer(update, executable, parent_pid, autostart):
    verify_installer(update.installer, update.release)
    script = installer_script(update, executable, parent_pid, autostart)
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    return subprocess.Popen([str(powershell), "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW)
