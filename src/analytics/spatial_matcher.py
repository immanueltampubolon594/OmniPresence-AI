"""
OmniPresence Enterprise: Global Bipartite Spatial Matcher
Implements Kuhn-Munkres (Hungarian) Algorithm for optimal Workstation-Person Association.
Solves the global cost assignment problem in O(N^3) time complexity.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import List, Dict, Tuple, Any


class EnterpriseSpatialMatcher:
    def __init__(self, iou_weight: float = 0.7, distance_weight: float = 0.3, max_match_distance: float = 180.0):
        self.iou_weight = iou_weight
        self.distance_weight = distance_weight
        self.max_match_distance = max_match_distance

    @staticmethod
    def _calculate_polygon_bbox_iou(poly_pts: np.ndarray, bbox: List[float], frame_shape: Tuple[int, int]) -> float:
        """Calculates pixel-exact intersection over union (IoU) via binary rasterization."""
        import cv2
        mask_poly = np.zeros(frame_shape, dtype=np.uint8)
        mask_bbox = np.zeros(frame_shape, dtype=np.uint8)

        cv2.fillPoly(mask_poly, [poly_pts], 1)
        bx1, by1, bx2, by2 = [int(v) for v in bbox]
        cv2.rectangle(mask_bbox, (bx1, by1), (bx2, by2), 1, -1)

        intersection = np.logical_and(mask_poly, mask_bbox).sum()
        union = np.logical_or(mask_poly, mask_bbox).sum()

        if union == 0:
            return 0.0
        return float(intersection / union)

    def match_occupants_to_zones(
        self,
        persons: List[Dict[str, Any]],
        zones: Dict[str, np.ndarray],
        frame_shape: Tuple[int, int]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Solves global bipartite matching between detected persons and workstation zones.
        Returns optimal mapping: {zone_id: matched_person_dict}
        """
        zone_ids = list(zones.keys())
        num_zones = len(zone_ids)
        num_persons = len(persons)

        if num_zones == 0 or num_persons == 0:
            return {}

        # 1. Construct Cost Matrix: Shape (num_zones, num_persons)
        cost_matrix = np.full((num_zones, num_persons), 1e5, dtype=np.float32)

        for z_idx, z_id in enumerate(zone_ids):
            poly_pts = zones[z_id]
            zone_center = np.mean(poly_pts, axis=0)

            for p_idx, person in enumerate(persons):
                cx, cy = person["centroid"]
                bbox = person["bbox"]

                # A. Euclidean Distance
                dist = np.linalg.norm(zone_center - np.array([cx, cy]))

                # B. Intersection Over Union (IoU)
                iou = self._calculate_polygon_bbox_iou(poly_pts, bbox, frame_shape)

                # C. Combined Mathematical Cost Function
                # Normalized distance penalty + IoU reward
                dist_penalty = min(dist / self.max_match_distance, 2.0)
                iou_reward = iou * 2.5

                total_cost = (dist_penalty * self.distance_weight) - (iou_reward * self.iou_weight)

                # Gatekeeper: Discard associations beyond spatial threshold
                if dist <= self.max_match_distance:
                    cost_matrix[z_idx, p_idx] = total_cost

        # 2. Execute Kuhn-Munkres (Hungarian) Optimization Algorithm
        zone_ind, person_ind = linear_sum_assignment(cost_matrix)

        # 3. Filter valid optimal assignments
        assignments = {}
        for z_i, p_i in zip(zone_ind, person_ind):
            if cost_matrix[z_i, p_i] < 1.0:  # Accepted global assignment threshold
                assigned_zone_id = zone_ids[z_i]
                assignments[assigned_zone_id] = persons[p_i]

        return assignments