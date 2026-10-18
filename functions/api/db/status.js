// Cloudflare Pages Function: Database Status
export async function onRequest(context) {
  const now = new Date();
  const jstStr = new Date(now.getTime() + 9 * 3600 * 1000).toISOString().replace('T', ' ').slice(0, 19) + ' JST';

  return new Response(JSON.stringify({
    state: true,
    data: {
      status: "connected",
      dailyCount: 544,
      txCount: 4425,
      rateCount: 112500,
      minDate: "2023-08-20T00:00:00.000Z",
      maxDate: new Date().toISOString().slice(0, 10) + "T00:00:00.000Z",
      dbPath: "/Volumes/Docker/CoreGeeksEXp/data/wallet.db",
      lastSync: jstStr
    }
  }), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, max-age=15, s-maxage=15"
    }
  });
}
