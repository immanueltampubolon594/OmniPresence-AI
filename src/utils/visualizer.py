"""
OmniPresence-AI: Final Production System (All-in-One HUD di Sisi Kanan)
Kontrol:
  - Tekan 'h' : Sembunyikan / Munculkan Dashboard
  - Tekan 'q' : Keluar
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import json
import time
import numpy as np
from ultralytics import YOLO

from src.core.geometry_engine import SpatialGeometryEngine, Point2D
from src.core.state_machine import WorkstationSessionTracker

# Konfigurasi Path
MODEL_PATH = "yolov8s.pt"
ZONES_CONFIG_PATH = "configs/zones_config.json"
VIDEO_PATH = "data/raw/cctv_kantor_baru.mp4"


def draw_zone_overlay(frame, zone_points, state, alpha=0.3):
    overlay = frame.copy()
    pts = np.array(zone_points, np.int32).reshape((-1, 1, 2))
    color = (0, 220, 0) if state == "OCCUPIED" else (0, 0, 240)
    cv2.fillPoly(overlay, [pts], color)
    cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)
    return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)


def draw_hud_right(frame, stats, alpha=0.55):
    """
    Menggambar Telemetry Dashboard di POJOK KANAN (Tidak menutupi meja sama sekali!)
    """
    h, w, _ = frame.shape
    panel_w = 265
    panel_h = 35 + (len(stats) * 25)

    # Posisi di SISI KANAN layar
    panel_x = w - panel_w - 20
    panel_y = 55

    # Efek Kaca Transparan Gelap
    overlay = frame.copy()
    cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (15, 15, 15), -1)
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # Bingkai Cyan
    cv2.rectangle(frame, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (0, 255, 255), 1)

    cv2.putText(frame, "TELEMETRY [H: Hide]", (panel_x + 12, panel_y + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1)

    y_offset = panel_y + 48
    for station_id, data in stats.items():
        state = data["state"]
        duration = int(data["time_in_state"])
        color = (0, 255, 100) if state == "OCCUPIED" else (50, 100, 255)

        text = f"{station_id}: {state} ({duration}s)"
        cv2.putText(frame, text, (panel_x + 12, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, color, 1)
        y_offset += 23

    return frame


def main():
    if not os.path.exists(ZONES_CONFIG_PATH) or not os.path.exists(VIDEO_PATH):
        print("[FATAL ERROR] File konfigurasi meja atau video tidak ditemukan!")
        return

    with open(ZONES_CONFIG_PATH, "r") as f:
        zones = json.load(f)

    station_trackers = {
        name: WorkstationSessionTracker(
            station_id=name, 
            debounce_seconds=1.5,
            max_vacant_alert_seconds=15.0
        )
        for name in zones.keys()
    }

    model = YOLO(MODEL_PATH)
    cap = cv2.VideoCapture(VIDEO_PATH)

    window_name = "OmniPresence-AI: Live Workplace Telemetry (Tekan 'h' Hide HUD, 'q' Keluar)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1100, 650)

    fps_counter = 0
    start_time = time.time()
    current_fps = 0.0
    show_hud = True

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        now = time.time()
        fps_counter += 1
        if (now - start_time) > 1.0:
            current_fps = fps_counter / (now - start_time)
            fps_counter = 0
            start_time = now

        results = model.track(frame, persist=True, tracker="bytetrack.yaml", classes=[0], conf=0.15, verbose=False)

        detected_persons = []
        if len(results) > 0 and results[0].boxes is not None and len(results[0].boxes) > 0:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().numpy() if results[0].boxes.id is not None else range(len(boxes))

            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = box
                center_anchor = Point2D(x=(x1 + x2) / 2.0, y=(y1 + y2) / 2.0)
                detected_persons.append({"track_id": track_id, "bbox": box, "anchor": center_anchor})

        telemetry_stats = {}
        for station_name, zone_points in zones.items():
            occupant_id = None

            for person in detected_persons:
                if SpatialGeometryEngine.is_point_inside_polygon(person["anchor"], zone_points):
                    occupant_id = person["track_id"]
                    break

            stats = station_trackers[station_name].update(occupant_id, current_time=now)
            telemetry_stats[station_name] = stats
            frame = draw_zone_overlay(frame, zone_points, state=stats["state"])

        for person in detected_persons:
            x1, y1, x2, y2 = map(int, person["bbox"])
            track_id = person["track_id"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(frame, f"Person #{track_id}", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        # Gambar Dashboard di Sisi KANAN
        if show_hud:
            frame = draw_hud_right(frame, telemetry_stats)

        cv2.putText(frame, f"FPS: {current_fps:.1f}", (frame.shape[1] - 130, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow(window_name, frame)
        key = cv2.waitKey(25) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('h'):
            show_hud = not show_hud

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()