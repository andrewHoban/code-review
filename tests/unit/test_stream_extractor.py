"""Unit tests for stream chunk extraction utilities."""

from __future__ import annotations

from app.utils.stream_extractor import coerce_review_output, extract_text_and_state


def test_extracts_text_from_dict_content_parts() -> None:
    chunks = [
        {"content": {"parts": [{"text": "hello"}]}},
        {"content": {"parts": [{"text": "world"}]}},
    ]
    combined_text, merged_state = extract_text_and_state(chunks)
    assert combined_text == "hello\nworld"
    assert merged_state == {}


def test_extracts_state_delta_from_dict_actions() -> None:
    chunks = [
        {"actions": {"state_delta": {"foo": "bar"}}},
        {"actions": {"state_delta": {"baz": 1}}},
    ]
    combined_text, merged_state = extract_text_and_state(chunks)
    assert combined_text == ""
    assert merged_state == {"foo": "bar", "baz": 1}


def test_coerce_prefers_code_review_output_from_state_delta() -> None:
    combined_text = "this should be ignored"
    merged_state = {
        "code_review_output": {
            "summary": "LGTM - no significant issues.",
            "inline_comments": [],
            "overall_status": "APPROVED",
            "metrics": {
                "files_reviewed": 1,
                "issues_found": 0,
                "critical_issues": 0,
                "warnings": 0,
                "suggestions": 0,
                "style_score": 100.0,
            },
        }
    }
    output = coerce_review_output(combined_text, merged_state)
    assert output["summary"].startswith("LGTM")
    assert output["overall_status"] == "APPROVED"


def test_coerce_parses_json_from_combined_text() -> None:
    combined_text = (
        "{\n"
        '  "summary": "Nice.",\n'
        '  "inline_comments": [],\n'
        '  "overall_status": "COMMENT",\n'
        '  "metrics": {"files_reviewed": 2, "issues_found": 0, "critical_issues": 0, "warnings": 0, "suggestions": 0, "style_score": 0.0}\n'
        "}\n"
    )
    output = coerce_review_output(combined_text, merged_state={})
    assert output["summary"] == "Nice."
    assert output["overall_status"] == "COMMENT"
    assert output["metrics"]["files_reviewed"] == 2


def test_coerce_parses_json_from_fenced_block() -> None:
    combined_text = (
        "```json\n"
        '{ "summary": "Nice.", "inline_comments": [], "overall_status": "COMMENT",'
        ' "metrics": {"files_reviewed": 1, "issues_found": 0, "critical_issues": 0, "warnings": 0, "suggestions": 0, "style_score": 0.0} }\n'
        "```\n"
    )
    output = coerce_review_output(combined_text, merged_state={})
    assert output["summary"] == "Nice."


def test_coerce_wraps_plain_text_as_comment() -> None:
    output = coerce_review_output("plain markdown text", merged_state={})
    assert output["summary"] == "plain markdown text"
    assert output["overall_status"] == "COMMENT"
