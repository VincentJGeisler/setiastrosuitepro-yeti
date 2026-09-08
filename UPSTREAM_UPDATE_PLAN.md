# YETI Upstream Update Plan

## Objective

Update Seti Astro Suite Pro YETI from its May 2026 base to upstream `v1.21.4`
(`upstream/main` at `d7f0d40e`) while preserving YETI's defining runtime and
distribution architecture.

Current comparison at plan creation:

- YETI `main`: `c5c5578a`
- Upstream `main`: `d7f0d40e`
- YETI-only history: 20 commits
- Upstream-only history: 650 commits
- Resulting tree delta: roughly 200 files, 98,953 insertions, 28,282 deletions

## Integration Strategy

Do not merge upstream into the old YETI tree and do not mechanically cherry-pick
650 upstream commits. Upstream history contains frequent dev-to-main merges,
release metadata commits, packaging churn, and changes that conflict with YETI's
reason for existing.

Instead:

1. Create `integration/upstream-1.21.4-yeti` from `upstream/main`.
2. Replay the *semantic content* of the YETI-only commits in chronological order.
3. Skip merge-only commits and changes already present upstream after verifying
   them by patch/content comparison.
4. Resolve conflicts in favor of current upstream application features, but in
   favor of YETI for runtime, dependency ownership, packaging, launch behavior,
   and enterprise accelerator support.
5. Keep the integration on its own branch until all validation gates pass.

## Non-Negotiable YETI Invariants

- The application runs as ordinary, unfrozen Python.
- Installation uses standard `pip`, conda, or user-created `venv` environments.
- The application never creates or owns a hidden/isolated Python runtime.
- The application never auto-installs Torch, ONNX Runtime, CUDA packages, or other
  Python dependencies.
- Torch is imported from the active environment; users/admins select compatible
  Torch and CUDA builds.
- Enterprise accelerators, especially A100-class compute capability 8.0 hardware,
  must not be rejected by consumer-GPU assumptions.
- ONNX Runtime selection remains externally managed, including nightly GPU builds
  where stable packages do not support the target datacenter GPU stack.
- Numba JIT remains usable and must not depend on PyInstaller/frozen behavior.
- Existing model discovery behavior, including the required `pyXXX` runtime path
  convention where still applicable, must not regress.
- No PyInstaller artifacts, self-extracting installers, or "one-click" environment
  management are reintroduced.

## Protected and High-Risk Areas

Treat changes in these files/areas as manual ports, not automatic conflict choices:

- `pyproject.toml`, `requirements.txt`, `poetry.lock`
- `src/setiastro/saspro/runtime_torch.py`
- `src/setiastro/saspro/accel_installer.py`
- `src/setiastro/saspro/accel_workers.py`
- `src/setiastro/saspro/__main__.py`, `gui_entry.py`, and launch scripts
- `src/setiastro/saspro/ops/settings.py`
- Torch-, ONNX-, Numba-, SyQon-, and Cosmic Clarity-related engines and model paths
- update/install UI and `updates.json`
- platform packaging scripts such as `create_dmg.sh`

## Implementation Phases

### 1. Establish the integration branch

- Branch from the fetched, immutable `upstream/main` commit identified above.
- Record the YETI and upstream SHAs in the integration commit message or notes.
- Do not modify or force-update `main`.

### 2. Replay YETI architecture

- Enumerate all commits reachable from YETI `main` but not from the fork point.
- Replay non-merge YETI commits with `git cherry-pick -n` or equivalent patch
  application so each conflict can be inspected before committing.
- Omit `5f783db1` (merge-only) unless it contains a unique tree change not supplied
  by its parents.
- Omit or reduce `c5c5578a` where its noise-suppression/sigma-clipping changes are
  already incorporated upstream.
- Preserve useful upstream evolution inside protected files, manually adapting it
  to the simplified YETI runtime API rather than replacing whole files blindly.

### 3. Reconcile packaging and dependencies

- Retain current upstream application dependencies needed by new features.
- Remove executable/freezer-only and application-managed-runtime dependencies.
- Preserve a valid PEP 440 YETI version identity.
- Ensure the console entry point launches ordinary Python package code.
- Ensure importing the package does not install, download, or mutate environments.

### 4. Reconcile accelerator behavior

- Port new upstream backend-selection and engine safeguards onto YETI's direct
  environment imports.
- Keep CPU fallback functional.
- Detect/report available Torch, CUDA, and ONNX providers without attempting repair.
- Avoid hard-coded GPU allowlists or compute-capability assumptions that exclude
  A100-class hardware.
- Keep model lookup compatible with YETI's established user runtime/model layout.

### 5. Preserve upstream features

- Retain all upstream tools and fixes added through 1.21.4 unless they inherently
  require forbidden runtime management.
- Wire new tools into menus, icons, presets, resources, and command IDs as upstream
  does.
- Preserve upstream data/catalog and image resources byte-for-byte where possible.

### 6. Validation gates

Run the strongest available subset locally and report anything blocked by missing
GPU hardware or optional dependencies:

1. `git diff --check`
2. Parse/compile all Python sources (`compileall` or equivalent).
3. Build package metadata/wheel without dependency installation when tooling allows.
4. Run the repository's focused and general tests that do not require unavailable
   models, GUI display, or GPU hardware.
5. Import smoke test for the package and key runtime/accelerator modules.
6. Static audit for environment creation, `pip` subprocesses, PyInstaller/frozen
   branches, and automatic Torch/ONNX installation.
7. Verify no YETI documentation or enterprise-runtime rationale was lost.
8. Compare the final tree against upstream and explain every remaining divergence in
   protected areas.

## Deliverables

- Integration branch only; `main` remains untouched.
- A logically grouped commit or small commit series with conflict decisions described.
- Test/audit results, including environmental limitations.
- A concise list of skipped upstream behavior and why it violates YETI invariants.
- No push to GitHub until explicitly requested.

## Review Corrections Applied

- `ensure_torch_installed` rejects the GUI's `0.0.0+unavailable` Torch stub.
- ONNX Runtime providers are external/user-managed. Provider entries were removed
  from `pyproject.toml` and generated `requirements.txt` so an ORT nightly install
  cannot be overwritten by a stable provider. The stale `poetry.lock` was removed
  because Poetry was unavailable to regenerate it after that dependency change;
  regenerate it with Poetry before publishing a lockfile-based release.
- README installation instructions now require exactly one provider for consumer
  NVIDIA, datacenter NVIDIA, CPU, or Windows DirectML environments.
