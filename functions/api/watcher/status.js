// Cloudflare Pages Function: Watcher Status — 実測値だけを出す（合成した「巡回中」を作らない）
// データ源: デプロイ済みの /data/live_state.json（NAS/Hermes のコレクターが更新する）
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

export async function onRequest(context) {
  const { ok, state, error } = await readLiveState(context);
  const generated = ok ? state.generated_at : null;
  const ageMin = generated ? Math.max(0, Math.round((Date.now() - new Date(generated).getTime()) / 60000)) : null;

  const content = (ok && state.content && state.content.data) || {};
  const watcher = (ok && state.watcher && state.watcher.data) || {};
  const chain = (ok && state.chain && state.chain.data) || {};

  // 巡回の実実行記録（NAS 側の hub/config と hub/output の実 mtime / crontab 実体）
  const lastChecked = content.watcherLastCheckedChronicle || watcher.lastHubOutputAtJst || null;
  const lastPublished = content.watcherLastPublishedCommunity || null;
  const schedule = watcher.crontabEntriesVisibleToCollector || [];

  let freshness = "unknown";
  if (ageMin !== null) freshness = ageMin <= 45 ? "fresh" : (ageMin <= 180 ? "stale" : "expired");

  const body = {
    state: ok,
    data: {
      // is_running は「巡回パイプラインのコレクターが最近動いたか」で判定（架空のカウント・pid は返さない）
      is_running: freshness === "fresh",
      status: ok ? (freshness === "fresh" ? "healthy" : freshness) : "unreachable",
      is_running_basis: "collector freshness (data/live_state.json の age)",
      last_checked: lastChecked,
      last_published: lastPublished,
      next_run: schedule.length ? schedule[0].schedule : null,
      schedule_crontab: schedule,
      collector_age_minutes: ageMin,
      collector_generated_at: generated,
      archive_count: content.archiveCount ?? null,
      archive_newest_date: content.archiveNewestDate ?? null,
      shortfall_count: content.shortfallCount ?? null,
      seen_posts: content.watcherSeenPosts ?? 0,
      last_payout_age_minutes: chain.lastPayoutAgeMin ?? null,
      earned_xcb_24h: chain.earnedXcb24h ?? null,
      note: "数値はすべて NAS/チェーン実測。取得できなかった項目は null のまま返す（値を補完しない）。"
    },
    error: ok ? null : error,
    measured_at: generated || new Date().toISOString()
  };

  return new Response(JSON.stringify(body), {
    status: ok ? 200 : 503,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store, no-cache, must-revalidate"
    }
  });
}
