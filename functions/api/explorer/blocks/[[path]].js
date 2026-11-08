// Cloudflare Pages Function: Recent Blocks — 架空の block hash / miner 名 / 線形 extrapolation した
// block_number を返す実装を撤去 (2026-11-08)。
// blockindex.net (Core BlockBook 0.4.6) は «直近ブロック一覧» API を持たないため、実測できるのは
//   (a) チェーンヘッド (backend.blocks / backend.bestBlockHash / blockbook.lastBlockTime)
//   (b) このウォレットの取引が載ったブロックの blockHash / blockHeight / blockTime (address 照合)
// の2種類だけ。 miner / coinbase reward は公開 API が無いため null（UI は未取得表示）。
const WALLET_ADDRESS = "0xcb57b88d24678c2091332971e3a38cca472dd8aac0cd";
const DEFAULT_BLOCK_LIMIT = 10;

async function fetchBlockindex(url, timeoutMs = 8000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
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
  const rawPage = Number.parseInt(context.params?.page ?? 1, 10);
  const rawLimit = Number.parseInt(context.params?.limit ?? DEFAULT_BLOCK_LIMIT, 10);
  const page = Math.max(1, Number.isFinite(rawPage) ? rawPage : 1);
  const limit = Math.max(1, Math.min(Number.isFinite(rawLimit) ? rawLimit : DEFAULT_BLOCK_LIMIT, 25));

  const [headRes, txsRes] = await Promise.all([
    fetchBlockindex("https://blockindex.net/api/v2"),
    fetchBlockindex(`https://blockindex.net/api/v2?address=${WALLET_ADDRESS}&page=1&pageSize=50&details=txs`)
  ]);

  const headBook = headRes.data?.blockbook || {};
  const headBack = headRes.data?.backend || {};
  const headHeight = Number(headBack.blocks ?? headBook.bestHeight);
  const headHash = headBack.bestBlockHash || null;
  const headTime = headBook.lastBlockTime || null;

  const txs = txsRes.data?.txs || [];
  const measuredBlocks = new Map();
  for (const tx of txs) {
    const height = Number(tx.blockHeight);
    const hash = tx.blockHash;
    if (!Number.isFinite(height) || height < 0 || !hash) continue;
    const entry = measuredBlocks.get(height) || {
      block_number: height,
      block_hash: hash,
      timestamp: tx.blockTime || null,
      ourTxCount: 0,
      miner: null,
      reward: null
    };
    entry.ourTxCount += 1;
    if (!entry.timestamp && tx.blockTime) entry.timestamp = tx.blockTime;
    measuredBlocks.set(height, entry);
  }

  const nowMs = Date.now();
  const describeAge = (timestamp) => {
    if (!timestamp) return null;
    const then = typeof timestamp === "number" ? timestamp * 1000 : Date.parse(String(timestamp));
    if (!Number.isFinite(then)) return null;
    const sec = Math.max(0, Math.round((nowMs - then) / 1000));
    if (sec < 60) return `${sec}秒前`;
    if (sec < 3600) return `${Math.floor(sec / 60)}分前`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}時間前`;
    return `${Math.floor(sec / 86400)}日前`;
  };

  let blocks = Array.from(measuredBlocks.values())
    .sort((a, b) => b.block_number - a.block_number)
    .map((b) => ({
      ...b,
      age: describeAge(b.timestamp),
      measuredAt: b.timestamp || null,
      source: "blockindex address txs (実測)"
    }));

  if (headHeight && !blocks.some((b) => b.block_number === headHeight)) {
    blocks.unshift({
      block_number: headHeight,
      block_hash: headHash,
      timestamp: headTime,
      ourTxCount: null,
      miner: null,
      reward: null,
      age: describeAge(headTime),
      measuredAt: headTime || null,
      source: "blockindex chain head (実測)"
    });
  }

  const offset = (page - 1) * limit;
  const pageBlocks = blocks.slice(offset, offset + limit);

  if (!pageBlocks.length) {
    return new Response(JSON.stringify({
      state: false,
      data: [],
      error: [
        headRes.error ? `chain head 取得失敗: ${headRes.error}` : null,
        txsRes.error ? `address txs 取得失敗: ${txsRes.error}` : "実測ブロック 0 件"
      ].filter(Boolean).join(" / "),
      reason: "Core BlockBook には直近ブロック一覧 API が無い。未取得項目は null のまま返し、値は作りません。"
    }), { status: 200, headers });
  }

  return new Response(JSON.stringify({
    state: true,
    data: pageBlocks,
    measuredAt: headTime || new Date().toISOString(),
    source: "https://blockindex.net/api/v2 (Core BlockBook)",
    head: Number.isFinite(headHeight) ? { block_number: headHeight, block_hash: headHash, timestamp: headTime } : null,
    note: " miner と coinbase reward は Core の公開 API が返さないため null（UI は未取得表示）。"
  }), { status: 200, headers });
}
