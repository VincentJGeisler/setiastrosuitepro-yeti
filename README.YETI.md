# Seti Astro Suite Pro - YETI Edition

**"No sippy cups. Just a proper screw-top coffee mug."**

This is a fork of [SetiAstroSuitePro](https://github.com/setiastro/setiastrosuitepro) that removes the over-engineered packaging, broken auto-installers, and PyInstaller executables that don't work.

## What Changed

### Removed (The Sippy Cup Bullshit)
- ❌ PyInstaller bundled executables
- ❌ Isolated runtime venv auto-installer
- ❌ Hardware acceleration auto-installer that tries to compile from source
- ❌ Complex runtime detection and package management
- ❌ Broken Numba JIT in frozen executables

### Kept (The Actual Coffee)
- ✅ All the actual astrophotography tools
- ✅ GPU acceleration with proper PyTorch
- ✅ The source code (which actually works)
- ✅ Simple installation as a normal Python package

## Why This Fork Exists

The original project tries to bundle everything into self-contained executables and manage its own Python environments. This approach:

1. **Breaks Numba JIT** - JIT compilation crashes in PyInstaller bundles
2. **Tries to compile from source** - Auto-installer fails without build tools
3. **Over-complicates everything** - Multiple failure points, zero error recovery
4. **Doesn't work on high-end hardware** - Users with 5x A100 GPUs couldn't use the software

**YETI Edition philosophy:** Trust users to manage their own Python environment. Ship as a normal package. Use pre-built wheels. Keep it simple.

## Installation

### Prerequisites
- Python 3.12, 3.13, or 3.14
- For GPU support: NVIDIA GPU with CUDA 12.4+ drivers

### Install

```bash
# Install PyTorch with CUDA support (for GPU acceleration)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# Install SetiAstroSuitePro YETI Edition
pip install git+https://github.com/VincentJGeisler/setiastrosuitepro-yeti.git

# Run it
setiastrosuitepro
```

That's it. No executables, no auto-installers, no isolated venvs, no compilation required.

### CPU-Only Installation

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install git+https://github.com/VincentJGeisler/setiastrosuitepro-yeti.git
```

## What Actually Works Now

- ✅ Launches without crashing
- ✅ Numba JIT compilation works
- ✅ GPU acceleration with PyTorch/CUDA
- ✅ SyQon AI tools (Prism, NAFNet, Parallax)
- ✅ All astrophotography processing features
- ✅ Proper error messages when things fail

## Development

```bash
git clone https://github.com/VincentJGeisler/setiastrosuitepro-yeti.git
cd setiastrosuitepro-yeti
pip install -r requirements.txt
pip install -e .
python setiastrosuitepro.py
```

## Credits

This fork is based on [SetiAstroSuitePro](https://github.com/setiastro/setiastrosuitepro) by Franklin Marek and contributors.

YETI Edition modifications: Remove broken packaging, keep working software.

## License

GNU General Public License v3.0 (same as original)

---

**Original issue that led to this fork:** https://github.com/setiastro/setiastrosuitepro/issues/84
