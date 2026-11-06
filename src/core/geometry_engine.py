from dataclasses import dataclass
from typing import List, Tuple, Union
import numpy as np
import cv2

@dataclass
class Point2D:
    x: float
    y: float

class SpatialGeometryEngine:
    @staticmethod
    def extract_bottom_anchor(bbox: Union[List[float], np.ndarray]) -> Point2D:
        x1, y1, x2, y2 = bbox
        bottom_center_x = (x1 + x2) / 2.0
        bottom_center_y = float(y2)
        return Point2D(x=bottom_center_x, y=bottom_center_y)

    @staticmethod
    def is_point_inside_polygon(point: Point2D, polygon_pts: List[List[int]]) -> bool:
        poly_np = np.array(polygon_pts, dtype=np.int32)
        pt = (float(point.x), float(point.y))
        return cv2.pointPolygonTest(poly_np, pt, measureDist=False) >= 0