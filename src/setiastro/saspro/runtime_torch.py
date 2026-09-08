"""
YETI Edition: Simplified PyTorch runtime shim.

Removes venv isolation complexity. Users manage their own Python environments.
Preserves all 18 public API functions from original runtime_torch.py.

This is a backward-compatible shim that maintains the exact same function
signatures while removing ~1700 lines of venv management code.
"""

from __future__ import annotations

import os
import sys
import platform
import subprocess
import warnings
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Globals
# ──────────────────────────────────────────────────────────────────────────────

_TORCH_CACHED = None
_SUPPORTED_PY_MINORS = [10, 11, 12, 13, 14]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _safe_text_kwargs() -> dict:
    """Return kwargs for subprocess text output with safe encoding."""
    import locale
    if platform.system() == "Windows":
        enc = locale.getpreferredencoding(False) or "cp1252"
    else:
        enc = locale.getpreferredencoding(False) or "utf-8"
    return {"text": True, "encoding": enc, "errors": "replace"}


def _rt_dbg(msg: str, status_cb=print):
    """Debug message with error handling."""
    try:
        status_cb(f"[RT] {msg}")
    except Exception:
        print(f"[RT] {msg}", flush=True)


# ──────────────────────────────────────────────────────────────────────────────
# 1. import_torch - Cache globally, raise if missing
# ──────────────────────────────────────────────────────────────────────────────

def import_torch(
    prefer_cuda: bool = True,
    prefer_xpu: bool = False,
    prefer_dml: bool = False,
    prefer_rocm: bool = False,
    status_cb=print,
    *,
    require_torchaudio: bool = False,
    allow_install: bool = False,
):
    """Import PyTorch from current environment (no venv isolation)."""
    global _TORCH_CACHED

    if _TORCH_CACHED is not None:
        return _TORCH_CACHED

    try:
        import torch
        if getattr(torch, "__version__", "") == "0.0.0+unavailable":
            raise ImportError("PyTorch unavailable stub is active")
        _TORCH_CACHED = torch
        _rt_dbg(f"Using PyTorch {torch.__version__}", status_cb)
        return torch
    except ImportError:
        raise RuntimeError(
            "PyTorch not found in current environment.\n"
            "Install with: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124\n"
            "Make sure you've activated your conda/venv environment."
        )


# ──────────────────────────────────────────────────────────────────────────────
# 2. add_runtime_to_sys_path - No-op in YETI
# ──────────────────────────────────────────────────────────────────────────────

def add_runtime_to_sys_path(status_cb=print) -> None:
    """No-op in YETI Edition - no isolated venv."""
    pass


# ──────────────────────────────────────────────────────────────────────────────
# 3. best_device - Keep existing logic
# ──────────────────────────────────────────────────────────────────────────────

def best_device(torch, *, prefer_cuda=True, prefer_dml=False, prefer_xpu=False):
    """Return the best available device (CUDA/XPU/DML/MPS/CPU)."""
    if prefer_cuda and getattr(torch, "cuda", None) and torch.cuda.is_available():
        return torch.device("cuda")
    if prefer_xpu and hasattr(torch, "xpu") and torch.xpu.is_available():
        return torch.device("xpu")
    if prefer_dml and platform.system() == "Windows":
        try:
            import torch_directml
            d = torch_directml.device()
            _ = (torch.ones(1, device=d) + 1).item()
            return d
        except Exception:
            pass
    if (prefer_cuda or prefer_xpu or prefer_dml) and \
            getattr(getattr(torch, "backends", None), "mps", None) and \
            torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def np_to_torch(arr, device=None, dtype=None, torch=None):
    """Convert a NumPy array without relying on torch's NumPy C bridge."""
    import numpy as np

    if torch is None:
        import torch as _torch
        torch = _torch
    a = np.ascontiguousarray(arr)
    try:
        tensor = torch.from_dlpack(a)
    except Exception:
        tensor = torch.as_tensor(a)
    if dtype is not None:
        tensor = tensor.to(dtype=dtype)
    if device is not None:
        tensor = tensor.to(device)
    return tensor


