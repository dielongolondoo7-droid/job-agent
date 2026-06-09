"""
mailer.py — Envía correo diario con las candidatas del día, ordenadas por score
Usa Gmail SMTP con App Password (no OAuth — más simple para GitHub Actions)
"""

import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── CONFIGURACIÓN ──────────────────────────────
GMAIL_USER     = os.environ["GMAIL_USER"]          # 
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASSWORD"]  # App Password de Google
DESTINATARIO   = "neutrondjym@gmail.com"
# ───────────────────────────────────────────────

ESTADO_EMOJI = {
    "🔥 FIT ALTO":  "#d4edda",
    "👍 FIT MEDIO": "#fff3cd",
    "⚠️ FIT BAJO":  "#f8d7da",
}


def build_html(aprobadas: list[dict], fecha: str, nuevas: int) -> str:
    fit_alto  = [j for j in aprobadas if j.get("score", 0) >= 75]
    fit_medio = [j for j in aprobadas if 50 <= j.get("score", 0) < 75]

    def render_tabla(jobs: list[dict]) -> str:
        if not jobs:
            return "<p style='color:#888;font-style:italic;'>Sin ofertas en esta categoría hoy.</p>"
        rows = ""
        for j in jobs:
            color = ESTADO_EMOJI.get(j.get("estado", ""), "#ffffff")
            url = j.get("url", "#")
            link = f'<a href="{url}" style="color:#1a73e8;text-decoration:none;">Ver oferta →</a>' if url != "#" else "—"
            rows += f"""
            <tr style="background:{color}">
                <td style="padding:8px 12px;font-weight:600;">{j.get('score',0)}</td>
                <td style="padding:8px 12px;">{j.get('cargo','')}</td>
                <td style="padding:8px 12px;">{j.get('empresa','')}</td>
                <td style="padding:8px 12px;">{j.get('ciudad','')}</td>
                <td style="padding:8px 12px;">{j.get('salario','') or '—'}</td>
                <td style="padding:8px 12px;">{j.get('modalidad', j.get('contrato','')) or '—'}</td>
                <td style="padding:8px 12px;">{link}</td>
            </tr>"""
        return f"""
        <table width="100%" cellpadding="0" cellspacing="0" 
               style="border-collapse:collapse;font-size:13px;font-family:Arial,sans-serif;">
            <thead>
                <tr style="background:#2c3e50;color:white;">
                    <th style="padding:10px 12px;text-align:left;">Score</th>
                    <th style="padding:10px 12px;text-align:left;">Cargo</th>
                    <th style="padding:10px 12px;text-align:left;">Empresa</th>
                    <th style="padding:10px 12px;text-align:left;">Ciudad</th>
                    <th style="padding:10px 12px;text-align:left;">Salario</th>
                    <th style="padding:10px 12px;text-align:left;">Modalidad</th>
                    <th style="padding:10px 12px;text-align:left;">Enlace</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:20px;">

  <!-- HEADER -->
  <table width="640" align="center" cellpadding="0" cellspacing="0"
         style="background:#2c3e50;border-radius:8px 8px 0 0;">
    <tr>
      <td style="padding:24px 32px;">
        <h1 style="color:white;margin:0;font-size:22px;">📋 Agente de Empleo</h1>
        <p style="color:#aab7c4;margin:6px 0 0;font-size:14px;">
          {fecha} · {nuevas} ofertas nuevas hoy · 
          {len(fit_alto)} FIT ALTO · {len(fit_medio)} FIT MEDIO
        </p>
      </td>
    </tr>
  </table>

  <!-- BODY -->
  <table width="640" align="center" cellpadding="0" cellspacing="0"
         style="background:white;border:1px solid #e0e0e0;border-top:none;">
    <tr><td style="padding:24px 32px;">

      <!-- SECCIÓN FIT ALTO -->
      <h2 style="color:#27ae60;border-bottom:2px solid #27ae60;padding-bottom:8px;
                 font-size:16px;margin-top:0;">
        🔥 FIT ALTO — Score ≥ 75 ({len(fit_alto)} ofertas)
      </h2>
      {render_tabla(fit_alto)}

      <div style="height:24px;"></div>

      <!-- SECCIÓN FIT MEDIO -->
      <h2 style="color:#e67e22;border-bottom:2px solid #e67e22;padding-bottom:8px;
                 font-size:16px;">
        👍 FIT MEDIO — Score 50-74 ({len(fit_medio)} ofertas)
      </h2>
      {render_tabla(fit_medio)}

    </td></tr>
  </table>

  <!-- FOOTER -->
  <table width="640" align="center" cellpadding="0" cellspacing="0"
         style="background:#ecf0f1;border:1px solid #e0e0e0;border-top:none;
                border-radius:0 0 8px 8px;">
    <tr>
      <td style="padding:16px 32px;font-size:12px;color:#7f8c8d;">
        <strong>Criterios de descarte activos:</strong> auxiliares, obra/labor, 
        inglés B2+, especialización excluyente, presencial fuera del radio definido.<br>
        <strong>Portales:</strong> Computrabajo Colombia · El Empleo<br>
        <strong>Radio geográfico:</strong> Armenia · Pereira · Manizales · Ibagué · Remoto Colombia
      </td>
    </tr>
  </table>

</td></tr>
</table>
</body>
</html>"""
    return html


def send_email(aprobadas: list[dict], nuevas: int):
    fecha = datetime.now().strftime("%d/%m/%Y")
    fit_alto_count = sum(1 for j in aprobadas if j.get("score", 0) >= 75)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"[Empleo] {fecha} · {nuevas} nuevas · {fit_alto_count} FIT ALTO"
    )
    msg["From"]    = GMAIL_USER
    msg["To"]      = DESTINATARIO

    # Plain text fallback
    plain = f"Agente de empleo — {fecha}\n"
    plain += f"{nuevas} ofertas nuevas | {fit_alto_count} FIT ALTO\n\n"
    for j in aprobadas[:10]:
        plain += f"[{j['score']}] {j['cargo']} @ {j['empresa']} — {j['ciudad']}\n"
        plain += f"  {j.get('url','')}\n\n"

    html = build_html(aprobadas, fecha, nuevas)

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        server.sendmail(GMAIL_USER, DESTINATARIO, msg.as_string())

    print(f"[INFO] Email enviado a {DESTINATARIO}: {nuevas} nuevas, {fit_alto_count} FIT ALTO")


if __name__ == "__main__":
    with open("jobs_scored.json", encoding="utf-8") as f:
        data = json.load(f)
    with open("write_result.json", encoding="utf-8") as f:
        result = json.load(f)

    send_email(data["aprobadas"], result["nuevas"])
