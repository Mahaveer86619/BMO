import os
import shutil
import subprocess


def detect_compute_mode(override: str = "") -> str:
    """Returns 'cuda' or 'cpu' — read by anything that needs to pick a device
    (faster-whisper's `device=`, XTTS, etc., once those are wired in).

    Resolution order:
      1. explicit `override` (AISettings.compute_mode_override / COMPUTE_MODE_OVERRIDE env var)
      2. BMO_COMPUTE_MODE — set by docker/entrypoint.sh at container boot after probing nvidia-smi
      3. torch.cuda.is_available(), if torch happens to already be installed
      4. a raw nvidia-smi probe, for when torch isn't installed yet
      5. "cpu"

    Note: this only decides *behavior* at runtime. Whether CUDA-enabled wheels
    (e.g. torch built for cu121) are even present in the image is a *build-time*
    choice — the ENABLE_GPU build arg in server/Dockerfile.
    """
    if override in ("cpu", "cuda"):
        return override

    env_mode = os.environ.get("BMO_COMPUTE_MODE", "")
    if env_mode in ("cpu", "cuda"):
        return env_mode

    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass

    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "-L"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and "GPU" in result.stdout:
                return "cuda"
        except Exception:
            pass

    return "cpu"
