"""
OmniPresence-Platform: Edge AI Model Quantization & ONNX Exporter
Deskripsi: Mengonversi bobot PyTorch (.pt) ke format ONNX untuk inferensi ultra-cepat.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ultralytics import YOLO
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ModelOptimizer")

SOURCE_MODEL = "yolov8s.pt"  # Atau "weights/best.pt"
OUTPUT_DIR = "weights"


def export_to_onnx():
    if not os.path.exists(SOURCE_MODEL):
        logger.error(f"Model sumber tidak ditemukan di: {SOURCE_MODEL}")
        return

    logger.info(f"Memuat model PyTorch: {SOURCE_MODEL}...")
    model = YOLO(SOURCE_MODEL)

    logger.info("Memulai proses ekspor ke format ONNX Runtime (imgsz=640, opset=12)...")
    
    # Ekspor menggunakan API Ultralytics
    exported_path = model.export(
        format="onnx",
        imgsz=640,
        dynamic=False,  # Static shape optimal untuk edge device
        simplify=True,  # ONNX-simplifier untuk memangkas node redundan
        opset=12
    )

    logger.info(f"Model berhasil dioptimasi dan diekspor ke: {exported_path}")

    # Bandingkan ukuran file
    pt_size = os.path.getsize(SOURCE_MODEL) / (1024 * 1024)
    onnx_size = os.path.getsize(exported_path) / (1024 * 1024)

    print("\n" + "=" * 55)
    print("  RINGKASAN OPTIMASI MODEL EDGE AI")
    print("=" * 55)
    print(f"Format PyTorch (.pt) : {pt_size:.2f} MB")
    print(f"Format ONNX (.onnx)  : {onnx_size:.2f} MB")
    print("Status               : READY FOR PRODUCTION INFERENCE")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    export_to_onnx()