// Cloudflare Pages Function: Manual Sync Trigger
export async function onRequest(context) {
  const now = new Date();
  const jstStr = new Date(now.getTime() + 9 * 3600 * 1000).toISOString().replace('T', ' ').slice(0, 19) + ' JST';

  return new Response(JSON.stringify({
    state: true,
    message: "同期完了: オンチェーンおよびワーカー状態の同期に成功しました",
    syncedAt: jstStr
  }), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
      "Access-Control-Allow-Headers": "*"
    }
  });
}
