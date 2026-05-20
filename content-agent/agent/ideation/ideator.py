"""Convierte tendencias en ideas de contenido usando Claude.

Usa el SDK de Anthropic con prompt caching sobre el bloque de contexto de
marca (estatico entre runs), de modo que generar 2 piezas reutilice el cache.
"""

from __future__ import annotations

import json
import logging
import re

from ..config import Settings
from ..models import ContentIdea, StoryboardFrame, TrendItem

log = logging.getLogger("agent.ideation")


def _brand_system_block(settings: Settings) -> str:
    b = settings.brand_cfg
    c = settings.content_cfg
    tone = "\n".join(f"- {t}" for t in b.get("tone", []))
    structure = "\n".join(f"- {s}" for s in c.get("script_structure", []))
    return f"""Sos el estratega de contenido de {b.get('name', 'la marca')}, una firma de \
consultoria de inteligencia artificial ({b.get('website', '')}).

SOBRE LA MARCA:
{b.get('description', '')}

AUDIENCIA:
{b.get('audience', '')}

TONO DE VOZ:
{tone}

FORMATO DE LAS PIEZAS:
- Plataformas: {', '.join(c.get('platforms', []))}
- Formato vertical {c.get('aspect_ratio', '9:16')}, video de {c.get('video_duration_seconds', 10)}s.
- Estructura del guion (voz en off, en {b.get('language', 'es')}):
{structure}

ESTILO VISUAL (para los prompts de imagen/video):
{c.get('visual_style', '')}

OBJETIVO: contenido educativo de IA aplicada al negocio, gancho honesto, \
siempre con un "que podes hacer con esto". CTA: {b.get('cta', '')}."""


