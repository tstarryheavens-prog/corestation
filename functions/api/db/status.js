// Cloudflare Pages Function: Database Status — data/wallet.db は Pages 側に存在しないため、
// collector の実測スナップショット (data/live_state.json) だけを返す。
// 固定値（544 / 4425 / 112500）や「maxDate = today」「lastSync = now」の捏造は撤去済み (2026-11-08)。
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

  const { data: state, error } = await readLiveState(context);
  if (!state) {
    return new Response(JSON.stringify({
      state: false,
      data: null,
      source: "none",
      error: `wallet.db は Pages 側に無く、実測スナップショットも未取得: ${error}`,
      measuredAt: null
    }), { status: 200, headers });
  }

  const dbSection = state.db || {};
  const d = dbSection.data || {};
  if (!dbSection.state || !d || !Object.keys(d).length) {
    return new Response(JSON.stringify({
      state: false,
      data: null,
      source: "data/live_state.json",
      error: d?.note || dbSection.error || "collector が DB 実測値を未取得",
      measuredAt: dbSection.measured_at || null
    }), { status: 200, headers });
  }

  const measuredAt = dbSection.measured_at || null;
  return new Response(JSON.stringify({
    state: true,
    data: {
      status: "measured_snapshot",
      dailyCount: d.dailyCount ?? null,
      txCount: d.txCount ?? null,
      rateCount: d.rateCount ?? null,
      minDate: d.minDate ?? null,
      maxDate: d.maxDate ?? null,
      dbPath: d.dbPath ?? null,
      lastSync: measuredAt,
      measuredAt: measuredAt,
      measuredAgo: dbSection.measured_ago ?? null,
      lastTxAtJst: d.lastTxAtJst ?? null,
      dbDataAgeDays: d.dbDataAgeDays ?? null,
      dbStaleNote: d.dbStaleNote ?? null,
      fileMtimeJst: d.fileMtimeJst ?? null,
      fileSizeBytes: d.fileSizeBytes ?? null,
      latestRates: d.latestRates ?? null
    },
    source: "data/live_state.json (collector 実測スナップショット)",
    note: "Pages 側に wallet.db は無い。lastSync は collector の取得時刻、lastTxAtJst が DB 内の実データ最終日。"
  }), { status: 200, headers });
}
