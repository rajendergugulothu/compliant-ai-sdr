"""Response text extraction must survive models that return thinking blocks.

Regression test for the silent-judge bug: reading resp.content[0].text assumed
the first content block is text, but models with extended thinking emit a
ThinkingBlock first. That raised AttributeError, which run_judge swallowed and
turned into a fail-open PASS — silently disabling the entire LLM-judge layer.
"""
from sdr_eval.llm import _text_from


class _Block:
    def __init__(self, type_, text=None):
        self.type = type_
        if text is not None:
            self.text = text


class _Resp:
    def __init__(self, blocks):
        self.content = blocks


def test_text_from_plain_text_block():
    resp = _Resp([_Block("text", "hello")])
    assert _text_from(resp) == "hello"


def test_text_from_skips_leading_thinking_block():
    # ThinkingBlock (no .text) precedes the real text block.
    resp = _Resp([_Block("thinking"), _Block("text", '[{"rule_id":"X"}]')])
    assert _text_from(resp) == '[{"rule_id":"X"}]'


def test_text_from_concatenates_multiple_text_blocks():
    resp = _Resp([_Block("text", "a"), _Block("text", "b")])
    assert _text_from(resp) == "ab"


def test_text_from_empty_is_empty_string():
    assert _text_from(_Resp([])) == ""
