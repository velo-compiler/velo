import os
import subprocess
import sys

# On Windows with native Win32 Python, CreateProcess fails on relative executable paths
# with forward slashes (e.g. "bin/velo.exe"). Normalize executable path in subprocess calls.
if sys.platform == "win32":
    _orig_popen = subprocess.Popen

    class _PatchedPopen(_orig_popen):
        def __init__(self, args, *a, **kw):
            if isinstance(args, (list, tuple)) and args:
                first = args[0]
                if isinstance(first, str) and "/" in first and not os.path.isabs(first):
                    args = list(args)
                    args[0] = os.path.normpath(first)
            super().__init__(args, *a, **kw)

    subprocess.Popen = _PatchedPopen

