"""
OmniPresence-Platform: FastAPI Enterprise Gateway
Server ini menyajikan REST API, Web Stream, Ingestion Video, dan Analytics Export untuk Next.js Frontend.
Dilengkapi dengan Enterprise Multi-Camera VMS Parallel Processing & Persistent State Management.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from src.services.telemetry_service import engine_instance
from src.services.multi_camera_service import multi_cam_manager  # <-- Manager Multi-Kamera
from src.api.routes.telemetry_routes import router as telemetry_router
from src.api.routes.stream_routes import router as stream_router
from src.api.routes.video_routes import router as video_router
from src.api.routes.calibration_routes import router as calibration_router
from src.api.routes.notification_routes import router as notification_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[SERVER] Menyalakan Engine Vision AI Utama di background...")
    engine_instance.start()
    
    # --- ENTERPRISE MULTI-CAMERA VMS PERSISTENT STATE ---
    print("[VMS] Memuat state kamera dari penyimpanan permanen...")
    state_path = Path("configs/vms_state.json")
    saved_state = {}
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                saved_state = json.load(f)
        except Exception:
            pass

    # Cari fallback video di folder data/raw/ jika state belum ada
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    video_files = list(raw_dir.glob("*.mp4"))

    default_video = "data/raw/Dataset_Uji.mp4"
    if video_files:
        default_video = str(video_files[0])

    # Ambil dari state permanen atau gunakan default
    video_alpha = saved_state.get("cam_alpha", default_video)
    video_beta = saved_state.get("cam_beta", video_alpha)

    # Daftarkan kamera dengan sumber video permanen
    multi_cam_manager.add_camera("cam_alpha", video_alpha)
    multi_cam_manager.add_camera("cam_beta", video_beta)
    
    print(f"[VMS] Cam Alpha dimuat dengan: {Path(video_alpha).name}")
    print(f"[VMS] Cam Beta dimuat dengan: {Path(video_beta).name}")
    # --------------------------------------------------

    yield
    
    print("[SERVER] Mematikan Engine Vision AI...")
    engine_instance.stop()
    for cam_id in list(multi_cam_manager.cameras.keys()):
        multi_cam_manager.remove_camera(cam_id)
    print("[VMS] Seluruh multi-camera worker dimatikan.")


app = FastAPI(
    title="OmniPresence-Platform API Gateway",
    description="Enterprise Vision AI & Spatial Telemetry Backend for Next.js (Multi-Camera VMS Enabled)",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Daftarkan semua router
app.include_router(telemetry_router)
app.include_router(stream_router)
app.include_router(video_router)
app.include_router(calibration_router)
app.include_router(calibration_router)
app.include_router(notification_router)


@app.get("/api/v1/analytics/latest-report/download", tags=["Analytics & Audit"])
def download_latest_audit_report():
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_files = list(reports_dir.glob("*.csv"))

    if not csv_files:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"occupancy_audit_report_{timestamp_str}.csv"

        stats = engine_instance.get_current_stats()
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("Workstation,Status,Behavior_State,Duration_Seconds,Ergonomic_Score,Posture_State\n")
            for station_id, data in stats.get("workstations", {}).items():
                ergo = data.get("ergonomics", {})
                f.write(
                    f"{station_id},{data.get('status')},{data.get('behavior_state')},"
                    f"{data.get('duration_seconds')},{ergo.get('ergonomic_score')},{ergo.get('posture_state')}\n"
                )
    else:
        report_file = max(csv_files, key=os.path.getctime)

    if not report_file.exists():
        raise HTTPException(status_code=404, detail="File laporan audit tidak ditemukan.")

    return FileResponse(
        path=str(report_file),
        media_type="text/csv",
        filename=report_file.name
    )


@app.get("/", tags=["Health Check"])
def root():
    return {
        "service": "OmniPresence-Platform Gateway",
        "status": "RUNNING",
        "version": "2.0.0 Enterprise Multi-Camera VMS",
        "docs_url": "/docs",
        "live_stream_single": "/api/v1/stream/video_feed",
        "live_stream_multicam": "/api/v1/stream/video_feed/{camera_id}",
        "telemetry_live": "/api/v1/telemetry/live",
        "video_upload": "/api/v1/video/upload",
        "calibration": "/api/v1/calibration/zones"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)