# Agente de contenido vertical — Okeybot

Agente que genera **2 piezas de contenido por día** (Instagram Reels, TikTok y
YouTube Shorts, formato vertical 9:16) para la firma de consultoría de IA
[okeybot.com](https://okeybot.com).

El flujo es:

```
investigar tendencias  →  idear contenido  →  generar imagen + video  →  borrador con aprobación
   (Reddit, YouTube,        (Claude, en           (Higgsfield:                (Buffer / Ayrshare /
    Twitter/X, RSS/HN)        español)             nano banana pro             cola local)
                                                   + seedance 2.0)
```

> **Regla de oro:** el agente **nunca publica solo**. Siempre deja un *borrador
> pendiente de aprobación*. Vos revisás y aprobás antes de que salga.

---

## Arquitectura

| Módulo | Qué hace |
|---|---|
| `agent/research/` | Agente investigador. Un colector por fuente (Reddit, YouTube, Twitter/X, RSS/Hacker News). Agrega, deduplica, filtra por frescura y rankea. |
| `agent/ideation/` | Convierte las tendencias en ideas de contenido con guion, prompts de imagen/video, caption y hashtags. Usa Claude (con *prompt caching* sobre el contexto de marca). |
| `agent/generation/` | Cliente de Higgsfield. Genera la imagen con **nano banana pro** y el video con **seedance 2.0** (image-to-video, la imagen es el primer frame). |
| `agent/publishing/` | Crea el borrador con aprobación obligatoria. Adaptadores: `local` (default), `buffer`, `ayrshare`. |
| `agent/pipeline.py` | Orquesta todo el flujo. |
| `agent/run.py` | CLI. |
| `config/brand.yaml` | Voz de marca, formato, fuentes a monitorear. **Editá esto para ajustar el contenido.** |

---

## Setup

```bash
cd content-agent
pip install -r requirements.txt
cp .env.example .env      # completá las credenciales que vayas a usar
```

### Probar sin credenciales (dry-run)

Corre el flujo completo con datos simulados, sin gastar crédito ni tocar APIs:

```bash
python -m agent.run --dry-run --pieces 2
```

Los resultados quedan en `output/` (manifest del día + cola de revisión en `output/review_queue/`).

### Correr de verdad

```bash
python -m agent.run            # usa PIECES_PER_RUN del .env (default 2)
```

---

## Credenciales (`.env`)

Cualquier fuente sin credenciales se **omite automáticamente** (no rompe el flujo).

| Variable | Para qué | Cómo obtenerla |
|---|---|---|
| `ANTHROPIC_API_KEY` | Ideación con Claude | console.anthropic.com |
| `HIGGSFIELD_API_KEY` + `HIGGSFIELD_SECRET` | Imagen + video | Dashboard de Higgsfield (API) |
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | Tendencias en Reddit | reddit.com/prefs/apps (app tipo *script*) |
| `YOUTUBE_API_KEY` | Tendencias en YouTube | Google Cloud → YouTube Data API v3 |
| `TWITTER_BEARER_TOKEN` | Tendencias en X (opcional) | developer.twitter.com |
| `PUBLISHER` | `local` \| `buffer` \| `ayrshare` | — |
| `BUFFER_ACCESS_TOKEN` + `BUFFER_PROFILE_IDS` | Publicar borradores en Buffer | buffer.com/developers |
| `AYRSHARE_API_KEY` | Publicar borradores en Ayrshare | ayrshare.com |

### Sobre Higgsfield

La API oficial (`platform.higgsfield.ai`) es asíncrona: se envía el job y se hace
*polling* hasta que termina. El cliente está escrito de forma defensiva, pero
**confirmá en tu dashboard** los nombres exactos de los modelos y endpoints:

- `HIGGSFIELD_IMAGE_MODEL` (default `nano-banana-pro`)
- `HIGGSFIELD_VIDEO_MODEL` (default `seedance2`)

Alternativa sin API keys: el [MCP de Higgsfield](https://higgsfield.ai/mcp)
(`https://mcp.higgsfield.ai/mcp`), que autentica con tu cuenta.

### Sobre la publicación

- **`local`** (default): deja cada pieza como `.md` en `output/review_queue/` para
  revisar a mano. Siempre funciona.
- **`buffer`**: crea el update *sin programar*, así queda en la cola de Buffer
  pendiente de aprobación/publicación manual.
- **`ayrshare`**: postea con `approvalRequired: true` (no sale hasta aprobarlo en
  el panel). Soporta IG, TikTok y YouTube Shorts en un solo POST.

---

## Ejecución automática (GitHub Actions)

El workflow `.github/workflows/daily-content.yml` corre **2 veces por día** (12:00
y 21:00 UTC) y también se puede disparar a mano (`workflow_dispatch`, con opción
de dry-run).

Configurá en el repo (**Settings → Secrets and variables → Actions**):

- **Secrets:** `ANTHROPIC_API_KEY`, `HIGGSFIELD_API_KEY`, `HIGGSFIELD_SECRET`,
  `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `YOUTUBE_API_KEY`,
  `TWITTER_BEARER_TOKEN`, `BUFFER_ACCESS_TOKEN`, `AYRSHARE_API_KEY`
- **Variables:** `PUBLISHER`, `BUFFER_PROFILE_IDS`, `IDEATION_MODEL`,
  `HIGGSFIELD_BASE_URL`, `HIGGSFIELD_IMAGE_MODEL`, `HIGGSFIELD_VIDEO_MODEL`

Los activos generados se suben como artefacto de la corrida.

---

## Tests

```bash
pytest -q
```

Cubren el ranking/deduplicación del investigador, el parseo de la respuesta del
ideador y una corrida dry-run completa del pipeline.

---

## Personalización rápida

Casi todo el comportamiento vive en `config/brand.yaml`: tono de voz, audiencia,
estructura del guion, hashtags base, subreddits, queries de YouTube/Twitter,
feeds RSS y estilo visual de los prompts. Editalo sin tocar código.
