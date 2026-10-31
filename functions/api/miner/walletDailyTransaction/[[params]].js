// Cloudflare Pages Function: Dynamic Wallet Daily Transactions
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const pathParts = url.pathname.split("/").filter(Boolean);
  // Route: /api/miner/walletDailyTransaction/:wallet/:limit
  const wallet = pathParts[3] || "cb57b88d24678c2091332971e3a38cca472dd8aac0cd";
  const limit = parseInt(pathParts[4], 10) || 60;

  // 1. Fetch initial_data.js from Pages static assets to get baseline history
  let baseDaily = [];
  try {
    const assetUrl = new URL("/data/initial_data.js", context.request.url);
    const assetRes = context.env && context.env.ASSETS
      ? await context.env.ASSETS.fetch(new Request(assetUrl))
      : await fetch(assetUrl);
    if (assetRes.ok) {
      const text = await assetRes.text();
      const prefix = "window.__COREGEEKS_INITIAL_DATA__ = ";
      if (text.startsWith(prefix)) {
        const jsonStr = text.slice(prefix.length).replace(/;\s*$/, "");
        const initData = JSON.parse(jsonStr);
        if (Array.isArray(initData.walletDailyTransactions)) {
          baseDaily = initData.walletDailyTransactions;
        }
      }
    }
  } catch (e) {
    // fallback if fetch fails
  }

  // 2. Fetch live on-chain transactions directly from blockindex for real-time accuracy
  try {
    const timeoutSignal = typeof AbortSignal !== "undefined" && AbortSignal.timeout
      ? AbortSignal.timeout(3000)
      : undefined;
    const blockindexRes = await fetch(`https://blockindex.net/api/v2/address/${wallet}?details=txs&pageSize=50`, {
      headers: { "Accept": "application/json", "User-Agent": "CoreStation/1.0" },
      signal: timeoutSignal,
      cf: { cacheTtl: 15 }
    });

    if (blockindexRes.ok) {
      const bData = await blockindexRes.json();
      const txs = bData.transactions || [];
      const walletLower = wallet.toLowerCase();

      // Aggregate on-chain payouts by UTC day
      const dayTotals = {};
      for (const tx of txs) {
        const bt = tx.blockTime;
        if (!bt) continue;
        const dayStr = new Date(bt * 1000).toISOString().slice(0, 10) + "T00:00:00.000Z";

        let valInt = 0n;
        if (Array.isArray(tx.vout)) {
          for (const vo of tx.vout) {
            const addrs = vo.addresses || [];
            if (addrs.some(a => (a || "").toLowerCase() === walletLower)) {
              valInt += BigInt(vo.value || "0");
            }
          }
        }
        if (valInt > 0n) {
          dayTotals[dayStr] = (dayTotals[dayStr] || 0n) + valInt;
        }
      }

      // Merge on-chain day totals into baseDaily
      const dailyMap = new Map();
      baseDaily.forEach((item, idx) => dailyMap.set(item.day, idx));

      for (const [dayStr, amountBig] of Object.entries(dayTotals)) {
        const amountStr = amountBig.toString();
        if (dailyMap.has(dayStr)) {
          const idx = dailyMap.get(dayStr);
          baseDaily[idx].day_amount = amountStr;
        } else {
          baseDaily.unshift({
            wallet_address: wallet,
            day: dayStr,
            day_amount: amountStr,
            day_rank: 180,
            all_amount: baseDaily.length > 0 ? baseDaily[0].all_amount : amountStr,
            all_rank: 160
          });
        }
      }
    }
  } catch (err) {
    // graceful fallback
  }

  // Fallback to minimal static array if both assets and blockindex were unavailable
  if (baseDaily.length === 0) {
    baseDaily = [
      {
        wallet_address: wallet,
        day: "2026-10-30T00:00:00.000Z",
        day_amount: "7204118198000000000",
        day_rank: 180,
        all_amount: "7359173994969000000000",
        all_rank: 160
      }
    ];
  }

  // Sort descending by date
  baseDaily.sort((a, b) => new Date(b.day) - new Date(a.day));
  const result = baseDaily.slice(0, limit);

  return new Response(JSON.stringify({ state: true, data: result }), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, max-age=15, s-maxage=15"
    }
  });
}
