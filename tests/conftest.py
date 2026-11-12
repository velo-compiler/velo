import os
import subprocess
import sys
from pathlib import Path

# On non-Windows platforms, ensure bin/velo.exe points to bin/velo if present
if sys.platform != "win32":
    root = Path(__file__).parent.parent
    bin_velo = root / "bin" / "velo"
    bin_velo_exe = root / "bin" / "velo.exe"
    if bin_velo.exists() and not bin_velo_exe.exists():
        try:
            os.symlink("velo", str(bin_velo_exe))
        except OSError:
            import shutil
            shutil.copy2(str(bin_velo), str(bin_velo_exe))

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
else:
    _orig_popen = subprocess.Popen

    class _PatchedPosixPopen(_orig_popen):
        def __init__(self, args, *a, **kw):
            if isinstance(args, (list, tuple)) and args:
                first = str(args[0])
                if first.endswith("velo.exe") and not os.path.exists(first):
                    alt = first[:-4]
                    if os.path.exists(alt):
                        args = list(args)
                        args[0] = alt
            super().__init__(args, *a, **kw)

    subprocess.Popen = _PatchedPosixPopen
