from fastapi import APIRouter
from src.services.telemetry_service import engine_instance
from src.services.multi_camera_service import multi_cam_manager
from src.api.schemas.telemetry_schema import TelemetrySummaryDTO

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])


@router.get("/live", response_model=TelemetrySummaryDTO)
def get_live_telemetry():
    """Mengambil status real-time semua meja kerja (Global / Default)"""
    return engine_instance.get_current_stats()


@router.get("/live/{camera_id}")
def get_camera_live_telemetry(camera_id: str):
    """Mengambil status real-time secara spesifik per kamera dari MultiCameraManager"""
    if camera_id in multi_cam_manager.cameras:
        worker = multi_cam_manager.cameras[camera_id]
        workstations = worker.workstation_states
        
        # Hitung statistik okupansi khusus untuk kamera ini
        total = len(workstations)
        occupied = sum(1 for w in workstations.values() if w["status"] == "OCCUPIED")
        vacant = total - occupied
        occupancy_rate = round((occupied / max(1, total)) * 100, 1)
        
        return {
            "camera_id": camera_id,
            "total_stations": total,
            "occupied_count": occupied,
            "vacant_count": vacant,
            "occupancy_rate_percent": occupancy_rate,
            "system_fps": worker.system_fps,
            "workstations": workstations
        }
    
    # Fallback ke engine utama jika kamera tidak ditemukan
    return engine_instance.get_current_stats()