// Cloudflare Pages Function: Core Blockchain Supply — 時刻からの線形 extrapolation で
// block height / supply を作る実装を撤去 (2026-11-08)。
// blockindex.net (Core BlockBook) は supply を返さない → 未取得は null のまま返す。
async function fetchBlockindex(timeoutMs = 8000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch("https://blockindex.net/api/v2", {
      method: "GET",
      headers: { "Accept": "application/json", "User-Agent": "CoreStation-Dashboard/1.0" },
      signal: controller.signal,
      cf: { cacheTtl: 60 }
    });
    if (!res.ok) return { data: null, error: `HTTP ${res.status}` };
    return { data: await res.json(), error: null };
  } catch (err) {
    return { data: null, error: String(err && err.message || err) };
  } finally {
    clearTimeout(timer);
  }
}

export async function onRequest(context) {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "public, max-age=60, s-maxage=60"
  };

  const { data: raw, error } = await fetchBlockindex();
  const book = raw?.blockbook || {};
  const back = raw?.backend || {};
  const height = Number(back.blocks ?? book.bestHeight);

  const supplyFields = ["circulatingSupply", "totalSupply", "maxSupply", "circulatingRatio"];
  const measuredSupply = supplyFields
    .map((k) => [k, back[k] ?? book[k]])
    .filter(([, v]) => v !== undefined && v !== null && v !== "");

  const data = {
    blockHeight: Number.isFinite(height) ? height : null,
    totalSupply: null,
    circulatingSupply: null,
    maxSupply: null,
    circulatingRatio: null,
    unit: "XCB"
  };
  for (const [k, v] of measuredSupply) {
    const num = Number(v);
    data[k] = Number.isFinite(num) ? num : String(v);
  }

  if (!Number.isFinite(height)) {
    return new Response(JSON.stringify({
      state: false,
      data: null,
      error: `blockindex 未取得: ${error || "block height が無い"}`,
      reason: "値は作っていません（線形 extrapolation 廃止）。"
    }), { status: 200, headers });
  }

  const unmeasured = Object.entries(data)
    .filter(([k, v]) => k !== "unit" && (v === null || v === undefined))
    .map(([k]) => k);

  return new Response(JSON.stringify({
    state: true,
    data,
    measuredAt: book.lastBlockTime || new Date().toISOString(),
    source: "https://blockindex.net/api/v2 (Core BlockBook)",
    unmeasured,
    reason: unmeasured.length
      ? `${unmeasured.join(", ")} は Core BlockBook が返さない（未取得）。線形 extrapolation による推定値は出しません。`
      : null,
    consensus: "PoDE (Proof of Distributed Efficiency)",
    algorithm: "Ouroboros-X",
    note: "consensus / algorithm は仕様上の定数（実測値ではない）"
  }), { status: 200, headers });
}
