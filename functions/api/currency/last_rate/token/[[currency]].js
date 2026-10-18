// Cloudflare Pages Function: Dynamic Currency Last Rate
export async function onRequest(context) {
  const params = context.params.currency;
  const currencyParam = Array.isArray(params) ? params[0] : (params || "JPY");
  const currency = (currencyParam || "JPY").toUpperCase();

  const ratesTable = {
    JPY: {
      xcb: { currency: "JPY", day: new Date().toISOString().slice(0, 10), rate: 4.985332 },
      ctn: { currency: "JPY", day: new Date().toISOString().slice(0, 10), rate: 1.031448 }
    },
    USD: {
      xcb: { currency: "USD", day: new Date().toISOString().slice(0, 10), rate: 0.033235 },
      ctn: { currency: "USD", day: new Date().toISOString().slice(0, 10), rate: 0.006876 }
    },
    EUR: {
      xcb: { currency: "EUR", day: new Date().toISOString().slice(0, 10), rate: 0.028900 },
      ctn: { currency: "EUR", day: new Date().toISOString().slice(0, 10), rate: 0.005980 }
    },
    CHF: {
      xcb: { currency: "CHF", day: new Date().toISOString().slice(0, 10), rate: 0.027300 },
      ctn: { currency: "CHF", day: new Date().toISOString().slice(0, 10), rate: 0.005650 }
    },
    CAD: {
      xcb: { currency: "CAD", day: new Date().toISOString().slice(0, 10), rate: 0.046500 },
      ctn: { currency: "CAD", day: new Date().toISOString().slice(0, 10), rate: 0.009620 }
    }
  };

  const data = ratesTable[currency] || ratesTable.JPY;

  return new Response(JSON.stringify({ state: true, data: data }), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, max-age=60, s-maxage=60"
    }
  });
}
