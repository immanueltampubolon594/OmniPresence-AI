"""
OmniPresence Video Ingestion API (Multi-Camera VMS Ready with Persistence):
1. Menyimpan video baru secara instan.
2. Mendukung upload spesifik per ruangan (/upload/cam_alpha atau /upload/cam_beta).
3. Menyimpan status video secara permanen ke vms_state.json agar tidak hilang saat restart.
4. Menjaga kalibrasi zona manual agar tetap aman dan tidak hilang.
"""

import json
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from src.services.multi_camera_service import multi_cam_manager

router = APIRouter(prefix="/api/v1/video", tags=["Video Ingestion"])

UPLOAD_DIR = Path("data/raw")
STATE_PATH = Path("configs/vms_state.json")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def save_vms_state(camera_id: str, video_path: str):
    """Menyimpan state video aktif secara permanen ke file JSON"""
    state_data = {}
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                state_data = json.load(f)
        except Exception:
            pass

    state_data[camera_id] = video_path
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=4)


@router.post("/upload")
async def upload_cctv_video(file: UploadFile = File(...)):
    """
    Endpoint Upload Universal (Fallback lama):
    Mengunggah video dan memperbarui seluruh kamera aktif di grid, lalu menyimpannya secara permanen.
    """
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm")):
        raise HTTPException(status_code=400, detail="Format tidak didukung.")

    target_path = UPLOAD_DIR / file.filename
    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan video: {str(e)}")

    try:
        active_cams = list(multi_cam_manager.cameras.keys())
        if not active_cams:
            multi_cam_manager.add_camera("cam_alpha", str(target_path))
            multi_cam_manager.add_camera("cam_beta", str(target_path))
            save_vms_state("cam_alpha", str(target_path))
            save_vms_state("cam_beta", str(target_path))
        else:
            for cam_id in active_cams:
                multi_cam_manager.remove_camera(cam_id)
                multi_cam_manager.add_camera(cam_id, str(target_path))
                save_vms_state(cam_id, str(target_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memperbarui engine: {str(e)}")

    return {
        "status": "success",
        "message": f"Video '{file.filename}' berhasil diunggah dan disimpan permanen ke semua kamera!",
        "filename": file.filename,
        "video_path": str(target_path)
    }


@router.post("/upload/{camera_id}")
async def upload_specific_video(camera_id: str, file: UploadFile = File(...)):
    """
    Endpoint Spesifik VMS Enterprise (Dengan Persistent State):
    Mengunggah video HANYA untuk ruangan tertentu (misal: cam_alpha atau cam_beta)
    dan menyimpannya secara permanen agar tidak hilang saat server restart.
    """
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm")):
        raise HTTPException(status_code=400, detail="Format file harus berupa video.")

    target_path = UPLOAD_DIR / file.filename

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[UPLOAD] Video khusus {camera_id} berhasil disimpan: {target_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan video: {str(e)}")

    # 1. Ganti video pada camera_id yang dipilih di memory manager
    try:
        multi_cam_manager.remove_camera(camera_id)
        multi_cam_manager.add_camera(camera_id, str(target_path))
        
        # 2. Simpan secara permanen ke vms_state.json
        save_vms_state(camera_id, str(target_path))
        
        print(f"[VMS] Kamera '{camera_id}' berhasil beralih ke video baru secara permanen.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memperbarui kamera {camera_id}: {str(e)}")

    return {
        "status": "success",
        "message": f"Video untuk {camera_id} berhasil diperbarui dan disimpan permanen!",
        "filename": file.filename,
        "camera_id": camera_id,
        "video_path": str(target_path)
    }