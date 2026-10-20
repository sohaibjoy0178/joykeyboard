import base64
import hashlib
import io
import json
import threading
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest

import updates

DATA = b"MZ" + b"installer fixture" * 128


def release_payload(tag="v0.5.0"):
    return {"tag_name": tag, "draft": False, "prerelease": False, "assets": [{
        "name": "JoyKeyboard-Setup.exe", "state": "uploaded", "size": len(DATA),
        "digest": "sha256:" + hashlib.sha256(DATA).hexdigest(),
        "browser_download_url": f"https://github.com/{updates.REPOSITORY}/releases/download/{tag}/JoyKeyboard-Setup.exe",
    }]}


def test_version_numbers_compare_numerically():
    assert updates.version_tuple("v0.4.10") > updates.version_tuple("0.4.9")
    assert updates.parse_release(release_payload("v0.4.9"), "0.4.9") is None
    assert updates.parse_release(release_payload("v0.4.8"), "0.4.9") is None
    assert updates.parse_release(release_payload("v0.4.10"), "0.4.9").version == "0.4.10"


@pytest.mark.parametrize("value", [None, "", "v1", "1.2.3-rc1", "../1.2.3", "1.2.3.4", "1.2.1000000", "1.2.3\n"])
def test_invalid_versions_rejected(value):
    with pytest.raises(updates.UpdateError):
        updates.version_tuple(value)


@pytest.mark.parametrize("field", ["draft", "prerelease"])
def test_only_published_stable_releases(field):
    payload = release_payload()
    payload[field] = True
    assert updates.parse_release(payload) is None


@pytest.mark.parametrize("change", [
    {"state": "new"}, {"size": 0}, {"size": True}, {"size": updates.MAX_INSTALLER_BYTES + 1},
    {"digest": None}, {"digest": "sha256:bad"}, {"browser_download_url": "https://example.com/installer.exe"},
])
def test_unverified_or_foreign_installer_rejected(change):
    payload = release_payload()
    payload["assets"][0].update(change)
    with pytest.raises(updates.UpdateError):
        updates.parse_release(payload)


def test_missing_and_duplicate_installers_rejected():
    for assets in ([], release_payload()["assets"] * 2):
        payload = release_payload()
        payload["assets"] = assets
        with pytest.raises(updates.UpdateError):
            updates.parse_release(payload)


@pytest.mark.parametrize("url", ["http://github.com/a", "file:///tmp/a", "https://github.com.evil.test/a", "https://user@github.com/a", "https://github.com:444/a"])
def test_redirects_reject_non_github_https(url):
    with pytest.raises(updates.UpdateError):
        updates._trusted_url(url)


def test_real_api_shape_and_response_size_limit(monkeypatch):
    monkeypatch.setattr(updates, "_open", lambda _: io.BytesIO(json.dumps(release_payload()).encode()))
    assert updates.check_latest().sha256 == hashlib.sha256(DATA).hexdigest()
    monkeypatch.setattr(updates, "_open", lambda _: io.BytesIO(b" " * 1_000_001))
    with pytest.raises(updates.UpdateError, match="too large"):
        updates.check_latest()


@pytest.mark.parametrize("code,expected", [(404, "No public"), (403, "limit"), (429, "limit"), (500, "could not")])
def test_check_errors_are_actionable(monkeypatch, code, expected):
    monkeypatch.setattr(updates, "_open", Mock(side_effect=HTTPError(updates.API_URL, code, "error", {}, None)))
    with pytest.raises(updates.UpdateError, match=expected):
        updates.check_latest()


def test_download_verifies_and_reuses_only_matching_cache(tmp_path, monkeypatch):
    release = updates.parse_release(release_payload())
    network = Mock(side_effect=lambda _: io.BytesIO(DATA))
    monkeypatch.setattr(updates, "_open", network)
    status = []
    path = updates.download_installer(release, tmp_path, threading.Event(), status.append)
    assert path.read_bytes() == DATA and status[-1].endswith("100%")
    assert updates.download_installer(release, tmp_path, threading.Event()) == path
    assert network.call_count == 1
    path.write_bytes(b"bad cache")
    updates.download_installer(release, tmp_path, threading.Event())
    assert network.call_count == 2 and path.read_bytes() == DATA


