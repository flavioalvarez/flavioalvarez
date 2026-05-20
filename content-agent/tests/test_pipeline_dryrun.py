from agent.config import load_settings
from agent.pipeline import run


def test_dry_run_pipeline_produces_drafts(tmp_path, monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("PIECES_PER_RUN", "2")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    settings = load_settings()

    pieces = run(settings)

    assert len(pieces) == 2
    assert all(p.status == "needs_approval" for p in pieces)
    assert all(p.asset.video_url for p in pieces)
    # se escribio el manifest del dia
    assert any(p.name == "manifest.json" for p in tmp_path.rglob("manifest.json"))
    # se encolaron borradores locales
    assert any(tmp_path.rglob("review_queue/*.md"))
