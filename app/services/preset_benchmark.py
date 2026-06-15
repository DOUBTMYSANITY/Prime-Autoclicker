"""Runtime telemetry for the Preset Benchmark plugin."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

_BENCH_FILE = Path.home() / ".mtautoclicker_benchmark.json"


@dataclass
class BenchmarkSession:
    enabled: bool = False
    started_at: float = 0.0
    warmup_seconds: float = 5.0
    click_count: int = 0
    accuracy_samples: list[float] = field(default_factory=list)
    actual_cps_samples: list[float] = field(default_factory=list)
    lag_events: int = 0
    preset_label: str = ""

    def start(self, *, preset_label: str = "", warmup_seconds: float = 5.0) -> None:
        self.enabled = True
        self.started_at = time.monotonic()
        self.warmup_seconds = max(0.0, float(warmup_seconds))
        self.click_count = 0
        self.accuracy_samples.clear()
        self.actual_cps_samples.clear()
        self.lag_events = 0
        self.preset_label = preset_label

    def stop(self) -> dict:
        self.enabled = False
        report = self.build_report()
        self._persist(report)
        return report

    def record_click(self) -> None:
        if self.enabled:
            self.click_count += 1

    def record_cps_sample(self, accuracy: float, actual_cps: float) -> None:
        if not self.enabled:
            return
        if time.monotonic() - self.started_at < self.warmup_seconds:
            return
        self.accuracy_samples.append(float(accuracy))
        self.actual_cps_samples.append(float(actual_cps))
        if accuracy < 65.0:
            self.lag_events += 1

    def build_report(self) -> dict:
        acc = self.accuracy_samples
        cps = self.actual_cps_samples
        avg_acc = sum(acc) / len(acc) if acc else 0.0
        avg_cps = sum(cps) / len(cps) if cps else 0.0
        stability = max(0.0, min(100.0, avg_acc))
        consistency = 100.0
        if len(cps) > 1:
            mean = avg_cps
            variance = sum((x - mean) ** 2 for x in cps) / len(cps)
            consistency = max(0.0, min(100.0, 100.0 - (variance ** 0.5) * 8.0))
        drift = max(0.0, min(100.0, 100.0 - self.lag_events * 4.0))
        score = stability * 0.5 + consistency * 0.3 + drift * 0.2
        return {
            "preset": self.preset_label,
            "clicks": self.click_count,
            "avg_accuracy": round(avg_acc, 2),
            "avg_cps": round(avg_cps, 2),
            "lag_events": self.lag_events,
            "stability_score": round(stability, 1),
            "consistency_score": round(consistency, 1),
            "smoothness_score": round(score, 1),
            "samples": len(acc),
        }

    def _persist(self, report: dict) -> None:
        try:
            history: list = []
            if _BENCH_FILE.is_file():
                history = json.loads(_BENCH_FILE.read_text(encoding="utf-8"))
                if not isinstance(history, list):
                    history = []
            history.append({**report, "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            history = history[-50:]
            _BENCH_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")
        except Exception:
            pass


benchmark_session = BenchmarkSession()
