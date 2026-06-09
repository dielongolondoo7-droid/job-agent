"""
scraper.py — Agente de empleo para Diego
Portales: Computrabajo Colombia, El Empleo
Ejecuta en GitHub Actions diariamente ~6am COL (11 UTC)
"""

import httpx
import time
import hashlib
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SEARCH_KEYWORDS = [
    "contador",
    "analista contable",
    "tributario",
    "outsourcing contable",
    "revisoría fiscal",
    "exógena",
]

CIUDADES_COMPUTRABAJO = [
    "armenia-quindio",
    "pereira",
    "manizales",
    "ibague",
    "colombia",  # remoto
]

# ──────────────────────────────────────────────
#  COMPUTRABAJO
# ──────────────────────────────────────────────

def scrape_computrabajo(keyword: str, ciudad: str) -> list[dict]:
    """Scrapea una página de resultados de Computrabajo Colombia."""
    slug = keyword.replace(" ", "-").lower()
    url = f"https://co.computrabajo.com/trabajo-de-{slug}-en-{ciudad}"
    jobs = []
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Computrabajo usa article.box_offer como contenedor de oferta
        ofertas = soup.select("article.box_offer, div.offerBlock")
        if not ofertas:
            # Fallback selector alternativo
            ofertas = soup.select("article[data-id]")

        for oferta in ofertas:
            try:
                titulo_el = oferta.select_one("h2 a, .titleOffer a, h2.title a")
                empresa_el = oferta.select_one(".nameCompany, .company, p.fs16")
                ciudad_el  = oferta.select_one(".location, .city, span[itemprop='addressLocality']")
                salario_el = oferta.select_one(".salary, .salaryTag")
                fecha_el   = oferta.select_one("p.fs13 span, .pubDate, time")
                contrato_el= oferta.select_one(".contractType, .typeJob")
                link_el    = oferta.select_one("h2 a, .titleOffer a")

                if not titulo_el:
                    continue

                href = link_el.get("href", "") if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://co.computrabajo.com" + href

                job = {
                    "portal":    "Computrabajo",
                    "cargo":     titulo_el.get_text(strip=True),
                    "empresa":   empresa_el.get_text(strip=True) if empresa_el else "N/D",
                    "ciudad":    ciudad_el.get_text(strip=True) if ciudad_el else ciudad,
                    "salario":   salario_el.get_text(strip=True) if salario_el else "",
                    "contrato":  contrato_el.get_text(strip=True) if contrato_el else "",
                    "fecha":     fecha_el.get_text(strip=True) if fecha_el else "",
                    "url":       href,
                    "descripcion": oferta.get_text(" ", strip=True)[:800],
                    "fecha_scrape": datetime.now().strftime("%Y-%m-%d"),
                }
                jobs.append(job)
            except Exception:
                continue

    except httpx.HTTPError as e:
        print(f"[WARN] Computrabajo error {keyword}/{ciudad}: {e}")
    except Exception as e:
        print(f"[WARN] Computrabajo parse error {keyword}/{ciudad}: {e}")

    time.sleep(2)  # cortesía al servidor
    return jobs


# ──────────────────────────────────────────────
#  EL EMPLEO
# ──────────────────────────────────────────────

CIUDADES_ELEMPLEO = {
    "armenia":   "117",
    "pereira":   "592",
    "manizales": "441",
    "ibague":    "357",
    "bogota":    "132",  # captura remotos publicados en Bogotá
    "cali":      "149",
}

