"""
OmniPresence Enterprise: Autonomous Spatial Zone Scanner
Automatically detects seated occupants and clusters workstation polygons dynamically.
Zero manual annotation required.
"""

import cv2
import json
import numpy as np
from pathlib import Path
from ultralytics import YOLO


def auto_calibrate_workstations(video_path: str = "data/raw/Dataset_Uji.mp4", output_config: str = "configs/zones_config.json"):
    print(f"\n[AI SCANNER] Memindai video untuk mendeteksi tata letak meja otomatis: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Gagal membuka video: {video_path}")
        return

    # Gunakan model YOLO untuk memindai posisi orang duduk
    model = YOLO("weights/yolov8n-pose.pt")
    detected_boxes = []

    # Pindai 40 frame pertama
    for _ in range(40):
        ret, frame = cap.read()
        if not ret:
            break
        results = model.predict(frame, conf=0.15, classes=[0], verbose=False)
        if results and results[0].boxes is not None:
            for box in results[0].boxes.xyxy.cpu().numpy():
                detected_boxes.append(box)

    cap.release()

    if not detected_boxes:
        print("[!] Tidak ada stasiun kerja yang terdeteksi.")
        return

    # Lakukan Spatial Clustering untuk menggabungkan deteksi menjadi meja-meja tetap
    boxes = np.array(detected_boxes)
    centroids = (boxes[:, :2] + boxes[:, 2:]) / 2.0

    # Cluster menggunakan Non-Maximum Suppression spasial sederhana
    unique_stations = []
    used = np.zeros(len(boxes), dtype=bool)

    for i in range(len(boxes)):
        if used[i]:
            continue
        c = centroids[i]
        # Cari deteksi yang berada di meja yang sama (radius 70 pixel)
        dists = np.linalg.norm(centroids - c, axis=1)
        cluster_mask = dists < 70
        used[cluster_mask] = True

        # Ambil rata-rata bounding box untuk stasiun kerja ini
        cluster_boxes = boxes[cluster_mask]
        mean_box = np.mean(cluster_boxes, axis=0)
        unique_stations.append(mean_box)

    # Buat poligon meja Cabin 1 sampai N dengan padding proporsional
    zones_dict = {}
    h_pad, w_pad = 20, 25

    # Urutkan meja dari atas ke bawah
    unique_stations = sorted(unique_stations, key=lambda b: (b[1], b[0]))

    for idx, b in enumerate(unique_stations):
        x1, y1, x2, y2 = b
        # Buat 4 titik poligon meja
        poly = [
            [int(x1 - w_pad), int(y1 - h_pad)],
            [int(x2 + w_pad), int(y1 - h_pad)],
            [int(x2 + w_pad), int(y2 + h_pad)],
            [int(x1 - w_pad), int(y2 + h_pad)]
        ]
        zones_dict[f"Cabin {idx + 1}"] = poly

    # Simpan ke configs/zones_config.json
    Path("configs").mkdir(parents=True, exist_ok=True)
    with open(output_config, "w") as f:
        json.dump({"zones": zones_dict}, f, indent=2)

    print(f"[✓] SUKSES! Ditemukan {len(zones_dict)} meja kerja secara otomatis.")
    print(f"[✓] Koordinat presisi telah disimpan ke: {output_config}\n")


if __name__ == "__main__":
    auto_calibrate_workstations()