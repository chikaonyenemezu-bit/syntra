from app.simulators.base import SimulatedSystem


class ERPSimulator(SimulatedSystem):
    """Enterprise Resource Planning: materials, inventory and batch status."""

    normal_latency_ms = (150, 600)
    down_reason = "Interface queue to MES stopped"
    activity = [
        "Goods receipt posted: API paracetamol lot R-26-1187 (quarantine)",
        "Batch status PCM500-2611-012 changed: QA release",
        "Process order 4500127 released to MES",
        "Material reservation created for order 4500128",
    ]
