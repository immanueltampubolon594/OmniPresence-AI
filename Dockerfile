FROM python:3.12-slim

WORKDIR /app

# Install dependency sistem untuk OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Salin requirements
COPY requirements.txt .

# Install PyTorch versi CPU khusus (jauh lebih ringan & cepat)
RUN pip install --no-cache-dir --default-timeout=1000 torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install dependensi lainnya
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt
RUN pip install --no-cache-dir onnx onnxruntime onnxslim

# Salin kode backend dan model
COPY src/ ./src/
COPY configs/ ./configs/
COPY weights/ ./weights/
COPY yolov8s.onnx ./yolov8s.onnx

# Buat folder laporan
RUN mkdir -p reports

EXPOSE 8000

CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]