def torch_to_np(tensor):
    """Convert a Torch tensor to a CPU NumPy array."""
    import numpy as np

    tensor = tensor.detach().cpu().contiguous()
    try:
        return np.from_dlpack(tensor)
    except Exception:
        return tensor.numpy()


def mps_is_usable(torch=None) -> bool:
    """Return whether Apple Silicon exposes a usable MPS backend."""
    if platform.system() != "Darwin" or platform.machine().lower() not in ("arm64", "aarch64"):
        return False
    try:
        if torch is None:
            import torch as _torch
            torch = _torch
        backend = getattr(getattr(torch, "backends", None), "mps", None)
        return bool(backend and backend.is_available())
    except Exception:
        return False


def directml_probe_ok(status_cb=lambda *_: None, timeout=60, force=False) -> bool:
    """Check an already-installed DirectML provider without changing the environment."""
    del timeout, force
    if platform.system() != "Windows":
        return False
    try:
        import torch
        import torch_directml

        device = torch_directml.device()
        _ = (torch.ones(1, device=device) + 1).item()
        return True
    except Exception as exc:
        try:
            status_cb(f"[RT] DirectML unavailable: {exc}")
        except Exception:
            pass
        return False


# ──────────────────────────────────────────────────────────────────────────────
# 4. _user_runtime_dir - Return LOCALAPPDATA path structure
# ──────────────────────────────────────────────────────────────────────────────

def _user_runtime_dir(status_cb=print) -> Path:
    """Return user runtime directory (LOCALAPPDATA/SASpro/runtime/pyXXX).

    CRITICAL: Must include pyXXX tag for model discovery compatibility.
    """
    env_override = os.getenv("SASPRO_RUNTIME_DIR")
    if env_override:
        return Path(env_override).expanduser().resolve()

    sysname = platform.system()
    if sysname == "Windows":
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sysname == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    # Include Python version tag (e.g., py313) for model directory compatibility
    tag = f"py{sys.version_info.major}{sys.version_info.minor}"
    return base / "SASpro" / "runtime" / tag


# ──────────────────────────────────────────────────────────────────────────────
# 5. _venv_paths - Return dict with current sys.executable
# ──────────────────────────────────────────────────────────────────────────────

def _venv_paths(rt: Path) -> dict:
    """Return venv path dict. In YETI, uses current Python."""
    return {
        "venv": rt / "venv",
        "python": Path(sys.executable),
        "marker": rt / "torch_installed.json",
    }


# ──────────────────────────────────────────────────────────────────────────────
# 6. _venv_pyver - Return sys.version_info
# ──────────────────────────────────────────────────────────────────────────────

