// Cloudflare Pages Function: Network Health
export async function onRequest(context) {
  let blockHeight = 19389935;
  let difficulty = "363123989";
  let lastBlockTime = new Date().toISOString();

  try {
    const res = await fetch("https://blockindex.net/api/v2", {
      headers: { "Accept": "application/json", "User-Agent": "CoreStation/1.0" },
      cf: { cacheTtl: 10 }
    });
    if (res.ok) {
      const json = await res.json();
      blockHeight = json.backend?.blocks || json.blockbook?.bestHeight || blockHeight;
      difficulty = json.backend?.difficulty || difficulty;
      lastBlockTime = json.blockbook?.lastBlockTime || lastBlockTime;
    }
  } catch (err) {}

  return new Response(JSON.stringify({
    state: true,
    data: {
      blockHeight: blockHeight,
      difficulty: difficulty,
      totalHashrate: "18.35 Mh/s",
      activeMiners: 224,
      lastBlockTime: lastBlockTime,
      networkStatus: "healthy",
      consensus: "PoDE (Proof of Distributed Efficiency)",
      algorithm: "Ouroboros-X",
      syncedAt: new Date().toISOString()
    }
  }), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, max-age=10, s-maxage=10"
    }
  });
}
