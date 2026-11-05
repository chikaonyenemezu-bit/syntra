from app.simulators.base import SimulatedSystem


class LIMSSimulator(SimulatedSystem):
    """Laboratory Information Management System: QC samples and results."""

    normal_latency_ms = (120, 450)
    down_reason = "Database connection pool exhausted"
    activity = [
        "Sample S-26-04418 registered (assay, dissolution)",
        "Result approved: S-26-04402 dissolution 92% (spec >= 80%)",
        "Instrument HPLC-07 results imported",
        "Stability pull T6M scheduled for lot IBU400-2605-002",
    ]
