"""Reports and export package."""

__all__ = ["DailyRunArtifacts", "DailyRunResult", "run_daily_workflow"]


def __getattr__(name: str):
    if name in __all__:
        from .daily_run import DailyRunArtifacts, DailyRunResult, run_daily_workflow

        exports = {
            "DailyRunArtifacts": DailyRunArtifacts,
            "DailyRunResult": DailyRunResult,
            "run_daily_workflow": run_daily_workflow,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
