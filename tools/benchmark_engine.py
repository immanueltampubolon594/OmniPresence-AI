"""
OmniPresence-Platform: Latency & Throughput Benchmark Engine
Membandingkan kecepatan inferensi: PyTorch Engine vs ONNX Runtime Engine.
"""

import time
import numpy as np
import cv2
import os
from ultralytics import YOLO

MODEL_PT = "yolov8s.pt"
MODEL_ONNX = "yolov8s.onnx"
WARMUP_ITERATIONS = 10
TEST_ITERATIONS = 50


def benchmark_engine(model_path, is_onnx=False):
    print(f"\n[BENCHMARK] Menguji engine: {model_path} ...")
    
    # Inisialisasi model
    model = YOLO(model_path, task="detect")
    dummy_frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

    # 1. Warm-up GPU/CPU cache
    for _ in range(WARMUP_ITERATIONS):
        _ = model(dummy_frame, verbose=False)

    # 2. Pengukuran Latency Presisi
    latencies = []
    for _ in range(TEST_ITERATIONS):
        t0 = time.perf_counter()
        _ = model(dummy_frame, verbose=False)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)  # Konversi ke milidetik

    avg_latency = np.mean(latencies)
    std_latency = np.std(latencies)
    throughput_fps = 1000.0 / avg_latency

    return avg_latency, std_latency, throughput_fps


def main():
    print("=" * 65)
    print("  OMNIPRESENCE-AI: HARDWARE INFERENCE BENCHMARK TOOL")
    print("=" * 65)

    if not os.path.exists(MODEL_PT):
        print(f"[ERROR] {MODEL_PT} tidak ditemukan!")
        return

    # Benchmark PyTorch
    pt_lat, pt_std, pt_fps = benchmark_engine(MODEL_PT)

    # Benchmark ONNX jika sudah diekspor
    if os.path.exists(MODEL_ONNX):
        onnx_lat, onnx_std, onnx_fps = benchmark_engine(MODEL_ONNX, is_onnx=True)
        speedup = ((pt_lat - onnx_lat) / pt_lat) * 100.0
    else:
        onnx_lat, onnx_std, onnx_fps, speedup = 0, 0, 0, 0

    print("\n" + "=" * 65)
    print("  HASIL TOLOK UKUR PERFORMA (BENCHMARK RESULTS)")
    print("=" * 65)
    print(f"1. PyTorch (.pt) Engine   : {pt_lat:.2f} ms ± {pt_std:.2f} ms | FPS: {pt_fps:.1f}")
    if os.path.exists(MODEL_ONNX):
        print(f"2. ONNX Runtime Engine    : {onnx_lat:.2f} ms ± {onnx_std:.2f} ms | FPS: {onnx_fps:.1f}")
        print(f"--> Peningkatan Efisiensi : {speedup:+.1f}% lebih responsif!")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()