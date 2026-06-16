"""期货日行情数据获取与处理。

数据来源：AkShare
- ``ak.get_futures_daily``  : 各交易所日行情（开/收盘价、成交量等）
- ``ak.futures_fees_info``  : 各合约手续费 / 保证金等配置（最新快照）

行情按交易所、交易日抓取；手续费信息为最新快照，按合约代码精确匹配，
匹配不到时回退到品种代码匹配。
"""

from __future__ import annotations

import time
from threading import Lock

import akshare as ak
import pandas as pd

from .exchanges import EXCHANGES, exchange_name
from .models import FuturesRecord

# ---------------------------------------------------------------------------
# 手续费信息缓存（快照型数据，缓存 1 小时即可）
# ---------------------------------------------------------------------------

_FEES_TTL_SECONDS = 60 * 60
_fees_lock = Lock()
_fees_cache: dict[str, object] = {"ts": 0.0, "by_contract": {}, "by_variety": {}}


def _build_fee_maps(df: pd.DataFrame) -> tuple[dict, dict]:
    """构建 合约代码->费率行 与 品种代码->代表行 两个字典。"""
    by_contract: dict[str, dict] = {}
    by_variety: dict[str, dict] = {}
    for _, row in df.iterrows():
        rec = {
            "contract_name": str(row.get("合约名称", "")),
            "variety_name": str(row.get("品种名称", "")),
            "fee_rate": _to_float(row.get("开仓费率")),
            "fee_single": _to_float(row.get("1手开仓费用")),
            "market_value": _to_float(row.get("1手市值")),
        }
        code = str(row.get("合约代码", "")).upper()
        variety = str(row.get("品种代码", "")).upper()
        if code:
            by_contract[code] = rec
        if variety and variety not in by_variety:
            by_variety[variety] = rec
    return by_contract, by_variety


def get_fee_maps(force: bool = False) -> tuple[dict, dict]:
    """获取（带缓存的）手续费映射表。"""
    now = time.time()
    with _fees_lock:
        fresh = now - float(_fees_cache["ts"]) < _FEES_TTL_SECONDS
        if not force and fresh and _fees_cache["by_contract"]:
            return _fees_cache["by_contract"], _fees_cache["by_variety"]  # type: ignore[return-value]
    # 网络请求放在锁外
    df = ak.futures_fees_info()
    by_contract, by_variety = _build_fee_maps(df)
    with _fees_lock:
        _fees_cache.update(ts=now, by_contract=by_contract, by_variety=by_variety)
    return by_contract, by_variety


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _to_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def normalize_date(date: str) -> str:
    """将 ``YYYY-MM-DD`` 或 ``YYYYMMDD`` 统一为 ``YYYYMMDD``。"""
    return date.replace("-", "").strip()


def _fmt_date(yyyymmdd: str) -> str:
    if len(yyyymmdd) == 8:
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    return yyyymmdd


def _split_contract(symbol: str, variety_hint: str) -> tuple[str, str]:
    """从合约代码拆出品种代码与月份部分，如 ``CU2408`` -> (``CU``, ``2408``)。"""
    variety = variety_hint.upper() if variety_hint else ""
    if not variety:
        variety = "".join(ch for ch in symbol if ch.isalpha()).upper()
    month = symbol.upper()[len(variety):] if symbol.upper().startswith(variety) else ""
    return variety, month


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def _records_for_exchange(
    market: str,
    yyyymmdd: str,
    by_contract: dict,
    by_variety: dict,
) -> list[FuturesRecord]:
    df = ak.get_futures_daily(start_date=yyyymmdd, end_date=yyyymmdd, market=market)
    if df is None or df.empty:
        return []

    records: list[FuturesRecord] = []
    trade_date = _fmt_date(yyyymmdd)
    ex_name = exchange_name(market)
    for _, row in df.iterrows():
        symbol = str(row.get("symbol", "")).upper()
        if not symbol:
            continue
        variety_code = str(row.get("variety", "")).upper()
        variety_code, month = _split_contract(symbol, variety_code)

        open_ = _to_float(row.get("open"))
        close = _to_float(row.get("close"))
        pre_settle = _to_float(row.get("pre_settle"))
        volume = _to_float(row.get("volume"))

        # 涨跌幅：优先以前结算价为基准，否则以开盘价
        change_pct: float | None = None
        if close is not None and pre_settle:
            change_pct = round((close - pre_settle) / pre_settle * 100, 2)
        elif close is not None and open_:
            change_pct = round((close - open_) / open_ * 100, 2)

        fee = by_contract.get(symbol) or by_variety.get(variety_code) or {}
        fee_rate = fee.get("fee_rate")
        fee_single = fee.get("fee_single")
        market_value = fee.get("market_value")
        # 单边手续费率：以实际单边手续费 / 合约市值估算，回退到配置费率
        fee_rate_single: float | None = None
        if fee_single is not None and market_value:
            fee_rate_single = round(fee_single / market_value, 8)
        else:
            fee_rate_single = fee_rate

        variety_name = fee.get("variety_name") or variety_code
        contract_name = f"{variety_name}{month}" if variety_name and month else symbol

        records.append(
            FuturesRecord(
                trade_date=trade_date,
                exchange=market,
                exchange_name=ex_name,
                contract_code=symbol,
                variety_code=variety_code,
                contract_name=contract_name,
                variety_name=variety_name,
                open=open_,
                close=close,
                change_pct=change_pct,
                volume=volume,
                volume_lots=volume,
                fee_rate=fee_rate,
                fee_rate_single=fee_rate_single,
                fee_single=fee_single,
            )
        )
    return records


def fetch_daily(
    date: str,
    exchanges: list[str] | None = None,
) -> tuple[str, list[FuturesRecord], list[str]]:
    """抓取指定日期、指定交易所的期货日行情。

    返回 ``(交易日期, 记录列表, 警告列表)``。
    """
    yyyymmdd = normalize_date(date)
    if len(yyyymmdd) != 8 or not yyyymmdd.isdigit():
        raise ValueError(f"非法日期: {date}")

    markets = [e.upper() for e in (exchanges or list(EXCHANGES))]
    invalid = [m for m in markets if m not in EXCHANGES]
    if invalid:
        raise ValueError(f"未知交易所: {', '.join(invalid)}")

    warnings: list[str] = []
    try:
        by_contract, by_variety = get_fee_maps()
    except Exception as exc:  # noqa: BLE001 - 手续费失败不应阻断行情
        by_contract, by_variety = {}, {}
        warnings.append(f"手续费信息获取失败，相关字段为空：{exc}")

    records: list[FuturesRecord] = []
    for market in markets:
        try:
            records.extend(
                _records_for_exchange(market, yyyymmdd, by_contract, by_variety)
            )
        except Exception as exc:  # noqa: BLE001 - 单个交易所失败不应阻断其他
            warnings.append(f"{exchange_name(market)}({market}) 数据获取失败：{exc}")

    return _fmt_date(yyyymmdd), records, warnings
