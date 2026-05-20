import pytest

from agent.ideation.ideator import _extract_json, _to_ideas


def test_extract_json_handles_markdown_fences():
    text = '```json\n{"ideas": [{"title": "x"}]}\n```'
    data = _extract_json(text)
    assert data["ideas"][0]["title"] == "x"


def test_extract_json_with_surrounding_text():
    text = 'Aca tenes:\n{"ideas": []}\nGracias!'
    assert _extract_json(text) == {"ideas": []}


def test_extract_json_raises_without_object():
    with pytest.raises(ValueError):
        _extract_json("no hay json aca")


def test_to_ideas_merges_base_hashtags_without_dupes():
    payload = {
        "ideas": [
            {
                "title": "T",
                "hook": "H",
                "script": "S",
                "video_prompt": "vid",
                "caption": "cap",
                "hashtags": ["#IA", "#especifico"],
                "based_on": ["http://x"],
                "frame_mode": "first",
                "first_frame": {"description": "d", "prompt": "img"},
            }
        ]
    }
    ideas = _to_ideas(payload, hashtags_base=["#okeybot", "#IA"])
    assert ideas[0].hashtags == ["#okeybot", "#IA", "#especifico"]
    assert ideas[0].based_on == ["http://x"]


def test_to_ideas_builds_both_frames():
    payload = {
        "ideas": [
            {
                "title": "T", "hook": "H", "script": "S", "caption": "c",
                "video_prompt": "v",
                "frame_mode": "both",
                "first_frame": {"description": "ini", "prompt": "p1"},
                "last_frame": {"description": "fin", "prompt": "p2"},
            }
        ]
    }
    idea = _to_ideas(payload, hashtags_base=[])[0]
    assert idea.frame_mode == "both"
    assert [f.role for f in idea.storyboard] == ["first", "last"]
    assert idea.frame("last").prompt == "p2"


def test_to_ideas_ignores_unused_frame():
    payload = {
        "ideas": [
            {
                "title": "T", "hook": "H", "script": "S", "caption": "c",
                "video_prompt": "v",
                "frame_mode": "last",
                "first_frame": {"description": "x", "prompt": "p1"},
                "last_frame": {"description": "fin", "prompt": "p2"},
            }
        ]
    }
    idea = _to_ideas(payload, hashtags_base=[])[0]
    assert [f.role for f in idea.storyboard] == ["last"]
