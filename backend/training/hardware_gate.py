"""Dry-run memory/throughput check before a long GRPO run."""

from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path

import yaml

from backend.app.config import get_settings


def run_gate(config_path: Path) -> dict:
    cfg = yaml.safe_load(config_path.read_text()) if config_path.is_file() else {}
    settings = get_settings()
    model_id = cfg.get("model_id", settings.model_id)
    revision = cfg.get("model_revision", settings.model_revision)
    device = cfg.get("model_device", settings.model_device)

    report: dict = {
        "ok": False,
        "model_id": model_id,
        "device": device,
        "error": None,
        "peak_memory_bytes": None,
        "step_seconds": None,
    }

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        report["error"] = f"Missing ML deps: {exc}. Install requirements-ml.txt"
        return report

    try:
        t0 = time.perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            torch_dtype=torch.float32 if device == "cpu" else torch.float16,
        )
        if device == "cpu":
            model = model.to("cpu")
        else:
            model = model.to(device)

        prompt = 'Reply with JSON only: {"guess":"crane"}'
        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        with torch.no_grad():
            _ = model.generate(**inputs, max_new_tokens=8)

        report["step_seconds"] = time.perf_counter() - t0
        if device.startswith("cuda") and torch.cuda.is_available():
            report["peak_memory_bytes"] = int(torch.cuda.max_memory_allocated())
        report["ok"] = True
        report["cuda_available"] = torch.cuda.is_available()
    except Exception as exc:  # noqa: BLE001
        report["error"] = f"{exc}\n{traceback.format_exc()}"

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("backend/configs/default.yaml"))
    args = parser.parse_args()

    settings = get_settings()
    report = run_gate(args.config)
    out = Path(settings.artifacts_dir) / "hardware_gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
