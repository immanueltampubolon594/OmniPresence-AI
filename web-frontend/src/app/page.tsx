"use client";

import ZoneCalibrator from "../components/ZoneCalibrator";
import React, { useState, useEffect } from "react";
import { 
  Activity, Users, UserX, PieChart as PieIcon, Video, Clock, 
  ShieldCheck, AlertTriangle, RefreshCw, Upload, Download, Crosshair, Mail, Server, Radio
} from "lucide-react";
import { TelemetryData } from "../types/telemetry";
import AnalyticsCharts from "../components/AnalyticsCharts";

const BACKEND_URL = "http://localhost:8000";

export default function DashboardPage() {
  const [selectedCamera, setSelectedCamera] = useState<string>("cam_alpha"); 
  const [data, setData] = useState<TelemetryData | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<string>("--:--:--");
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [showCalibrator, setShowCalibrator] = useState<boolean>(false);
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    if (!mounted) return;
    const fetchTelemetry = async () => {
      try {
       const response = await fetch(`${BACKEND_URL}/api/v1/telemetry/live/${selectedCamera}`, { cache: "no-store" });
        if (response.ok) {
          const json: TelemetryData = await response.json();
          setData(json);
          setIsConnected(true);
          setLastUpdated(new Date().toLocaleTimeString());
        } else {
          setIsConnected(false);
        }
      } catch {
        setIsConnected(false);
      }
    };
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 1000);
    return () => clearInterval(interval);
 }, [mounted, selectedCamera]);

  const handleSpecificVideoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setIsUploading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/video/upload/${selectedCamera}`, { method: "POST", body: formData });
      const resJson = await res.json();
      if (res.ok) {
        alert(`Sukses! Video untuk ${selectedCamera} berhasil diperbarui.`);
        window.location.reload();
      } else {
        alert(`Gagal Upload: ${resJson.detail || "Terjadi kesalahan"}`);
      }
    } catch {
      alert("Gagal menghubungi backend untuk upload video.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownloadReport = () => {
    window.open(`${BACKEND_URL}/api/v1/analytics/latest-report/download`, "_blank");
  };

  const handleSendEmailReport = async () => {
    const email = prompt("Masukkan alamat Gmail penerima laporan eksekutif:");
    if (!email) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/notifications/send-report-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recipient: email })
      });
      const json = await res.json();
      if (res.ok) alert(json.message);
      else alert(`Gagal: ${json.detail}`);
    } catch {
      alert("Gagal menghubungi server untuk kirim email.");
    }
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-[#030712] flex items-center justify-center text-cyan-400">
        <RefreshCw className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <main suppressHydrationWarning className="min-h-screen bg-gradient-to-br from-[#030712] via-[#0b1329] to-[#030712] text-slate-100 p-4 md:p-8 font-sans selection:bg-cyan-500 selection:text-black">

      {/* COMMAND CENTER HEADER */}
      <header className="glass-panel rounded-2xl p-5 mb-6 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 shadow-2xl border border-slate-800/80">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
              <Server className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-black tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-100 to-cyan-400">
                OMNIPRESENCE<span className="text-cyan-400">-</span>AI
              </h1>
              <p className="text-xs text-slate-400 font-medium tracking-wide">
                Autonomous Workplace Spatial Intelligence & Vision Telemetry Platform
              </p>
            </div>
            <span className="hidden sm:inline-block px-3 py-1 text-[11px] font-bold uppercase tracking-wider rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
              v2.0 Enterprise VMS
            </span>
          </div>
        </div>

        {/* CONTROLS & ACTIONS */}
        <div className="flex flex-wrap items-center gap-2.5 w-full lg:w-auto">
          <div className="flex items-center gap-2 bg-slate-900/90 px-3.5 py-2 rounded-xl border border-slate-800 text-xs">
            <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span className="text-slate-400 font-medium">Channel:</span>
          <select
  value={selectedCamera}
  onChange={(e) => setSelectedCamera(e.target.value)}
  className="bg-slate-800 text-cyan-300 font-semibold rounded-lg px-2.5 py-1 outline-none border border-slate-700 cursor-pointer hover:border-cyan-500/50 transition"
>
  <option value="cam_alpha">Room 1 — Main Floor (Alpha)</option>
  <option value="cam_beta">Room 2 — Executive Lounge (Beta)</option>
  <option value="cam_03">Room 3 — Meeting Room A</option>
  <option value="cam_04">Room 4 — Collaboration Hub</option>
</select>
          </div>

          <label className="flex items-center gap-2 bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 text-xs font-semibold px-4 py-2.5 rounded-xl border border-slate-700/80 cursor-pointer transition shadow-lg active:scale-95">
            {isUploading ? <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" /> : <Upload className="w-4 h-4 text-cyan-400" />}
            <span>{isUploading ? "Mengunggah..." : `Upload (${selectedCamera})`}</span>
            <input type="file" accept="video/*" className="hidden" disabled={isUploading} onChange={handleSpecificVideoUpload} />
          </label>

          <button
            onClick={() => setShowCalibrator(true)}
            className="flex items-center gap-2 bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 text-xs font-semibold px-4 py-2.5 rounded-xl border border-slate-700/80 transition shadow-lg active:scale-95"
          >
            <Crosshair className="w-4 h-4 text-emerald-400" />
            <span>Kalibrasi</span>
          </button>

          <button
            onClick={handleSendEmailReport}
            className="flex items-center gap-2 bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 text-xs font-semibold px-4 py-2.5 rounded-xl border border-slate-700/80 transition shadow-lg active:scale-95"
          >
            <Mail className="w-4 h-4 text-amber-400" />
            <span>Kirim Email</span>
          </button>

          <button
            onClick={handleDownloadReport}
            className="flex items-center gap-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-lg shadow-cyan-900/30 transition active:scale-95"
          >
            <Download className="w-4 h-4" />
            <span>Export CSV</span>
          </button>

          <div className="flex items-center gap-2.5 bg-slate-900/90 px-3.5 py-2 rounded-xl border border-slate-800 text-xs ml-auto lg:ml-0">
            <div className={`w-2.5 h-2.5 rounded-full shadow-[0_0_10px_currentColor] ${isConnected ? "bg-emerald-400 text-emerald-400 animate-pulse" : "bg-rose-500 text-rose-500"}`} />
            <span className="text-slate-300 font-medium">{isConnected ? "Live Connected" : "Offline"}</span>
            <span className="text-slate-500 text-[10px] hidden xl:inline">({lastUpdated})</span>
          </div>
        </div>
      </header>

      {/* KPI METRICS CARDS */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="glass-panel glass-panel-hover rounded-2xl p-5 flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl group-hover:bg-cyan-500/10 transition"></div>
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Tingkat Okupansi</span>
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
              <PieIcon className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-3xl md:text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
              {data ? `${data.occupancy_rate_percent}%` : "0%"}
            </div>
            <div className="text-xs text-slate-400 mt-1 flex items-center gap-1.5 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
              Dari {data?.total_stations || 0} stasiun kerja aktif
            </div>
          </div>
        </div>

        <div className="glass-panel glass-panel-hover rounded-2xl p-5 flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl group-hover:bg-emerald-500/10 transition"></div>
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Kabin Terisi</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-3xl md:text-4xl font-extrabold text-emerald-400">
              {data ? data.occupied_count : 0}
            </div>
            <div className="text-xs text-slate-400 mt-1 flex items-center gap-1.5 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Personil terverifikasi
            </div>
          </div>
        </div>

        <div className="glass-panel glass-panel-hover rounded-2xl p-5 flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-amber-500/5 rounded-full blur-xl group-hover:bg-amber-500/10 transition"></div>
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Kabin Kosong</span>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
              <UserX className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-3xl md:text-4xl font-extrabold text-amber-400">
              {data ? data.vacant_count : 0}
            </div>
            <div className="text-xs text-slate-400 mt-1 flex items-center gap-1.5 font-medium">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Siap dialokasikan
            </div>
          </div>
        </div>

        <div className="glass-panel glass-panel-hover rounded-2xl p-5 flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-blue-500/5 rounded-full blur-xl group-hover:bg-blue-500/10 transition"></div>
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Kecepatan Inferensi</span>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-3xl md:text-4xl font-extrabold text-white">
              {data ? `${data.system_fps}` : "0.0"} <span className="text-lg font-medium text-slate-400">FPS</span>
            </div>
            <div className="text-xs text-slate-400 mt-1 flex items-center gap-1.5 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping"></span> Redis 3-Thread Pipeline
            </div>
          </div>
        </div>
      </section>

      {/* ANALYTICS CHARTS SECTION */}
      <section className="mb-6">
       <AnalyticsCharts data={data} selectedCamera={selectedCamera} />
      </section>

      {/* CCTV MULTI-CAMERA SPLIT-SCREEN */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800 shadow-xl">
          <div className="px-5 py-4 border-b border-slate-800/80 flex justify-between items-center bg-slate-900/50">
            <div className="flex items-center gap-2.5">
              <Video className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold text-slate-200 uppercase tracking-widest">Room Alpha — cam_alpha</span>
            </div>
            <span className="text-[11px] font-bold text-cyan-400 bg-cyan-500/10 px-2.5 py-0.5 rounded-full border border-cyan-500/30 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span> LIVE STREAM
            </span>
          </div>
          <div className="relative aspect-video w-full bg-black flex items-center justify-center">
            {isConnected ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={`${BACKEND_URL}/api/v1/stream/video_feed/cam_alpha`} alt="Cam Alpha" className="w-full h-full object-cover" />
            ) : (
              <div className="text-slate-500 text-xs font-medium flex items-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" /> Menghubungkan ke Cam Alpha...
              </div>
            )}
          </div>
        </div>

        <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800 shadow-xl">
          <div className="px-5 py-4 border-b border-slate-800/80 flex justify-between items-center bg-slate-900/50">
            <div className="flex items-center gap-2.5">
              <Video className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold text-slate-200 uppercase tracking-widest">Room Beta — cam_beta</span>
            </div>
            <span className="text-[11px] font-bold text-cyan-400 bg-cyan-500/10 px-2.5 py-0.5 rounded-full border border-cyan-500/30 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span> LIVE STREAM
            </span>
          </div>
          <div className="relative aspect-video w-full bg-black flex items-center justify-center">
            {isConnected ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={`${BACKEND_URL}/api/v1/stream/video_feed/cam_beta`} alt="Cam Beta" className="w-full h-full object-cover" />
            ) : (
              <div className="text-slate-500 text-xs font-medium flex items-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" /> Menghubungkan ke Cam Beta...
              </div>
            )}
          </div>
        </div>
      </section>

      {/* WORKSTATION STATUS MATRIX */}
      <section className="glass-panel rounded-2xl p-6 shadow-xl border border-slate-800">
        <div className="flex justify-between items-center mb-5 pb-3 border-b border-slate-800/80">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-widest text-slate-200">Workstation Status Matrix</h3>
            <p className="text-xs text-slate-400 mt-0.5">Real-time spatial telemetry & ergonomic posture analysis per workstation</p>
          </div>
          <span className="text-xs font-semibold px-3 py-1 rounded-xl bg-slate-800/80 text-cyan-400 border border-slate-700">
            Multi-Camera Grid
          </span>
        </div>
        
        <div className="max-h-[400px] overflow-y-auto pr-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
  {data && data.workstations && Object.keys(data.workstations).length > 0 ? (
    Object.values(data.workstations).map((station: any) => {
      const isOccupied = station.status === "OCCUPIED" || station.state === "OCCUPIED";
      const ergoScore = station.ergonomics?.ergonomic_score ?? 100;
      const postureState = station.ergonomics?.posture_state || "VACANT";
      
      return (
        <div key={station.station_id}
          className={`p-4 rounded-xl border flex flex-col gap-3 transition-all duration-200 ${
            isOccupied 
              ? "bg-cyan-950/20 border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.05)] hover:border-cyan-500/60" 
              : "bg-slate-900/40 border-slate-800/80 hover:border-slate-700"
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`w-2.5 h-2.5 rounded-full ${isOccupied ? "bg-cyan-400 shadow-[0_0_8px_#22d3ee]" : "bg-slate-600"}`} />
              <span className="font-bold text-xs text-slate-200 truncate max-w-[110px]">
                {station.name || station.station_id}
              </span>
            </div>
            <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-md tracking-wider ${
              isOccupied ? "text-cyan-300 bg-cyan-500/15 border border-cyan-500/30" : "text-slate-400 bg-slate-800 border border-slate-700"
            }`}>
              {isOccupied ? "OCC" : "VAC"}
            </span>
          </div>

          <div className="space-y-1.5 text-xs text-slate-400 pt-1 border-t border-slate-800/60">
            <div className="flex justify-between">
              <span className="text-slate-500">Occupant:</span>
              <span className="font-semibold text-slate-300">{station.occupant_id ? `#${station.occupant_id}` : "—"}</span>
            </div>
            {isOccupied && postureState !== "VACANT" && (
              <div className="flex justify-between">
                <span className="text-slate-500">Ergonomics:</span>
                <span className={`font-bold ${ergoScore < 70 ? "text-rose-400" : "text-emerald-400"}`}>
                  {ergoScore}%
                </span>
              </div>
            )}
            <div className="flex items-center justify-between pt-1">
              <span className="flex items-center gap-1 text-slate-500">
                <Clock className="w-3 h-3 text-slate-400" /> Active Dwell:
              </span>
              <span className="font-mono text-cyan-300 font-semibold">{station.duration_seconds || 0}s</span>
            </div>
          </div>
        </div>
      );
    })
  ) : (
    <div className="col-span-full text-center text-slate-500 text-xs py-10">
      Memuat status kabin kerja...
    </div>
  )}
</div>
        </div>
      </section>

      {/* ZONE CALIBRATOR MODAL */}
      {showCalibrator && (
        <ZoneCalibrator
          cameraId={selectedCamera}
          onClose={() => { setShowCalibrator(false); window.location.reload(); }}
        />
      )}
    </main>
  );
}