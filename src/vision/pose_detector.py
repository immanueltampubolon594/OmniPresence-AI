"""
OmniPresence Vision Engine: Clean Enterprise Camera Feed
Extracts biomechanics & keypoints for telemetry without drawing clutter on video.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from ultralytics import YOLO

from src.analytics.ergonomics_engine import ErgonomicsEngine


class BiomechanicsPoseDetector:
    def __init__(self, model_path: str = "weights/yolov8n-pose.pt", conf_thresh: float = 0.18):
        self.conf_thresh = conf_thresh
        self.ergo_engine = ErgonomicsEngine()

        weights_dir = Path("weights")
        weights_dir.mkdir(parents=True, exist_ok=True)
        target_model = Path(model_path)

        if not target_model.exists():
            print("[AI] Mengunduh YOLOv8-Pose model...")
            self.model = YOLO("yolov8n-pose.pt")
            try:
                self.model.save(str(target_model))
            except Exception:
                pass
        else:
            self.model = YOLO(str(target_model))

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        results = self.model.predict(
            source=frame,
            conf=self.conf_thresh,
            classes=[0],
            verbose=False
        )

        detections = []
        # Frame tetap bersih alami (tidak digambar garis-garis badan)
        annotated_frame = frame.copy()

        if not results or len(results) == 0 or results[0].keypoints is None:
            return annotated_frame, detections

        res = results[0]
        boxes = res.boxes.xyxy.cpu().numpy() if res.boxes is not None else []
        keypoints_data = res.keypoints.xy.cpu().numpy()
        confidences_data = res.keypoints.conf.cpu().numpy() if res.keypoints.conf is not None else None

        num_persons = len(keypoints_data)

        for i in range(num_persons):
            kpts = keypoints_data[i]
            confs = confidences_data[i] if confidences_data is not None else np.ones(17)

            ergo_result = self.ergo_engine.evaluate_posture(kpts, confs)

            bbox = boxes[i].tolist() if i < len(boxes) else [0, 0, 0, 0]
            cx = (bbox[0] + bbox[2]) / 2.0
            cy = (bbox[1] + bbox[3]) / 2.0

            person_info = {
                "bbox": [round(c, 1) for c in bbox],
                "centroid": (float(cx), float(cy)),
                "ergonomics": ergo_result,
                "keypoints": kpts.tolist()
            }
            detections.append(person_info)

        # Mengembalikan frame jernih tanpa garis kerangka
        return annotated_frame, detections