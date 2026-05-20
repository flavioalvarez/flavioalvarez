import pytest

from agent.config import load_settings
from agent.studio import (
    approve_frame,
    generate_storyboard,
    render_video,
    research_and_ideate,
)


def _settings(tmp_path, monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    return load_settings()


def test_storyboard_generates_variants_per_frame(tmp_path, monkeypatch):
    settings = _settings(tmp_path, monkeypatch)
    idea = research_and_ideate(settings, n=1)[0]
    generate_storyboard(settings, idea, tmp_path, variants=3)
    assert idea.storyboard, "la idea mock debe tener frames"
    for fr in idea.storyboard:
        assert len(fr.variants) == 3


def test_render_requires_approved_frames(tmp_path, monkeypatch):
    settings = _settings(tmp_path, monkeypatch)
    idea = research_and_ideate(settings, n=1)[0]
    generate_storyboard(settings, idea, tmp_path, variants=2)
    with pytest.raises(ValueError):
        render_video(settings, idea, tmp_path)  # nada aprobado todavia


def test_approve_then_render(tmp_path, monkeypatch):
    settings = _settings(tmp_path, monkeypatch)
    idea = research_and_ideate(settings, n=1)[0]
    generate_storyboard(settings, idea, tmp_path, variants=2)
    for fr in idea.storyboard:
        approve_frame(idea, fr.role, variant=1)
    asset = render_video(settings, idea, tmp_path)
    assert asset.video_url


def test_approve_invalid_variant_raises(tmp_path, monkeypatch):
    settings = _settings(tmp_path, monkeypatch)
    idea = research_and_ideate(settings, n=1)[0]
    generate_storyboard(settings, idea, tmp_path, variants=2)
    role = idea.storyboard[0].role
    with pytest.raises(ValueError):
        approve_frame(idea, role, variant=99)
