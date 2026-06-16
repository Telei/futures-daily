"""FastAPI 应用入口：每日期货数据 API。"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .exchanges import EXCHANGES
from .futures import fetch_daily
from .models import DailyResponse

app = FastAPI(
    title="每日期货数据 API",
    description="基于 AkShare 获取中国期货市场日行情与手续费信息。",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/exchanges")
def list_exchanges() -> list[dict[str, str]]:
    """返回支持的交易所列表。"""
    return [{"code": code, "name": name} for code, name in EXCHANGES.items()]


@app.get("/api/futures/daily", response_model=DailyResponse)
def daily(
    date: str = Query(..., description="交易日期，YYYY-MM-DD 或 YYYYMMDD"),
    exchange: str | None = Query(
        None,
        description="交易所代码，多个用逗号分隔；留空表示全部",
    ),
) -> DailyResponse:
    """查询指定交易日的期货日行情（含手续费信息）。"""
    exchanges = (
        [e.strip() for e in exchange.split(",") if e.strip()] if exchange else None
    )
    try:
        trade_date, records, warnings = fetch_daily(date, exchanges)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DailyResponse(
        trade_date=trade_date,
        count=len(records),
        records=records,
        warnings=warnings,
    )
