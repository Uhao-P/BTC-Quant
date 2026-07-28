"""AI-assisted market analysis API."""
import json

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config.settings import settings
from data.store.store import store
from services.ai_prediction import AIPredictionService


router = APIRouter()
service = AIPredictionService()


class PredictionRequest(BaseModel):
    prompt: str
    snapshot: dict
    news: list[dict]


def _validate_symbol(symbol: str):
    if symbol not in settings.SYMBOLS:
        raise HTTPException(status_code=400, detail="Unsupported symbol")


def _serialize_record(record):
    if not record:
        return None
    return {
        "id": record.id,
        "symbol": record.symbol,
        "model": record.model,
        "prompt": record.prompt,
        "snapshot": json.loads(record.snapshot),
        "news": json.loads(record.news),
        "analysis": json.loads(record.analysis),
        "created_at": record.created_at.isoformat(),
    }


@router.get("/context")
async def get_ai_prediction_context(symbol: str = Query("BTC-USDT-SWAP")):
    """Collect quant evidence/news and return the exact prompt without model spend."""
    _validate_symbol(symbol)
    try:
        return await service.build_context(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/analyze")
async def analyze_with_llm(request: PredictionRequest, symbol: str = Query("BTC-USDT-SWAP")):
    """Analyze exactly the evidence/prompt reviewed by the user and persist it."""
    _validate_symbol(symbol)
    if request.snapshot.get("symbol") != symbol:
        raise HTTPException(status_code=422, detail="Snapshot symbol does not match request symbol")
    try:
        result = await service.analyze_context({
            "symbol": symbol,
            "snapshot": request.snapshot,
            "news": request.news,
            "prompt": request.prompt,
            "model": settings.LLM_MODEL,
            "model_configured": service.llm_client.configured,
        })
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=f"LLM analysis failed: {exc}") from exc

    with store.get_session() as session:
        record = store.save_ai_prediction(session, {
            "symbol": symbol,
            "model": result["model"],
            "prompt": result["prompt"],
            "snapshot": json.dumps(result["snapshot"], ensure_ascii=False),
            "news": json.dumps(result["news"], ensure_ascii=False),
            "analysis": json.dumps(result["analysis"], ensure_ascii=False),
        })
        session.commit()
        session.refresh(record)
        result["id"] = record.id
        result["created_at"] = record.created_at.isoformat()
    return result


@router.get("/latest")
async def get_latest_ai_prediction(symbol: str = Query("BTC-USDT-SWAP")):
    """Restore the latest saved model analysis after a page refresh."""
    _validate_symbol(symbol)
    return {"data": _serialize_record(store.get_latest_ai_prediction(symbol))}
