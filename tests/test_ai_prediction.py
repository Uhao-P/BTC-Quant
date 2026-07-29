import json

import pytest
import httpx

from services.ai_prediction import (
    AIPredictionService,
    build_prediction_prompt,
    parse_llm_response,
    parse_news_rss,
    LLMClient,
)


class RecordingLLM:
    configured = True

    def __init__(self):
        self.prompt = None

    async def analyze(self, prompt):
        self.prompt = prompt
        return {"direction": "neutral", "confidence": 50}


def test_news_rss_parser_keeps_source_time_and_link():
    xml = b"""<?xml version="1.0"?>
    <rss><channel><item>
      <title>Bitcoin ETF flows rise</title>
      <link>https://example.com/story</link>
      <pubDate>Wed, 29 Jul 2026 01:00:00 GMT</pubDate>
      <source>Example News</source>
    </item></channel></rss>"""

    assert parse_news_rss(xml) == [{
        "title": "Bitcoin ETF flows rise",
        "url": "https://example.com/story",
        "published_at": "Wed, 29 Jul 2026 01:00:00 GMT",
        "source": "Example News",
    }]


def test_prompt_contains_every_evidence_group_and_strict_output_contract():
    snapshot = {
        "symbol": "BTC-USDT-SWAP",
        "market": {"close": 100.0},
        "indicators": {"rsi_14": 55.0},
        "quant_signal": {"direction": "long", "score": 3.5},
        "funding": {"latest": 0.0001},
        "recent_signals": [{"direction": "long"}],
        "backtest": {"win_rate": 0.55},
    }
    news = [{"title": "Bitcoin adoption", "source": "Example", "url": "https://example.com"}]

    prompt = build_prediction_prompt(snapshot, news)

    for heading in ("MARKET_DATA", "TECHNICAL_INDICATORS", "QUANT_SIGNAL", "FUNDING",
                    "RECENT_SIGNALS", "BACKTEST", "NEWS"):
        assert heading in prompt
    assert '"direction": "long | short | neutral"' in prompt
    assert "untrusted evidence" in prompt


@pytest.mark.parametrize("payload", [
    {"output_text": '{"direction":"long","confidence":72,"summary":"up","bullish_factors":[],"bearish_factors":[],"risks":[],"time_horizon":"24h","invalidation":"below support"}'},
    {"choices": [{"message": {"content": '```json\n{"direction":"short","confidence":65,"summary":"down","bullish_factors":[],"bearish_factors":[],"risks":[],"time_horizon":"24h","invalidation":"above resistance"}\n```'}}]},
])
def test_llm_response_parser_accepts_responses_and_chat_completions(payload):
    result = parse_llm_response(payload)

    assert result["direction"] in {"long", "short"}
    assert 0 <= result["confidence"] <= 100


@pytest.mark.asyncio
async def test_analyze_context_sends_the_exact_reviewed_prompt():
    llm = RecordingLLM()
    service = AIPredictionService(llm_client=llm)
    context = {"prompt": "reviewed prompt", "snapshot": {"symbol": "BTC-USDT-SWAP"}, "news": []}

    result = await service.analyze_context(context)

    assert llm.prompt == "reviewed prompt"
    assert result["analysis"]["direction"] == "neutral"


@pytest.mark.asyncio
async def test_chat_completions_request_matches_litellm_contract(monkeypatch):
    from config.settings import settings

    captured = {}

    async def fake_post(_self, url, headers, json):
        captured.update(url=url, headers=headers, body=json)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"direction":"neutral","confidence":50}'}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://litellm.example/v1")
    monkeypatch.setattr(settings, "LLM_MODEL", "xiaosuan-8")
    monkeypatch.setattr(settings, "LLM_API_STYLE", "chat_completions")
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    await LLMClient().analyze("你是谁")

    assert captured["url"] == "https://litellm.example/v1/chat/completions"
    assert captured["body"] == {
        "model": "xiaosuan-8",
        "messages": [{"role": "user", "content": "你是谁"}],
    }
    assert captured["headers"]["Authorization"] == "Bearer test-key"
