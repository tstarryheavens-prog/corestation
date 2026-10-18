// Cloudflare Pages Function: Live Address & Transactions
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const wallet = url.searchParams.get("wallet") || "cb57b88d24678c2091332971e3a38cca472dd8aac0cd";
  const pageSize = url.searchParams.get("pageSize") || "20";

  const targetUrl = `https://blockindex.net/api/v2/address/${wallet}?details=txs&pageSize=${pageSize}`;

  try {
    const res = await fetch(targetUrl, {
      headers: {
        "Accept": "application/json",
        "User-Agent": "CoreStation/1.0"
      },
      cf: { cacheTtl: 15 }
    });

    if (res.ok) {
      const data = await res.json();
      return new Response(JSON.stringify({ state: true, data: data }), {
        status: 200,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "public, max-age=15, s-maxage=15"
        }
      });
    }
  } catch (err) {}

  return new Response(JSON.stringify({ state: false, error: "Failed to fetch on-chain address" }), {
    status: 502,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*"
    }
  });
}