def _venv_pyver(venv_python: Path) -> tuple[int, int] | None:
    """Return (major, minor) for Python interpreter."""
    try:
        out = subprocess.check_output(
            [str(venv_python), "-c",
             "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
            **_safe_text_kwargs(),
        ).strip()
        maj, min_ = out.split(".")
        return int(maj), int(min_)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# 7. _check_cuda_in_venv - In-process check
# ──────────────────────────────────────────────────────────────────────────────

def _check_cuda_in_venv(venv_python: Path, status_cb=print) -> tuple[bool, str | None, str | None]:
    """Check if CUDA is available in venv Python."""
    warnings.warn(
        "_check_cuda_in_venv: 'venv_python' parameter is ignored in YETI Edition. "
        "CUDA availability is checked in the current process, not a subprocess. "
        "This function may be removed in a future release.",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        import torch
        cuda_tag = getattr(getattr(torch, "version", None), "cuda", None)
        has_cuda = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
        return has_cuda, cuda_tag, None
    except Exception as e:
        return False, None, str(e)


# ──────────────────────────────────────────────────────────────────────────────
# 7. _ban_shadow_torch_paths - No-op
# ──────────────────────────────────────────────────────────────────────────────

def _ban_shadow_torch_paths(status_cb=print) -> None:
    """No-op in YETI Edition."""
    pass


# ──────────────────────────────────────────────────────────────────────────────
# 8. _purge_bad_torch_from_sysmodules - No-op
# ──────────────────────────────────────────────────────────────────────────────

def _purge_bad_torch_from_sysmodules(status_cb=print) -> None:
    """No-op in YETI Edition."""
    pass


# ──────────────────────────────────────────────────────────────────────────────
# 9. prewarm_torch_cache - No-op
# ──────────────────────────────────────────────────────────────────────────────

def prewarm_torch_cache(
    status_cb=print,
    *,
    require_torchaudio: bool = False,
    ensure_venv: bool = True,
    ensure_numpy: bool = False,
    validate_marker: bool = True,
) -> None:
    """No-op in YETI Edition."""
    pass


# ──────────────────────────────────────────────────────────────────────────────
# 10. _find_system_python_cmd_for_minor - Simplified probe
# ──────────────────────────────────────────────────────────────────────────────

def _find_system_python_cmd_for_minor(minor: int) -> list[str] | None:
    """Find Python X.Y command for given minor version."""
    sysname = platform.system()

    if sysname == "Windows":
        try:
            subprocess.check_output(["py", f"-3.{minor}", "--version"], **_safe_text_kwargs(), timeout=5)
            return ["py", f"-3.{minor}"]
        except Exception:
            pass
    else:
        cmd = f"python3.{minor}"
        try:
            subprocess.check_output([cmd, "--version"], **_safe_text_kwargs(), timeout=5)
            return [cmd]
        except Exception:
            pass

    return None


# ──────────────────────────────────────────────────────────────────────────────
# 11. is_supported_runtime_python - Check against _SUPPORTED_PY_MINORS
# ──────────────────────────────────────────────────────────────────────────────

def is_supported_runtime_python(version: tuple[int, int] | None = None) -> bool:
    """Check if version is supported."""
    if version is None:
        version = (sys.version_info.major, sys.version_info.minor)
    major, minor = version
    return major == 3 and minor in _SUPPORTED_PY_MINORS


# ──────────────────────────────────────────────────────────────────────────────
# 12. supported_python_version_strings - Format list
# ──────────────────────────────────────────────────────────────────────────────

def supported_python_version_strings() -> list[str]:
    """Return list of supported Python versions as strings."""
    return [f"3.{minor}" for minor in _SUPPORTED_PY_MINORS]


# ──────────────────────────────────────────────────────────────────────────────
# 13. supported_python_versions_text - Format with conjunction
# ──────────────────────────────────────────────────────────────────────────────

def supported_python_versions_text(*, conjunction: str = "or") -> str:
    """Return supported Python versions as formatted text."""
    versions = supported_python_version_strings()
    if not versions:
        return ""
    if len(versions) == 1:
        return versions[0]
    return f"{', '.join(versions[:-1])}, {conjunction} {versions[-1]}"


# ──────────────────────────────────────────────────────────────────────────────
# 14. _runtime_base_dir - Return platform LOCALAPPDATA/SASpro/runtime
# ──────────────────────────────────────────────────────────────────────────────

def _runtime_base_dir() -> Path:
    """Return base runtime directory."""
    env_override = os.getenv("SASPRO_RUNTIME_DIR")
    if env_override:
        base = Path(env_override).expanduser().resolve()
    else:
        sysname = platform.system()
        if sysname == "Windows":
            base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        elif sysname == "Darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        base = base / "SASpro" / "runtime"
    return base


# ──────────────────────────────────────────────────────────────────────────────
# 15. _detect_rocm_arch - Keep existing (simple, 20 lines)
# ──────────────────────────────────────────────────────────────────────────────

def _detect_rocm_arch() -> str:
    """Return AMD ROCm gfx architecture string if detected (Linux only)."""
    try:
        if platform.system() != "Linux":
            return ""
        r = subprocess.run(
            ["rocminfo"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=8, **_safe_text_kwargs(),
        )
        out = r.stdout or ""
        for line in out.splitlines():
            s = line.strip()
            if s.startswith("Name:") and "gfx" in s:
                parts = s.split()
                for p in reversed(parts):
                    if p.startswith("gfx"):
                        return p
    except Exception:
        pass
    return ""


# ──────────────────────────────────────────────────────────────────────────────
# 16. _demote_shadow_torch_paths - Alias to _ban_shadow_torch_paths
# ──────────────────────────────────────────────────────────────────────────────

_demote_shadow_torch_paths = _ban_shadow_torch_paths
