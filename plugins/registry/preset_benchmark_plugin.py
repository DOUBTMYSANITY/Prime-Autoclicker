def register(context: dict) -> dict:
    return {
        "id": "preset_benchmark_plugin",
        "name": "Preset",
        "version": "1.1.0",
        "description": "Reports runtime telemetry: CPU load impact, lag, missed inputs, and smoothness score.",
    }