def scrape_elempleo(keyword: str, ciudad_id: str, ciudad_nombre: str) -> list[dict]:
    """Scrapea ElEmpleo.com para una keyword y ciudad."""
    keyword_enc = keyword.replace(" ", "+")
    url = (
        f"https://www.elempleo.com/co/resultados-busqueda/"
        f"?busqueda={keyword_enc}&idCiudad={ciudad_id}"
    )
    jobs = []
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=25, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        ofertas = soup.select(
            "div.result-item, article.job-item, div[class*='jobOffer'], li.job-listing"
        )

        for oferta in ofertas:
            try:
                titulo_el  = oferta.select_one("h2, h3, .job-title, a.title")
                empresa_el = oferta.select_one(".company-name, .empresa, .company")
                salario_el = oferta.select_one(".salary, .salario")
                fecha_el   = oferta.select_one(".date, .fecha, time")
                link_el    = oferta.select_one("a[href*='/co/oferta-de-empleo/']")
                modalidad_el = oferta.select_one(".modality, .modalidad, .work-mode")

                if not titulo_el:
                    continue

                href = link_el.get("href", "") if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.elempleo.com" + href

                job = {
                    "portal":    "ElEmpleo",
                    "cargo":     titulo_el.get_text(strip=True),
                    "empresa":   empresa_el.get_text(strip=True) if empresa_el else "N/D",
                    "ciudad":    ciudad_nombre,
                    "salario":   salario_el.get_text(strip=True) if salario_el else "",
                    "contrato":  "",
                    "modalidad": modalidad_el.get_text(strip=True) if modalidad_el else "",
                    "fecha":     fecha_el.get_text(strip=True) if fecha_el else "",
                    "url":       href,
                    "descripcion": oferta.get_text(" ", strip=True)[:800],
                    "fecha_scrape": datetime.now().strftime("%Y-%m-%d"),
                }
                jobs.append(job)
            except Exception:
                continue

    except httpx.HTTPError as e:
        print(f"[WARN] ElEmpleo error {keyword}/{ciudad_nombre}: {e}")
    except Exception as e:
        print(f"[WARN] ElEmpleo parse error {keyword}/{ciudad_nombre}: {e}")

    time.sleep(2)
    return jobs


# ──────────────────────────────────────────────
#  RECOLECTOR PRINCIPAL
# ──────────────────────────────────────────────

def collect_all_jobs() -> list[dict]:
    all_jobs = []
    print("[INFO] Iniciando scraping Computrabajo...")
    for keyword in SEARCH_KEYWORDS:
        for ciudad in CIUDADES_COMPUTRABAJO:
            jobs = scrape_computrabajo(keyword, ciudad)
            print(f"  ✓ {keyword} / {ciudad}: {len(jobs)} ofertas")
            all_jobs.extend(jobs)
            time.sleep(1)

    print("[INFO] Iniciando scraping ElEmpleo...")
    for keyword in SEARCH_KEYWORDS:
        for ciudad_nombre, ciudad_id in CIUDADES_ELEMPLEO.items():
            jobs = scrape_elempleo(keyword, ciudad_id, ciudad_nombre)
            print(f"  ✓ {keyword} / {ciudad_nombre}: {len(jobs)} ofertas")
            all_jobs.extend(jobs)
            time.sleep(1)

    print(f"[INFO] Total raw: {len(all_jobs)} ofertas")
    return all_jobs


# ──────────────────────────────────────────────
#  DEDUPLICACIÓN INTERNA (antes de enviar al Sheet)
# ──────────────────────────────────────────────

def dedup_jobs(jobs: list[dict]) -> list[dict]:
    """Elimina duplicados dentro del mismo batch usando hash cargo+empresa."""
    seen = set()
    unique = []
    for job in jobs:
        key = hashlib.sha256(
            f"{job['cargo'].lower()}{job['empresa'].lower()}".encode()
        ).hexdigest()[:12]
        if key not in seen:
            seen.add(key)
            job["_hash"] = key
            unique.append(job)
    print(f"[INFO] Post-dedup interno: {len(unique)} ofertas únicas")
    return unique


if __name__ == "__main__":
    jobs = collect_all_jobs()
    jobs = dedup_jobs(jobs)
    # Guardar para que scorer.py lo consuma
    with open("jobs_raw.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print("[INFO] jobs_raw.json guardado.")
