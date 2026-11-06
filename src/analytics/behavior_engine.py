"""
OmniPresence Enterprise: Temporal Workplace Behavior & State Engine
Implements a Finite State Machine (FSM) with temporal sliding windows
to classify employee workplace states beyond binary occupied/vacant.
"""

import time
import numpy as np
from typing import Dict, Any, List


class WorkplaceBehaviorEngine:
    def __init__(self, idle_threshold_sec: float = 20.0, stepout_threshold_sec: float = 30.0):
        self.idle_threshold_sec = idle_threshold_sec
        self.stepout_threshold_sec = stepout_threshold_sec
        
        # State memory per workstation: {zone_id: {history, last_active_ts, ...}}
        self.station_memory = {}

    def update_station(self, zone_id: str, matched_person: Any, current_ts: float) -> Dict[str, Any]:
        """
        Updates and returns the temporal behavioral state of a workstation.
        Possible States:
        - 'ACTIVE_WORKING'     : Person present and actively moving/typing
        - 'IDLE_DWELL'         : Person present but stationary (fatigue or resting)
        - 'STEPPED_OUT'        : Person recently left (temporary coffee/toilet break)
        - 'VACANT'             : Empty workstation
        """
        if zone_id not in self.station_memory:
            self.station_memory[zone_id] = {
                "state": "VACANT",
                "last_seen_ts": 0.0,
                "last_motion_ts": current_ts,
                "prev_centroid": None,
                "active_duration_sec": 0,
                "idle_duration_sec": 0
            }

        mem = self.station_memory[zone_id]

        if matched_person is not None:
            # Person is detected at the workstation
            cx, cy = matched_person["centroid"]
            mem["last_seen_ts"] = current_ts

            # Measure micro-motion (typing, hand movements, head tilt)
            if mem["prev_centroid"] is not None:
                motion_delta = np.linalg.norm(np.array([cx, cy]) - np.array(mem["prev_centroid"]))
                if motion_delta > 2.5:  # Noticeable micro-movement threshold
                    mem["last_motion_ts"] = current_ts

            mem["prev_centroid"] = (cx, cy)

            # Check if person is Active or Idle
            time_stationary = current_ts - mem["last_motion_ts"]
            if time_stationary > self.idle_threshold_sec:
                mem["state"] = "IDLE_DWELL"
                mem["idle_duration_sec"] += 1
            else:
                mem["state"] = "ACTIVE_WORKING"
                mem["active_duration_sec"] += 1

        else:
            # No person currently at the workstation
            mem["prev_centroid"] = None
            time_since_seen = current_ts - mem["last_seen_ts"]

            if time_since_seen < self.stepout_threshold_sec and mem["state"] in ["ACTIVE_WORKING", "IDLE_DWELL", "STEPPED_OUT"]:
                mem["state"] = "STEPPED_OUT"
            else:
                mem["state"] = "VACANT"
                mem["active_duration_sec"] = 0
                mem["idle_duration_sec"] = 0

        # State color badge (Hex)
        color_map = {
            "ACTIVE_WORKING": "#10B981",    # Emerald Green
            "IDLE_DWELL": "#F59E0B",        # Amber Warning
            "STEPPED_OUT": "#3B82F6",       # Blue (Temporary)
            "VACANT": "#EF4444"             # Rose Red
        }

        return {
            "behavior_state": mem["state"],
            "active_duration_sec": mem["active_duration_sec"],
            "idle_duration_sec": mem["idle_duration_sec"],
            "badge_color": color_map.get(mem["state"], "#6B7280")
        }