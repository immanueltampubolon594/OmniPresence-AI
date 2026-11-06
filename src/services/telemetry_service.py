"""
OmniPresence Enterprise: Async Pipeline Architecture (Redis-backed)
─────────────────────────────────────────────────────────────────────
Thread 1 (Capture)   → baca frame dari video → push ke Redis queue
Thread 2 (Inference) → ambil frame dari Redis → jalankan YOLO → push hasil
Thread 3 (Broadcast) → ambil hasil dari Redis → update state → render frame
"""

import cv2
import json
import time
import threading
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any
from ultralytics import YOLO

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from src.analytics.ergonomics_engine import ErgonomicsEngine

REDIS_HOST    = "localhost"
REDIS_PORT    = 6379
QUEUE_FRAMES  = "omnipresence:frames"
QUEUE_RESULTS = "omnipresence:results"
QUEUE_MAX_LEN = 4


class EnterpriseTelemetryWorker:
    def __init__(self, video_path="data/raw/Dataset_Uji.mp4", config_path="configs/zones_config.json"):
        self.video_path  = video_path
        self.config_path = config_path
        self.lock        = threading.Lock()
        self.is_running  = False
        self.threads     = []

        self.current_frame       = np.zeros((480, 640, 3), dtype=np.uint8)
        self.current_frame_bytes = None
        self.system_fps          = 0.0

        self.zones              = self._load_zones_config()
        self.workstation_states = self._init_states()

        print("[AI CORE] Memuat Model Perception...")
        self.model       = YOLO("weights/yolov8n-pose.pt")
        self.ergo_engine = ErgonomicsEngine()

        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST, port=REDIS_PORT,
                    db=0, socket_timeout=1,
                    protocol=2
                )
                self.redis_client.ping()
                self.redis_client.delete(QUEUE_FRAMES, QUEUE_RESULTS)
                print("[REDIS] Koneksi berhasil — pipeline asinkron aktif.")
            except Exception as e:
                print(f"[REDIS] Tidak tersedia ({e}) — fallback ke single-thread.")
                self.redis_client = None

        self.start()

    def _load_zones_config(self):
        path = Path(self.config_path)
        if not path.exists():
            return {}
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data.get("zones", data)
        except Exception:
            return {}

    def _init_states(self):
        states = {}
        for zone_id, zone_val in self.zones.items():
            name = zone_val.get("name", zone_id) if isinstance(zone_val, dict) else zone_id
            states[zone_id] = {
                "station_id": zone_id, "name": name,
                "status": "VACANT", "state": "VACANT",
                "duration_seconds": 0, "occupant_id": None,
                "ergonomics": {
                    "posture_state": "VACANT", "ergonomic_score": 100.0,
                    "torso_angle_deg": 0.0, "neck_angle_deg": 0.0,
                },
            }
        return states

    def _get_polygon(self, zone_val):
        pts = zone_val.get("polygon", []) if isinstance(zone_val, dict) else zone_val
        return np.array(pts, dtype=np.int32)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        if self.redis_client:
            self.threads = [
                threading.Thread(target=self._thread_capture,   daemon=True, name="Capture"),
                threading.Thread(target=self._thread_inference, daemon=True, name="Inference"),
                threading.Thread(target=self._thread_broadcast, daemon=True, name="Broadcast"),
            ]
        else:
            self.threads = [
                threading.Thread(target=self._run_inference_loop, daemon=True, name="SingleThread"),
            ]
        for t in self.threads:
            t.start()
        mode = "ASYNC 3-thread (Redis)" if self.redis_client else "SYNC single-thread"
        print(f"[AI PIPELINE] Engine aktif — mode: {mode}")

    def stop(self):
        self.is_running = False
        for t in self.threads:
            t.join(timeout=2.0)

    def _thread_capture(self):
        target = Path(self.video_path)
        if not target.exists():
            candidates = list(Path("data").rglob("*.mp4"))
            if candidates:
                target = candidates[0]
        cap = cv2.VideoCapture(str(target))
        if not cap.isOpened():
            self.is_running = False
            return
        fps_timer, frame_count = time.time(), 0
        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            frame_count += 1
            if frame_count % 10 == 0:
                self.system_fps = round(10.0 / max(time.time() - fps_timer, 1e-4), 1)
                fps_timer = time.time()
            if self.redis_client.llen(QUEUE_FRAMES) >= QUEUE_MAX_LEN:
                self.redis_client.lpop(QUEUE_FRAMES)
            self.redis_client.rpush(QUEUE_FRAMES, pickle.dumps(frame, protocol=4))
            time.sleep(0.015)
        cap.release()

    def _thread_inference(self):
        while self.is_running:
            raw = self.redis_client.blpop(QUEUE_FRAMES, timeout=1)
            if raw is None:
                continue
            frame = pickle.loads(raw[1])
            results = self.model.predict(frame, conf=0.10, classes=[0], verbose=False)
            persons = []
            if results and results[0].boxes is not None:
                res   = results[0]
                boxes = res.boxes.xyxy.cpu().numpy()
                kpts_data  = res.keypoints.xy.cpu().numpy()   if res.keypoints else None
                confs_data = res.keypoints.conf.cpu().numpy() if res.keypoints else None
                for i, box in enumerate(boxes):
                    cx, cy = (box[0]+box[2])/2.0, (box[1]+box[3])/2.0
                    kpts  = kpts_data[i]  if kpts_data  is not None else np.zeros((17,2))
                    confs = confs_data[i] if confs_data is not None else np.ones(17)
                    persons.append({
                        "bbox": box.tolist(), "centroid": (float(cx), float(cy)),
                        "ergonomics": self.ergo_engine.evaluate_posture(kpts, confs),
                    })
            payload = pickle.dumps({"frame": frame, "persons": persons}, protocol=4)
            if self.redis_client.llen(QUEUE_RESULTS) >= QUEUE_MAX_LEN:
                self.redis_client.lpop(QUEUE_RESULTS)
            self.redis_client.rpush(QUEUE_RESULTS, payload)

    def _thread_broadcast(self):
        while self.is_running:
            raw = self.redis_client.blpop(QUEUE_RESULTS, timeout=1)
            if raw is None:
                continue
            data    = pickle.loads(raw[1])
            frame   = data["frame"]
            persons = data["persons"]
            matched = self._match_persons_to_zones(persons)
            with self.lock:
                self._update_states_and_render(frame.copy(), matched)

    def _run_inference_loop(self):
        target = Path(self.video_path)
        if not target.exists():
            candidates = list(Path("data").rglob("*.mp4"))
            if candidates:
                target = candidates[0]
        cap = cv2.VideoCapture(str(target))
        if not cap.isOpened():
            self.is_running = False
            return
        fps_timer, frame_count = time.time(), 0
        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            frame_count += 1
            if frame_count % 10 == 0:
                self.system_fps = round(10.0 / max(time.time() - fps_timer, 1e-4), 1)
                fps_timer = time.time()
            results = self.model.predict(frame, conf=0.10, classes=[0], verbose=False)
            persons = []
            if results and results[0].boxes is not None:
                res   = results[0]
                boxes = res.boxes.xyxy.cpu().numpy()
                kpts_data  = res.keypoints.xy.cpu().numpy()   if res.keypoints else None
                confs_data = res.keypoints.conf.cpu().numpy() if res.keypoints else None
                for i, box in enumerate(boxes):
                    cx, cy = (box[0]+box[2])/2.0, (box[1]+box[3])/2.0
                    kpts  = kpts_data[i]  if kpts_data  is not None else np.zeros((17,2))
                    confs = confs_data[i] if confs_data is not None else np.ones(17)
                    persons.append({
                        "bbox": box.tolist(), "centroid": (float(cx), float(cy)),
                        "ergonomics": self.ergo_engine.evaluate_posture(kpts, confs),
                    })
            matched = self._match_persons_to_zones(persons)
            with self.lock:
                self._update_states_and_render(frame.copy(), matched)
            time.sleep(0.015)
        cap.release()

    def _match_persons_to_zones(self, persons):
        matched = {}
        for person in persons:
            cx, cy       = person["centroid"]
            _, py1, _, _ = person["bbox"]
            best, max_score = None, 0.0
            for zone_id, zone_val in self.zones.items():
                poly = self._get_polygon(zone_val)
                if len(poly) < 3:
                    continue
                inside = (
                    cv2.pointPolygonTest(poly, (float(cx), float(cy)),  False) >= 0 or
                    cv2.pointPolygonTest(poly, (float(cx), float(py1)), False) >= 0
                )
                if inside:
                    dist  = np.linalg.norm(np.array([cx, cy]) - np.mean(poly, axis=0))
                    score = 1000.0 - dist
                    if score > max_score:
                        max_score = score
                        best      = zone_id
            if best and best not in matched:
                matched[best] = person
        return matched

    def _update_states_and_render(self, frame, matched):
        for zone_id, zone_val in self.zones.items():
            poly = self._get_polygon(zone_val)
            if len(poly) < 3:
                continue
            state = self.workstation_states[zone_id]
            if zone_id in matched:
                p = matched[zone_id]
                state.update({
                    "status": "OCCUPIED", "state": "OCCUPIED",
                    "duration_seconds": state["duration_seconds"] + 1,
                    "occupant_id": 100 + list(self.workstation_states.keys()).index(zone_id),
                    "ergonomics": p["ergonomics"],
                })
                color, tag = (0, 230, 118), "Occupied"
            else:
                state.update({
                    "status": "VACANT", "state": "VACANT",
                    "duration_seconds": 0, "occupant_id": None,
                    "ergonomics": {"posture_state": "VACANT", "ergonomic_score": 100.0,
                                   "torso_angle_deg": 0.0, "neck_angle_deg": 0.0},
                })
                color, tag = (70, 70, 235), "Vacant"
            cv2.polylines(frame, [poly], True, color, thickness=1, lineType=cv2.LINE_AA)
            top    = poly[np.argmin(poly[:, 1])]
            bx, by = int(top[0]), max(22, int(top[1]) - 6)
            text   = f"{state['name']}  {tag}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
            ov = frame.copy()
            cv2.rectangle(ov, (bx-4, by-th-5), (bx+tw+8, by+4), (15, 23, 42), -1)
            cv2.addWeighted(ov, 0.82, frame, 0.18, 0, frame)
            cv2.circle(frame, (bx+2, by-th//2-1), 3, color, -1, lineType=cv2.LINE_AA)
            cv2.putText(frame, text, (bx+10, by-2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (245, 245, 245), 1, cv2.LINE_AA)
        self.current_frame = frame.copy()
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        if ok:
            self.current_frame_bytes = buf.tobytes()

    def get_current_stats(self):
        with self.lock:
            total    = len(self.workstation_states)
            occupied = sum(1 for w in self.workstation_states.values() if w["status"] == "OCCUPIED")
            scores   = [w["ergonomics"]["ergonomic_score"]
                        for w in self.workstation_states.values()
                        if w["status"] == "OCCUPIED" and w["ergonomics"]["posture_state"] != "VACANT"]
            return {
                "total_stations": total, "occupied_count": occupied,
                "vacant_count": total - occupied,
                "occupancy_rate_percent": round(occupied / max(1, total) * 100, 1),
                "average_ergonomic_score": round(sum(scores)/len(scores), 1) if scores else 100.0,
                "system_fps": self.system_fps,
                "workstations": self.workstation_states,
            }

    def get_live_telemetry(self): return self.get_current_stats()

    def get_current_frame(self):
        with self.lock: return self.current_frame

    def get_current_frame_bytes(self):
        with self.lock: return self.current_frame_bytes

    def generate_frames(self):
        while True:
            fb = self.get_current_frame_bytes()
            if fb:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + fb + b"\r\n"
            time.sleep(0.03)


engine_instance  = EnterpriseTelemetryWorker()
telemetry_worker = engine_instance