"""Private host logging boundary; native permissions run only in owned Linux."""
import copy
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from tests.mcp_logging_fixture import CONTAINER_LOG, HOST_LOG, DockerCommands, launch_inputs, release


class LoggingLaunchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="v8std-logging-command-")
        self.addCleanup(temporary.cleanup)
        self.record, policy = launch_inputs()
        self.adapter = release.HostAdapter(Path(temporary.name), policy)
        self.daemon = DockerCommands(self.record)
        # macOS command tests do not claim Linux root ownership evidence.
        self.enterContext(patch.object(release, "prepare_usage_log", create=True))
        self.enterContext(patch.object(release.os, "chown"))
        self.enterContext(patch.object(release, "run", self.daemon))

    def start(self):
        self.adapter.start(self.record, time.monotonic() + 5)

    def test_actual_host_start_binds_only_the_private_file_and_enables_existing_flag(self):
        self.start()
        command = next(call for call in self.daemon.calls if call[1] == "run")
        self.assertIn("type=bind,source=/var/log/v8std-mcp/tool-usage.jsonl,target=/var/log/v8std-mcp-usage.jsonl", command)
        self.assertEqual(command[command.index("--usage-log") + 1], "/var/log/v8std-mcp-usage.jsonl")
        self.assertEqual(command.count("--usage-log"), 1)
        self.assertEqual(len(self.daemon.info["Mounts"]), 3)
        self.assertEqual(command[command.index("--user") + 1], "10001:10001")

    def test_start_checks_logging_profile_but_owned_stop_still_works(self):
        self.start()
        valid = copy.deepcopy(self.daemon.info)
        # Use independently specified profiles, including a valid binding for
        # running/restart reuse; no reliance on the create command being correct.
        valid["Mounts"] = [{"Type": "bind", "Source": str(HOST_LOG),
                            "Destination": CONTAINER_LOG, "RW": True}]
        valid["Config"]["Cmd"] = ["--transport", "streamable-http", "--usage-log", CONTAINER_LOG]
        for fault in ("missing", "wrong_source", "readonly", "volume", "directory", "flag", "duplicate_flag"):
            for running in (False, True):
                with self.subTest(fault=fault, running=running):
                    info = copy.deepcopy(valid)
                    info["State"]["Running"] = running
                    if fault == "missing":
                        info["Mounts"] = []
                    elif fault == "flag":
                        info["Config"]["Cmd"] = ["--usage-log", "/tmp/wrong.jsonl"]
                    elif fault == "duplicate_flag":
                        info["Config"]["Cmd"] += ["--usage-log", "/tmp/wrong.jsonl"]
                    elif fault == "directory":
                        info["Mounts"].append({"Type": "bind", "Source": str(HOST_LOG.parent),
                                               "Destination": "/history", "RW": False})
                    else:
                        field, value = {"wrong_source": ("Source", "/tmp/wrong.jsonl"),
                                        "readonly": ("RW", False), "volume": ("Type", "volume")}[fault]
                        info["Mounts"][0][field] = value
                    self.daemon.info = info
                    self.daemon.calls.clear()
                    with self.assertRaisesRegex(release.ReleaseError, "usage_log"):
                        self.start()
                    self.assertFalse(any(call[1] in {"run", "start"} for call in self.daemon.calls))
                    self.adapter.stop(self.record, time.monotonic() + 5)
                    self.assertFalse(self.daemon.info["State"]["Running"])

    def test_valid_reuse_restarts_without_creating_another_container(self):
        self.start()
        self.daemon.info["State"]["Running"] = False
        self.daemon.calls.clear()
        self.start()
        self.assertEqual([call[1] for call in self.daemon.calls], ["inspect", "start"])
        self.assertTrue(self.daemon.info["State"]["Running"])

    def test_rotation_policy_retains_legacy_bytes_and_separate_root_copytruncate(self):
        expected = (
            "/var/lib/v8std-mcp/tool-usage.jsonl {\n"
            "    daily\n    rotate 365\n    compress\n    missingok\n    notifempty\n"
            "    copytruncate\n    su v8std-mcp v8std-mcp\n    create 0640 v8std-mcp v8std-mcp\n}\n"
            "\n/var/log/v8std-mcp/tool-usage.jsonl {\n"
            "    daily\n    rotate 365\n    compress\n    missingok\n    notifempty\n"
            "    copytruncate\n    su root root\n}\n"
        )
        path = Path(__file__).resolve().parents[1] / "scripts/v8std_mcp_usage.logrotate"
        self.assertEqual(path.read_bytes(), expected.encode())


@unittest.skipUnless(sys.platform == "linux" and os.getuid() == 0
                     and os.environ.get("V8STD_LOGGING_NATIVE") == "1", "owned native Linux root fixture only")
