// Cloudflare Pages Function: Live Network Status — 取得失敗時に架空のブロック高を作らない
export async function onRequest(context) {
  const livePromise = (async () => {
    try {
      const assetUrl = new URL("/data/live_state.json", context.request.url);
      const res = await context.fetch(new Request(assetUrl.toString(), { headers: { "Accept": "application/json" } }));
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  })();

  let liveErr = null;
  try {
    const signal = typeof AbortSignal !== "undefined" && AbortSignal.timeout ? AbortSignal.timeout(12000) : undefined;
    const res = await fetch("https://blockindex.net/api/v2", {
      headers: { "Accept": "application/json", "User-Agent": "CoreStation/1.0" },
      signal, cf: { cacheTtl: 15 }
    });
    if (res.ok) {
      const json = await res.json();
      const backend = json.backend || {};
      const blockbook = json.blockbook || {};
      return new Response(JSON.stringify({
        state: true,
        data: {
          blockHeight: backend.blocks || blockbook.bestHeight || null,
          difficulty: backend.difficulty || null,
          lastBlockTime: blockbook.lastBlockTime || null,
          version: backend.version || null,
          inSync: blockbook.inSync,
          coin: blockbook.coin,
          measuredAt: new Date().toISOString(),
          source: "blockindex.net/api/v2 (live)"
        }
      }), {
        status: 200,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "public, max-age=15, s-maxage=15"
        }
      });
    }
    liveErr = `upstream HTTP ${res.status}`;
  } catch (e) {
    liveErr = String(e);
  }

  // 失敗時: 架空の現在ブロック高を線形計算して返さない。直近の実測値とその時刻をそのまま返す。
  const st = await livePromise;
  const ch = st && st.chain && st.chain.data ? st.chain.data : null;
  return new Response(JSON.stringify({
    state: false,
    error: liveErr,
    data: ch ? {
      blockHeight: ch.blockHeight,
      difficulty: ch.difficulty,
      lastBlockTime: ch.lastBlockTime,
      measuredAt: st.chain.measured_at,
      staleMinutes: Math.round((Date.now() - new Date(st.chain.measured_at).getTime()) / 60000),
      source: "data/live_state.json (last measured)"
    } : null
  }), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store"
    }
  });
}
