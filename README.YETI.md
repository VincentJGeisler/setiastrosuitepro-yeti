# Seti Astro Suite Pro - YETI Edition

**"No sippy cups. Just a proper screw-top coffee mug."**

This is a fork of [SetiAstroSuitePro](https://github.com/setiastro/setiastrosuitepro) that removes the over-engineered packaging, broken auto-installers, and PyInstaller executables that don't work.

> **🚧 ACTIVE DEVELOPMENT:** Major refactoring in progress to eliminate isolated venv complexity and use standard Python packaging. The goal: install like any other Python package, manage your own environment, no surprises.

## Why This Fork Exists

The original project tries to bundle everything into self-contained executables and manage its own Python environments. This approach:

1. **Breaks Numba JIT** - JIT compilation crashes in PyInstaller bundles (see [issue #84](https://github.com/setiastro/setiastrosuitepro/issues/84))
2. **Tries to compile from source** - Auto-installer fails without Visual Studio Build Tools
3. **Over-complicates everything** - Isolated venvs, auto-installers, complex package management
4. **Doesn't work on high-end hardware** - Crashes on systems with 5x A100 GPUs before it can even detect them

**YETI Edition philosophy:**
- Standard Python packaging (conda/venv)
- Users manage their own environments
- Pre-built wheels from official sources
- No auto-install, no bundled executables, no sippy cups

## Installation (The Right Way)

### Create an environment (Conda example)

```bash
conda create -n saspro python=3.12
conda activate saspro
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

You can use a standard Python venv instead:

```bash
python3.12 -m venv ~/saspro-env
source ~/saspro-env/bin/activate  # Windows: ~/saspro-env/Scripts/activate.bat
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

Install exactly one ONNX Runtime provider in that active environment. YETI does
not declare or replace any provider package:

```bash
# Consumer NVIDIA GPU (RTX 30xx/40xx):
pip install onnxruntime-gpu

# NVIDIA datacenter GPU (A100/A6000/H100): use the nightly provider instead.
pip uninstall -y onnxruntime onnxruntime-gpu ort-nightly-gpu  # if present
pip install ort-nightly-gpu --index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/ORT-Nightly/pypi/simple/

# CPU-only (all platforms):
pip install onnxruntime

# Windows AMD/Intel DirectML (instead of the providers above):
pip install onnxruntime-directml
```

Do not install more than one of `onnxruntime`, `onnxruntime-gpu`,
`ort-nightly-gpu`, or `onnxruntime-directml` in the same environment.

Finally install and run YETI:

```bash
pip install git+https://github.com/VincentJGeisler/setiastrosuitepro-yeti.git
setiastrosuitepro
```

### For Different CUDA Versions

- **CUDA 12.1:** `https://download.pytorch.org/whl/cu121`
- **CUDA 11.8:** `https://download.pytorch.org/whl/cu118`
- **ROCm (AMD):** `https://download.pytorch.org/whl/rocm6.0`
- See [PyTorch installation](https://pytorch.org/get-started/locally/) for more options

## Why Use a Virtual Environment?

**You should ALWAYS use a conda/venv environment for this application:**

✅ **Isolation** - Dependencies don't conflict with other projects
✅ **Control** - You choose Python version, PyTorch version, CUDA version
✅ **Clean** - Easy to delete and recreate if something breaks
✅ **Standard** - This is how Python development works
✅ **Reproducible** - Same environment on different machines

**Don't install into system Python.** Seriously, don't.

## Current Status

### What Works
- ✅ Installation via pip (in a venv)
- ✅ All astrophotography processing tools
- ✅ GPU acceleration with manually installed PyTorch
- ✅ Numba JIT compilation (when not frozen by PyInstaller)
- ✅ SyQon AI tools (Prism, NAFNet, Parallax) with proper PyTorch

### What's Being Fixed
- 🚧 Removing isolated runtime venv code (~800 lines of complexity)
- 🚧 Simplifying hardware acceleration installer
- 🚧 Removing PyInstaller build scripts
- 🚧 Making all engine files use system torch directly
- 🚧 Updating settings dialog to show status instead of auto-install

### What's Removed
- ❌ PyInstaller bundled executables (.exe/.app)
- ❌ Auto-installer that compiles from source
- ❌ Isolated runtime venv management
- ❌ "Sippy cup" complexity

## Runtime and provider ownership

The application uses the Python interpreter that launched it. It never creates
an application-owned runtime and never installs Torch, CUDA, or ONNX packages.
The acceleration status control only reports what is present in the active
environment; install or change providers manually using the commands above.

## Development

```bash
# Clone and setup
git clone https://github.com/VincentJGeisler/setiastrosuitepro-yeti.git
cd setiastrosuitepro-yeti
conda create -n saspro-dev python=3.12
conda activate saspro-dev

# Install dependencies
pip install -r requirements.txt

# Install in editable mode
pip install -e .

# Run from source
python setiastrosuitepro.py
```

## Contributing

The main goal right now: **Simplify the runtime code.**

Priority areas:
1. Remove isolated venv creation from `runtime_torch.py`
2. Simplify `accel_installer.py` to just check for torch availability
3. Update all engine files to use standard `import torch`
4. Remove PyInstaller build scripts
5. Document proper venv-based installation

See the refactoring plan in [DEVELOPMENT.md](DEVELOPMENT.md) (coming soon).

## Credits

This fork is based on [SetiAstroSuitePro](https://github.com/setiastro/setiastrosuitepro) by Franklin Marek and contributors.

YETI Edition: Strip out the over-engineering, keep the astrophotography tools.

## License

GNU General Public License v3.0 (same as original)

---

**Original issue that led to this fork:** https://github.com/setiastro/setiastrosuitepro/issues/84
**Discussion:** [YETI Edition Goals](https://github.com/VincentJGeisler/setiastrosuitepro-yeti/discussions) (TBD)
