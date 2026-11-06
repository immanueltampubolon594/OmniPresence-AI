from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.services.notification_service import notification_service

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications & Reports"])

class EmailRequest(BaseModel):
    recipient: str

@router.post("/send-report-email")
def send_report_email(req: EmailRequest):
    """Endpoint untuk mengirimkan Executive PDF Report langsung ke Gmail target"""
    success = notification_service.send_email_alert(
        recipient_email=req.recipient,
        subject="[OMNIPRESENCE-AI] Automated Executive Workplace Audit Report",
        body="Halo,\n\nTerlampir adalah Laporan Audit Okupansi Ruangan & Ergonomi Pekerja otomatis dari sistem OmniPresence-Platform Enterprise VMS.\n\nSalam,\nAI Surveillance System",
        attach_pdf=True
    )
    if not success:
        raise HTTPException(status_code=500, detail="Gagal mengirim email. Periksa konfigurasi SMTP Gmail.")
    return {"status": "success", "message": f"Laporan PDF berhasil dikirim ke {req.recipient}!"}