"""
scorer.py — Motor de filtrado y scoring para el agente de empleo de Diego Londoño
Score 0-100. Umbral de aplicación automática: >= 75
"""

import re
import json
from typing import Optional


# ──────────────────────────────────────────────
#  CRITERIOS DE DESCARTE
# ──────────────────────────────────────────────

NIVEL_BAJO = re.compile(
    r"\b(auxiliar|asistente|aprendiz|practicante|pasante|intern|junior\s*contable)\b",
    re.IGNORECASE
)

CONTADOR_JUNIOR = re.compile(
    r"\b(contador\s*junior|contable\s*junior)\b",
    re.IGNORECASE
)

INGLES_ALTO = re.compile(
    r"\b(inglés|ingles|english)\b.{0,60}(b2|c1|c2|avanzado|fluido|fluente|fluent|advanced)",
    re.IGNORECASE
)
INGLES_ALTO_INV = re.compile(
    r"\b(b2|c1|c2|avanzado|fluido)\b.{0,30}(inglés|ingles|english)",
    re.IGNORECASE
)

ESPECIALIZACION_EXCLUYENTE = re.compile(
    r"(especialización|maestría|posgrado|magíster).{0,40}(requerida|obligatoria|excluyente|indispensable|requisito)",
    re.IGNORECASE
)

OBRA_LABOR = re.compile(
    r"\b(obra\s*y?\s*labor|obra\s*o\s*labor|contrato\s*de\s*obra)\b",
    re.IGNORECASE
)

SALARIO_BAJO = re.compile(
    r"\$?\s*([1-2][,.]?\d{3}[,.]?\d{3}|\d{7})\b"
)

CIUDADES_FUERA_RADIO = re.compile(
    r"\b(bogotá|bogota|medellín|medellin|cali|barranquilla|cartagena|bucaramanga|"
    r"santa marta|cúcuta|cucuta|villavicencio|pasto|neiva|montería|sincelejo)\b",
    re.IGNORECASE
)

PRESENCIAL_EXCLUYENTE = re.compile(
    r"\b(presencial|on-?site|en sitio)\b",
    re.IGNORECASE
)

REMOTO_KEYWORDS = re.compile(
    r"\b(remoto|remote|teletrabajo|trabajo\s*desde\s*casa|home\s*office|híbrido|hibrido|virtual)\b",
    re.IGNORECASE
)

EJE_CAFETERO = re.compile(
    r"\b(armenia|pereira|manizales|dosquebradas|ibagué|ibague|quindío|quindio|risaralda|caldas|tolima)\b",
    re.IGNORECASE
)

# Cargos que no son roles contables aunque mencionen "financiero"
CARGO_NO_CONTABLE = re.compile(
    r"^(asesor\s*(comercial|externo|de\s*cobranza|libranza|microcr[eé]dito)|"
    r"ejecutivo\s*comercial|promotor|analista\s*(de\s*)?(fraude|riesgo|trazabilidad|"
    r"pqr|kpi|cartera|cr[eé]dito|cuentas\s*m[eé]dicas|transporte|cobranza|nomina|nómina)|"
    r"t[eé]cnico\s*de\s*mantenimiento|quickbooks\s*senior|senior\s*accountant\s*us|"
    r"assistant\s*manager\s*accounting)\b",
    re.IGNORECASE
)

# Ciudades presenciales fuera del radio cuando ciudad="colombia"
CIUDADES_PRESENCIAL_FUERA = re.compile(
    r"\b(bogot[aá]|medell[ií]n|barranquilla|cali|bucaramanga|cartagena)\b",
    re.IGNORECASE
)


def debe_descartar(texto: str, salario_raw: str = "", ciudad: str = "",
                   contrato: str = "", cargo: str = "") -> tuple[bool, str]:
    """
    Retorna (descartar: bool, razon: str)
    texto = cargo + descripcion concatenados
    cargo = campo cargo por separado para filtros exactos
    """
    full = f"{texto} {salario_raw} {ciudad} {contrato}"

    # Cargo no contable (evalúa solo el título del cargo)
    if CARGO_NO_CONTABLE.search(cargo):
        return True, "Cargo no contable"

    # Nivel bajo
    if NIVEL_BAJO.search(texto):
        return True, "Nivel auxiliar/asistente"

    # Contador Junior
    if CONTADOR_JUNIOR.search(cargo):
        return True, "Contador Junior — nivel bajo"

    # Obra/labor
    if OBRA_LABOR.search(full):
        return True, "Contrato obra/labor"

    # Inglés B2+
    if INGLES_ALTO.search(full) or INGLES_ALTO_INV.search(full):
        return True, "Inglés B2+ excluyente"

    # Especialización excluyente
    if ESPECIALIZACION_EXCLUYENTE.search(full):
        return True, "Especialización excluyente"

    # Presencial fuera del radio geográfico
    if (CIUDADES_FUERA_RADIO.search(ciudad) and
            PRESENCIAL_EXCLUYENTE.search(full) and
            not REMOTO_KEYWORDS.search(full)):
        return True, f"Presencial fuera del radio: {ciudad}"

    # Ciudad "colombia" pero oferta presencial en Bogotá/Medellín sin indicar remoto
    if (ciudad == "colombia" and
            CIUDADES_PRESENCIAL_FUERA.search(texto) and
            not REMOTO_KEYWORDS.search(texto)):
        return True, "Presencial fuera del radio (sin remoto)"

    # Salario explícito bajo
    salario_match = SALARIO_BAJO.search(salario_raw)
    if salario_match:
        raw = re.sub(r"[,\.]", "", salario_match.group(1))
        try:
            valor = int(raw)
            if valor < 3_000_000:
                return True, f"Salario explícito < $3M: ${valor:,}"
        except ValueError:
            pass

    return False, ""


