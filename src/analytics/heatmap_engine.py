"""
OmniPresence Enterprise: 2D Spatial Density Heatmap Engine
Generates real-time thermal occupancy accumulation maps using Gaussian Kernel Density Estimation.
"""

import cv2
import numpy as np
from typing import List, Tuple


class SpatialHeatmapEngine:
    def __init__(self, decay_factor: float = 0.985, kernel_size: int = 41, sigma: float = 15.0):
        self.decay_factor = decay_factor
        self.kernel_size = kernel_size
        self.sigma = sigma
        self.accumulator = None

    def update_and_render(
        self,
        frame: np.ndarray,
        occupant_centroids: List[Tuple[float, float]],
        alpha: float = 0.40
    ) -> np.ndarray:
        """
        Accumulates spatial coordinates, applies 2D Gaussian KDE, and blends
        an authentic thermal heatmap onto the video frame.
        """
        h, w = frame.shape[:2]

        # Initialize accumulator matrix on first frame
        if self.accumulator is None or self.accumulator.shape != (h, w):
            self.accumulator = np.zeros((h, w), dtype=np.float32)

        # 1. Apply Exponential Temporal Decay (Fade past movements)
        self.accumulator *= self.decay_factor

        # 2. Inject 2D Gaussian Splat for Each Active Person
        for cx, cy in occupant_centroids:
            x, y = int(cx), int(cy)
            if 0 <= x < w and 0 <= y < h:
                # Add intense localized density energy
                cv2.circle(self.accumulator, (x, y), radius=int(self.sigma * 1.5), color=1.0, thickness=-1)

        # 3. Gaussian Blur to synthesize continuous Kernel Density Estimation
        blurred_density = cv2.GaussianBlur(self.accumulator, (self.kernel_size, self.kernel_size), self.sigma)

        # 4. Normalize Density to 8-bit [0 - 255]
        norm_density = cv2.normalize(blurred_density, None, 0, 255, cv2.NORM_MINMAX)
        norm_density = np.uint8(norm_density)

        # 5. Apply Enterprise TURBO Thermal Colormap (Cyan -> Green -> Yellow -> Red)
        color_heatmap = cv2.applyColorMap(norm_density, cv2.COLORMAP_TURBO)

        # 6. Mask Out Low-Density Noise (Keep background clean)
        threshold_mask = norm_density > 25
        heatmap_masked = np.zeros_like(frame)
        heatmap_masked[threshold_mask] = color_heatmap[threshold_mask]

        # 7. Alpha Blend Thermal Heatmap on Frame
        blended_frame = frame.copy()
        cv2.addWeighted(heatmap_masked, alpha, blended_frame, 1.0, 0, blended_frame)

        return blended_frame