"""Robot-independent outcome monitoring using validated profile thresholds."""
from .profiles import resolve_profile

class WalkingMonitor:
    def __init__(self, command_x=0.5, hold_s=None, robot="g1", limits=None):
        self.limits = dict(limits) if limits is not None else resolve_profile(robot).monitor
        c = self.limits
        self.fall_bodies = set(c["fall_contact_bodies"])
        self.root_body = c["fall_contact_bodies"][0]  # Compatibility for old callers.
        self.low_height = c["posture_min_height_m"]
        self.recovery_height = c["recovery_min_height_m"]
        self.command_x = command_x
        self.hold_s = c["recovery_hold_s"] if hold_s is None else hold_s
        self.contact_since = self.posture_since = None
        self.fall_time = self.posture_time = None
        self.recovery_since = self.recovery_time = None

    def update(self, state, push_end=None):
        c, t = self.limits, state["time_s"]
        body_contact = bool(self.fall_bodies.intersection(state["floor_contact_bodies"]))
        if body_contact:
            if self.contact_since is None:
                self.contact_since = t
            if self.fall_time is None and t - self.contact_since >= c["fall_hold_s"] - 1e-9:
                self.fall_time = t
        else:
            self.contact_since = None
        bad = state["tilt_deg"] > c["posture_tilt_deg"] or state["position"][2] < self.low_height
        if bad:
            if self.posture_since is None:
                self.posture_since = t
            if self.posture_time is None and t - self.posture_since >= c["posture_hold_s"] - 1e-9:
                self.posture_time = t
        else:
            self.posture_since = None
        if push_end is not None and t >= push_end and self.fall_time is None:
            tolerance = c["recovery_velocity_tolerance_m_s"]
            recovered = (state["tilt_deg"] <= c["recovery_tilt_deg"]
                         and state["position"][2] >= self.recovery_height
                         and abs(state["velocity"][0] - self.command_x) <= tolerance
                         and abs(state["velocity"][1]) <= tolerance and not body_contact)
            if recovered:
                if self.recovery_since is None:
                    self.recovery_since = t
                if self.recovery_time is None and t - self.recovery_since >= self.hold_s - 1e-9:
                    self.recovery_time = t
            else:
                self.recovery_since = None
