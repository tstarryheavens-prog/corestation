// Cloudflare Pages Function: Network Health — 固定値 (totalHashrate "18.35 Mh/s" / activeMiners 224 /
// networkStatus "healthy" / syncedAt=now) を撤去 (2026-11-08)。
// Core BlockBook (blockindex.net) が返すのは bestHeight・difficulty・lastBlockTime・inSync だけ。
// 全網ハッシュレートとアクティブマイナー数は公開 API が無い → null（UI は未取得表示）。
async function fetchBlockindex(timeoutMs = 20000) {
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

export async function onRequest(context) {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "public, max-age=10, s-maxage=10"
  };

  let { data: raw, error } = await fetchBlockindex();

  // blockindex が応答しないときは collector の実測スナップショットを「いつの実測か」明示して使う
  if (!raw) {
    const { data: snapshot } = await readLiveState(context);
    const chainSection = (snapshot && snapshot.chain) || {};
    const cd = chainSection.data || {};
    const snapHeight = Number(cd.blockHeight);
    if ((chainSection.ok === true || chainSection.state === true) && Number.isFinite(snapHeight)) {
      return new Response(JSON.stringify({
        state: true,
        data: {
          blockHeight: snapHeight,
          difficulty: cd.difficulty ?? null,
          bestBlockHash: cd.bestBlockHash || null,
          lastBlockTime: cd.lastBlockTime || null,
          lastBlockAgeSeconds: cd.lastBlockAgeSeconds ?? null,
          inSync: cd.inSync ?? null,
          totalHashrate: null,
          activeMiners: null,
          networkStatus: "snapshot_only",
          unmeasured: ["totalHashrate", "activeMiners"],
          consensus: "PoDE (Proof of Distributed Efficiency)",
          algorithm: "Ouroboros-X",
          measuredAt: chainSection.measured_at || null
        },
        source: "data/live_state.json (collector 実測スナップショット)",
        snapshotAgeLabel: cd.lastBlockAgeLabel || null,
        reason: `blockindex ライブ未取得 (${error}) — collector の ${chainSection.measured_at || "時刻不明"} 実測スナップショットを表示（鮮度注意）。totalHashrate / activeMiners は Core BlockBook が返さない。`,
        note: "consensus / algorithm は仕様上の定数（実測値ではない）。"
      }), { status: 200, headers });
    }
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
