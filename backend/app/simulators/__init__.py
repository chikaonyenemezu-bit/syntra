from app.simulators.base import SimulatedSystem
from app.simulators.erp import ERPSimulator
from app.simulators.lims import LIMSSimulator
from app.simulators.mes import MESSimulator

SIMULATORS: dict[str, SimulatedSystem] = {
    "MES": MESSimulator(),
    "LIMS": LIMSSimulator(),
    "ERP": ERPSimulator(),
}

FAULT_MODES = ("degraded", "down", "silent")

__all__ = ["SIMULATORS", "FAULT_MODES", "SimulatedSystem"]
