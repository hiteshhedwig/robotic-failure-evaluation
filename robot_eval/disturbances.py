"""One reusable world-frame root-body force pulse for any compliant adapter."""
import numpy as np

class ForcePulse:
    def __init__(self,config,timing):
        self.config=config
        self.timing=timing
        self.force=np.array(config["force_n"] if config is not None else [0,0,0],dtype=float)
        self.impulse=np.zeros(3)

    @property
    def end_s(self):
        return None if self.timing.finish is None else self.timing.finish*self.timing.dt

    def apply(self,sim,index):
        active=self.config is not None and self.timing.begin<=index<self.timing.finish
        force=self.force if active else np.zeros(3)
        sim.apply_force_world(force)
        if active:
            self.impulse+=force*self.timing.dt
        return active,force

    def clear(self,sim):
        sim.apply_force_world(np.zeros(3))
