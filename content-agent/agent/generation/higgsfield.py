"""Cliente de Higgsfield: generacion de imagen (nano banana pro) y video (seedance 2.0).

La API de Higgsfield es asincrona: se envia un job y se hace polling del estado
hasta que termina. Los nombres exactos de endpoints/campos pueden variar segun
tu plan; este cliente esta escrito de forma defensiva (lee varios nombres de
campo comunes) y todo es configurable via variables de entorno.

Doc de referencia:
- Auth tipo key+secret (HIGGSFIELD_API_KEY + HIGGSFIELD_SECRET).
- Base: https://platform.higgsfield.ai
- Alternativa: MCP en https://mcp.higgsfield.ai/mcp (auth por cuenta, sin keys).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional

import requests

from ..config import Settings
from ..models import GeneratedImage

log = logging.getLogger("agent.generation")

_DONE = {"completed", "succeeded", "success", "done", "finished"}
_FAILED = {"failed", "error", "nsfw", "canceled", "cancelled"}


class HiggsfieldError(RuntimeError):
    pass


class HiggsfieldClient:
    def __init__(self, settings: Settings):
        self.s = settings
        self.base = settings.higgsfield_base_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {settings.higgsfield_api_key}",
                "hf-secret": settings.higgsfield_secret,
                "Content-Type": "application/json",
            }
        )

    # -- helpers de bajo nivel -------------------------------------------------
    def _submit(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base}/{path.lstrip('/')}"
        resp = self.session.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _first(d: dict[str, Any], *keys: str) -> Optional[Any]:
        for k in keys:
            if k in d and d[k]:
                return d[k]
        return None

    def _status_url(self, submit_resp: dict[str, Any]) -> str:
        url = self._first(submit_resp, "status_url", "statusUrl")
        if url:
            return url
        rid = self._first(submit_resp, "request_id", "generation_id", "id", "requestId")
        if not rid:
            raise HiggsfieldError(f"Respuesta sin id ni status_url: {submit_resp}")
        return f"{self.base}/v1/predictions/{rid}/result"

    def _poll(self, status_url: str, timeout_s: int = 600, interval_s: int = 3) -> dict[str, Any]:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            resp = self.session.get(status_url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            state = str(self._first(data, "status", "state") or "").lower()
            if state in _DONE or self._extract_media_url(data):
                if state in _FAILED:
                    raise HiggsfieldError(f"Generacion fallida: {data}")
                return data
            if state in _FAILED:
                raise HiggsfieldError(f"Generacion fallida: {data}")
            time.sleep(interval_s)
        raise HiggsfieldError(f"Timeout esperando {status_url}")

    @staticmethod
    def _extract_media_url(data: dict[str, Any]) -> Optional[str]:
        # busca url en formas comunes: output, result, data, results[0]...
        for key in ("output_url", "url", "video_url", "image_url"):
            if data.get(key):
                return data[key]
        for container in ("output", "result", "data"):
            val = data.get(container)
            if isinstance(val, str) and val.startswith("http"):
                return val
            if isinstance(val, dict):
                for key in ("url", "video_url", "image_url", "output_url"):
                    if val.get(key):
                        return val[key]
            if isinstance(val, list) and val:
                first = val[0]
                if isinstance(first, str) and first.startswith("http"):
                    return first
                if isinstance(first, dict):
                    for key in ("url", "video_url", "image_url"):
                        if first.get(key):
                            return first[key]
        return None

    def _download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self.session.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(chunk_size=8192):
                    fh.write(chunk)
        return dest

    # -- API de alto nivel -----------------------------------------------------
    def generate_image(
        self, prompt: str, dest: Path, variant: int = 0, aspect_ratio: str = "9:16"
    ) -> GeneratedImage:
        """Genera UNA imagen (nano banana pro) y la descarga a `dest`."""
        payload = {
            "model": self.s.higgsfield_image_model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": self.s.content_cfg.get("image_resolution", "1080p"),
        }
        submit = self._submit("v1/image/generations", payload)
        data = self._poll(self._status_url(submit))
        url = self._extract_media_url(data)
        if not url:
            raise HiggsfieldError(f"Sin URL de imagen en: {data}")
        path = self._download(url, dest)
        return GeneratedImage(variant=variant, url=url, path=str(path))

    def generate_image_variants(
        self, prompt: str, dest_template: Path, count: int, aspect_ratio: str = "9:16"
    ) -> list[GeneratedImage]:
        """Genera `count` variantes del mismo prompt para que el humano elija.

        `dest_template` se usa con sufijo _vN (ej. frame_first.png -> frame_first_v0.png).
        """
        out: list[GeneratedImage] = []
        for i in range(count):
            dest = dest_template.with_name(f"{dest_template.stem}_v{i}{dest_template.suffix}")
            out.append(self.generate_image(prompt, dest, variant=i, aspect_ratio=aspect_ratio))
        return out

    def generate_video(
        self,
        prompt: str,
        dest: Path,
        first_frame_url: Optional[str] = None,
        last_frame_url: Optional[str] = None,
        aspect_ratio: str = "9:16",
        duration: int = 10,
    ) -> tuple[str, Path]:
        """Genera el video (seedance 2.0).

        Acepta frame inicial, final o ambos (interpolacion). Los nombres de
        campo exactos para el frame final pueden variar segun el modelo; se
        envian las variantes mas comunes para maxima compatibilidad.
        """
        if not (first_frame_url or last_frame_url):
            raise HiggsfieldError("Se requiere al menos un frame (inicial o final)")
        payload: dict[str, Any] = {
            "model": self.s.higgsfield_video_model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
        }
        if first_frame_url:
            payload["image_url"] = first_frame_url        # primer frame
        if last_frame_url:
            payload["end_image_url"] = last_frame_url     # ultimo frame
            payload["last_frame_url"] = last_frame_url    # alias defensivo
        submit = self._submit("v1/video/generations", payload)
        data = self._poll(self._status_url(submit), timeout_s=900)
        url = self._extract_media_url(data)
        if not url:
            raise HiggsfieldError(f"Sin URL de video en: {data}")
        path = self._download(url, dest)
        return url, path
