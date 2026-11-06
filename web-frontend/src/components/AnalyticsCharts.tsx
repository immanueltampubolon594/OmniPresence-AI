"use client";

import React from "react";
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, Legend 
} from "recharts";
import { TelemetryData } from "../types/telemetry";
import { BarChart3, PieChart as PieIcon } from "lucide-react";

interface Props {
  data: TelemetryData | null;
  selectedCamera: string; // <-- Tambahan prop untuk mengetahui ruangan aktif
}

export default function AnalyticsCharts({ data, selectedCamera }: Props) {
  if (!data) return null;

  // Format nama ruangan agar ramah dibaca di grafik
  const roomLabel = selectedCamera === "cam_alpha" ? "Room 1" : selectedCamera === "cam_beta" ? "Room 2" : selectedCamera;

  // Siapkan data untuk grafik batang durasi kerja (Dwell-time) dengan menyertakan nama ruangan
  const barData = Object.values(data.workstations).map((station: any) => ({
    name: `${roomLabel} - ${station.name || station.station_id}`,
    duration: station.duration_seconds || 0,
  }));

  // Siapkan data untuk donut chart okupansi
  const pieData = [
    { name: "Terisi (Occupied)", value: data.occupied_count, color: "#06b6d4" },
    { name: "Kosong (Vacant)", value: data.vacant_count, color: "#334155" },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 my-6">
      
      {/* WORKSTATION DWELL-TIME DISTRIBUTION (2 Columns) */}
      <div className="lg:col-span-2 glass-panel rounded-2xl p-5 border border-slate-800 shadow-xl flex flex-col justify-between">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400">
              <BarChart3 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">Workstation Dwell-Time Distribution ({roomLabel})</h3>
              <p className="text-[11px] text-slate-400">Durasi waktu kerja aktif per meja (detik)</p>
            </div>
          </div>
          <span className="text-[10px] font-semibold px-2.5 py-1 rounded-lg bg-slate-800/80 text-cyan-400 border border-cyan-500/30">
            {roomLabel} Active
          </span>
        </div>

        <div className="h-[220px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <XAxis 
                dataKey="name" 
                stroke="#64748b" 
                fontSize={10} 
                tickLine={false} 
                axisLine={{ stroke: '#334155' }} 
              />
              <YAxis 
                stroke="#64748b" 
                fontSize={11} 
                tickLine={false} 
                axisLine={{ stroke: '#334155' }} 
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#0f172a', 
                  borderColor: '#334155', 
                  borderRadius: '12px',
                  color: '#f8fafc',
                  fontSize: '12px',
                  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)'
                }}
                formatter={(value: any) => [`${value} detik`, "Dwell Time"]}
                cursor={{ fill: 'rgba(6, 182, 212, 0.05)' }}
              />
              <Bar 
                dataKey="duration" 
                fill="url(#colorCyan)" 
                radius={[6, 6, 0, 0]} 
              />
              <defs>
                <linearGradient id="colorCyan" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="#0891b2" stopOpacity={0.4} />
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* OCCUPANCY RATIO (1 Column) */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 shadow-xl flex flex-col justify-between">
        <div className="flex justify-between items-center mb-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
              <PieIcon className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">Occupancy Ratio</h3>
              <p className="text-[11px] text-slate-400">Kapasitas {roomLabel}</p>
            </div>
          </div>
        </div>

        <div className="h-[180px] w-full flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                innerRadius={55}
                outerRadius={75}
                paddingAngle={6}
                dataKey="value"
                stroke="none"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#0f172a', 
                  borderColor: '#334155', 
                  borderRadius: '12px',
                  color: '#f8fafc',
                  fontSize: '12px'
                }}
              />
              <Legend 
                verticalAlign="bottom" 
                height={32} 
                formatter={(value) => <span className="text-[11px] text-slate-300 font-medium">{value}</span>}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-2 pt-3 border-t border-slate-800/80 flex justify-between items-center text-xs">
          <span className="text-slate-400 font-medium">Kapasitas Aktif:</span>
          <span className="font-extrabold text-cyan-400 text-sm">{data.occupancy_rate_percent}%</span>
        </div>
      </div>

    </div>
  );
}