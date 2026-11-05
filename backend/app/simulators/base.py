import random

from app.services.health_monitor import Heartbeat


class SimulatedSystem:
    """Fakes the heartbeat of a real system so monitoring has something to watch.

    Fault modes (set per system from the API, demo only):
      None       normal operation
      "degraded" slow and error-prone, still reports up
      "down"     reports itself as down
      "silent"   sends nothing at all (tests the heartbeat timeout)
    """

    normal_latency_ms: tuple[int, int] = (80, 300)
    activity: list[str] = ["OK"]
    down_reason: str = "Service unavailable"

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()

    def heartbeat(self, fault: str | None) -> Heartbeat | None:
        r = self.rng
        if fault == "silent":
            return None
        if fault == "down":
            return Heartbeat("down", latency_ms=0, error_rate=1.0, message=self.down_reason)
        if fault == "degraded":
            return Heartbeat("up", latency_ms=r.randint(1800, 4500),
                             error_rate=round(r.uniform(0.08, 0.25), 3),
                             message=f"Slow response: {r.choice(self.activity)}")
        return Heartbeat("up", latency_ms=r.randint(*self.normal_latency_ms),
                         error_rate=round(r.uniform(0.0, 0.01), 3),
                         message=r.choice(self.activity))
