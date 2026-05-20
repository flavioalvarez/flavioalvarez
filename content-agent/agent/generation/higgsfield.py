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
    def generate_image(self, prompt: str, dest: Path, aspect_ratio: str = "9:16") -> tuple[str, Path]:
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
        return url, path

    def generate_video(
        self,
        prompt: str,
        image_url: Optional[str],
        dest: Path,
        aspect_ratio: str = "9:16",
        duration: int = 10,
    ) -> tuple[str, Path]:
        payload: dict[str, Any] = {
            "model": self.s.higgsfield_video_model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
        }
        if image_url:
            # image-to-video: la imagen de nano banana es el primer frame
            payload["image_url"] = image_url
        submit = self._submit("v1/video/generations", payload)
        data = self._poll(self._status_url(submit), timeout_s=900)
        url = self._extract_media_url(data)
        if not url:
            raise HiggsfieldError(f"Sin URL de video en: {data}")
        path = self._download(url, dest)
        return url, path
