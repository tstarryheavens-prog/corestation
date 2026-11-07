// Cloudflare Pages Function: Watcher Status — 実測値だけを出す（合成した「巡回中」を作らない）
// データ源: デプロイ済みの /data/live_state.json（NAS/Hermes のコレクターが更新する）
async function readLiveState(context) {
  try {
    const assetUrl = new URL("/data/live_state.json", context.request.url);
    const res = await context.fetch(new Request(assetUrl.toString(), { headers: { "Accept": "application/json" } }));
    if (!res.ok) return { ok: false, error: `live_state.json HTTP ${res.status}` };
    return { ok: true, state: await res.json() };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
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
