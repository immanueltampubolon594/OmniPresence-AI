"""
OmniPresence Calibration Routes (Multi-Camera VMS Independent Zones):
Menyimpan dan memuat koordinat zona secara spesifik per kamera.
"""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/v1/calibration", tags=["Calibration"])

class Point(BaseModel):
    x: int
    y: int

class Zone(BaseModel):
    name: str
    points: List[Point]

class CalibrationPayload(BaseModel):
    zones: List[Zone]
    frame_width: int
    frame_height: int


@router.post("/zones/save")
def save_calibration_zones(payload: CalibrationPayload, camera_id: str = Query("cam_alpha")):
    """
    Menyimpan zona kalibrasi secara spesifik berdasarkan kamera yang sedang dikalibrasi.
    Contoh: configs/zones_config_cam_alpha.json atau configs/zones_config_cam_beta.json
    """
    try:
        # Tentukan file config spesifik berdasarkan camera_id
        config_path = Path(f"configs/zones_config_{camera_id}.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)

        formatted_zones = {}
        for idx, zone in enumerate(payload.zones, start=1):
            pts = [[p.x, p.y] for p in zone.points]
            formatted_zones[f"Cabin {idx}"] = {
                "name": f"Cabin {idx}",
                "polygon": pts
            }

        data_to_save = {
            "frame_width": payload.frame_width,
            "frame_height": payload.frame_height,
            "zones": formatted_zones
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4)

        # Update juga worker yang sedang aktif di memory agar langsung merender zona baru tanpa restart server!
        from src.services.multi_camera_service import multi_cam_manager
        if camera_id in multi_cam_manager.cameras:
            multi_cam_manager.cameras[camera_id].zones = formatted_zones
            print(f"[CALIBRATION] Memori worker '{camera_id}' langsung diperbarui dengan zona baru.")

        print(f"[CALIBRATION] Berhasil menyimpan {len(payload.zones)} zona ke {config_path}")
        return {
            "status": "success",
            "message": f"Kalibrasi untuk {camera_id} berhasil disimpan dan diterapkan!",
            "file": str(config_path)
        }
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan kalibrasi: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan file zona: {str(e)}")