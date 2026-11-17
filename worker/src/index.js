// HSBC Partnership News helper (Cloudflare Worker). It does two small jobs:
//
// 1. Starts the news collector at 07:45 UK time on weekdays. GitHub's own
//    schedule has been starting runs hours late; Cloudflare's timers are on time.
//    On Mondays it asks for 72 hours so Friday evening and the weekend are covered.
//
// 2. Passes on "Summarise my picks" clicks from the page to GitHub, which writes
//    bullets for those stories only. The page is public, so the click has to come
//    from the page's own address AND carry the access key you set (PICK_KEY).
//
// Secrets (set with `npx wrangler secret put NAME`, never written in this file):
//   GITHUB_TOKEN  a fine-grained GitHub token for this one repo, "Actions: read and write"
//   PICK_KEY      any long passphrase; you type it into the page once per browser

const REPO = "jberraondo/Client-Partnership-News";
const ALLOWED_ORIGIN = "https://jberraondo.github.io";
const ID_RE = /^[A-Za-z0-9_-]{4,64}$/;
const MAX_IDS = 20;

async function dispatch(env, workflow, inputs) {
  const res = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "partnership-news-worker",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: "main", inputs }),
    }
  );
  return res.status === 204 ? null : `GitHub said ${res.status}: ${(await res.text()).slice(0, 200)}`;
}

function londonNow(date) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/London", hour: "2-digit", hourCycle: "h23", weekday: "short",
  }).formatToParts(date);
  const get = (t) => parts.find((p) => p.type === t)?.value;
  return { hour: Number(get("hour")), weekday: get("weekday") };
}

function cors(origin) {
  return {
    "Access-Control-Allow-Origin": origin === ALLOWED_ORIGIN ? ALLOWED_ORIGIN : "null",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Pick-Key",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function reply(origin, status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...cors(origin) },
  });
}

// Constant-time comparison, so the key can't be guessed by timing.
function sameKey(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export default {
  // Job 1: the weekday morning start. Two UTC times are booked (winter and summer);
  // only the one that is 07:xx in London goes ahead.
  async scheduled(event, env, ctx) {
    const { hour, weekday } = londonNow(new Date(event.scheduledTime));
    if (hour !== 7) return;
    const windowHours = weekday === "Mon" ? "72" : "48";
    const err = await dispatch(env, "scrape.yml", { window_hours: windowHours });
    if (err) console.log("Morning start failed: " + err);
  },

  // Job 2: the "Summarise my picks" button.
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
    if (url.pathname !== "/summarise" || request.method !== "POST") return reply(origin, 404, { error: "Not found" });
    if (origin !== ALLOWED_ORIGIN) return reply(origin, 403, { error: "Not allowed from this page" });
    if (!env.PICK_KEY || !sameKey(request.headers.get("X-Pick-Key") || "", env.PICK_KEY))
      return reply(origin, 401, { error: "Wrong access key" });

    let ids;
    try {
      ids = (await request.json()).ids;
    } catch {
      return reply(origin, 400, { error: "Could not read the request" });
    }
    if (!Array.isArray(ids) || ids.length === 0 || ids.length > MAX_IDS || !ids.every((i) => ID_RE.test(i)))
      return reply(origin, 400, { error: `Send between 1 and ${MAX_IDS} story ids` });

    const err = await dispatch(env, "summarise-picks.yml", { ids: [...new Set(ids)].join(",") });
    if (err) return reply(origin, 502, { error: err });
    return reply(origin, 202, { ok: true, queued: ids.length });
  },
};
