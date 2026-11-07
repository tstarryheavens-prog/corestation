// Cloudflare Pages Function: Live Network Status — 取得失敗時に架空のブロック高を作らない
export async function onRequest(context) {
async function readLiveState(context) {
  // Pages の静的アセットは env.ASSETS 経由で読む（context.fetch だけでは asset ルートに届かない）
  const url = new URL("/data/live_state.json", context.request.url);
  const attempts = [];
  const readers = [];
  if (context.env && context.env.ASSETS && typeof context.env.ASSETS.fetch === "function") {
    readers.push((u) => context.env.ASSETS.fetch(new Request(u.toString(), { headers: { Accept: "application/json" } })));
  }
  if (typeof context.fetch === "function") {
    readers.push((u) => context.fetch(new Request(u.toString(), { headers: { Accept: "application/json" } })));
  }
  readers.push((u) => fetch(u.toString(), { headers: { Accept: "application/json", "User-Agent": "CoreStation/1.0" } }));
  for (const read of readers) {
    try {
      const res = await read(url);
      attempts.push({ via: read.name || "reader", http: res.status });
      if (!res.ok) continue;
      const ct = res.headers.get("content-type") || "";
      if (ct.includes("text/html")) { attempts.push({ note: "html fallback" }); continue; }
      return { ok: true, state: await res.json(), attempts };
    } catch (e) {
      attempts.push({ error: String(e).slice(0, 120) });
    }
  }
  return { ok: false, error: `live_state.json 読み取り失敗: ${JSON.stringify(attempts)}` };
}

  const livePromise = (async () => {
    const r = await readLiveState(context);
    return r.ok ? r.state : null;
  })();

  let liveErr = null;
  try {
    const signal = typeof AbortSignal !== "undefined" && AbortSignal.timeout ? AbortSignal.timeout(26000) : undefined;
    const res = await fetch("https://blockindex.net/api/v2", {
      headers: { "Accept": "application/json", "User-Agent": "CoreStation/1.0" },
      signal, cf: { cacheTtl: 15, timeoutMs: 25000 }
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
