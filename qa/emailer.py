"""Stage 7: send the HTML report via SMTP (Mailpit by default)."""
import smtplib
from email.message import EmailMessage


def send_report(cfg: dict, run) -> str:
    c = cfg["email"]
    s = run.read_json("summary.json")
    body = run.path("report.html").read_text(encoding="utf-8")
    msg = EmailMessage()
    msg["From"], msg["To"] = c["from"], c["to"]
    msg["Subject"] = f"[QA] {s['verdict']} - {s['totals']['passed']}/{s['totals']['total']} passed ({s['run_id']})"
    msg.set_content(f"Release verdict: {s['verdict']}. Open the HTML report for details.")
    msg.add_alternative(body, subtype="html")
    msg.add_attachment(body.encode("utf-8"), maintype="text", subtype="html", filename="report.html")
    with smtplib.SMTP(c["smtp_host"], c["smtp_port"], timeout=20) as smtp:
        if c.get("tls"):
            smtp.starttls()
        smtp.send_message(msg)
    return c.get("inbox_url", "")
