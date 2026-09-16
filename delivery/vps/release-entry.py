#!/usr/bin/python3 -I
"""Root-owned SSH forced command; no shell, SCP, SFTP or argument passthrough."""
import os
import sys

PUBLIC = {"validate-envelope", "deploy", "recover", "status", "publish-index"}
command = os.environ.get("SSH_ORIGINAL_COMMAND", "")
if command not in PUBLIC or len(sys.argv) != 1:
    raise SystemExit("restricted command")
os.execve("/usr/bin/sudo", ["sudo", "-n", "/usr/bin/python3", "-I",
          "/opt/v8std-release/delivery/vps/v8std_mcp_release.py", command],
          {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
