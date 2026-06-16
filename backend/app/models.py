"""API 数据模型。"""

from pydantic import BaseModel, Field


class FuturesRecord(BaseModel):
    """单条期货日行情记录（含手续费信息）。"""

    trade_date: str = Field(..., description="交易日期 YYYY-MM-DD")
    exchange: str = Field(..., description="交易所代码")
    exchange_name: str = Field(..., description="交易所名称")
    contract_code: str = Field(..., description="期货代码（合约代码）")
    variety_code: str = Field(..., description="期货品种代码")
    contract_name: str = Field(..., description="期货名称（合约名称）")
    variety_name: str = Field(..., description="期货品种名称")

    open: float | None = Field(None, description="开盘价")
    close: float | None = Field(None, description="收盘价")
    change_pct: float | None = Field(None, description="涨跌幅 %")

    volume: float | None = Field(None, description="成交量（手）")
    volume_lots: float | None = Field(None, description="成交手数")

    fee_rate: float | None = Field(None, description="手续费率（开仓费率）")
    fee_rate_single: float | None = Field(None, description="单边手续费率")
    fee_single: float | None = Field(None, description="单边手续费（元/手）")


class DailyResponse(BaseModel):
    """日行情查询响应。"""

    trade_date: str
    count: int
    records: list[FuturesRecord]
    warnings: list[str] = []
