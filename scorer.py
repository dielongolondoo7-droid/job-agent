"""
scorer.py — Motor de filtrado y scoring para el agente de empleo de Diego
Score 0-100. Umbral de aplicación automática: >= 75
"""

import re
import json
from typing import Optional


# ──────────────────────────────────────────────
#  CRITERIOS DE DESCARTE (retorna True si debe descartarse)
# ──────────────────────────────────────────────

# Palabras que implican nivel auxiliar/asistente
NIVEL_BAJO = re.compile(
    r"\b(auxiliar|asistente|aprendiz|practicante|pasante|intern|junior\s*contable)\b",
    re.IGNORECASE
)

# Inglés excluyente B2 o superior
INGLES_ALTO = re.compile(
    r"\b(inglés|ingles|english)\b.{0,60}(b2|c1|c2|avanzado|fluido|fluente|fluent|advanced)",
    re.IGNORECASE
)
INGLES_ALTO_INV = re.compile(
    r"\b(b2|c1|c2|avanzado|fluido)\b.{0,30}(inglés|ingles|english)",
    re.IGNORECASE
)

# Especialización excluyente
ESPECIALIZACION_EXCLUYENTE = re.compile(
    r"(especialización|maestría|posgrado|magíster).{0,40}(requerida|obligatoria|excluyente|indispensable|requisito)",
    re.IGNORECASE
)

# Contrato obra/
OBRA_ = re.compile(
    r"\b(obra\s*y?\s*labor|obra\s*o\s*labor|contrato\s*de\s*obra)\b",
    re.IGNORECASE
)

# Cargos que no son contables aunque mencionen "financiero"
CARGO_NO_CONTABLE = re.compile(
    r"^(asesor\s*(comercial|externo|de\s*cobranza|libranza|microcr[eé]dito)|"
    r"ejecutivo\s*comercial|promotor|analista\s*(de\s*)?(fraude|riesgo|trazabilidad|"
    r"pqr|kpi|cartera|cr[eé]dito|cuentas\s*m[eé]dicas|transporte|cobranza)|"
    r"t[eé]cnico\s*de\s*mantenimiento|quickbooks|senior\s*accountant\s*us)\b",
    re.IGNORECASE
)

# Contador Junior — nivel insuficiente para el perfil
CONTADOR_JUNIOR = re.compile(
    r"\b(contador\s*junior|contable\s*junior)\b",
    re.IGNORECASE
)

# Ciudades presenciales que no son el radio objetivo
CIUDADES_PRESENCIAL_FUERA = re.compile(
    r"\b(bogot[aá]|medell[ií]n|barranquilla|cali|bucaramanga|cartagena)\b",
    re.IGNORECASE
)

# Salario muy bajo (detecta salarios explícitos < 3M)
SALARIO_BAJO = re.compile(
    r"\$?\s*([1-2][,.]?\d{3}[,.]?\d{3}|\d{7})\b"  # 1M-2.9M explícito
)

# Ciudades fuera del radio (presencial exigido)
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


def debe_descartar(texto: str, salario_raw: str = "", ciudad: str = "", contrato: str = "", cargo: str = "") -> tuple[bool, str]:
    """
    Retorna (descartar: bool, razon: str)
    Texto debe ser la concatenación de cargo + descripción.
    """
    full = f"{texto} {salario_raw} {ciudad} {contrato}"

    if NIVEL_BAJO.search(texto):
        return True, "Nivel auxiliar/asistente"

    if OBRA_LABOR.search(full):
        return True, "Contrato obra/labor"

    if INGLES_ALTO.search(full) or INGLES_ALTO_INV.search(full):
        return True, "Inglés B2+ excluyente"

    if ESPECIALIZACION_EXCLUYENTE.search(full):
        return True, "Especialización excluyente"

    # Solo descarta por ciudad si menciona presencial Y ciudad fuera del radio Y no menciona remoto
    if (CIUDADES_FUERA_RADIO.search(ciudad) and
            PRESENCIAL_EXCLUYENTE.search(full) and
            not REMOTO_KEYWORDS.search(full)):
        return True, f"Presencial fuera del radio: {ciudad}"

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

    # Cargo que no es rol contable
    if CARGO_NO_CONTABLE.search(job.get("cargo", "") if isinstance(job, dict) else texto):
        return True, "Cargo no contable"

    # Contador Junior
    cargo = job.get("cargo", "") if isinstance(job, dict) else texto
    if CONTADOR_JUNIOR.search(cargo):
        return True, "Contador Junior — nivel bajo"

    # Ciudad "colombia" pero oferta presencial en Bogotá/Medellín
    if (ciudad == "colombia" and
            CIUDADES_PRESENCIAL_FUERA.search(texto) and
            not REMOTO_KEYWORDS.search(texto)):
        return True, "Presencial fuera del radio (sin indicar remoto)"

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
    """
    Retorna score 0-100 basado en perfil de Diego.
    
    Pesos:
      +25  Tributaria colombiana mencionada
      +20  Remoto o eje cafetero
      +20  Salario >= 3.5M explícito (si no se menciona, +10 beneficio de la duda)
      +15  Contrato indefinido
      +10  Sin inglés requerido
      +10  Sin especialización excluyente
      Bonus:
      +5   Revisoría fiscal / auditoría mencionada
      +5   Multiempresa / outsourcing (fit natural con perfil)
    """
    texto = f"{job.get('cargo','')} {job.get('descripcion','')} {job.get('contrato','')}"
    salario_raw = job.get("salario", "")
    ciudad = job.get("ciudad", "")
    score = 0

    # +25: Tributaria
    if TRIBUTARIA.search(texto):
        score += 25

    # +20: Modalidad/ubicación
    if REMOTO_KEYWORDS.search(texto):
        score += 20
    elif EJE_CAFETERO.search(ciudad) or EJE_CAFETERO.search(texto):
        score += 20

    # +20: Salario (si es explícito y >= 3.5M) o +10 si no se menciona
    if SALARIO_ALTO.search(salario_raw):
        score += 20
    elif not salario_raw.strip():
        score += 10  # beneficio de la duda

    # +15: Contrato indefinido
    if CONTRATO_INDEFINIDO.search(texto):
        score += 15

    # +10: Sin inglés requerido
    ingles_mencionado = re.search(r"\b(inglés|ingles|english)\b", texto, re.IGNORECASE)
    if not ingles_mencionado:
        score += 10

    # +10: Sin especialización excluyente (ya filtrado, pero suma si no se menciona en absoluto)
    especializacion_mencionada = re.search(
        r"\b(especialización|maestría|posgrado)\b", texto, re.IGNORECASE
    )
    if not especializacion_mencionada:
        score += 10

    # Bonus +5: Revisoría fiscal / auditoría
    if REVISOR_FISCAL.search(texto):
        score += 5

    # Bonus +5: Outsourcing / multiempresa
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
    """
    Retorna (aprobadas, descartadas)
    Agrega campos: score, estado, razon_descarte
    """
    aprobadas = []
    descartadas = []

    for job in jobs:
        texto = f"{job.get('cargo','')} {job.get('descripcion','')}"
        descarte, razon = debe_descartar(
            texto,
            job.get("salario", ""),
            job.get("ciudad", ""),
            job.get("contrato", ""),
            job.get("cargo", "")   # ← agregar este argumento
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

    # Ordenar por score descendente
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
