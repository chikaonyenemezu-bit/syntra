from app.simulators.base import SimulatedSystem


class MESSimulator(SimulatedSystem):
    """Manufacturing Execution System: electronic batch records on the shop floor."""

    normal_latency_ms = (90, 350)
    down_reason = "EBR service not reachable from Tablet Line 2 terminals"
    activity = [
        "Batch PCM500-2611-014: compression step started",
        "Batch PCM500-2611-014: IPC tablet weight recorded",
        "Batch PCM500-2611-013: packaging line clearance signed",
        "Batch IBU400-2611-007: granulation endpoint recorded",
        "Equipment TP-02 status: in use",
    ]
