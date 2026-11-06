<div align="center">

# OmniPresence-AI

### Autonomous Workplace Spatial Intelligence & Vision Telemetry Platform

Real-time desk-occupancy analytics from CCTV. Pose-based ergonomics monitoring.
Executive audit reporting. Built as a production-grade multi-camera VMS.

<br/>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.11x-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Async_Pipeline-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Pose-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)
![Next.js](https://img.shields.io/badge/Next.js_14-App_Router-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_v4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)

</div>

---

## 📐 System Architecture

OmniPresence-AI is built in **six decoupled layers**. The critical design decision is
layer ②: video capture, model inference, and stream delivery each run on their **own
thread**, communicating only through Redis queues. No layer ever blocks another.

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui, sans-serif','fontSize':'13px','primaryColor':'#ffffff','primaryTextColor':'#1f2328','primaryBorderColor':'#d0d7de','lineColor':'#8c959f','textColor':'#1f2328','clusterBkg':'#f6f8fa','clusterBorder':'#d0d7de','edgeLabelBackground':'#ffffff'}}}%%
flowchart TB

    subgraph ING["&nbsp; ① &nbsp;INGESTION LAYER&nbsp; "]
        direction LR
        CAM1["<b>cam_alpha</b><br/>Room 1"]
        CAM2["<b>cam_beta</b><br/>Room 2"]
        CAM3["<b>cam_03 · cam_04</b><br/><i>hot-swappable</i>"]
        CAM1 ~~~ CAM2 ~~~ CAM3
    end

    subgraph CORE["&nbsp; ② &nbsp;ASYNC VISION CORE &nbsp;·&nbsp; 3-Thread Redis Pipeline&nbsp; "]
        direction LR
        TC["<b>THREAD 1</b><br/>CAPTURE<br/><br/>non-blocking<br/>frame grabber"]
        RQ1[("<b>raw:frames</b><br/>MAXLEN = 4<br/><i>back-pressure</i>")]
        TI["<b>THREAD 2</b><br/>INFERENCE<br/><br/>YOLOv8n-pose<br/>+ ByteTrack"]
        RQ2[("<b>telemetry:state</b><br/>live JSON<br/><i>snapshot</i>")]
        TB["<b>THREAD 3</b><br/>BROADCAST<br/><br/>MJPEG multipart<br/>encoder"]
        TC --> RQ1 --> TI --> RQ2 --> TB
    end

    subgraph INTEL["&nbsp; ③ &nbsp;SPATIAL INTELLIGENCE ENGINE&nbsp; "]
        direction LR
        ZN["<b>Zone Resolver</b><br/>cv2.pointPolygonTest<br/>polygon hit-test"]
        ER["<b>Ergonomics Engine</b><br/>17-keypoint posture<br/>SLOUCH · CERVICAL_STRAIN"]
        DW["<b>Dwell Aggregator</b><br/>per-station duration<br/>occupancy rate"]
        ZN --> ER --> DW
    end

    subgraph SVC["&nbsp; ④ &nbsp;FASTAPI SERVICE LAYER&nbsp; "]
        direction LR
        EP1["<b>/stream</b><br/>video_feed/{cam}"]
        EP2["<b>/telemetry</b><br/>live"]
        EP3["<b>/analytics</b><br/>report · CSV export"]
        EP4["<b>/zones</b><br/>calibration CRUD"]
        EP1 ~~~ EP2 ~~~ EP3 ~~~ EP4
    end

    subgraph DATA["&nbsp; ⑤ &nbsp;PERSISTENCE &amp; EXECUTIVE REPORTING&nbsp; "]
        direction LR
        DB[("<b>SQLite</b><br/>incidents<br/>audit_log")]
        PDF["<b>ReportLab</b><br/>Executive PDF<br/><i>auto text-wrap</i>"]
        MAIL["<b>Gmail SMTP</b><br/>HTML + attachment"]
        DB --> PDF --> MAIL
    end

    subgraph WEB["&nbsp; ⑥ &nbsp;NEXT.JS 14 COMMAND CENTER&nbsp; "]
        direction LR
        UI2["<b>Dual Viewport</b><br/>MJPEG split-screen"]
        UI1["<b>KPI Grid</b><br/>1s live poll"]
        UI3["<b>Recharts</b><br/>dwell · occupancy"]
        UI4["<b>Zone Calibrator</b><br/>canvas polygon editor"]
        UI2 ~~~ UI1 ~~~ UI3 ~~~ UI4
    end

    CAM1 --> TC
    CAM2 --> TC
    CAM3 -.-> TC

    TI  -->|"keypoints + track IDs"| ZN
    ER  -.->|"incident"| DB

    TB  --> EP1
    RQ2 --> EP2
    DW  --> EP3
    MAIL -.-> EP3

    EP1 --> UI2
    EP2 --> UI1
    EP3 --> UI3
    EP4 <-.->|"polygon JSON"| UI4

    classDef thread fill:#cffafe,stroke:#0891b2,stroke-width:2px,color:#0c4a56
    classDef store  fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#713f12
    classDef intel  fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#4c1d95
    classDef api    fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a8a
    classDef ui     fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef cam    fill:#ffffff,stroke:#8c959f,stroke-width:1.5px,color:#1f2328
    classDef rep    fill:#ffedd5,stroke:#ea580c,stroke-width:1.5px,color:#7c2d12

    class TC,TI,TB thread
    class RQ1,RQ2,DB store
    class ZN,ER,DW intel
    class EP1,EP2,EP3,EP4 api
    class UI1,UI2,UI3,UI4 ui
    class CAM1,CAM2,CAM3 cam
    class PDF,MAIL rep
```

---

## ⚡ The Async Vision Core

A naive CV service does `read → infer → encode → yield` in one loop. That couples
camera FPS to model latency: inference stalls the grab, frames pile up, and the
browser receives a stream that is seconds behind reality.

OmniPresence splits that loop into **three independent threads** joined by Redis:

| Thread | Responsibility | Blocks on | Why it is isolated |
|:---|:---|:---|:---|
| **① Capture** | `cv2.VideoCapture.read()`, JPEG encode, `LPUSH raw:frames` | I/O only | Keeps grabbing at native camera FPS even while the model is busy |
| **② Inference** | `BRPOP` → YOLOv8n-pose → ByteTrack → zone + ergonomics → `SET telemetry:state` | CPU / GPU | The only expensive stage; isolating it stops it from throttling capture |
| **③ Broadcast** | `BRPOP processed:frames` → `multipart/x-mixed-replace` | network | Slow or disconnecting clients can never back-pressure the model |

### Bounded queue — the anti-lag guarantee

```python
QUEUE_MAX_LEN = 4          # ~130ms of buffer at 30fps
pipe.lpush("raw:frames", payload)
pipe.ltrim("raw:frames", 0, QUEUE_MAX_LEN - 1)   # discard stale frames
```

If inference falls behind, old frames are **dropped, not buffered**. The viewer
always sees the present rather than an ever-growing backlog — the correct trade-off
for live surveillance, where a frame from 8 seconds ago has no value.

### Graceful degradation

Redis is an accelerator, not a hard dependency. If the connection fails at startup,
the engine logs the reason and falls back to a single-threaded synchronous loop.
The dashboard keeps working at reduced throughput; nothing crashes.

> **Compatibility note.** Redis 3.0.504 (the common Windows build) predates RESP3 and
> rejects the `HELLO` handshake that `redis-py` sends by default. The client is pinned
> with `protocol=2` so the same codebase runs on both legacy Windows Redis and modern
> Linux Redis.

---

## 🔄 Request Lifecycle

How a single photon of light becomes a number on the dashboard:

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui, sans-serif','fontSize':'13px','primaryColor':'#ffffff','primaryTextColor':'#1f2328','primaryBorderColor':'#d0d7de','lineColor':'#8c959f','textColor':'#1f2328','actorBkg':'#dbeafe','actorBorder':'#2563eb','actorTextColor':'#1e3a8a','actorLineColor':'#c9d1d9','signalColor':'#57606a','signalTextColor':'#1f2328','labelBoxBkg':'#ffffff','labelBoxBorderColor':'#d0d7de','labelTextColor':'#1f2328','loopTextColor':'#1f2328','noteBkgColor':'#fef3c7','noteBorderColor':'#d97706','noteTextColor':'#713f12','sequenceNumberColor':'#ffffff'}}}%%
sequenceDiagram
    autonumber
    participant CV as 🎥 OpenCV Source
    participant T1 as 🧵 Thread 1<br/>CAPTURE
    participant R as 🔴 Redis 3.0<br/>(protocol=2)
    participant T2 as 🧵 Thread 2<br/>INFERENCE
    participant T3 as 🧵 Thread 3<br/>BROADCAST
    participant API as 🚀 FastAPI
    participant UI as 🖥️ Dashboard

    rect rgb(224, 247, 250)
    note over T1,R: Producer — never blocks on inference
    loop every frame
        CV->>T1: read() raw BGR frame
        T1->>R: LPUSH raw:frames (JPEG bytes)
        T1->>R: LTRIM 0..3 — drop stale frames
    end
    end

    rect rgb(226, 237, 255)
    note over T2,R: Consumer — the only GPU/CPU-heavy stage
    loop worker loop
        R-->>T2: BRPOP raw:frames
        T2->>T2: YOLOv8n-pose → 17 keypoints
        T2->>T2: ByteTrack ID association
        T2->>T2: pointPolygonTest → zone occupancy
        T2->>T2: Ergonomics score + incident check
        T2->>R: SET telemetry:state (JSON)
        T2->>R: LPUSH processed:frames (annotated)
    end
    end

    rect rgb(243, 232, 255)
    note over T3,UI: Delivery — decoupled from inference FPS
    R-->>T3: BRPOP processed:frames
    T3->>API: yield multipart/x-mixed-replace
    API-->>UI: MJPEG stream (continuous)
    UI->>API: GET /telemetry/live (1s poll)
    API->>R: GET telemetry:state
    R-->>API: JSON snapshot
    API-->>UI: occupancy · FPS · ergonomics
    end

    note over T1,UI: ⚠️ Redis unreachable → engine auto-degrades<br/>to single-thread synchronous mode. Zero downtime.
```

---

## 🧠 Spatial Intelligence Pipeline

Inside Thread 2, each frame passes through four stages:

| Stage | Technique | Output |
|:---|:---|:---|
| **Detection** | YOLOv8n-pose | Person boxes + 17 COCO keypoints |
| **Identity** | ByteTrack association | Stable `track_id` across frames |
| **Localization** | `cv2.pointPolygonTest` against calibrated polygons | `station_id ← track_id` binding |
| **Ergonomics** | Neck/torso/shoulder angles from keypoints | Score 0-100, `SEVERE_SLOUCH` / `CERVICAL_STRAIN` incidents |

Zones are not hard-coded. The **Zone Calibrator** in the dashboard lets an operator
draw occupancy polygons directly on a live frame; the geometry is persisted per
camera and reloaded by the engine, so deploying to a new room needs no code change.

---

## 🗂️ Project Structure

```
OmniPresence-AI/
│
├── src/
│   ├── services/
│   │   ├── telemetry_service.py      # ⚡ 3-thread Redis pipeline + fallback
│   │   ├── notification_service.py   # Gmail SMTP, HTML body + PDF attachment
│   │   └── report_service.py         # ReportLab executive PDF generator
│   ├── core/
│   │   ├── ergonomics.py             # 17-keypoint posture scoring
│   │   ├── tracker.py                # ByteTrack ID association
│   │   └── zones.py                  # pointPolygonTest occupancy resolver
│   ├── api/v1/
│   │   ├── stream.py                 # MJPEG multipart endpoints
│   │   ├── telemetry.py              # live state snapshot
│   │   ├── analytics.py              # CSV export + report download
│   │   └── notifications.py          # email dispatch
│   ├── db/
│   │   ├── database.py               # SQLite session + schema
│   │   └── seeder.py                 # demo incident generator
│   └── main.py                       # FastAPI app factory + lifespan
│
├── web-frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx              # Command center dashboard
│       │   └── globals.css           # Tailwind v4 entry
│       ├── components/
│       │   ├── AnalyticsCharts.tsx   # Recharts dwell-time + occupancy
│       │   └── ZoneCalibrator.tsx    # Canvas polygon editor
│       └── types/
│           └── telemetry.ts          # Shared API contract types
│
├── data/
│   ├── videos/                       # per-camera source footage
│   ├── zones/                        # calibrated polygon JSON
│   └── omnipresence.db               # SQLite store
│
├── models/
│   └── yolov8n-pose.pt
│
└── requirements.txt
```

---

## 🛠️ Tech Stack

| Layer | Technology | Role |
|:---|:---|:---|
| **Vision** | YOLOv8n-pose · OpenCV · ByteTrack | Detection, keypoints, identity persistence |
| **Concurrency** | Redis · Python `threading` | Decoupled 3-stage pipeline, bounded queues |
| **Backend** | FastAPI · Uvicorn · Pydantic | Async HTTP, MJPEG streaming, typed contracts |
| **Persistence** | SQLite · SQLAlchemy | Incident store + immutable audit trail |
| **Reporting** | ReportLab · smtplib | Executive PDF, Gmail SMTP delivery |
| **Frontend** | Next.js 14 (App Router) · TypeScript | Server/client component dashboard |
| **UI** | Tailwind CSS v4 · Recharts · lucide-react | Command-center visual system |

---

## 🌐 API Reference

| Method | Endpoint | Purpose |
|:---|:---|:---|
| `GET` | `/api/v1/stream/video_feed/{camera_id}` | Annotated MJPEG live stream |
| `GET` | `/api/v1/telemetry/live` | Occupancy, FPS, per-station ergonomics |
| `POST` | `/api/v1/video/upload/{camera_id}` | Hot-swap source footage for a channel |
| `GET` | `/api/v1/analytics/latest-report/download` | CSV export of session analytics |
| `POST` | `/api/v1/notifications/send-report-email` | Email executive PDF to a recipient |
| `GET` `POST` | `/api/v1/zones/{camera_id}` | Read / persist occupancy polygons |

---

## 🚀 Quick Start

```bash
# 1 — Backend
git clone https://github.com/immanueltampubolon594/OmniPresence-AI.git
cd OmniPresence-AI
python -m venv venv && venv\Scripts\activate       # Windows
pip install -r requirements.txt

redis-server                                        # separate terminal
uvicorn src.main:app --reload --port 8000

# 2 — Frontend
cd web-frontend
npm install
npm run dev                                         # http://localhost:3000
```

On a healthy start the engine reports:

```
[REDIS] Koneksi berhasil — pipeline asinkron aktif.
[ENGINE] cam_alpha  → CAPTURE | INFERENCE | BROADCAST threads online
[ENGINE] cam_beta   → CAPTURE | INFERENCE | BROADCAST threads online
```

Without Redis it reports the fallback instead, and the dashboard still runs:

```
[REDIS] Tidak tersedia — beralih ke mode single-thread sinkron.
```