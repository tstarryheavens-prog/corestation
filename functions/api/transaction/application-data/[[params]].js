// Cloudflare Pages Function: Transaction Application Data (Tax CSV)
export async function onRequest(context) {
  return new Response(JSON.stringify({
    state: true,
    data: [] // Handled gracefully by client-side allTransactions bundle
  }), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, max-age=60, s-maxage=60"
    }
  });
}
