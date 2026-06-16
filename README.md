# 每日期货数据

一个获取中国期货市场**每日行情 + 手续费信息**的网页应用，前后端分离。

- 后端：FastAPI（Python），数据来源 [AkShare](https://akshare.akfamily.xyz/)
- 前端：React + Vite + TypeScript

## 字段说明

| 字段 | 说明 | 来源 |
| --- | --- | --- |
| 交易日期 | 查询的交易日 | 入参 |
| 交易所 | SHFE/DCE/CZCE/CFFEX/INE/GFEX | `get_futures_daily` |
| 期货代码 | 合约代码，如 `CU2408` | `get_futures_daily` |
| 期货品种代码 | 品种代码，如 `CU` | `get_futures_daily` |
| 期货名称 | 合约名称（品种名称+月份） | 拼接 |
| 期货品种名称 | 如 `铜` | `futures_fees_info` |
| 开盘价 / 收盘价 | 当日开/收盘价 | `get_futures_daily` |
| 涨跌幅 | `(收盘价-前结算价)/前结算价`，无前结算价时以开盘价为基准 | 计算 |
| 成交量 / 成交手数 | 当日成交量（手） | `get_futures_daily` |
| 手续费率 | 开仓费率（按比例品种为真实费率，按手品种为占位值） | `futures_fees_info` |
| 单边手续费 | 单边（开仓）一手手续费，元 | `futures_fees_info`（`1手开仓费用`） |
| 单边手续费率 | `单边手续费 / 一手合约市值`，对按比例/按手品种均有意义 | 计算 |

> 说明：手续费信息为 AkShare 提供的**最新快照**（非历史值），按合约代码精确匹配，匹配不到时回退到品种代码匹配。

## 目录结构

```
backend/    FastAPI 服务（app/）+ 测试（app/tests/）
frontend/   React + Vite 前端
```

## 本地运行

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API 文档：http://127.0.0.1:8000/docs

主要接口：

- `GET /api/health` 健康检查
- `GET /api/exchanges` 交易所列表
- `GET /api/futures/daily?date=2024-07-22&exchange=SHFE,DCE` 日行情查询
  - `date`：`YYYY-MM-DD` 或 `YYYYMMDD`
  - `exchange`：交易所代码，多个用逗号分隔，留空表示全部

### 前端

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

前端开发服务器已将 `/api` 代理到 `http://127.0.0.1:8000`，可用
`VITE_API_TARGET` 环境变量覆盖后端地址。

生产构建：`npm run build`（产物在 `frontend/dist`）。

## 测试与检查

```bash
cd backend
pip install -r requirements-dev.txt
ruff check app          # 代码检查
pytest -q               # 单元测试（mock AkShare，无需联网）

cd ../frontend
npm run lint            # tsc 类型检查
npm run build
```

## 已知限制

- 大连商品交易所（DCE）的 `get_futures_daily` 上游接口当前返回异常，
  该交易所数据会在响应的 `warnings` 中提示且暂时缺失；其余交易所正常。
- AkShare 行情仅在交易日收盘后更新，非交易日查询将返回空结果。