def _user_prompt(trends: list[TrendItem], n: int, hashtags_base: list[str]) -> str:
    lines = []
    for i, t in enumerate(trends, 1):
        lines.append(
            f"{i}. [{t.source}] {t.title}\n   {t.summary[:300]}\n   fuente: {t.url}"
        )
    trends_block = "\n".join(lines)
    return f"""Estas son las tendencias de IA detectadas hoy (rankeadas):

{trends_block}

Elegi los {n} temas con mayor potencial para nuestra audiencia y crea {n} \
ideas de contenido para short-form vertical (~10 segundos).

Para cada idea pensa un STORYBOARD de frames clave que se generaran con un \
modelo de imagen (nano banana pro) y luego se animaran con un modelo de video \
(seedance). Decidi el `frame_mode`:
- "first": el video arranca desde una imagen (definis solo el primer frame).
- "last": el video termina en una imagen (definis solo el ultimo frame).
- "both": definis primer Y ultimo frame, el video interpola entre ambos (mejor control).

Devolve EXCLUSIVAMENTE un JSON valido con esta forma (sin texto extra, sin markdown):

{{
  "ideas": [
    {{
      "title": "titulo interno corto",
      "hook": "primera frase que corta el scroll (max 12 palabras)",
      "script": "guion completo de voz en off siguiendo la estructura, ~25-40 palabras",
      "caption": "caption en espanol para el post, 1-3 frases con gancho",
      "hashtags": ["#tag1", "#tag2"],
      "based_on": ["url de la/las fuentes usadas"],
      "frame_mode": "first | last | both",
      "video_prompt": "prompt en INGLES describiendo el movimiento/camara/animacion de 10s (seedance)",
      "first_frame": {{"description": "que muestra esta escena (espanol)", "prompt": "prompt nano banana en INGLES, vertical 9:16, detallado"}},
      "last_frame": {{"description": "que muestra esta escena (espanol)", "prompt": "prompt nano banana en INGLES, vertical 9:16, detallado"}}
    }}
  ]
}}

Reglas: incluI `first_frame` solo si frame_mode es "first" o "both"; incluI \
`last_frame` solo si es "last" o "both". Incluye estos hashtags base ademas de \
los especificos: {', '.join(hashtags_base)}."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    # quita posibles fences de markdown
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No se encontro JSON en la respuesta: {text[:200]}")
    return json.loads(text[start : end + 1])


def _build_storyboard(raw: dict) -> tuple[str, list[StoryboardFrame]]:
    mode = (raw.get("frame_mode") or "first").strip().lower()
    if mode not in {"first", "last", "both"}:
        mode = "first"
    frames: list[StoryboardFrame] = []
    if mode in {"first", "both"} and raw.get("first_frame"):
        ff = raw["first_frame"]
        frames.append(
            StoryboardFrame(
                role="first",
                description=ff.get("description", "").strip(),
                prompt=ff.get("prompt", "").strip(),
            )
        )
    if mode in {"last", "both"} and raw.get("last_frame"):
        lf = raw["last_frame"]
        frames.append(
            StoryboardFrame(
                role="last",
                description=lf.get("description", "").strip(),
                prompt=lf.get("prompt", "").strip(),
            )
        )
    return mode, frames


def _to_ideas(payload: dict, hashtags_base: list[str]) -> list[ContentIdea]:
    ideas = []
    for raw in payload.get("ideas", []):
        tags = list(dict.fromkeys(hashtags_base + raw.get("hashtags", [])))
        mode, frames = _build_storyboard(raw)
        ideas.append(
            ContentIdea(
                title=raw.get("title", "").strip(),
                hook=raw.get("hook", "").strip(),
                script=raw.get("script", "").strip(),
                caption=raw.get("caption", "").strip(),
                video_prompt=raw.get("video_prompt", "").strip(),
                frame_mode=mode,
                storyboard=frames,
                hashtags=tags,
                based_on=raw.get("based_on", []),
            )
        )
    return ideas


def _mock_ideas(trends: list[TrendItem], n: int, hashtags_base: list[str]) -> list[ContentIdea]:
    out = []
    for t in trends[:n]:
        out.append(
            ContentIdea(
                title=f"[MOCK] {t.title[:40]}",
                hook="Esto cambia como trabajas con IA.",
                script=(
                    f"{t.title}. Te explico en 10 segundos que significa para tu "
                    "negocio y como aplicarlo hoy mismo. Segui a Okeybot."
                ),
                caption=f"{t.title} — que significa para tu negocio. ",
                video_prompt=(
                    "Smooth cinematic push-in from the opening frame, subtle particle "
                    "motion, soft light shift, resolving into the closing frame, 10s, vertical"
                ),
                frame_mode="both",
                storyboard=[
                    StoryboardFrame(
                        role="first",
                        description="Apertura: gancho visual del tema",
                        prompt=(
                            "Vertical 9:16, modern clean tech aesthetic, vibrant accent "
                            "colors, high contrast, abstract AI concept, mobile-first composition"
                        ),
                    ),
                    StoryboardFrame(
                        role="last",
                        description="Cierre: la idea aplicada al negocio + marca",
                        prompt=(
                            "Vertical 9:16, same style, confident closing shot with subtle "
                            "Okeybot brand accent, clean negative space for caption"
                        ),
                    ),
                ],
                hashtags=hashtags_base,
                based_on=[t.url],
            )
        )
    return out


def generate_ideas(settings: Settings, trends: list[TrendItem], n: int) -> list[ContentIdea]:
    hashtags_base = settings.content_cfg.get("hashtags_base", [])

    if settings.dry_run or not settings.anthropic_api_key:
        if not settings.dry_run:
            log.warning("Sin ANTHROPIC_API_KEY: usando ideas simuladas")
        return _mock_ideas(trends, n, hashtags_base)

    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    system_block = _brand_system_block(settings)

    resp = client.messages.create(
        model=settings.ideation_model,
        max_tokens=2000,
        system=[
            {
                "type": "text",
                "text": system_block,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": _user_prompt(trends, n, hashtags_base)}
        ],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    payload = _extract_json(text)
    ideas = _to_ideas(payload, hashtags_base)
    log.info("Ideas generadas: %d", len(ideas))
    return ideas[:n]
