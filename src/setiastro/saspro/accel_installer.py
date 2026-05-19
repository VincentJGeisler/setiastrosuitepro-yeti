# saspro/accel_installer_yeti.py
"""
YETI Edition: Simplified hardware acceleration status checker.

No auto-installation, no venv management, no subprocess pip calls.
Just checks if PyTorch is available and reports the backend.
"""
from __future__ import annotations
import platform
import subprocess
import sys
import os
from typing import Callable, Optional

LogCB = Callable[[str], None]


def _run(cmd):
    """Run command and return result."""
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def _has_amd_rocm() -> tuple[bool, str]:
    """Check if AMD ROCm GPU is available (Linux only)."""
    try:
        if platform.system() != "Linux":
            return False, ""
        from setiastro.saspro.runtime_torch import _detect_rocm_arch
        arch = _detect_rocm_arch()
        return (True, arch) if arch else (False, "")
    except Exception:
        return False, ""


def _has_intel_arc() -> bool:
    """Check if Intel Arc GPU is available."""
    try:
        sysname = platform.system()
        if sysname == "Windows":
            ps = _run(["powershell", "-NoProfile", "-Command",
                       "(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join ';'"])
            out = (ps.stdout or "").lower()
            return ("intel" in out) and (
                "arc" in out or "iris xe" in out
                or "a770" in out or "a750" in out or "a580" in out or "a380" in out
            )
        if sysname == "Linux":
            r = _run(["bash", "-lc", "lspci -nn | grep -i 'vga\\|3d'"])
            s = (r.stdout or "").lower()
            return ("intel" in s) and ("arc" in s or "iris xe" in s or "xe" in s)
        return False
    except Exception:
        return False


def _has_nvidia() -> bool:
    """Check if NVIDIA GPU is available."""
    try:
        sysname = platform.system()
        if sysname == "Windows":
            ps = _run(["powershell", "-NoProfile", "-Command",
                       "(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join ';'"])
            out = (ps.stdout or "").lower()
            if "nvidia" in out:
                return True
            w = _run(["wmic", "path", "win32_VideoController", "get", "name"])
            return "nvidia" in (w.stdout or "").lower()
        if sysname == "Linux":
            r = _run(["nvidia-smi", "-L"])
            return "GPU" in (r.stdout or "")
        return False
    except Exception:
        return False


def _nvidia_driver_ok(log_cb: LogCB) -> bool:
    """Check if NVIDIA driver is available and working."""
    try:
        r = _run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"])
        drv = (r.stdout or "").strip()
        if not drv:
            log_cb("nvidia-smi not found or driver not detected.")
            return False
        log_cb(f"NVIDIA driver detected: {drv}")
        return True
    except Exception:
        log_cb("Unable to query NVIDIA driver via nvidia-smi.")
        return False


