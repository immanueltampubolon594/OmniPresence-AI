"""
OmniPresence-AI: Autonomous Workstation Zone Detector (v3)
1. Klaster titik tengah orang dari banyak frame -> kursi/meja terisi
2. Jangkar perabot (keyboard/laptop) -> meja yang selalu kosong
3. Resolusi tumpang tindih -> zona saling bersebelahan, tidak menumpuk
Juga menyimpan gambar pratinjau ke data/zones_preview.png.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import json
import numpy as np
from ultralytics import YOLO

VIDEO_PATH = "data/ra/Dataset_Uji.mp4"
OUTPUT_CONFIG_PATH = "configs/zones_config.json"
BACKUP_CONFIG_PATH = "configs/zones_config_backup.json"
PREVIEW_PATH       = "data/zones_preview.png"
MODEL_PATH         = "yolov8s.pt"

NUM_SAMPLES      = 40
CLUSTER_DIST     = 120
ANCHOR_DIST      = 220
MIN_HITS_PERSON  = 5
MIN_HITS_ANCHOR  = 3
ZONE_SCALE       = 1.1
ZONE_SCALE_H     = 1.1
PERSON_CLASS     = 0
ANCHOR_CLASSES   = [63, 66]   # laptop, keyboard


def cluster_points(points, dist):
    """Pengelompokan greedy: tiap titik masuk ke klaster terdekat dalam jarak dist."""
    clusters = []
    for x, y in points:
        best, best_d = None, dist
        for c in clusters:
            d = np.hypot(x - c["cx"], y - c["cy"])
            if d < best_d:
                best, best_d = c, d
        if best is None:
            clusters.append({"cx": x, "cy": y, "n": 1})
        else:
            best["cx"] = (best["cx"] * best["n"] + x) / (best["n"] + 1)
            best["cy"] = (best["cy"] * best["n"] + y) / (best["n"] + 1)
            best["n"] += 1
    return clusters


def resolve_overlaps(rects, passes=6):
    """Pisahkan zona bertabrakan dengan memotong tepat di tengah area tumpang tindih."""
    for _ in range(passes):
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                ox = min(a[2], b[2]) - max(a[0], b[0])
                oy = min(a[3], b[3]) - max(a[1], b[1])
                if ox <= 0 or oy <= 0:
                    continue
                if ox < oy:
                    mid = (max(a[0], b[0]) + min(a[2], b[2])) / 2
                    if a[0] < b[0]:
                        a[2] = mid - 2
                        b[0] = mid + 2
                    else:
                        b[2] = mid - 2
                        a[0] = mid + 2
                else:
                    mid = (max(a[1], b[1]) + min(a[3], b[3])) / 2
                    if a[1] < b[1]:
                        a[3] = mid - 2
                        b[1] = mid + 2
                    else:
                        b[3] = mid - 2
                        a[1] = mid + 2
    return rects


def main():
    print("=" * 60)
    print("  DETEKSI MEJA OTOMATIS v3 (KLASTER + JANGKAR + ANTI-TUMPANG-TINDIH)")
    print("=" * 60)

    if not os.path.exists(VIDEO_PATH):
        print(f"[ERROR] Video tidak ditemukan: {VIDEO_PATH}")
        return

    cap = cv2.VideoCapture(VIDEO_PATH)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        print("[ERROR] Video kosong atau tidak terbaca.")
        return

    model = YOLO(MODEL_PATH)
    step = max(1, total // NUM_SAMPLES)

    person_pts, person_sizes, anchor_pts = [], [], []
    preview_frame = None
    fw = fh = 0

    print(f"[INFO] Memindai {NUM_SAMPLES} frame...")
    for i in range(NUM_SAMPLES):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
        ret, frame = cap.read()
        if not ret:
            continue
        if preview_frame is None:
            preview_frame = frame.copy()
        fh, fw = frame.shape[:2]

        res = model(frame, conf=0.25, classes=[PERSON_CLASS] + ANCHOR_CLASSES, verbose=False)
        boxes = res[0].boxes.xyxy.cpu().numpy()
        classes = res[0].boxes.cls.cpu().numpy().astype(int)
        for (x1, y1, x2, y2), c in zip(boxes, classes):
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            if c == PERSON_CLASS:
                person_pts.append((cx, cy))
                person_sizes.append((x2 - x1, y2 - y1))
            else:
                anchor_pts.append((cx, cy))
    cap.release()

    if not person_pts:
        print("[ERROR] Tidak ada orang terdeteksi. Coba video lain.")
        return

    # Tahap 1: kursi dari titik orang
    seats = [c for c in cluster_points(person_pts, CLUSTER_DIST) if c["n"] >= MIN_HITS_PERSON]

    # Tahap 2: jangkar perabot — yang jauh dari semua kursi dianggap meja kosong
    far_anchors = [p for p in anchor_pts
                   if all(np.hypot(p[0] - s["cx"], p[1] - s["cy"]) > ANCHOR_DIST for s in seats)]
    desks = [c for c in cluster_points(far_anchors, CLUSTER_DIST) if c["n"] >= MIN_HITS_ANCHOR]

    centers = [(s["cx"], s["cy"]) for s in seats] + [(d["cx"], d["cy"]) for d in desks]
    if not centers:
        print("[ERROR] Tidak ada meja ditemukan.")
        return

    med_w = float(np.median([w for w, _ in person_sizes])) * ZONE_SCALE
    med_h = float(np.median([h for _, h in person_sizes])) * ZONE_SCALE

    # Zona: lebar pakai ZONE_SCALE, tinggi pakai ZONE_SCALE_H (lebih besar)
    rects = [
        [
            cx - med_w * ZONE_SCALE / 2,
            cy - med_h * ZONE_SCALE_H / 2,
            cx + med_w * ZONE_SCALE / 2,
            cy + med_h * ZONE_SCALE_H / 2,
        ]
        for cx, cy in centers
    ]

    # Tahap 3: pisahkan zona yang bertabrakan
    rects = resolve_overlaps(rects)

    # Urutkan baris demi baris (kiri-atas ke kanan-bawah)
    rects.sort(key=lambda r: (round(r[1] / 150), r[0]))

    zones = {}
    for idx, (x1, y1, x2, y2) in enumerate(rects, start=1):
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(fw, int(x2)), min(fh, int(y2))
        zones[f"Cabin {idx}"] = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

    os.makedirs(os.path.dirname(OUTPUT_CONFIG_PATH), exist_ok=True)
    if os.path.exists(OUTPUT_CONFIG_PATH):
        os.replace(OUTPUT_CONFIG_PATH, BACKUP_CONFIG_PATH)
    with open(OUTPUT_CONFIG_PATH, "w") as f:
        json.dump(zones, f, indent=4)

    # Simpan pratinjau
    if preview_frame is not None:
        for name, pts in zones.items():
            arr = np.array(pts, np.int32).reshape((-1, 1, 2))
            cv2.polylines(preview_frame, [arr], True, (0, 255, 255), 3)
            x, y = int(arr[:, :, 0].min()), int(arr[:, :, 1].min())
            cv2.putText(preview_frame, name, (x + 6, y + 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        os.makedirs(os.path.dirname(PREVIEW_PATH), exist_ok=True)
        cv2.imwrite(PREVIEW_PATH, preview_frame)

    print(f"\n[SUKSES] {len(seats)} kursi terisi + {len(desks)} meja kosong = {len(zones)} zona.")
    print(f"[INFO] Konfigurasi : {OUTPUT_CONFIG_PATH}")
    print(f"[INFO] Pratinjau   : {PREVIEW_PATH}")


if __name__ == "__main__":
    main()