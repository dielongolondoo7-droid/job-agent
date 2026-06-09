# SETUP — Agente de Empleo Diego Londoño
**Tiempo estimado: 45 minutos · Costo: $0 · Duración sin intervención: 30+ días**

---

## PASO 1 — Crear el Google Sheet

1. Ve a [sheets.google.com](https://sheets.google.com) → **Nuevo**.
2. Renombra el archivo: `Agente Empleo Diego`.
3. Renombra la pestaña `Hoja1` → `Pipeline`.
4. En fila 1, escribe estas columnas exactamente:
   ```
   A: Fecha | B: Portal | C: Empresa | D: Cargo | E: Ciudad
   F: Salario | G: Modalidad | H: Score | I: Estado | J: URL
   K: Aplicado | L: Fecha_Apl | M: Hash
   ```
5. Copia la URL del Sheet. El ID está entre `/d/` y `/edit`:
   `https://docs.google.com/spreadsheets/d/**ESTE_ES_EL_ID**/edit`
   → Guárdalo, lo necesitas en el Paso 4.

**Formato recomendado:**
- Columna H (Score): Formato > Número
- Columna J (URL): puedes usar `=HYPERLINK(J2,"Ver")` en columna auxiliar
- Congela fila 1: Ver > Fijar > 1 fila

---

## PASO 2 — Crear Service Account de Google

1. Ve a [console.cloud.google.com](https://console.cloud.google.com).
2. **Crear proyecto** → nombre: `agente-empleo`.
3. Menú lateral → **APIs y servicios** → **Biblioteca**.
4. Busca y activa:
   - `Google Sheets API`
   - `Google Drive API`
5. Menú lateral → **APIs y servicios** → **Credenciales**.
6. **+ Crear credenciales** → **Cuenta de servicio**.
   - Nombre: `agente-empleo-bot`
   - Rol: **Editor**
   - Clic en **Crear y continuar** → **Listo**.
7. Clic en la cuenta recién creada → pestaña **Claves** → **Agregar clave** → **JSON**.
8. Descarga el archivo `.json`. Ábrelo — luce así:
   ```json
   {"type": "service_account", "project_id": "...", "private_key": "...", ...}
   ```
   → Copia **todo el contenido** del archivo. Lo usarás en el Paso 4.
9. **Compartir el Sheet:** en el archivo descargado busca `"client_email"`. 
   Copia ese email (termina en `.gserviceaccount.com`).
   Ve a tu Google Sheet → **Compartir** → pega ese email → rol **Editor** → **Enviar**.

---

## PASO 3 — Configurar Gmail App Password

1. Ve a [myaccount.google.com/security](https://myaccount.google.com/security).
2. Activa **Verificación en dos pasos** si no está activa.
3. En la barra de búsqueda de la página, escribe: `contraseñas de aplicación`.
4. Nombre de la app: `agente-empleo` → **Crear**.
5. Google te muestra una contraseña de 16 caracteres (ej: `abcd efgh ijkl mnop`).
   → Cópiala **sin espacios**: `abcdefghijklmnop`.
   → Guárdala, solo se muestra una vez.

---

## PASO 4 — Crear el repositorio en GitHub

1. Ve a [github.com](https://github.com) → **New repository**.
   - Nombre: `job-agent`
   - **Public** ✅ (para que GitHub Actions sea 100% gratis)
   - Inicializar con README: ✅
2. Sube estos archivos al repo (drag & drop o `git push`):
   ```
   scraper.py
   scorer.py
   sheets_writer.py
   mailer.py
   requirements.txt
   .github/workflows/job_agent.yml
   ```
3. **Agregar Secrets:** Settings → Secrets and variables → Actions → **New repository secret**.
   
   Crea estos 4 secrets exactamente con estos nombres:

   | Secret name | Valor |
   |---|---|
   | `SPREADSHEET_ID` | El ID del Sheet del Paso 1 |
   | `GOOGLE_SERVICE_ACCOUNT_JSON` | Todo el contenido del JSON del Paso 2 |
   | `GMAIL_USER` | `dielongo.londoo7@gmail.com` |
   | `GMAIL_APP_PASSWORD` | La contraseña de 16 chars del Paso 3 |

---

## PASO 5 — Primer test manual

1. En GitHub, ve a tu repo → **Actions** → `Agente de Empleo — Diego Londoño`.
2. Clic en **Run workflow** → **Run workflow** (botón verde).
3. Espera ~10 minutos.
4. Si aparece ✅ verde: revisa tu email y el Google Sheet.
5. Si aparece ❌ rojo: clic en el job fallido → busca el paso con error → el mensaje es explícito.

**Errores comunes:**
- `Authentication error`: verifica que compartiste el Sheet con el email del service account.
- `SPREADSHEET_ID not found`: verifica que el ID del Sheet sea correcto.
- `Username and Password not accepted (Gmail)`: la App Password tiene espacios; elimínalos.

---

## PASO 6 — Verificar ejecución automática

El workflow corre todos los días a las **10:30 UTC = 05:30 COL**.
El email debe llegar antes de las 7am COL.

Para verificar: Actions → ve al historial de ejecuciones después del día siguiente al setup.

---

## PASO 7 — Ajustes opcionales post-setup

**Cambiar horario:** en `job_agent.yml` modifica la línea cron:
- `"30 10 * * *"` = 5:30am COL (recomendado)
- `"0 11 * * *"` = 6:00am COL
- `"0 12 * * *"` = 7:00am COL

**Agregar keywords:** en `scraper.py`, agrega a la lista `SEARCH_KEYWORDS`.

**Cambiar umbral de scoring:** en `scorer.py`, modifica la constante en `clasificar_estado()`.

**Ver ofertas descartadas:** están en la pestaña `Descartadas` del Sheet con la razón de descarte.

---

## PLAN DE MANTENIMIENTO MENSUAL (~20 min)

**Semana 1 de cada mes:**

1. ✅ Revisar en GitHub Actions si hubo ejecuciones fallidas el mes anterior.
2. ✅ Verificar que el Sheet no tenga duplicados visibles (columna M = Hash previene esto automáticamente).
3. ✅ Si el scraping de un portal retornó 0 ofertas consistentemente, revisar si el portal cambió su HTML (corre el script localmente y verifica el log).
4. ✅ Opcional: revisar la pestaña `Descartadas` para calibrar si el filtro está siendo demasiado agresivo.
5. ✅ Marcar como `Sí` en columna K (Aplicado) las ofertas a las que ya aplicaste, con fecha en columna L.

**Cada 3 meses:**
- Actualizar selectores CSS en `scraper.py` si los portales cambian su diseño.
- Revisar si Computrabajo o El Empleo bloquearon el User-Agent (en ese caso, rotar el string en `HEADERS`).

---

## ESTRUCTURA FINAL DEL REPO

```
job-agent/
├── .github/
│   └── workflows/
│       └── job_agent.yml      ← Scheduler y orquestación
├── scraper.py                 ← Scraping Computrabajo + El Empleo
├── scorer.py                  ← Filtros de descarte + scoring 0-100
├── sheets_writer.py           ← Escritura en Google Sheets con dedup
├── mailer.py                  ← Email HTML diario
├── requirements.txt           ← Dependencias Python
└── README.md
```

---

## COSTOS FINALES

| Componente | Plan | Costo mensual |
|---|---|---|
| GitHub Actions | Free (repo público) | $0 |
| Google Sheets | Google Account | $0 |
| Gmail SMTP | Google Account | $0 |
| Apify / n8n | No se usa | $0 |
| VPS / servidor | No se usa | $0 |
| **TOTAL** | | **$0** |
