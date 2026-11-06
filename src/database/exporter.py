"""
OmniPresence-AI: Audit Report Exporter
Deskripsi: Otomasi rekapitulasi data okupansi meja ke format CSV/Excel.
"""

import os
import csv
from datetime import datetime
from typing import Dict, Any


class TelemetryReportExporter:
    @staticmethod
    def export_session_summary(report_data: Dict[str, Dict[str, float]], output_dir: str = "reports") -> str:
        """
        Menyimpan ringkasan okupansi tiap meja ke file CSV berstempel waktu (timestamped).
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(output_dir, f"occupancy_audit_report_{timestamp}.csv")

        headers = [
            "Nama Meja (Cabin)",
            "Total Waktu Terisi (Detik)",
            "Total Waktu Kosong (Detik)",
            "Tingkat Utilisasi (%)",
            "Status Akhir"
        ]

        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["=== LAPORAN OKUPANSI RUANG KERJA (OMNIPRESENCE-AI) ==="])
            writer.writerow([f"Waktu Cetak: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            writer.writerow([])
            writer.writerow(headers)

            for station_name, metrics in report_data.items():
                occ_time = metrics.get("total_occupied", 0.0)
                vac_time = metrics.get("total_vacant", 0.0)
                total_time = occ_time + vac_time

                utilization = (occ_time / total_time * 100) if total_time > 0 else 0.0
                last_state = metrics.get("last_state", "UNKNOWN")

                writer.writerow([
                    station_name,
                    f"{occ_time:.1f}",
                    f"{vac_time:.1f}",
                    f"{utilization:.1f}%",
                    last_state
                ])

        return file_path