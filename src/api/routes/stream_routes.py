"""
OmniPresence Stream Routes:
Menyajikan Live Video Feed, Multi-Camera VMS Stream, dan Clean Snapshot untuk Kalibrasi.
"""

import cv2
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
from src.services.telemetry_service import engine_instance
from src.services.multi_camera_service import multi_cam_manager

router = APIRouter(prefix="/api/v1/stream", tags=["Streaming"])


def generate_frames():
    while True:
        frame = engine_instance.get_current_frame()
        if frame is None:
            time.sleep(0.05)
            continue

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.03)


@router.get("/video_feed")
def video_feed():
    """Streaming video CCTV utama yang dianotasi langsung ke komponen web Next.js"""
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


# ==========================================
# MULTI-CAMERA VMS STREAMING (CAM ALPHA & BETA)
# ==========================================

def generate_multi_frames(camera_id: str):
    """Generator frame khusus untuk kamera tertentu di VMS Grid"""
    while True:
        frame_bytes = multi_cam_manager.get_frame_bytes(camera_id)
        if frame_bytes is None:
            time.sleep(0.05)
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.03)


@router.get("/video_feed/{camera_id}")
def multi_camera_video_feed(camera_id: str):
    """Streaming video CCTV spesifik berdasarkan ID kamera untuk VMS Grid"""
    if camera_id not in multi_cam_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Kamera dengan ID '{camera_id}' tidak ditemukan.")
    
    return StreamingResponse(generate_multi_frames(camera_id), media_type="multipart/x-mixed-replace; boundary=frame")


@router.get("/snapshot")
def get_snapshot():
    """Frame dengan anotasi zona — untuk preview biasa."""
    frame = engine_instance.get_current_frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="Frame tidak tersedia.")

    ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ret:
        raise HTTPException(status_code=500, detail="Gagal encode frame.")

    return Response(content=buffer.tobytes(), media_type="image/jpeg")


@router.get("/snapshot/clean")
def get_clean_snapshot(camera_id: str = "cam_alpha"):
    """
    Frame BERSIH tanpa anotasi zona sama sekali — khusus untuk UI kalibrasi.
    Mendukung pengambilan snapshot dinamis berdasarkan camera_id (cam_alpha / cam_beta).
    """
    # Ambil path video dari multi_cam_manager berdasarkan camera_id yang dikirim
    video_path = "data/raw/Dataset_Uji.mp4" # Default fallback
    if camera_id in multi_cam_manager.cameras:
        video_path = multi_cam_manager.cameras[camera_id].video_path

    cap = cv2.VideoCapture(str(video_path))
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_POS_FRAMES, 60)
        ret, frame = cap.read()
        cap.release()
    else:
        ret, frame = False, None

    if not ret or frame is None:
        raise HTTPException(status_code=503, detail=f"Frame bersih tidak tersedia untuk {camera_id}.")

    ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ret:
        raise HTTPException(status_code=500, detail="Gagal encode frame.")

    return Response(content=buffer.tobytes(), media_type="image/jpeg")