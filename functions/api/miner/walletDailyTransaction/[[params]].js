// Cloudflare Pages Function: Wallet Daily Transactions
export async function onRequest(context) {
  const transactions = [
    {
      wallet_address: "cb57b88d24678c2091332971e3a38cca472dd8aac0cd",
      day: "2026-10-18T00:00:00.000Z",
      day_amount: "3258562736000000000",
      day_rank: 3,
      all_amount: "7459714218193000000000",
      all_rank: 3
    },
    {
      wallet_address: "cb57b88d24678c2091332971e3a38cca472dd8aac0cd",
      day: "2026-10-17T00:00:00.000Z",
      day_amount: "17181970954000000000",
      day_rank: 3,
      all_amount: "7459714218193000000000",
      all_rank: 3
    },
    {
      wallet_address: "cb57b88d24678c2091332971e3a38cca472dd8aac0cd",
      day: "2026-10-16T00:00:00.000Z",
      day_amount: "14558758200000000000",
      day_rank: 3,
      all_amount: "7459714218193000000000",
      all_rank: 3
    },
    {
      wallet_address: "cb57b88d24678c2091332971e3a38cca472dd8aac0cd",
      day: "2026-10-12T00:00:00.000Z",
      day_amount: "8792733992000000000",
      day_rank: 180,
      all_amount: "7297624076812000000000",
      all_rank: 160
    },
    {
      wallet_address: "cb57b88d24678c2091332971e3a38cca472dd8aac0cd",
      day: "2026-10-11T00:00:00.000Z",
      day_amount: "12993501629000000000",
      day_rank: 180,
      all_amount: "7288831342820000000000",
      all_rank: 160
    },
    {
      wallet_address: "cb57b88d24678c2091332971e3a38cca472dd8aac0cd",
      day: "2026-10-10T00:00:00.000Z",
      day_amount: "13571481113000000000",
      day_rank: 180,
      all_amount: "7275837841191000000000",
      all_rank: 160
    },
    {
      wallet_address: "cb57b88d24678c2091332971e3a38cca472dd8aac0cd",
      day: "2026-10-09T00:00:00.000Z",
      day_amount: "14028510369000000000",
      day_rank: 180,
      all_amount: "7262266360078000000000",
      all_rank: 160
    }
  ];

  return new Response(JSON.stringify({ state: true, data: transactions }), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, max-age=30, s-maxage=30"
    }
  });
}