@pytest.mark.parametrize("contents", [DATA[:-1], b"X" * len(DATA), DATA + b"X"])
def test_bad_download_never_replaces_old_installer(tmp_path, monkeypatch, contents):
    release = updates.parse_release(release_payload())
    target = tmp_path / "JoyKeyboard-Setup.exe"
    target.write_bytes(b"old verified version")
    monkeypatch.setattr(updates, "_open", lambda _: io.BytesIO(contents))
    with pytest.raises(updates.UpdateError):
        updates.download_installer(release, tmp_path, threading.Event())
    assert target.read_bytes() == b"old verified version"
    assert not (tmp_path / "JoyKeyboard-Setup.exe.part").exists()


def test_cancelled_and_failed_downloads_remove_partial_file(tmp_path, monkeypatch):
    release = updates.parse_release(release_payload())
    cancel = threading.Event()
    class CancelStream(io.BytesIO):
        def read1(self, count):
            cancel.set()
            return super().read1(count)
    monkeypatch.setattr(updates, "_open", lambda _: CancelStream(DATA))
    with pytest.raises(updates.UpdateCancelled):
        updates.download_installer(release, tmp_path, cancel)
    assert not list(tmp_path.iterdir())
    monkeypatch.setattr(updates, "_open", Mock(side_effect=URLError("offline")))
    with pytest.raises(updates.UpdateError, match="internet"):
        updates.download_installer(release, tmp_path, threading.Event())
    assert not list(tmp_path.iterdir())


def test_no_new_release_does_not_download(monkeypatch, tmp_path):
    monkeypatch.setattr(updates, "check_latest", lambda _: None)
    download = Mock()
    monkeypatch.setattr(updates, "download_installer", download)
    assert updates.prepare_update(tmp_path, threading.Event()) is None
    download.assert_not_called()


def test_install_helper_waits_verifies_preserves_startup_and_quotes_paths(tmp_path, monkeypatch):
    release = updates.parse_release(release_payload())
    path = tmp_path / "Joy's $(literal) folder" / "JoyKeyboard-Setup.exe"
    path.parent.mkdir()
    path.write_bytes(DATA)
    update = updates.ReadyUpdate(release, path)
    launch = Mock()
    monkeypatch.setattr(updates.subprocess, "Popen", launch)
    executable = tmp_path / "App With Spaces" / "JoyKeyboard.exe"
    updates.launch_installer(update, executable, 1234, True)
    arguments = launch.call_args.args[0]
    assert arguments[1:4] == ["-NoProfile", "-NonInteractive", "-EncodedCommand"]
    script = base64.b64decode(arguments[4]).decode("utf-16le")
    assert script.index("Wait-Process") < script.index("[Security.Cryptography.SHA256]::Create()") < script.index("$result = Start-Process")
    assert "Joy''s $(literal) folder" in script and "/TASKS=autostart" in script
    assert "/NORESTART" in script and "/FORCECLOSEAPPLICATIONS" not in script
    assert launch.call_args.kwargs["creationflags"] == updates.subprocess.CREATE_NO_WINDOW
    assert "/TASKS='" in updates.installer_script(update, executable, 1234, False)


def test_changed_installer_is_never_launched(tmp_path, monkeypatch):
    path = tmp_path / "JoyKeyboard-Setup.exe"
    path.write_bytes(b"tampered")
    update = updates.ReadyUpdate(updates.parse_release(release_payload()), path)
    launch = Mock()
    monkeypatch.setattr(updates.subprocess, "Popen", launch)
    with pytest.raises(updates.UpdateError):
        updates.launch_installer(update, tmp_path / "JoyKeyboard.exe", 1234, True)
    launch.assert_not_called()
