# ONNX Runtime Windows+NVIDIA assumption is broken: hardcoded DirectML kills datacenter GPU performance

## Problem

`pyproject.toml` lines 64-69 hardcode `onnxruntime-directml` for **all Windows systems**:

```toml
"onnxruntime-gpu" = [
    {version = ">=1.19.0,<1.25.0", markers = "sys_platform == 'linux' and python_version == '3.10'"},
    {version = ">=1.25.0", markers = "sys_platform == 'linux' and python_version >= '3.11'"}
]
"onnxruntime-directml" = {version = ">=1.20.0", markers = "sys_platform == 'win32'"}
```

**This assumes Windows = consumer laptop with integrated graphics.** It completely ignores Windows systems with NVIDIA datacenter GPUs.

## Impact

On a **Windows 10 Pro system with 5x NVIDIA A100-80GB GPUs**:

1. `CUDAExecutionProvider` is available
2. ONNX Runtime attempts to use it
3. **"CUDA kernel mismatch detected — falling back to CPU..."**
4. Processing takes **260 seconds on CPU** when it should take **seconds on GPU**

```
🔍 Available ONNX providers: TensorrtExecutionProvider, CUDAExecutionProvider, CPUExecutionProvider
🔍 Attempting providers: CUDAExecutionProvider, CPUExecutionProvider
✅ Aberration AI: Using GPU provider CUDAExecutionProvider
CUDA kernel mismatch detected — falling back to CPU...
```

## Why This Is Badly Vibe Coded Bullshit

The original codebase makes **broken assumptions** about Windows users:

- **Assumption**: Windows users have consumer hardware
- **Reality**: Scientific computing happens on Windows workstations with NVIDIA datacenter GPUs
- **Result**: Zero support for Windows+NVIDIA CUDA, forcing CPU fallback on $80k+ GPU hardware

Meanwhile, **PyTorch 2.6.0+cu124 works perfectly** on the same system with the same CUDA 12.4/13.2 drivers.

## System Specs

- **OS**: Windows 10 Pro (10.0.19045)
- **GPUs**: 5x NVIDIA A100-80GB (CUDA Capability 8.0)
- **CUDA Toolkit**: 12.4
- **Driver**: 566.36 (supports CUDA 13.2)
- **PyTorch**: 2.6.0+cu124 (works fine with CUDA)
- **ONNX Runtime**: Falls back to CPU due to DirectML conflict

## Root Cause

1. `pyproject.toml` installs `onnxruntime-directml` on Windows
2. DirectML conflicts with CUDA provider loading
3. Even after uninstalling DirectML and installing `onnxruntime-gpu`, kernel mismatch forces CPU fallback
4. The ONNX Runtime version bundled doesn't properly support this CUDA environment

## Fix Needed

`pyproject.toml` needs to detect **Windows+NVIDIA** and install `onnxruntime-gpu` instead of DirectML:

```toml
"onnxruntime-gpu" = [
    {version = ">=1.19.0,<1.25.0", markers = "(sys_platform == 'linux' or (sys_platform == 'win32' and has_nvidia_gpu)) and python_version == '3.10'"},
    {version = ">=1.25.0", markers = "(sys_platform == 'linux' or (sys_platform == 'win32' and has_nvidia_gpu)) and python_version >= '3.11'"}
]
"onnxruntime-directml" = {version = ">=1.20.0", markers = "sys_platform == 'win32' and not has_nvidia_gpu"}
```

Or at minimum, **document that Windows+NVIDIA CUDA is not supported** and users need to manually fix the dependencies.

## The YETI Fork Goal

This is exactly the kind of **sippy cup over-engineering** that YETI Edition exists to fix. The original codebase tries to be too clever about hardware detection and auto-installation, making broken assumptions that kill performance on real scientific computing hardware.

**Stop assuming. Let users manage their own environments.**
