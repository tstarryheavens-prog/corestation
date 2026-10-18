// Cloudflare Pages Function: Core Blockchain Supply
export async function onRequest(context) {
  const baselineHeight = 18891676;
  const baselineSupply = 397677423;
  const baselineCirc = 98681863;
  const now = Date.now();
  // Core block time ~10s
  const currentHeight = 19389855 + Math.floor((now - 1792295830000) / 10000);
  const deltaBlocks = Math.max(0, currentHeight - baselineHeight);
  const totalSupply = Math.round(baselineSupply + (deltaBlocks * 1.65));
  const circSupply = Math.round(baselineCirc + (deltaBlocks * 1.65));

  return new Response(JSON.stringify({
    state: true,
    data: {
      blockHeight: currentHeight,
      totalSupply: totalSupply,
      circulatingSupply: circSupply,
      maxSupply: 500000000,
      circulatingRatio: ((circSupply / totalSupply) * 100).toFixed(1) + "%",
      unit: "XCB"
    }
  }), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, max-age=60, s-maxage=60"
    }
  });
}
