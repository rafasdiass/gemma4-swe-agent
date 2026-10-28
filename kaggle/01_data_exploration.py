# Kaggle kernel: 01_data_exploration (T-05 proof of life, Gemma 4 Developer Agent Competition)
# Probes the L4x4 session: GPU count, per-GPU VRAM, CUDA/torch versions, disk.
# No competition data is read here; this is environment verification only.

import json
import shutil
import subprocess


def _sh(cmd: str) -> str:
    if shutil.which(cmd.split()[0]) is None:
        return f"[{cmd.split()[0]} not found]"
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    return proc.stdout.strip() or proc.stderr.strip()


def main() -> None:
    print("=== nvidia-smi ===")
    print(_sh("nvidia-smi"))

    print("\n=== nvidia-smi query (name/memory.total) ===")
    print(_sh("nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv"))

    print("\n=== python env ===")
    try:
        import torch  # noqa: PLC0415

        print(f"torch: {torch.__version__}")
        print(f"cuda available: {torch.cuda.is_available()}")
        print(f"cuda version: {torch.version.cuda}")
        print(f"device count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            print(f"  gpu{i}: {props.name}, {props.total_memory / 1024**3:.1f} GiB")
    except Exception as exc:  # noqa: BLE001
        print(f"torch probe failed: {exc}")

    print("\n=== disk ===")
    print(_sh("df -h / /kaggle/working 2>/dev/null || df -h /"))

    print("\n=== cpu/mem ===")
    print(_sh("nproc"))
    print(_sh("free -g | head -2"))

    print("\nPROBE_COMPLETE")
    print(json.dumps({"status": "ok"}))


main()
