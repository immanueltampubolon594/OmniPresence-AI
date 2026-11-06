from enum import Enum
import time
from typing import Optional, Dict, Any

class WorkstationState(Enum):
    VACANT = "VACANT"
    OCCUPIED = "OCCUPIED"
    UNATTENDED_ALERT = "UNATTENDED_ALERT"

class WorkstationSessionTracker:
    def __init__(self, station_id: str, debounce_seconds: float = 2.0, max_vacant_alert_seconds: float = 10.0):
        self.station_id = station_id
        self.debounce_seconds = debounce_seconds
        self.max_vacant_alert_seconds = max_vacant_alert_seconds

        self.current_state = WorkstationState.VACANT
        self.current_occupant_id: Optional[int] = None

        self.last_seen_timestamp: float = 0.0
        self.state_enter_timestamp: float = time.time()
        self.total_occupied_duration: float = 0.0

    def update(self, detected_occupant_id: Optional[int], current_time: Optional[float] = None) -> Dict[str, Any]:
        now = current_time or time.time()

        if detected_occupant_id is not None:
            self.last_seen_timestamp = now
            if self.current_state != WorkstationState.OCCUPIED:
                self.current_state = WorkstationState.OCCUPIED
                self.current_occupant_id = detected_occupant_id
                self.state_enter_timestamp = now
            else:
                self.total_occupied_duration += (now - self.last_seen_timestamp)
        else:
            time_since_last_seen = now - self.last_seen_timestamp
            if self.current_state == WorkstationState.OCCUPIED:
                if time_since_last_seen > self.debounce_seconds:
                    self.current_state = WorkstationState.VACANT
                    self.current_occupant_id = None
                    self.state_enter_timestamp = now
            elif self.current_state == WorkstationState.VACANT:
                vacant_duration = now - self.state_enter_timestamp
                if vacant_duration > self.max_vacant_alert_seconds:
                    self.current_state = WorkstationState.UNATTENDED_ALERT

        return {
            "station_id": self.station_id,
            "state": self.current_state.value,
            "occupant_id": self.current_occupant_id,
            "time_in_state": now - self.state_enter_timestamp,
            "total_occupied_sec": self.total_occupied_duration
        }