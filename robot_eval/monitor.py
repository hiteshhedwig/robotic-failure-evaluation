"""Outcome detection from simulator ground truth, independently of policy output."""
import math

class WalkingMonitor:
    def __init__(self, command_x=0.5, hold_s=0.4, robot="g1"):
        if robot not in ("g1","go1"): raise ValueError("Unsupported robot")
        self.root_body="pelvis" if robot=="g1" else "trunk"
        self.low_height=0.45 if robot=="g1" else 0.12
        self.recovery_height=0.65 if robot=="g1" else 0.22
        self.command_x=command_x
        self.hold_s=hold_s
        self.contact_since=None
        self.posture_since=None
        self.fall_time=None
        self.posture_time=None
        self.recovery_since=None
        self.recovery_time=None

    def update(self,state,push_end=None):
        t=state["time_s"]
        if self.root_body in state["floor_contact_bodies"]:
            if self.contact_since is None:
                self.contact_since=t
            if self.fall_time is None and t-self.contact_since>=0.02-1e-9:
                self.fall_time=t
        else:
            self.contact_since=None
        bad=state["tilt_deg"]>60 or state["position"][2]<self.low_height
        if bad:
            if self.posture_since is None:
                self.posture_since=t
            if self.posture_time is None and t-self.posture_since>=0.1-1e-9:
                self.posture_time=t
        else:
            self.posture_since=None
        if push_end is not None and t>=push_end and self.fall_time is None:
            recovered=(state["tilt_deg"]<=10 and state["position"][2]>=self.recovery_height
                       and abs(state["velocity"][0]-self.command_x)<=0.25
                       and abs(state["velocity"][1])<=0.25
                       and self.root_body not in state["floor_contact_bodies"])
            if recovered:
                if self.recovery_since is None:
                    self.recovery_since=t
                if self.recovery_time is None and t-self.recovery_since>=self.hold_s-1e-9:
                    self.recovery_time=t
            else:
                self.recovery_since=None