# ──────────────────────────────────────────────
#  SCORING (0-100)
# ──────────────────────────────────────────────

TRIBUTARIA = re.compile(
    r"\b(tributari|iva|retención|retencion|ica|exógena|exogena|dian|impuesto|fiscal|"
    r"declaración de renta|información exógena|renta)\b",
    re.IGNORECASE
)

CONTRATO_INDEFINIDO = re.compile(
    r"\b(indefinido|término indefinido|termino indefinido|fijo largo|permanent)\b",
    re.IGNORECASE
)

SALARIO_ALTO = re.compile(
    r"\$?\s*(3[,\.]?[5-9]\d{2}[,\.]?\d{3}|[4-9][,\.]?\d{3}[,\.]?\d{3})",
    re.IGNORECASE
)

REVISOR_FISCAL = re.compile(
    r"\b(revisor.{0,5}fiscal|auditor.{0,5}interno|auditoría)\b",
    re.IGNORECASE
)

MULTIEMPRESA = re.compile(
    r"\b(outsourcing|multiempresa|varias empresas|clientes|portafolio de empresas|"
    r"firma contable|firma de contadores)\b",
    re.IGNORECASE
)


def score_oferta(job: dict) -> int:
    texto = f"{job.get('cargo','')} {job.get('descripcion','')} {job.get('contrato','')}"
    salario_raw = job.get("salario", "")
    ciudad = job.get("ciudad", "")
    score = 0

    if TRIBUTARIA.search(texto):
        score += 25

    if REMOTO_KEYWORDS.search(texto):
        score += 20
    elif EJE_CAFETERO.search(ciudad) or EJE_CAFETERO.search(texto):
        score += 20

    if SALARIO_ALTO.search(salario_raw):
        score += 20
    elif not salario_raw.strip():
        score += 10

    if CONTRATO_INDEFINIDO.search(texto):
        score += 15

    ingles_mencionado = re.search(r"\b(inglés|ingles|english)\b", texto, re.IGNORECASE)
    if not ingles_mencionado:
        score += 10

    especializacion_mencionada = re.search(
        r"\b(especialización|maestría|posgrado)\b", texto, re.IGNORECASE
    )
    if not especializacion_mencionada:
        score += 10

    if REVISOR_FISCAL.search(texto):
        score += 5

    if MULTIEMPRESA.search(texto):
        score += 5

    return min(score, 100)


def clasificar_estado(score: int) -> str:
    if score >= 75:
        return "🔥 FIT ALTO"
    elif score >= 50:
        return "👍 FIT MEDIO"
    else:
        return "⚠️ FIT BAJO"


# ──────────────────────────────────────────────
#  PIPELINE COMPLETO
# ──────────────────────────────────────────────

def procesar_jobs(jobs: list[dict]) -> tuple[list[dict], list[dict]]:
    aprobadas = []
    descartadas = []

    for job in jobs:
        cargo = job.get("cargo", "")
        texto = f"{cargo} {job.get('descripcion','')}"
        descarte, razon = debe_descartar(
            texto,
            job.get("salario", ""),
            job.get("ciudad", ""),
            job.get("contrato", ""),
            cargo
        )

        if descarte:
            job["score"] = 0
            job["estado"] = "❌ DESCARTADA"
            job["razon_descarte"] = razon
            descartadas.append(job)
        else:
            job["score"] = score_oferta(job)
            job["estado"] = clasificar_estado(job["score"])
            job["razon_descarte"] = ""
            aprobadas.append(job)

    aprobadas.sort(key=lambda x: x["score"], reverse=True)
    return aprobadas, descartadas


if __name__ == "__main__":
    with open("jobs_raw.json", encoding="utf-8") as f:
        jobs = json.load(f)

    aprobadas, descartadas = procesar_jobs(jobs)

    print(f"\n{'='*50}")
    print(f"RESULTADOS: {len(aprobadas)} aprobadas | {len(descartadas)} descartadas")
    print(f"FIT ALTO (>=75): {sum(1 for j in aprobadas if j['score'] >= 75)}")
    print(f"{'='*50}\n")

    for job in aprobadas[:5]:
        print(f"[{job['score']}] {job['cargo']} @ {job['empresa']} — {job['ciudad']}")

    with open("jobs_scored.json", "w", encoding="utf-8") as f:
        json.dump({"aprobadas": aprobadas, "descartadas": descartadas}, f,
                  ensure_ascii=False, indent=2)
    print("\n[INFO] jobs_scored.json guardado.")
