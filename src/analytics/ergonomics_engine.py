"""
OmniPresence Biomechanics Engine: Real-time Ergonomics & Posture Analytics
Calculates joint angles, spine curvature, and workplace ergonomics compliance.
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple


class ErgonomicsEngine:
    """
    COCO Keypoint Indexes:
    0: Nose, 1: Left Eye, 2: Right Eye, 3: Left Ear, 4: Right Ear,
    5: Left Shoulder, 6: Right Shoulder, 7: Left Elbow, 8: Right Elbow,
    9: Left Wrist, 10: Right Wrist, 11: Left Hip, 12: Right Hip
    """

    def __init__(self, slouch_threshold_deg: float = 20.0, severe_slouch_deg: float = 35.0):
        self.slouch_threshold = slouch_threshold_deg
        self.severe_slouch = severe_slouch_deg

    @staticmethod
    def _calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        """
        Calculates angle ABC (in degrees) using vector dot product.
        Vector BA and Vector BC.
        """
        ba = a - b
        bc = c - b

        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        angle = np.degrees(np.arccos(cosine_angle))
        return float(angle)

    @staticmethod
    def _vertical_deviation_angle(top_point: np.ndarray, bottom_point: np.ndarray) -> float:
        """
        Calculates the angle deviation (in degrees) of a vector relative to the true vertical axis.
        0 degrees = perfectly upright (straight vertical).
        """
        vector = top_point - bottom_point
        # True vertical vector pointing downwards: [0, 1] (in image coordinates where Y goes down)
        vertical = np.array([0.0, -1.0])  # pointing upwards
        
        # Invert Y for Cartesian alignment
        v_cartesian = np.array([vector[0], -vector[1]])
        
        norm = np.linalg.norm(v_cartesian)
        if norm < 1e-6:
            return 0.0
            
        cosine = np.dot(v_cartesian, np.array([0.0, 1.0])) / norm
        cosine = np.clip(cosine, -1.0, 1.0)
        return float(np.degrees(np.arccos(cosine)))

    def evaluate_posture(self, keypoints: np.ndarray, confidences: np.ndarray) -> Dict[str, Any]:
        """
        Evaluates ergonomics based on 17 2D skeleton keypoints.
        Args:
            keypoints: shape (17, 2) [x, y] coordinates
            confidences: shape (17,) confidence score per keypoint
        """
        # Threshold for reliable keypoints
        CONF_MIN = 0.35

        # Check required joints: Shoulders (5, 6) and Ears (3, 4) or Nose (0)
        left_shoulder_valid = confidences[5] > CONF_MIN
        right_shoulder_valid = confidences[6] > CONF_MIN

        if not (left_shoulder_valid or right_shoulder_valid):
            return {
                "posture_state": "UNDETERMINED",
                "ergonomic_score": 100.0,
                "torso_angle_deg": 0.0,
                "neck_angle_deg": 0.0,
                "message": "Insufficient keypoint visibility"
            }

        # Calculate Mid-Shoulder
        if left_shoulder_valid and right_shoulder_valid:
            mid_shoulder = (keypoints[5] + keypoints[6]) / 2.0
        elif left_shoulder_valid:
            mid_shoulder = keypoints[5]
        else:
            mid_shoulder = keypoints[6]

        # Calculate Mid-Hip (11, 12) if visible, else estimate downward
        left_hip_valid = confidences[11] > CONF_MIN
        right_hip_valid = confidences[12] > CONF_MIN

        if left_hip_valid and right_hip_valid:
            mid_hip = (keypoints[11] + keypoints[12]) / 2.0
        elif left_hip_valid:
            mid_hip = keypoints[11]
        elif right_hip_valid:
            mid_hip = keypoints[12]
        else:
            # Fallback for overhead/desk view where hips are occluded by desk
            # Estimate spine direction from neck-shoulder perpendicular
            mid_hip = mid_shoulder + np.array([0.0, 80.0])

        # 1. Torso Spine Inclination Angle (Deviation from upright 90 deg)
        torso_angle = self._vertical_deviation_angle(mid_shoulder, mid_hip)

        # 2. Neck Flexion Angle (Head tilt relative to shoulders)
        head_point = None
        if confidences[0] > CONF_MIN:  # Nose
            head_point = keypoints[0]
        elif confidences[3] > CONF_MIN and confidences[4] > CONF_MIN:  # Ears
            head_point = (keypoints[3] + keypoints[4]) / 2.0

        neck_angle = 0.0
        if head_point is not None:
            neck_angle = self._vertical_deviation_angle(head_point, mid_shoulder)

        # 3. Ergonomic Penalty Score Calculation (0 to 100)
        # Ideal: Torso angle < 15 deg, Neck angle < 20 deg
        penalty = (max(0.0, torso_angle - 10.0) * 1.5) + (max(0.0, neck_angle - 15.0) * 1.0)
        ergonomic_score = max(0.0, min(100.0, 100.0 - penalty))

        # 4. Posture Classification
        if torso_angle >= self.severe_slouch or ergonomic_score < 50.0:
            posture_state = "SEVERE_SLOUCH"
        elif torso_angle >= self.slouch_threshold or ergonomic_score < 75.0:
            posture_state = "MILD_SLOUCH"
        else:
            posture_state = "OPTIMAL"

        return {
            "posture_state": posture_state,
            "ergonomic_score": round(ergonomic_score, 1),
            "torso_angle_deg": round(torso_angle, 1),
            "neck_angle_deg": round(neck_angle, 1),
            "status_color": (
                "#10B981" if posture_state == "OPTIMAL" else
                "#F59E0B" if posture_state == "MILD_SLOUCH" else "#EF4444"
            )
        }