def ensure_torch_installed(
    prefer_gpu: bool,
    log_cb: LogCB,
    preferred_backend: str = "auto",
) -> tuple[bool, Optional[str]]:
    """
    Check if PyTorch is installed and report backend status.

    Returns:
        (success: bool, error_msg: Optional[str])
        - If success: (True, None) - PyTorch is available
        - If failed: (False, error_msg) - PyTorch not found or error

    Notes:
        This is YETI Edition - status check only, NO auto-installation.
        Users must install PyTorch manually via pip/conda.
    """
    log_cb(
        "[YETI] Note: This checks PyTorch availability only. "
        "No packages will be downloaded or installed. "
        "To install PyTorch, use pip/conda manually."
    )
    try:
        # Try to import torch
        try:
            import torch
        except ImportError:
            error_msg = (
                "PyTorch not installed in current environment.\n"
                "Install with one of these commands:\n"
                "  NVIDIA CUDA 12.4:  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124\n"
                "  NVIDIA CUDA 11.8:  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118\n"
                "  CPU only:          pip install torch torchvision\n"
                "  AMD ROCm:          pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm5.7\n"
                "\nOr use conda: conda install pytorch torchvision pytorch-cuda=12.4 -c pytorch -c nvidia"
            )
            log_cb(error_msg)
            return False, error_msg

        log_cb(f"PyTorch {torch.__version__} found")

        # Check what backends are available
        cuda_ok = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
        xpu_ok = bool(hasattr(torch, "xpu") and torch.xpu.is_available())
        mps_ok = bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available())

        # Check ROCm (AMD)
        rocm_ok = False
        rocm_ver = None
        try:
            rocm_ver = getattr(getattr(torch, "version", None), "hip", None)
            rocm_ok = bool(cuda_ok and rocm_ver)
        except Exception:
            rocm_ok = False

        # Report backend status
        if rocm_ok:
            arch_str = ""
            has_amd, amd_arch = _has_amd_rocm()
            if amd_arch:
                arch_str = f" ({amd_arch})"
            log_cb(f"AMD ROCm available{arch_str}; using ROCm backend (HIP {rocm_ver}).")
            return True, None

        if cuda_ok:
            try:
                name = torch.cuda.get_device_name(0)
                log_cb(f"CUDA available; using NVIDIA backend ({name}).")
            except Exception:
                log_cb("CUDA available; using NVIDIA backend.")
            return True, None

        if xpu_ok:
            try:
                name = None
                if hasattr(torch.xpu, "get_device_name"):
                    name = torch.xpu.get_device_name(0)
                if name:
                    log_cb(f"Intel XPU available ({name}).")
                else:
                    log_cb("Intel XPU available.")
            except Exception:
                log_cb("Intel XPU available.")
            return True, None

        if mps_ok:
            log_cb("Apple Metal Performance Shaders available.")
            return True, None

        # Fallback to CPU
        log_cb("PyTorch available, using CPU backend (no GPU detected).")
        return True, None

    except Exception as e:
        error_msg = str(e)
        if "PyTorch C-extension check failed" in error_msg or "Failed to load PyTorch C extensions" in error_msg:
            error_msg += (
                "\n\nHints:\n"
                " • Make sure you are not launching from a folder containing a 'torch' directory.\n"
                " • Check PYTHONPATH for conflicting PyTorch installations.\n"
                " • Try reinstalling PyTorch: pip uninstall torch && pip install torch torchvision"
            )
        log_cb(f"Error checking PyTorch: {error_msg}")
        return False, error_msg


def current_backend() -> str:
    """
    Return a human-readable string describing the current PyTorch backend.

    Returns:
        One of:
        - "CUDA (GPU name)" - NVIDIA GPU
        - "ROCm (GPU name, HIP version)" - AMD ROCm
        - "Intel XPU (GPU name)" - Intel Arc
        - "Apple MPS" - Apple Metal Performance Shaders
        - "CPU" - CPU-only
        - "Not installed" - PyTorch not found
    """
    try:
        import torch
        import importlib

        # Check for ROCm (AMD) - must check before CUDA
        try:
            hip_ver = getattr(getattr(torch, "version", None), "hip", None)
        except Exception:
            hip_ver = None

        if getattr(torch, "cuda", None) and torch.cuda.is_available():
            if hip_ver:
                # ROCm detected
                try:
                    name = torch.cuda.get_device_name(0)
                except Exception:
                    name = "AMD GPU"
                return f"ROCm ({name}, HIP {hip_ver})"
            else:
                # NVIDIA CUDA
                try:
                    name = torch.cuda.get_device_name(0)
                except Exception:
                    name = "CUDA"
                return f"CUDA ({name})"

        # Check Intel XPU
        if hasattr(torch, "xpu") and torch.xpu.is_available():
            try:
                name = None
                if hasattr(torch.xpu, "get_device_name"):
                    name = torch.xpu.get_device_name(0)
            except Exception:
                name = None
            return f"Intel XPU{f' ({name})' if name else ''}"

        # Check Apple MPS
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "Apple MPS"

        # Check if CUDA is compiled in but not available
        cuda_tag = getattr(getattr(torch, "version", None), "cuda", None)
        has_nv = _has_nvidia() and platform.system() in ("Windows", "Linux")
        if cuda_tag and has_nv:
            return f"CPU (CUDA {cuda_tag} not available — check NVIDIA driver/CUDA runtime)"

        # Check DirectML on Windows
        if platform.system() == "Windows":
            try:
                import torch_directml  # noqa
                return "DirectML"
            except Exception:
                pass

        # Default to CPU
        return "CPU"

    except Exception as e:
        import traceback
        print(f"[current_backend] Error: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return "Not installed"
