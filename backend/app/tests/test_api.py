"""API 与数据处理测试（mock AkShare，无需网络）。"""

from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import futures
from app.main import app

client = TestClient(app)


FAKE_DAILY = pd.DataFrame(
    [
        {
            "symbol": "CU2408",
            "date": "20240722",
            "open": 76350.0,
            "high": 76470.0,
            "low": 75570.0,
            "close": 75640.0,
            "volume": 80286,
            "open_interest": 137371,
            "turnover": 3055786.58,
            "settle": 76120,
            "pre_settle": 76780,
            "variety": "CU",
        }
    ]
)

FAKE_FEES = pd.DataFrame(
    [
        {
            "交易所": "SHFE",
            "合约代码": "CU2408",
            "合约名称": "CU2408",
            "品种代码": "CU",
            "品种名称": "沪铜",
            "开仓费率": 0.00005,
            "开仓费用/手": 0.01,
            "1手开仓费用": 19.0,
            "1手市值": 378200.0,
        }
    ]
)


@pytest.fixture(autouse=True)
def _mock_akshare(monkeypatch):
    def fake_get_futures_daily(start_date, end_date, market):
        if market == "SHFE":
            return FAKE_DAILY.copy()
        if market == "DCE":
            raise ValueError("upstream down")
        return pd.DataFrame()

    monkeypatch.setattr(futures.ak, "get_futures_daily", fake_get_futures_daily)
    monkeypatch.setattr(futures.ak, "futures_fees_info", lambda: FAKE_FEES.copy())
    # 清空手续费缓存
    futures._fees_cache.update(ts=0.0, by_contract={}, by_variety={})
    yield


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_exchanges():
    data = client.get("/api/exchanges").json()
    codes = {e["code"] for e in data}
    assert {"SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"} <= codes


def test_daily_shfe():
    resp = client.get("/api/futures/daily", params={"date": "2024-07-22", "exchange": "SHFE"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    rec = body["records"][0]
    assert rec["contract_code"] == "CU2408"
    assert rec["variety_code"] == "CU"
    assert rec["variety_name"] == "沪铜"
    assert rec["contract_name"] == "沪铜2408"
    assert rec["open"] == 76350.0
    assert rec["close"] == 75640.0
    # 涨跌幅 = (75640-76780)/76780*100
    assert rec["change_pct"] == pytest.approx(-1.48, abs=0.01)
    assert rec["volume"] == 80286
    assert rec["volume_lots"] == 80286
    assert rec["fee_rate"] == 0.00005
    assert rec["fee_single"] == 19.0
    # 单边手续费率 = 19/378200
    assert rec["fee_rate_single"] == pytest.approx(19.0 / 378200.0, abs=1e-7)


def test_daily_partial_failure_warning():
    resp = client.get("/api/futures/daily", params={"date": "20240722", "exchange": "SHFE,DCE"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert any("DCE" in w for w in body["warnings"])


def test_invalid_date():
    resp = client.get("/api/futures/daily", params={"date": "not-a-date"})
    assert resp.status_code == 400


def test_invalid_exchange():
    resp = client.get("/api/futures/daily", params={"date": "20240722", "exchange": "XXX"})
    assert resp.status_code == 400
