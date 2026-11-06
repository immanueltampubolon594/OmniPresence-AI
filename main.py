"""
OmniPresence-AI: High-Speed Real-Time Telemetry System with Auto-Reporting
Fitur:
  - Kecepatan Asli Mulus (Real-time FPS)
  - Ukuran Ringan CPU (imgsz=640)
  - Toleransi waktu 1.0 detik
  - Bar status rapi di pojok bawah
  - AUTO-EXPORT LAPORAN CSV saat keluar (Tekan Q)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import json
import time
import numpy as np
from ultralytics import YOLO

from src.database.exporter import TelemetryReportExporter

MODEL_PATH = "yolov8s.pt"
ZONES_CONFIG_PATH = "configs/zones_config.json"
VIDEO_PATH = "data/raw/Dataset_Uji.mp4"

# Toleransi 1.0 detik
TOLERANCE_SECONDS = 1.0


def is_person_in_zone(bbox, zone_points):
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) / 2.0
    center_y = (y1 + y2) / 2.0
    poly_np = np.array(zone_points, dtype=np.int32)
    return cv2.pointPolygonTest(poly_np, (center_x, center_y), measureDist=False) >= 0


def draw_minimalist_zone(frame, zone_points, station_name, state, duration):
    overlay = frame.copy()
    pts = np.array(zone_points, np.int32).reshape((-1, 1, 2))
    
    color = (0, 220, 0) if state == "OCCUPIED" else (0, 0, 240)

    cv2.fillPoly(overlay, [pts], color)
    cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)
    frame = cv2.addWeighted(overlay, 0.25, frame, 0.75, 0)

    min_x = int(np.min(pts[:, :, 0]))
    min_y = int(np.min(pts[:, :, 1]))
    label_y = max(22, min_y - 6)

    label_text = f"{station_name}: {state[:3]} ({duration}s)"
    (w_text, h_text), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    
    sub_overlay = frame.copy()
    cv2.rectangle(sub_overlay, (min_x, label_y - h_text - 4), (min_x + w_text + 6, label_y + 4), (10, 10, 10), -1)
    frame = cv2.addWeighted(sub_overlay, 0.6, frame, 0.4, 0)

    cv2.putText(frame, label_text, (min_x + 3, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    return frame


def draw_bottom_mini_bar(frame, stats, current_fps):
    h, w, _ = frame.shape
    total = len(stats)
    occupied = sum(1 for d in stats.values() if d["state"] == "OCCUPIED")
    rate = (occupied / total * 100) if total > 0 else 0

    bar_text = f"OMNIPRESENCE-AI | Okupansi: {rate:.0f}% ({occupied}/{total} Meja) | FPS: {current_fps:.1f} | [Q: Keluar]"
    (w_text, h_text), _ = cv2.getTextSize(bar_text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)

    overlay = frame.copy()
    cv2.rectangle(overlay, (10, h - 38), (w_text + 25, h - 10), (15, 15, 15), -1)
    frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)
    
    cv2.rectangle(frame, (10, h - 38), (w_text + 25, h - 10), (0, 255, 255), 1)
    cv2.putText(frame, bar_text, (18, h - 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1)
    return frame


def main():
    if not os.path.exists(ZONES_CONFIG_PATH) or not os.path.exists(VIDEO_PATH):
        print("[ERROR] File konfigurasi meja atau video tidak ditemukan!")
        return

    with open(ZONES_CONFIG_PATH, "r") as f:
        zones = json.load(f)

    now = time.time()
    trackers = {}
    for name in zones.keys():
        trackers[name] = {
            "state": "VACANT",
            "last_seen_time": 0.0,
            "timer": 0.0,
            "last_update": now,
            "total_occupied_time": 0.0,  # Pencatat kumulatif total terisi
            "total_vacant_time": 0.0     # Pencatat kumulatif total kosong
        }

    model = YOLO(MODEL_PATH)
    cap = cv2.VideoCapture(VIDEO_PATH)

    window_name = "OmniPresence-AI: Real-Time Speed Telemetry"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1100, 650)

    fps_counter = 0
    start_time = time.time()
    current_fps = 0.0

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

        results = model.track(frame, persist=True, tracker="bytetrack.yaml", classes=[0], conf=0.10, imgsz=640, verbose=False)

        detected_persons = []
        if len(results) > 0 and results[0].boxes is not None and len(results[0].boxes) > 0:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().numpy() if results[0].boxes.id is not None else range(len(boxes))

            for box, track_id in zip(boxes, track_ids):
                detected_persons.append({"track_id": track_id, "bbox": box})

        telemetry_stats = {}
        for station_name, zone_points in zones.items():
            t = trackers[station_name]
            person_found = False

            for person in detected_persons:
                if is_person_in_zone(person["bbox"], zone_points):
                    person_found = True
                    break

            dt = now - t["last_update"]
            t["last_update"] = now

            if person_found:
                t["last_seen_time"] = now
                if t["state"] != "OCCUPIED":
                    t["state"] = "OCCUPIED"
                    t["timer"] = 0.0
                else:
                    t["timer"] += dt
            else:
                time_since_last_seen = now - t["last_seen_time"]
                if time_since_last_seen > TOLERANCE_SECONDS:
                    if t["state"] != "VACANT":
                        t["state"] = "VACANT"
                        t["timer"] = 0.0
                    else:
                        t["timer"] += dt
                else:
                    t["timer"] += dt

            # Akumulasikan total durasi untuk laporan akhir
            if t["state"] == "OCCUPIED":
                t["total_occupied_time"] += dt
            else:
                t["total_vacant_time"] += dt

            duration_val = int(t["timer"])
            telemetry_stats[station_name] = {"state": t["state"]}

            frame = draw_minimalist_zone(frame, zone_points, station_name, t["state"], duration_val)

        for person in detected_persons:
            x1, y1, x2, y2 = map(int, person["bbox"])
            track_id = person["track_id"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(frame, f"ID:{track_id}", (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        frame = draw_bottom_mini_bar(frame, telemetry_stats, current_fps)

        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # Ekspor Laporan Otomatis saat Program Selesai
    print("\n[INFO] Mengompilasi data sesi telemetri...")
    report_data = {}
    for name, t in trackers.items():
        report_data[name] = {
            "total_occupied": t["total_occupied_time"],
            "total_vacant": t["total_vacant_time"],
            "last_state": t["state"]
        }
    
    saved_path = TelemetryReportExporter.export_session_summary(report_data)
    print(f"[SUKSES] Laporan audit berhasil diekspor ke: {saved_path}")
    print("[INFO] Sistem selesai dimatikan dengan aman.")


if __name__ == "__main__":
    main()