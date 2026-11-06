"""
OmniPresence-AI: Zone Preview Tool
Menggambar semua zona dari zones_config.json ke satu frame video
dan menyimpannya sebagai gambar, supaya zona bisa diperiksa dengan cepat.
"""

import json
import os

import cv2
import numpy as np

VIDEO_PATH = "data/raw/cctv_kantor_baru.mp4"
ZONES_CONFIG_PATH = "configs/zones_config.json"
OUTPUT_IMAGE_PATH = "data/zones_preview.png"
FRAME_INDEX = 30  # ambil frame ke-30 (bukan frame 0, karena bisa miring/buram)


def main():
    if not os.path.exists(VIDEO_PATH) or not os.path.exists(ZONES_CONFIG_PATH):
        print("[ERROR] Video atau zones_config.json tidak ditemukan.")
        return

    with open(ZONES_CONFIG_PATH, "r") as f:
        zones = json.load(f)

    cap = cv2.VideoCapture(VIDEO_PATH)
    cap.set(cv2.CAP_PROP_POS_FRAMES, FRAME_INDEX)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("[ERROR] Gagal membaca frame dari video.")
        return

    for name, points in zones.items():
        pts = np.array(points, np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 255), thickness=2)
        x, y = int(pts[:, :, 0].min()), int(pts[:, :, 1].min())
        cv2.putText(frame, name, (x, max(20, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    os.makedirs(os.path.dirname(OUTPUT_IMAGE_PATH), exist_ok=True)
    cv2.imwrite(OUTPUT_IMAGE_PATH, frame)
    print(f"[SUKSES] {len(zones)} zona digambar. Gambar tersimpan di: {OUTPUT_IMAGE_PATH}")


if __name__ == "__main__":
    main()