class NativeLoggingPreparationTests(unittest.TestCase):
    def setUp(self):
        # The Docker runner provides this private tmpfs, not a real host path.
        temporary = tempfile.TemporaryDirectory(prefix="case-", dir="/native-tests")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.log = self.root / "logs/tool-usage.jsonl"
        self.enterContext(patch.object(release, "USAGE_LOG", self.log, create=True))
        self.record, policy = launch_inputs()
        self.adapter = release.HostAdapter(self.root / "state", policy)
        self.daemon = DockerCommands(self.record)
        self.enterContext(patch.object(release, "run", self.daemon))
        old = os.umask(0o077)
        self.addCleanup(os.umask, old)

    def start(self):
        self.adapter.start(self.record, time.monotonic() + 5)

    def test_exclusive_creation_under_umask_and_reuse_preserve_inode_and_history(self):
        import pwd
        with self.assertRaises(KeyError):
            pwd.getpwuid(10001)  # Numeric ownership needs no host passwd entry.
        self.start()
        self.assertTrue(self.log.is_file(), "HostAdapter.start did not provision its private usage file")
        parent, info = self.log.parent.stat(), self.log.stat()
        self.assertEqual((parent.st_uid, parent.st_gid, stat.S_IMODE(parent.st_mode)), (0, 0, 0o700))
        self.assertEqual((info.st_uid, info.st_gid, info.st_nlink, stat.S_IMODE(info.st_mode)), (10001, 0, 1, 0o640))
        self.log.write_bytes(b'{"ts":"before","tool":"legacy-format"}\n')
        saved = self.log.read_bytes()
        self.daemon.info["State"]["Running"] = False
        self.start()
        self.assertEqual(self.log.stat().st_ino, info.st_ino)
        self.assertEqual(self.log.read_bytes(), saved)

    def test_missing_reuse_file_is_not_recreated_and_owned_stop_remains_possible(self):
        self.start()
        self.log.unlink()  # Exact disposable file, simulating operator damage.
        self.daemon.calls.clear()
        with self.assertRaisesRegex(release.ReleaseError, "usage_log_missing"):
            self.start()
        self.assertFalse(self.log.exists())
        self.assertFalse(any(call[1] in {"run", "start"} for call in self.daemon.calls))
        self.adapter.stop(self.record, time.monotonic() + 5)
        self.assertFalse(self.daemon.info["State"]["Running"])

    def test_unsafe_preexisting_files_fail_without_rewriting_history(self):
        for shape in ("symlink", "hardlink", "directory", "fifo", "owner", "group", "public", "special_mode"):
            with self.subTest(shape=shape), tempfile.TemporaryDirectory(dir=self.root) as case:
                path = Path(case) / "usage.jsonl"
                sentinel = Path(case) / "history.jsonl"
                sentinel.write_bytes(b"private unchanged history\n")
                if shape == "symlink": path.symlink_to(sentinel)
                elif shape == "hardlink": os.link(sentinel, path)
                elif shape == "directory": path.mkdir()
                elif shape == "fifo": os.mkfifo(path)
                else:
                    path.write_bytes(sentinel.read_bytes())
                    os.chown(path, 0 if shape == "owner" else 10001, 1 if shape == "group" else 0)
                    path.chmod(0o644 if shape == "public" else 0o2640 if shape == "special_mode" else 0o640)
                before = path.lstat()
                self.daemon.info = None
                self.daemon.calls.clear()
                with patch.object(release, "USAGE_LOG", path, create=True), self.assertRaises(release.ReleaseError):
                    self.start()
                after = path.lstat()
                self.assertEqual((after.st_ino, after.st_mode, after.st_uid, after.st_gid, after.st_size),
                                 (before.st_ino, before.st_mode, before.st_uid, before.st_gid, before.st_size))
                self.assertEqual(sentinel.read_bytes(), b"private unchanged history\n")
                if stat.S_ISREG(before.st_mode):
                    self.assertEqual(path.read_bytes(), b"private unchanged history\n")
                self.assertFalse(any(call[1] in {"run", "start"} for call in self.daemon.calls))

    def test_unsafe_parent_is_not_repaired_or_followed(self):
        for shape in ("symlink", "owner", "group", "public"):
            with self.subTest(shape=shape), tempfile.TemporaryDirectory(dir=self.root) as case:
                parent = Path(case) / "logs"
                other = Path(case) / "other"
                other.mkdir(mode=0o700)
                if shape == "symlink": parent.symlink_to(other, target_is_directory=True)
                else:
                    parent.mkdir(mode=0o755 if shape == "public" else 0o700)
                    if shape == "public": parent.chmod(0o755)
                    os.chown(parent, 10001 if shape == "owner" else 0, 1 if shape == "group" else 0)
                before = parent.lstat()
                with patch.object(release, "USAGE_LOG", parent / "usage.jsonl", create=True), self.assertRaises(release.ReleaseError):
                    self.start()
                after = parent.lstat()
                self.assertEqual((after.st_ino, after.st_mode, after.st_uid, after.st_gid),
                                 (before.st_ino, before.st_mode, before.st_uid, before.st_gid))
                self.assertEqual(list(other.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
