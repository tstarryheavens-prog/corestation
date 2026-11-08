// Cloudflare Pages Function: Network Health — 固定値 (totalHashrate "18.35 Mh/s" / activeMiners 224 /
// networkStatus "healthy" / syncedAt=now) を撤去 (2026-11-08)。
// Core BlockBook (blockindex.net) が返すのは bestHeight・difficulty・lastBlockTime・inSync だけ。
// 全網ハッシュレートとアクティブマイナー数は公開 API が無い → null（UI は未取得表示）。
async function fetchBlockindex(timeoutMs = 8000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch("https://blockindex.net/api/v2", {
      method: "GET",
      headers: { "Accept": "application/json", "User-Agent": "CoreStation-Dashboard/1.0" },
      signal: controller.signal,
      cf: { cacheTtl: 10 }
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
    "Cache-Control": "public, max-age=10, s-maxage=10"
  };

  const { data: raw, error } = await fetchBlockindex();
  if (!raw) {
    return new Response(JSON.stringify({
      state: false,
      data: null,
      error: `blockindex 未取得: ${error}`,
      reason: "値は作っていません（固定値・healthy 判定・syncedAt=now を廃止）。"
    }), { status: 200, headers });
  }

  const book = raw.blockbook || {};
  const back = raw.backend || {};
  const height = Number(back.blocks ?? book.bestHeight);
  const difficulty = back.difficulty ?? book.difficulty ?? null;
  const lastBlockTime = book.lastBlockTime || null;
  const measuredAt = new Date().toISOString();

  let lastBlockAgeSeconds = null;
  if (lastBlockTime) {
    const then = Date.parse(String(lastBlockTime));
    if (Number.isFinite(then)) lastBlockAgeSeconds = Math.max(0, Math.round((Date.now() - then) / 1000));
  }

  const inSync = book.inSync === true && book.initialSync === false;
  const chainActive = lastBlockAgeSeconds !== null && lastBlockAgeSeconds <= 120;

  return new Response(JSON.stringify({
    state: true,
    data: {
      blockHeight: Number.isFinite(height) ? height : null,
      difficulty,
      bestBlockHash: back.bestBlockHash || null,
      lastBlockTime,
      lastBlockAgeSeconds,
      inSync: book.inSync ?? null,
      initialSync: book.initialSync ?? null,
      lastBlockAgeSecondsSince: lastBlockAgeSeconds,
      totalHashrate: null,
      activeMiners: null,
      networkStatus: chainActive ? "chain_advancing" : (inSync ? "synced_no_recent_block" : "unknown"),
      unmeasured: ["totalHashrate", "activeMiners"],
      reason: "totalHashrate / activeMiners は Core BlockBook が返さない（未取得）。固定値 '18.35 Mh/s'・224 は撤去しました。",
      consensus: "PoDE (Proof of Distributed Efficiency)",
      algorithm: "Ouroboros-X",
      measuredAt
    },
    source: "https://blockindex.net/api/v2 (Core BlockBook)",
    note: "consensus / algorithm は仕様上の定数（実測値ではない）。"
  }), { status: 200, headers });
}
