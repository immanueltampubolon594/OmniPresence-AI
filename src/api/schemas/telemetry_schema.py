"""
OmniPresence-Platform: Telemetry Data Transfer Objects (DTO)
Validation standard: Pydantic v2
"""

from pydantic import BaseModel
from typing import Dict, List, Optional


class WorkstationStatusDTO(BaseModel):
    station_id: str
    state: str  # OCCUPIED atau VACANT
    duration_seconds: int
    occupant_id: Optional[int] = None


class TelemetrySummaryDTO(BaseModel):
    total_stations: int
    occupied_count: int
    vacant_count: int
    occupancy_rate_percent: float
    system_fps: float
    workstations: Dict[str, WorkstationStatusDTO]