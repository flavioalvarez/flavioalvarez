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
                "image_prompt": "img",
                "video_prompt": "vid",
                "caption": "cap",
                "hashtags": ["#IA", "#especifico"],
                "based_on": ["http://x"],
            }
        ]
    }
    ideas = _to_ideas(payload, hashtags_base=["#okeybot", "#IA"])
    assert ideas[0].hashtags == ["#okeybot", "#IA", "#especifico"]
    assert ideas[0].based_on == ["http://x"]
