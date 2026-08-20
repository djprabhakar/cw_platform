import pytest
from cw_platform.llm.provider import LLMProvider, LLMResponse, FakeLLMProvider


def test_fake_provider_returns_scripted_responses_in_order():
    provider = FakeLLMProvider(script=["first", "second"])
    r1 = provider.complete("prompt one")
    r2 = provider.complete("prompt two")
    assert r1 == LLMResponse(text="first")
    assert r2 == LLMResponse(text="second")


def test_fake_provider_raises_when_script_exhausted():
    provider = FakeLLMProvider(script=["only one"])
    provider.complete("prompt one")
    with pytest.raises(IndexError):
        provider.complete("prompt two")


def test_fake_provider_matches_by_prompt_substring():
    provider = FakeLLMProvider(script={"currency": "USD found", "unit scale": "thousands"})
    r = provider.complete("Please determine the currency for this field")
    assert r.text == "USD found"


def test_fake_provider_substring_no_match_raises():
    provider = FakeLLMProvider(script={"currency": "USD found"})
    with pytest.raises(AssertionError):
        provider.complete("totally unrelated prompt")


def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()
