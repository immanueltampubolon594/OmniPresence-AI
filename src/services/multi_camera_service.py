import cv2
import json
import time
import threading
import numpy as np
from pathlib import Path
from typing import Dict, Any
from ultralytics import YOLO
from src.analytics.ergonomics_engine import ErgonomicsEngine
from src.services.audit_logger import audit_logger

class SingleCameraWorker:
    def __init__(self, camera_id: str, video_path: str, config_path: str = None):
        self.camera_id = camera_id
        self.video_path = video_path
        
        # Pengaturan zona independen per kamera
    # Pengaturan zona independen mutlak per kamera
        if not config_path:
            self.config_path = f"configs/zones_config_{self.camera_id}.json"
            # Jika file spesifik belum ada, salin dari zones_config.json utama sebagai awal
            if not Path(self.config_path).exists():
                default_path = Path("configs/zones_config.json")
                if default_path.exists():
                    import shutil
                    shutil.copy(default_path, self.config_path)
        else:
            self.config_path = config_path

        self.lock = threading.Lock()
        self.is_running = False
        self.thread = None
        self.current_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.current_frame_bytes = None
        self.system_fps = 0.0

        self.zones = self._load_zones_config()
        self.workstation_states = {}
        
        for zone_id, zone_val in self.zones.items():
            name = zone_val.get("name", zone_id) if isinstance(zone_val, dict) else zone_id
            
            # ID unik secara global agar tidak tumpang tindih antar kamera di Status Matrix
            unique_station_id = f"{self.camera_id}_{zone_id.replace(' ', '_')}"
            display_name = f"[{self.camera_id.upper()}] {name}"

            self.workstation_states[unique_station_id] = {
                "station_id": unique_station_id,
                "name": display_name,
                "status": "VACANT",
                "state": "VACANT",
                "duration_seconds": 0,
                "occupant_id": None,
                "ergonomics": {
                    "posture_state": "VACANT",
                    "ergonomic_score": 100.0,
                    "torso_angle_deg": 0.0,
                    "neck_angle_deg": 0.0
                }
            }

        print(f"[AI CORE - {self.camera_id}] Memuat Model Perception...")
        self.model = YOLO("weights/yolov8n-pose.pt")
        self.ergo_engine = ErgonomicsEngine()
        self.start()

    def _load_zones_config(self) -> Dict[str, Any]:
        path = Path(self.config_path)
        if not path.exists():
            return {}
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data.get("zones", data)
        except Exception:
            return {}

    def _get_polygon(self, zone_val: Any) -> np.ndarray:
        if isinstance(zone_val, dict):
            pts = zone_val.get("polygon", [])
        else:
            pts = zone_val
        return np.array(pts, dtype=np.int32)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run_inference_loop, daemon=True)
            self.thread.start()
            print(f"[AI PIPELINE] Worker Kamera '{self.camera_id}' Aktif.")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run_inference_loop(self):
        target_video = Path(self.video_path)
        if not target_video.exists():
            candidates = list(Path("data").rglob("*.mp4")) + list(Path(".").glob("*.mp4"))
            if candidates:
                target_video = candidates[0]

        cap = cv2.VideoCapture(str(target_video))
        if not cap.isOpened():
            self.is_running = False
            return

        fps_timer = time.time()
        frame_count = 0

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            current_ts = time.time()
            frame_count += 1

            if frame_count % 10 == 0:
                elapsed = current_ts - fps_timer
                self.system_fps = round(10.0 / max(elapsed, 1e-4), 1)
                fps_timer = current_ts

            clean_frame = frame.copy()
            results = self.model.predict(frame, conf=0.10, classes=[0], verbose=False)

            detected_persons = []
            if results and len(results) > 0 and results[0].boxes is not None:
                res = results[0]
                boxes = res.boxes.xyxy.cpu().numpy()
                kpts_data = res.keypoints.xy.cpu().numpy() if res.keypoints is not None else None
                confs_data = res.keypoints.conf.cpu().numpy() if res.keypoints is not None else None

                for i, box in enumerate(boxes):
                    cx = (box[0] + box[2]) / 2.0
                    cy = (box[1] + box[3]) / 2.0
                    kpts = kpts_data[i] if kpts_data is not None else np.zeros((17, 2))
                    confs = confs_data[i] if confs_data is not None else np.ones(17)
                    ergo = self.ergo_engine.evaluate_posture(kpts, confs)
                    detected_persons.append({
                        "bbox": box.tolist(),
                        "centroid": (float(cx), float(cy)),
                        "ergonomics": ergo
                    })

            matched_cabins = {}
            for person in detected_persons:
                cx, cy = person["centroid"]
                px1, py1, px2, py2 = person["bbox"]
                best_cabin = None
                max_score = 0.0

                for zone_id, zone_val in self.zones.items():
                    poly_pts = self._get_polygon(zone_val)
                    if len(poly_pts) < 3:
                        continue

                    is_inside = cv2.pointPolygonTest(poly_pts, (float(cx), float(cy)), False) >= 0
                    if not is_inside:
                        is_inside = cv2.pointPolygonTest(poly_pts, (float(cx), float(py1)), False) >= 0

                    if is_inside:
                        zone_center = np.mean(poly_pts, axis=0)
                        dist = np.linalg.norm(np.array([cx, cy]) - zone_center)
                        score = 1000.0 - dist
                        if score > max_score:
                            max_score = score
                            best_cabin = zone_id

                if best_cabin and best_cabin not in matched_cabins:
                    matched_cabins[best_cabin] = person

            with self.lock:
                for zone_id, zone_val in self.zones.items():
                    poly_pts = self._get_polygon(zone_val)
                    if len(poly_pts) < 3:
                        continue

                    unique_station_id = f"{self.camera_id}_{zone_id.replace(' ', '_')}"
                    state = self.workstation_states[unique_station_id]

                    if zone_id in matched_cabins:
                        person = matched_cabins[zone_id]
                        state["status"] = "OCCUPIED"
                        state["state"] = "OCCUPIED"
                        state["duration_seconds"] += 1
                        # --- PENCATATAN AUDIT LOG OTOMATIS ---
                        score = person["ergonomics"]["ergonomic_score"]
                        posture = person["ergonomics"]["posture_state"]
                        if posture == "Severe Slouch" and state["duration_seconds"] % 15 == 0:
                            audit_logger.log_event(
                                camera_id=self.camera_id,
                                station_id=zone_id,
                                event_type="ERGONOMIC_HAZARD",
                                severity="WARNING",
                                description=f"Pekerja bungkuk parah (Skor: {score}%) di {zone_id}"
                            )
                        # -------------------------------------
                        state["occupant_id"] = 200 + list(self.zones.keys()).index(zone_id)
                        state["ergonomics"] = person["ergonomics"]
                        color = (0, 230, 118)
                        tag_text = "Occupied"
                    else:
                        state["status"] = "VACANT"
                        state["state"] = "VACANT"
                        state["duration_seconds"] = 0
                        state["occupant_id"] = None
                        state["ergonomics"] = {
                            "posture_state": "VACANT",
                            "ergonomic_score": 100.0,
                            "torso_angle_deg": 0.0,
                            "neck_angle_deg": 0.0
                        }
                        color = (70, 70, 235)
                        tag_text = "Vacant"

                    cv2.polylines(clean_frame, [poly_pts], True, color, thickness=1, lineType=cv2.LINE_AA)
                    top_corner = poly_pts[np.argmin(poly_pts[:, 1])]
                    bx, by = int(top_corner[0]), max(22, int(top_corner[1]) - 6)
                    pill_text = f"{zone_id} {tag_text}"
                    (tw, th), _ = cv2.getTextSize(pill_text, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)

                    overlay = clean_frame.copy()
                    cv2.rectangle(overlay, (bx - 4, by - th - 5), (bx + tw + 8, by + 4), (15, 23, 42), -1)
                    cv2.addWeighted(overlay, 0.82, clean_frame, 0.18, 0, clean_frame)
                    cv2.circle(clean_frame, (bx + 2, by - th // 2 - 1), 3, color, -1, lineType=cv2.LINE_AA)
                    cv2.putText(clean_frame, pill_text, (bx + 10, by - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (245, 245, 245), 1, cv2.LINE_AA)

                self.current_frame = clean_frame.copy()
                ret_enc, buffer = cv2.imencode(".jpg", clean_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
                if ret_enc:
                    self.current_frame_bytes = buffer.tobytes()

            time.sleep(0.015)
        cap.release()

class MultiCameraManager:
    def __init__(self):
        self.cameras: Dict[str, SingleCameraWorker] = {}

    def add_camera(self, camera_id: str, video_path: str, config_path: str = None):
        if camera_id in self.cameras:
            return
        self.cameras[camera_id] = SingleCameraWorker(camera_id, video_path, config_path)

    def remove_camera(self, camera_id: str):
        if camera_id in self.cameras:
            self.cameras[camera_id].stop()
            del self.cameras[camera_id]

    def get_all_stats(self) -> Dict[str, Any]:
        combined_stats = {}
        for cam_id, worker in self.cameras.items():
            combined_stats.update(worker.workstation_states)
        return combined_stats

    def get_frame_bytes(self, camera_id: str):
        if camera_id in self.cameras:
            return self.cameras[camera_id].current_frame_bytes
        return None

# Global Multi-Camera Manager Instance
multi_cam_manager = MultiCameraManager()