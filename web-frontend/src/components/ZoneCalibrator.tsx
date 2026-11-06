"use client";

import { useEffect, useRef, useState } from "react";

const BACKEND_URL = "http://localhost:8000";

interface Point { x: number; y: number; }
interface Zone { name: string; points: Point[]; }

export default function ZoneCalibrator({ cameraId = "cam_alpha", onClose }: { cameraId?: string; onClose: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [currentPoints, setCurrentPoints] = useState<Point[]>([]);
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [loaded, setLoaded] = useState(false);
  const zonesRef = useRef<Zone[]>([]);
  const currentPointsRef = useRef<Point[]>([]);

  useEffect(() => { zonesRef.current = zones; }, [zones]);
  useEffect(() => { currentPointsRef.current = currentPoints; }, [currentPoints]);

  useEffect(() => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    // Mengambil snapshot bersih secara dinamis berdasarkan cameraId yang dikirim dari page.tsx
    img.src = `${BACKEND_URL}/api/v1/stream/snapshot/clean?camera_id=${cameraId}&t=${Date.now()}`;
    img.onload = () => {
      imgRef.current = img;
      setImgSize({ w: img.naturalWidth, h: img.naturalHeight });
      setLoaded(true);
      redraw(img, [], []);
    };
    img.onerror = () => setMsg("Gagal memuat snapshot untuk " + cameraId);
  }, [cameraId]);

  function getCoords(e: React.MouseEvent<HTMLCanvasElement>): Point {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return {
      x: Math.round((e.clientX - rect.left) * (canvas.width / rect.width)),
      y: Math.round((e.clientY - rect.top) * (canvas.height / rect.height)),
    };
  }

  function redraw(img: HTMLImageElement, drawnZones: Zone[], pts: Point[]) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    ctx.drawImage(img, 0, 0);

    // Zona selesai — hijau
    drawnZones.forEach((z) => {
      if (z.points.length < 2) return;
      ctx.beginPath();
      z.points.forEach((p, j) => j === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
      ctx.closePath();
      ctx.fillStyle = "rgba(0,255,100,0.15)";
      ctx.fill();
      ctx.strokeStyle = "#00ff64";
      ctx.lineWidth = 2;
      ctx.stroke();
      const lx = Math.min(...z.points.map(p => p.x));
      const ly = Math.min(...z.points.map(p => p.y));
      ctx.fillStyle = "rgba(0,0,0,0.75)";
      ctx.fillRect(lx, ly - 24, 90, 24);
      ctx.fillStyle = "#00ff64";
      ctx.font = `bold 14px monospace`;
      ctx.fillText(z.name, lx + 5, ly - 6);
    });

    // Poligon sedang digambar — kuning
    if (pts.length >= 2) {
      ctx.beginPath();
      pts.forEach((p, j) => j === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
      ctx.strokeStyle = "#facc15";
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Titik klik — kuning
    pts.forEach((p, i) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
      ctx.fillStyle = "#facc15";
      ctx.fill();
      ctx.strokeStyle = "#000";
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.fillStyle = "#000";
      ctx.font = "bold 11px monospace";
      ctx.fillText(String(i + 1), p.x - 4, p.y + 4);
    });
  }

  function handleClick(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!imgRef.current) return;
    const p = getCoords(e);
    const newPts = [...currentPointsRef.current, p];
    setCurrentPoints(newPts);
    redraw(imgRef.current, zonesRef.current, newPts);
  }

  function finishZone() {
    if (currentPoints.length < 3) { setMsg("Minimal 3 titik."); return; }
    const name = `Cabin ${zonesRef.current.length + 1}`;
    const newZones = [...zonesRef.current, { name, points: currentPoints }];
    setZones(newZones);
    setCurrentPoints([]);
    if (imgRef.current) redraw(imgRef.current, newZones, []);
    setMsg(`✓ ${name} disimpan. Klik titik zona berikutnya.`);
  }

  function undoPoint() {
    const newPts = currentPoints.slice(0, -1);
    setCurrentPoints(newPts);
    if (imgRef.current) redraw(imgRef.current, zonesRef.current, newPts);
  }

  function undoZone() {
    const newZones = zones.slice(0, -1);
    setZones(newZones);
    if (imgRef.current) redraw(imgRef.current, newZones, currentPoints);
  }

  function resetAll() {
    setZones([]); setCurrentPoints([]);
    if (imgRef.current) redraw(imgRef.current, [], []);
    setMsg("");
  }

  async function saveZones() {
    if (zones.length === 0) { setMsg("Belum ada zona."); return; }
    setSaving(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/calibration/zones/save?camera_id=${cameraId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ zones, frame_width: imgSize.w, frame_height: imgSize.h }),
      });
      const json = await res.json();
      if (res.ok) {
        setMsg(`✓ ${json.message}`);
        setTimeout(() => onClose(), 1800);
      } else {
        setMsg(`✗ ${json.detail}`);
      }
    } catch { setMsg("✗ Gagal menghubungi backend."); }
    finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/85 z-50 flex items-center justify-center p-3">
      <div className="bg-[#161b22] border border-gray-700 rounded-2xl w-full max-w-5xl flex flex-col" style={{ height: "95vh" }}>

        <div className="flex justify-between items-start p-5 border-b border-gray-800 flex-shrink-0">
          <div>
            <h2 className="text-lg font-bold text-white">🎯 Kalibrasi Zona Meja ({cameraId})</h2>
            <p className="text-xs text-gray-400 mt-1">
              <b className="text-yellow-400">Klik titik-titik sudut meja</b> mengikuti bentuknya →
              tekan <b className="text-emerald-400">Selesai Zona</b> →
              ulangi → <b className="text-cyan-400">Simpan</b>
            </p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-2xl ml-4">✕</button>
        </div>

        <div className="relative bg-black overflow-y-auto flex-1">
          {!loaded && (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
              Memuat frame video untuk {cameraId}...
            </div>
          )}
          <canvas
            ref={canvasRef}
            onClick={handleClick}
            style={{ width: "100%", height: "auto", display: "block", cursor: "crosshair" }}
          />
        </div>

        <div className="flex-shrink-0 p-4 border-t border-gray-800 flex flex-col gap-3">
          <div className="flex flex-wrap gap-3 items-center">
            <button onClick={finishZone} disabled={currentPoints.length < 3}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm font-bold rounded-lg">
              ✓ Selesai Zona {zones.length + 1}
            </button>
            <button onClick={undoPoint} disabled={currentPoints.length === 0}
              className="px-4 py-2 bg-yellow-700 hover:bg-yellow-600 disabled:opacity-40 text-white text-sm font-bold rounded-lg">
              ↩ Undo Titik
            </button>
            <button onClick={undoZone} disabled={zones.length === 0}
              className="px-4 py-2 bg-orange-700 hover:bg-orange-600 disabled:opacity-40 text-white text-sm font-bold rounded-lg">
              ↩ Undo Zona
            </button>
            <button onClick={resetAll}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-bold rounded-lg">
              ✕ Reset
            </button>
            <button onClick={saveZones} disabled={saving || zones.length === 0}
              className="px-5 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-white text-sm font-bold rounded-lg ml-auto">
              {saving ? "Menyimpan..." : `💾 Simpan ${zones.length} Zona`}
            </button>
          </div>
          <div className="text-xs text-gray-400 flex flex-wrap gap-4">
            <span>Zona: <span className="text-emerald-400 font-bold">{zones.length > 0 ? zones.map(z => z.name).join(", ") : "-"}</span></span>
            <span>Titik aktif: <span className="text-yellow-400 font-bold">{currentPoints.length}</span></span>
            {msg && <span className="text-cyan-300">{msg}</span>}
          </div>
        </div>
      </div>
    </div>
  );
}