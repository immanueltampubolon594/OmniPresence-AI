export interface WorkstationStatus {
  station_id: string;
  state: "OCCUPIED" | "VACANT";
  duration_seconds: number;
  occupant_id: number | null;
}

export interface TelemetryData {
  total_stations: number;
  occupied_count: number;
  vacant_count: number;
  occupancy_rate_percent: number;
  system_fps: number;
  workstations: Record<string, WorkstationStatus>;
}