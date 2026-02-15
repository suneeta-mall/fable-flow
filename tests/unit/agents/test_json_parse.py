from __future__ import annotations

import pytest

from fable_flow.agents._json_parse import parse_json_response


def test_plain_json_array():
    response = '[{"a": 1}, {"a": 2}]'
    assert parse_json_response(response, expect=list) == [{"a": 1}, {"a": 2}]


def test_plain_json_object():
    response = '{"k": "v"}'
    assert parse_json_response(response, expect=dict) == {"k": "v"}


def test_fenced_code_block():
    response = """Some preamble.

```json
[{"id": 1}, {"id": 2}]
```

Trailing remarks."""
    assert parse_json_response(response, expect=list) == [{"id": 1}, {"id": 2}]


def test_embedded_array_in_prose():
    response = 'Here is the data: [{"x": 1}] please review.'
    assert parse_json_response(response, expect=list) == [{"x": 1}]


def test_nested_object_with_arrays():
    response = """```
{"chapters": [{"n": 1}, {"n": 2}]}
```"""
    parsed = parse_json_response(response, expect=dict)
    assert parsed["chapters"] == [{"n": 1}, {"n": 2}]


def test_raises_on_unparseable():
    with pytest.raises(ValueError):
        parse_json_response("just plain text, no json", expect=list)


def test_multiple_candidates_picks_valid():
    response = """Note the [broken format below.
```json
[{"valid": true}]
```"""
    assert parse_json_response(response, expect=list) == [{"valid": True}]
