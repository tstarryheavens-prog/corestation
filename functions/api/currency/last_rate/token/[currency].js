// Cloudflare Pages Function: Last exchange rate per currency — collector が wallet.db から実測した
// latest_rates だけを、実測日を明示して返す（固定値 + day=today の捏造は撤去済み 2026-11-08）。
async function readLiveState(context) {
  try {
    if (!context?.env?.ASSETS) return { data: null, error: "ASSETS binding 未取得" };
    const url = new URL("/data/live_state.json", context.url || "https://corestation.pages.dev/");
    const res = await context.env.ASSETS.fetch(new Request(url.toString(), { cf: { cacheTtl: 5 } }));
    if (!res.ok) return { data: null, error: `live_state.json 未取得 (HTTP ${res.status})` };
    return { data: await res.json(), error: null };
  } catch (err) {
    return { data: null, error: String(err && err.message || err) };
  }
}

const TOKEN_KEYS = ["XCB", "CTN"];

export async function onRequest(context) {
  const headers = { "Content-Type": "application/json" };
  const requested = String(context.params?.currency || "JPY").trim().toUpperCase();

  const { data: state, error } = await readLiveState(context);
  if (!state) {
    return new Response(JSON.stringify({
      state: false, data: null, source: "none",
      error: `実測レート未取得: ${error}`, measuredAt: null
    }), { status: 200, headers });
  }

  const dbSection = state.db || {};
  const rates = (dbSection.data && dbSection.data.latestRates) || [];
  const dbOk = dbSection.ok === true || dbSection.state === true;
  if (!dbOk || !rates.length) {
    return new Response(JSON.stringify({
      state: false, data: null, source: "data/live_state.json",
      error: "latest_rates 実測値が未取得（collector の DB 取得失敗 or 空）",
      measuredAt: dbSection.measured_at || null
    }), { status: 200, headers });
  }

  const rows = rates.filter((r) => String(r.currency || "").toUpperCase() === requested);
  if (!rows.length) {
    const available = Array.from(new Set(rates.map((r) => r.currency))).sort();
    return new Response(JSON.stringify({
      state: false, data: null, currency: requested, source: "data/live_state.json (wallet.db latest_rates 実測)",
      error: `通貨 ${requested} の実測レートは wallet.db に無い（取得可能: ${available.join(", ")}）`,
      measuredAt: dbSection.measured_at || null
    }), { status: 200, headers });
  }

  const out = {};
  let measuredDay = null;
  for (const r of rows) {
    const token = String(r.token || "").toUpperCase();
    if (!TOKEN_KEYS.includes(token)) continue;
    measuredDay = measuredDay || r.day || null;
    out[token.toLowerCase()] = {
      currency: r.currency,
      token,
      rate: r.rate ?? null,
      // day は wallet.db に実測保存された日付（今日ではない）
      day: r.day || null,
      rateUpdatedAt: r.updated_at || null,
      rateAgeDays: r.ageDays ?? null,
      stale: true
    };
  }

  return new Response(JSON.stringify({
    state: Object.keys(out).length > 0,
    data: Object.keys(out).length ? out : null,
    currency: requested,
    source: "wallet.db latest_rates（collector 実測スナップショット）",
    measuredDay,
    collectorMeasuredAt: dbSection.measured_at || null,
    note: "レートは wallet.db に保存された実測値。実測日 (day/rateUpdatedAt) と経過日数 (rateAgeDays) を表示すること。"
  }), { status: 200, headers });
}
