"""
sheets_writer.py — Escribe ofertas aprobadas en Google Sheets con deduplicación SHA256
Requiere: GOOGLE_SERVICE_ACCOUNT_JSON (secret en GitHub Actions)
"""

import json
import os
import hashlib
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ── CONFIGURACIÓN ──────────────────────────────
SPREADSHEET_ID   = os.environ.get("SPREADSHEET_ID", "")        # ID del Google Sheet
SHEET_NAME       = "Pipeline"                           # Nombre de la pestaña
SHEET_DESCARTE   = "Descartadas"
SERVICE_ACCOUNT  = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")  # JSON completo como secret
# ───────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Columnas del Sheet (orden exacto)
HEADERS = [
    "Fecha",       # A
    "Portal",      # B
    "Empresa",     # C
    "Cargo",       # D
    "Ciudad",      # E
    "Salario",     # F
    "Modalidad",   # G
    "Score",       # H
    "Estado",      # I
    "URL",         # J
    "Aplicado",    # K
    "Fecha_Apl",   # L
    "Hash",        # M — columna oculta para dedup
]


def get_client() -> gspread.Client:
    sa_info = json.loads(SERVICE_ACCOUNT)
    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_sheet(client: gspread.Client, nombre: str) -> gspread.Worksheet:
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    try:
        ws = spreadsheet.worksheet(nombre)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=nombre, rows=2000, cols=len(HEADERS))
        ws.append_row(HEADERS, value_input_option="RAW")
        # Congelar fila 1
        ws.freeze(rows=1)
    return ws


def get_existing_hashes(ws: gspread.Worksheet) -> set[str]:
    """Lee la columna M (Hash) para detectar duplicados contra el Sheet."""
    try:
        hashes = ws.col_values(13)  # columna M = índice 13
        return set(h for h in hashes[1:] if h)  # skip header
    except Exception:
        return set()


def job_to_hash(job: dict) -> str:
    key = f"{job.get('cargo','').lower().strip()}{job.get('empresa','').lower().strip()}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def job_to_row(job: dict, job_hash: str) -> list:
    return [
        job.get("fecha_scrape", datetime.now().strftime("%Y-%m-%d")),
        job.get("portal", ""),
        job.get("empresa", ""),
        job.get("cargo", ""),
        job.get("ciudad", ""),
        job.get("salario", ""),
        job.get("modalidad", job.get("contrato", "")),
        job.get("score", 0),
        job.get("estado", ""),
        job.get("url", ""),
        "No",            # Aplicado
        "",              # Fecha_Apl
        job_hash,        # Hash
    ]


def write_jobs(aprobadas: list[dict], descartadas: list[dict]) -> dict:
    client = get_client()

    # ── Sheet principal: Pipeline ──
    ws_pipeline = get_or_create_sheet(client, SHEET_NAME)
    existing = get_existing_hashes(ws_pipeline)

    nuevas = []
    for job in aprobadas:
        h = job_to_hash(job)
        if h not in existing:
            nuevas.append(job_to_row(job, h))
            existing.add(h)

    if nuevas:
        ws_pipeline.append_rows(nuevas, value_input_option="RAW")
        print(f"[INFO] {len(nuevas)} ofertas nuevas escritas en '{SHEET_NAME}'")
    else:
        print("[INFO] Sin ofertas nuevas — todo ya estaba en el Sheet")

    # ── Sheet descartadas (log de auditoría) ──
    ws_desc = get_or_create_sheet(client, SHEET_DESCARTE)
    existing_desc = get_existing_hashes(ws_desc)
    desc_rows = []
    for job in descartadas:
        h = job_to_hash(job)
        if h not in existing_desc:
            row = job_to_row(job, h)
            row[8] = job.get("razon_descarte", "")  # Columna Estado → razón
            desc_rows.append(row)
    if desc_rows:
        ws_desc.append_rows(desc_rows, value_input_option="RAW")

    return {"nuevas": len(nuevas), "total_aprobadas": len(aprobadas)}


if __name__ == "__main__":
    with open("jobs_scored.json", encoding="utf-8") as f:
        data = json.load(f)

    result = write_jobs(data["aprobadas"], data["descartadas"])
    # Guardar conteo para que mailer lo use
    with open("write_result.json", "w") as f:
        json.dump(result, f)
    print(f"[INFO] Escritura completada: {result}")
