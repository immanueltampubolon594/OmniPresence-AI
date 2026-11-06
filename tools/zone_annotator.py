"""
OmniPresence-AI: Final Zone Annotator Tool (Independent & Self-Contained)
"""

import sys
import os
# Tambahkan path root agar Python mengenali seluruh folder proyek
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import json
import numpy as np

VIDEO_PATH = "data/raw/cctv_kantor_baru.mp4"
OUTPUT_CONFIG_PATH = "configs/zones_config.json"

current_zone_points = []
all_zones = {}
zone_counter = 1


def mouse_callback(event, x, y, flags, param):
    global current_zone_points
    if event == cv2.EVENT_LBUTTONDOWN:
        current_zone_points.append([x, y])
        print(f"[Titik Ditambahkan] Cabin {zone_counter}: ({x}, {y})")


def main():
    global current_zone_points, all_zones, zone_counter

    if not os.path.exists(VIDEO_PATH):
        print(f"[ERROR] File video tidak ditemukan di: {VIDEO_PATH}")
        return

    cap = cv2.VideoCapture(VIDEO_PATH)
    # Lompat ke detik ke-4.5 saat kamera lurus tegak
    cap.set(cv2.CAP_PROP_POS_MSEC, 4500)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print("[ERROR] Gagal membaca frame video.")
        return

    window_name = "Workstation Zone Annotator (Frame Lurus)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1100, 650)
    cv2.setMouseCallback(window_name, mouse_callback)

    print("\n" + "=" * 60)
    print("TOOL PENANDA MEJA (FRAME LURUS)")
    print("1. Klik 4 sudut di masing-masing meja.")
    print("2. Tekan 'n' untuk lanjut ke meja berikutnya.")
    print("3. Tekan 's' untuk MENYIMPAN dan keluar.")
    print("=" * 60 + "\n")

    while True:
        display_frame = frame.copy()

        # Render zona yang sudah selesai dibuat (Biru)
        for name, points in all_zones.items():
            pts = np.array(points, np.int32).reshape((-1, 1, 2))
            cv2.polylines(display_frame, [pts], isClosed=True, color=(255, 120, 0), thickness=2)
            cv2.putText(display_frame, name, (points[0][0], points[0][1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 120, 0), 2)

        # Render titik yang sedang aktif dibuat (Kuning)
        if len(current_zone_points) > 0:
            for pt in current_zone_points:
                cv2.circle(display_frame, tuple(pt), 5, (0, 255, 255), -1)
            if len(current_zone_points) > 1:
                pts = np.array(current_zone_points, np.int32).reshape((-1, 1, 2))
                cv2.polylines(display_frame, [pts], isClosed=False, color=(0, 255, 255), thickness=2)

        hud_text = f"Membuat: Cabin {zone_counter} (Titik: {len(current_zone_points)}) | [n]: Next | [s]: Simpan | [u]: Undo"
        cv2.putText(display_frame, hud_text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

        cv2.imshow(window_name, display_frame)
        key = cv2.waitKey(20) & 0xFF

        if key == ord('n'):
            if len(current_zone_points) >= 3:
                cabin_name = f"Cabin {zone_counter}"
                all_zones[cabin_name] = current_zone_points
                print(f"[SUKSES] {cabin_name} tersimpan.")
                zone_counter += 1
                current_zone_points = []
            else:
                print("[PERINGATAN] Minimal butuh 3 titik!")

        elif key == ord('u'):
            if current_zone_points:
                current_zone_points.pop()

        elif key == ord('s'):
            if len(current_zone_points) >= 3:
                all_zones[f"Cabin {zone_counter}"] = current_zone_points

            os.makedirs(os.path.dirname(OUTPUT_CONFIG_PATH), exist_ok=True)
            with open(OUTPUT_CONFIG_PATH, "w") as f:
                json.dump(all_zones, f, indent=4)
            print(f"\n[SELESAI] Koordinat {len(all_zones)} meja berhasil disimpan ke: {OUTPUT_CONFIG_PATH}\n")
            break

        elif key == ord('q'):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()