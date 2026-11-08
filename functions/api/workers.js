// Cloudflare Pages Function: Mining Workers — 実測できるものだけ返す（固定値・jitter 合成を廃止）
// 1) Catch That Rabbit の実 API（証明書失効/522 で通らない場合は ok:false と理由をそのまま返す）
// 2) リグ上で worker_reporter.py が書いた data/machine_metrics/*.json（H/s・温度・電力の実測）
// 3) オンチェーン実績（最終着金時刻・24h/7d/30d の着金 XCB）— マシン実測ではなく実績
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
  const url = new URL(context.request.url);
  const wallet = url.searchParams.get("wallet") || "cb57b88d24678c2091332971e3a38cca472dd8aac0cd";

  const live = await readLiveState(context);
  const liveData = live.ok ? (live.state || {}) : {};
  const machines = (liveData.machines && liveData.machines.data) || {};
  const chain = (liveData.chain && liveData.chain.data) || {};
  const dbSection = (liveData.db && liveData.db.data) || {};
  const dbWorkers = Array.isArray(dbSection.dbWorkersSnapshot) ? dbSection.dbWorkersSnapshot : [];
  const workerMachineAlias = machines.workerMachineAlias || {};

  // 1) リグ報告（実測 H/s / temperature / power）
  const reporters = Array.isArray(machines.rigReporters) ? machines.rigReporters : [];
  const workers = reporters
    .filter(r => r && (r.hashrateHs !== undefined || r.hashrate !== undefined))
    .map(r => ({
      workerName: r.worker || r.host || r.id || "rig",
      pool: r.pool || "local report",
      hr: Number(r.hashrateHs ?? r.hashrate ?? 0),
      threads: r.threads ?? null,
      temperatureC: r.temperatureC ?? null,
      powerW: r.powerW ?? null,
      acceptedPct: r.acceptedPct ?? null,
      offline: !!(r.online === false),
      statusDesc: r.statusDesc || (r.online === false ? "報告停止" : "実測報告中"),
      measuredAt: r.measured_at || null,
      source: "worker_reporter"
    }));

  // 2) プール API を実際に試みる（失敗したら理由を正直に載せる）
  const poolAttempts = [];
  const pools = ["https://api.catchthatrabbit.com/api/v2", "https://as.catchthatrabbit.com/api/v2"];
  for (const base of pools) {
    const target = `${base}?wallet=${wallet}&workers=1`;
    try {
      const signal = typeof AbortSignal !== "undefined" && AbortSignal.timeout ? AbortSignal.timeout(4000) : undefined;
      const res = await fetch(target, {
        headers: { "Accept": "application/json", "User-Agent": "CoreStation/1.0" },
        signal, cf: { cacheTtl: 30 }
      });
      const text = await res.text();
      let parsed = null;
      try { parsed = JSON.parse(text); } catch { /* HTML or empty */ }
      poolAttempts.push({ url: target, http: res.status, ok: res.ok && !!parsed, sample: text.slice(0, 120) });
      if (res.ok && parsed && (parsed.workers || parsed.results)) {
        for (const w of (parsed.workers || parsed.results || [])) {
          workers.push({
            workerName: w.name || w.worker || "pool-worker",
            pool: base.replace("https://", "").replace("/api/v2", ""),
            hr: Number(w.hash_rate || w.hashRate || w.speed || 0),
            threads: w.threads ?? null,
            acceptedPct: w.accepted_share ?? w.acceptedPct ?? null,
            temperatureC: w.temperature ?? null,
            powerW: null,
            offline: !!w.offline,
            statusDesc: w.offline ? "プール側で offline 表示" : "プール実測",
            measuredAt: new Date().toISOString(),
            source: "pool_api"
          });
        }
        break;
      }
    } catch (e) {
      poolAttempts.push({ url: target, ok: false, error: String(e) });
    }
  }

  const totalHr = workers.reduce((a, w) => a + (Number(w.hr) || 0), 0);

  return new Response(JSON.stringify({
    state: true,
    data: {
      workers,
      totalHashrate: workers.length ? totalHr : null,
      hashrateMeasured: workers.length > 0,
      activeCount: workers.filter(w => !w.offline).length,
      totalCount: workers.length,
      poolApi: poolAttempts.some(p => p.ok)
        ? { ok: true, attempts: poolAttempts }
        : { ok: false, reason: "Catch That Rabbit API が応答しない（実測: 522 / 404・TLS 証明書失効）", attempts: poolAttempts },
      onChainEvidence: {
        lastPayoutAtJst: chain.lastPayoutAtJst ?? null,
        lastPayoutAgeMinutes: chain.lastPayoutAgeMin ?? null,
        payoutIntervalMeasuredH: chain.payoutIntervalMeasuredH ?? null,
        payoutGapNowH: chain.payoutGapNowH ?? null,
        payoutGapExceedsCadence: chain.payoutGapExceedsCadence ?? null,
        earnedXcb24h: chain.earnedXcb24h ?? null,
        earnedXcb7d: chain.earnedXcb7d ?? null,
        earnedXcb30d: chain.earnedXcb30d ?? null,
        blocksFound24hEstimate: chain.blocksFound24hEstimate ?? null,
        walletBalanceXcb: chain.walletBalanceXcb ?? null
      },
      rigReporterCount: workers.filter(w => w.source === "worker_reporter").length,
      // プール登録ワーカーのアーカイブ実測（wallet.db workers 卓）— ライブ H/s ではなく「いつのの実測か」を明示
      poolWorkerArchive: Array.isArray(dbWorkers) ? dbWorkers.map(w => ({
        workerName: w.worker_name ?? null,
        pool: w.pool ?? null,
        hr: w.hr ?? null,
        offline: w.offline ?? null,
        archiveUpdatedAt: w.updated_at ?? null,
        machineAlias: workerMachineAlias[String(w.worker_name || "").trim()] || null
      })) : [],
      poolWorkerArchiveNote: dbWorkers.length
        ? "wallet.db の workers 卓は最後にデータ同期できた時点の実測（ライブ値ではない）。machineAlias はユーザー申告マッピング。"
        : "wallet.db に workers 記録が無い",
      machineAlias: workerMachineAlias,
      rigNodes: (Array.isArray(machines.nodes) ? machines.nodes : [])
        .filter(n => n && (n.kind === "rig" || String(n.id || "").includes("X600")))
        .map(n => ({
          id: n.id || null, role: n.role || null, online: n.online ?? null,
          openPorts: n.openPorts ?? null, latencyMs: n.latencyMs ?? null,
          hashrate: n.hashrate ?? null, temperature: n.temperature ?? null, power: n.power ?? null,
          poolWorkers: n.poolWorkers ?? null, workerNameSource: n.workerNameSource ?? null,
          tailnet: n.tailnet ?? null, tailnetError: n.tailnetError ?? null,
          hasRigReport: n.hasRigReport ?? false,
          minerWorkerNames: n.minerWorkerNames ?? null,
          minerProcessCount: n.minerProcessCount ?? null,
          stratumSessions: n.stratumSessions ?? null,
          rigMeasuredAt: n.rigMeasuredAt ?? null, rigUnavailable: n.rigUnavailable ?? null,
          error: n.error ?? null, measuredAt: n.measured_at || null
        })),
      measuredAt: (liveData.machines && liveData.machines.measured_at) || new Date().toISOString(),
      liveStateFresh: live.ok,
      note: "H/s はリグ実測（worker_reporter）またはプール API の値のみ。両方が取得できないときは hashrateMeasured=false を返す（数値は作らない）。"
    }
  }), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store, no-cache, must-revalidate"
    }
  });
}
