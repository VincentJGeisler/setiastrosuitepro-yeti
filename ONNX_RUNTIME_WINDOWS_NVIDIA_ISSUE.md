# ONNX Runtime provider ownership in YETI

YETI does not select or install an ONNX Runtime provider for the user. This is
intentional: stable GPU wheels can be incompatible with A100-class hardware,
and installing a stable provider alongside `ort-nightly-gpu` can overwrite or
conflict with the datacenter configuration.

## User-managed choices

Install exactly one provider in the active conda/venv environment before
installing YETI:

- Consumer NVIDIA GPU: `pip install onnxruntime-gpu`
- NVIDIA A100/A6000/H100: install `ort-nightly-gpu` from the ORT nightly index
- CPU-only: `pip install onnxruntime`
- Windows AMD/Intel DirectML: `pip install onnxruntime-directml`

Do not install multiple provider packages in one environment. YETI keeps only
the `onnx` model-format dependency in package metadata and reports available
providers without attempting repair or replacement.

## A100 rationale

On Windows systems with NVIDIA datacenter GPUs, hard-coded DirectML or stable
GPU provider assumptions can force CUDA execution to fall back to CPU. The
provider choice must therefore remain an administrator/user decision based on
the installed driver, CUDA, and ONNX Runtime stack.

See [README.YETI.md](README.YETI.md) for copy-and-paste installation commands.
