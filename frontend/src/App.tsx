import { useEffect, useMemo, useState } from "react";
import {
  fetchDaily,
  fetchExchanges,
  type DailyResponse,
  type Exchange,
  type FuturesRecord,
} from "./api";

interface Column {
  key: keyof FuturesRecord;
  label: string;
  numeric?: boolean;
  format?: (r: FuturesRecord) => string;
}

const fmtNum = (v: number | null, digits = 2): string =>
  v === null || v === undefined || Number.isNaN(v)
    ? "-"
    : v.toLocaleString("zh-CN", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });

const fmtInt = (v: number | null): string =>
  v === null || v === undefined || Number.isNaN(v)
    ? "-"
    : v.toLocaleString("zh-CN", { maximumFractionDigits: 0 });

const fmtRate = (v: number | null): string =>
  v === null || v === undefined || Number.isNaN(v)
    ? "-"
    : `${(v * 100).toFixed(4)}%`;

const COLUMNS: Column[] = [
  { key: "trade_date", label: "交易日期" },
  { key: "exchange_name", label: "交易所" },
  { key: "contract_code", label: "期货代码" },
  { key: "variety_code", label: "品种代码" },
  { key: "contract_name", label: "期货名称" },
  { key: "variety_name", label: "品种名称" },
  { key: "open", label: "开盘价", numeric: true, format: (r) => fmtNum(r.open) },
  { key: "close", label: "收盘价", numeric: true, format: (r) => fmtNum(r.close) },
  {
    key: "change_pct",
    label: "涨跌幅",
    numeric: true,
    format: (r) => (r.change_pct === null ? "-" : `${r.change_pct.toFixed(2)}%`),
  },
  { key: "volume", label: "成交量", numeric: true, format: (r) => fmtInt(r.volume) },
  { key: "volume_lots", label: "成交手数", numeric: true, format: (r) => fmtInt(r.volume_lots) },
  { key: "fee_rate", label: "手续费率", numeric: true, format: (r) => fmtRate(r.fee_rate) },
  {
    key: "fee_rate_single",
    label: "单边手续费率",
    numeric: true,
    format: (r) => fmtRate(r.fee_rate_single),
  },
  { key: "fee_single", label: "单边手续费", numeric: true, format: (r) => fmtNum(r.fee_single) },
];

function todayStr(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

type SortDir = "asc" | "desc";

export default function App() {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [date, setDate] = useState<string>(todayStr());
  const [data, setData] = useState<DailyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<keyof FuturesRecord | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  useEffect(() => {
    fetchExchanges()
      .then(setExchanges)
      .catch((e) => setError(String(e)));
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetchDaily(date, selected);
      setData(resp);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  function toggleExchange(code: string) {
    setSelected((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  }

  function toggleSort(key: keyof FuturesRecord) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const rows = useMemo(() => {
    if (!data) return [];
    let r = data.records;
    const q = search.trim().toLowerCase();
    if (q) {
      r = r.filter(
        (x) =>
          x.contract_code.toLowerCase().includes(q) ||
          x.variety_code.toLowerCase().includes(q) ||
          x.variety_name.toLowerCase().includes(q) ||
          x.contract_name.toLowerCase().includes(q)
      );
    }
    if (sortKey) {
      const dir = sortDir === "asc" ? 1 : -1;
      r = [...r].sort((a, b) => {
        const av = a[sortKey];
        const bv = b[sortKey];
        if (av === null || av === undefined) return 1;
        if (bv === null || bv === undefined) return -1;
        if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
        return String(av).localeCompare(String(bv), "zh-CN") * dir;
      });
    }
    return r;
  }, [data, search, sortKey, sortDir]);

  function exportCsv() {
    if (rows.length === 0) return;
    const header = COLUMNS.map((c) => c.label).join(",");
    const lines = rows.map((r) =>
      COLUMNS.map((c) => {
        const raw = r[c.key];
        return raw === null || raw === undefined ? "" : String(raw);
      }).join(",")
    );
    const csv = "\ufeff" + [header, ...lines].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `期货数据_${date}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page">
      <header>
        <h1>每日期货数据</h1>
        <p className="subtitle">数据来源：AkShare · 中国期货市场日行情与手续费</p>
      </header>

      <section className="controls">
        <label className="field">
          <span>交易日期</span>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>

        <div className="field exchanges">
          <span>交易所（不选=全部）</span>
          <div className="chips">
            {exchanges.map((ex) => (
              <button
                key={ex.code}
                type="button"
                className={`chip ${selected.includes(ex.code) ? "active" : ""}`}
                onClick={() => toggleExchange(ex.code)}
                title={ex.name}
              >
                {ex.name}
              </button>
            ))}
          </div>
        </div>

        <button className="primary" onClick={load} disabled={loading}>
          {loading ? "查询中…" : "查询"}
        </button>
      </section>

      {error && <div className="error">⚠ {error}</div>}

      {data && (
        <>
          {data.warnings.length > 0 && (
            <div className="warnings">
              {data.warnings.map((w, i) => (
                <div key={i}>⚠ {w}</div>
              ))}
            </div>
          )}

          <section className="toolbar">
            <span className="count">
              {data.trade_date} · 共 {rows.length} / {data.count} 条
            </span>
            <input
              className="search"
              placeholder="搜索代码 / 品种名称"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button onClick={exportCsv} disabled={rows.length === 0}>
              导出 CSV
            </button>
          </section>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {COLUMNS.map((c) => (
                    <th
                      key={c.key}
                      className={c.numeric ? "num" : ""}
                      onClick={() => toggleSort(c.key)}
                    >
                      {c.label}
                      {sortKey === c.key ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={`${r.contract_code}-${i}`}>
                    {COLUMNS.map((c) => {
                      const text = c.format ? c.format(r) : String(r[c.key] ?? "-");
                      let cls = c.numeric ? "num" : "";
                      if (c.key === "change_pct" && r.change_pct !== null) {
                        cls += r.change_pct > 0 ? " up" : r.change_pct < 0 ? " down" : "";
                      }
                      return (
                        <td key={c.key} className={cls}>
                          {text}
                        </td>
                      );
                    })}
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={COLUMNS.length} className="empty">
                      无数据（该日期可能非交易日，或上游数据源暂不可用）
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!data && !error && !loading && (
        <div className="hint">选择交易日期与交易所后点击「查询」。</div>
      )}
    </div>
  );
}
