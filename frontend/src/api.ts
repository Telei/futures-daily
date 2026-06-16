export interface FuturesRecord {
  trade_date: string;
  exchange: string;
  exchange_name: string;
  contract_code: string;
  variety_code: string;
  contract_name: string;
  variety_name: string;
  open: number | null;
  close: number | null;
  change_pct: number | null;
  volume: number | null;
  volume_lots: number | null;
  fee_rate: number | null;
  fee_rate_single: number | null;
  fee_single: number | null;
}

export interface DailyResponse {
  trade_date: string;
  count: number;
  records: FuturesRecord[];
  warnings: string[];
}

export interface Exchange {
  code: string;
  name: string;
}

export async function fetchExchanges(): Promise<Exchange[]> {
  const res = await fetch("/api/exchanges");
  if (!res.ok) throw new Error("获取交易所列表失败");
  return res.json();
}

export async function fetchDaily(
  date: string,
  exchanges: string[]
): Promise<DailyResponse> {
  const params = new URLSearchParams({ date });
  if (exchanges.length > 0) params.set("exchange", exchanges.join(","));
  const res = await fetch(`/api/futures/daily?${params.toString()}`);
  if (!res.ok) {
    let detail = `请求失败 (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}
