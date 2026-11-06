import smtplib
import os
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from src.services.audit_logger import audit_logger


class NotificationService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "immanueltampubolon594@gmail.com"
        self.sender_password = "zhzveeqxeztksysr"

    def generate_pdf_report(self, output_path: str = "reports/Executive_Audit_Report.pdf") -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            output_path, 
            pagesize=letter,
            rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=40
        )
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=6
        )
        story.append(Paragraph("OmniPresence-AI: Executive Workplace Audit Report", title_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-System Enterprise VMS", styles['Normal']))
        story.append(Spacer(1, 15))

        incidents = audit_logger.get_recent_incidents(limit=15)

        cell_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1e293b")
        )
        
        header_style = ParagraphStyle(
            'HeaderCellText',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            fontName='Helvetica-Bold',
            textColor=colors.whitesmoke,
            alignment=1
        )

        data = [[
            Paragraph("Timestamp", header_style),
            Paragraph("Camera", header_style),
            Paragraph("Station", header_style),
            Paragraph("Event Type", header_style),
            Paragraph("Severity", header_style),
            Paragraph("Description", header_style)
        ]]

        if not incidents:
            data.append([
                Paragraph("-", cell_style),
                Paragraph("-", cell_style),
                Paragraph("-", cell_style),
                Paragraph("NO_INCIDENTS", cell_style),
                Paragraph("INFO", cell_style),
                Paragraph("No ergonomic hazards recorded yet.", cell_style)
            ])
        else:
            for inc in incidents:
                data.append([
                    Paragraph(str(inc["timestamp"]), cell_style),
                    Paragraph(str(inc["camera_id"]), cell_style),
                    Paragraph(str(inc["station_id"]), cell_style),
                    Paragraph(str(inc["event_type"]), cell_style),
                    Paragraph(str(inc["severity"]), cell_style),
                    Paragraph(str(inc["description"]), cell_style)
                ])

        t = Table(data, colWidths=[95, 55, 50, 105, 55, 192])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))

        story.append(t)
        doc.build(story)
        return output_path

    def _build_html_email(self, incident_count: int, generated_at: str) -> str:
        return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f1f5f9;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
          <tr>
            <td style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);padding:32px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <p style="margin:0;color:#38bdf8;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;">ENTERPRISE AI SURVEILLANCE</p>
                    <h1 style="margin:8px 0 0;color:#ffffff;font-size:24px;font-weight:800;letter-spacing:-0.5px;">OmniPresence-AI</h1>
                    <p style="margin:4px 0 0;color:#94a3b8;font-size:13px;">Workplace Spatial Intelligence Platform</p>
                  </td>
                  <td align="right">
                    <div style="background:rgba(56,189,248,0.15);border:1px solid rgba(56,189,248,0.3);border-radius:8px;padding:10px 16px;display:inline-block;">
                      <p style="margin:0;color:#38bdf8;font-size:11px;font-weight:700;text-transform:uppercase;">AUTO REPORT</p>
                      <p style="margin:4px 0 0;color:#ffffff;font-size:13px;font-weight:600;">{generated_at}</p>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background:#fef3c7;border-left:4px solid #f59e0b;padding:16px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="32" valign="middle"><span style="font-size:20px;">⚠️</span></td>
                  <td style="padding-left:12px;">
                    <p style="margin:0;color:#92400e;font-size:13px;font-weight:700;">Automated Ergonomic Audit Report</p>
                    <p style="margin:4px 0 0;color:#b45309;font-size:12px;">
                      Sistem mendeteksi <strong>{incident_count} insiden ergonomi</strong> yang memerlukan perhatian manajemen.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 40px;">
              <p style="margin:0 0 16px;color:#334155;font-size:14px;line-height:1.6;">Yth. Tim Manajemen,</p>
              <p style="margin:0 0 24px;color:#475569;font-size:14px;line-height:1.6;">
                Sistem <strong>OmniPresence-AI Enterprise VMS</strong> secara otomatis telah menyelesaikan siklus audit berkala terhadap kondisi ergonomi dan tingkat okupansi ruang kerja. Laporan lengkap dalam format PDF terlampir pada email ini.
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                <tr>
                  <td width="33%" style="padding-right:8px;">
                    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px;text-align:center;">
                      <p style="margin:0;color:#16a34a;font-size:22px;font-weight:800;">{incident_count}</p>
                      <p style="margin:4px 0 0;color:#15803d;font-size:11px;font-weight:600;text-transform:uppercase;">Insiden Tercatat</p>
                    </div>
                  </td>
                  <td width="33%" style="padding:0 4px;">
                    <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:16px;text-align:center;">
                      <p style="margin:0;color:#1d4ed8;font-size:22px;font-weight:800;">AUTO</p>
                      <p style="margin:4px 0 0;color:#1e40af;font-size:11px;font-weight:600;text-transform:uppercase;">Mode Audit</p>
                    </div>
                  </td>
                  <td width="33%" style="padding-left:8px;">
                    <div style="background:#fdf4ff;border:1px solid #e9d5ff;border-radius:8px;padding:16px;text-align:center;">
                      <p style="margin:0;color:#7e22ce;font-size:22px;font-weight:800;">PDF</p>
                      <p style="margin:4px 0 0;color:#6b21a8;font-size:11px;font-weight:600;text-transform:uppercase;">Format Laporan</p>
                    </div>
                  </td>
                </tr>
              </table>
              <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin-bottom:24px;">
                <p style="margin:0;color:#64748b;font-size:12px;line-height:1.6;">
                  📎 <strong>Lampiran:</strong> Executive_Audit_Report.pdf<br>
                  🕐 <strong>Dibuat:</strong> {generated_at}<br>
                  🤖 <strong>Sumber:</strong> OmniPresence-AI Enterprise VMS v2.0
                </p>
              </div>
              <p style="margin:0;color:#475569;font-size:14px;line-height:1.6;">
                Hormat kami,<br>
                <strong style="color:#0f172a;">OmniPresence-AI Automated System</strong>
              </p>
            </td>
          </tr>
          <tr>
            <td style="background:#0f172a;padding:20px 40px;">
              <p style="margin:0;color:#475569;font-size:11px;">© 2026 OmniPresence-AI Enterprise VMS. Confidential.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    def send_email_alert(self, recipient_email: str, subject: str, body: str, attach_pdf: bool = True):
        try:
            generated_at = datetime.now().strftime("%d %B %Y, %H:%M WIB")
            incidents = audit_logger.get_recent_incidents(limit=15)
            incident_count = len(incidents) if incidents else 0

            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = "OmniPresence-AI VMS <immanueltampubolon594@gmail.com>"
            msg["To"] = recipient_email

            html_body = self._build_html_email(incident_count, generated_at)
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            if attach_pdf:
                pdf_path = self.generate_pdf_report()
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()
                pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
                pdf_attachment.add_header("Content-Disposition", "attachment", filename=Path(pdf_path).name)
                msg.attach(pdf_attachment)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, msg.as_string())

            print(f"[NOTIFICATION] Email HTML berhasil dikirim ke {recipient_email}")
            return True

        except Exception as e:
            print(f"[NOTIFICATION ERROR] Gagal mengirim email: {e}")
            return False


# Global Instance
notification_service = NotificationService()