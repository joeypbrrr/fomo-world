/**
 * Optional manual scan in the browser.
 * DexScreener and GeckoTerminal send Access-Control-Allow-Origin: *.
 * News, Google Trends, Wikipedia, and Reddit stay on the Python publisher.
 * Nothing here is written to gh-pages.
 */

const STOP = new Set(["the", "and", "for", "with", "coin", "token", "inu", "sol", "solana", "eth", "ethereum", "base", "usd", "usdc", "swap", "pool", "official", "meme", "pump", "dex"]);
const BRANDS = new Set(["tesla", "elon", "musk", "trump", "nike", "apple", "google", "nvidia", "disney", "openai", "bitcoin", "pepe", "doge"]);
const NOUNS = ["Sprout", "Lantern", "Minnow", "Kettle", "Orbit", "Acorn", "Puddle", "Nest", "Comet", "Locket"];

function words(value) {
  return (value || "").toLowerCase().match(/[a-z][a-z0-9]{3,}/g)?.filter((word) => word.length >= 4 && !STOP.has(word)) || [];
}

function num(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

async function getJson(url, headers) {
  const response = await fetch(url, { headers });
  if (!response.ok) throw new Error(`${response.status} ${url}`);
  return response.json();
}

function hash(text) {
  let value = 0;
  for (const char of text) value = (value * 33 + char.charCodeAt(0)) >>> 0;
  return value;
}

export async function browserScan() {
  const errors = [];
  const profiles = await getJson("https://api.dexscreener.com/token-profiles/latest/v1").catch((error) => {
    errors.push(String(error));
    return [];
  });
  const boosts = await getJson("https://api.dexscreener.com/token-boosts/top/v1").catch((error) => {
    errors.push(String(error));
    return [];
  });
  const gecko = await getJson("https://api.geckoterminal.com/api/v2/networks/trending_pools?page=1", {
    Accept: "application/json;version=20230203",
  }).catch((error) => {
    errors.push(String(error));
    return { data: [] };
  });

  const map = new Map();
  function upsert(token) {
    if (!token.chain || !token.address) return;
    const key = `${token.chain}:${token.address}`;
    const current = map.get(key) || token;
    if (token.description && !current.description) current.description = token.description;
    if (token.volume_usd != null) current.volume_usd = token.volume_usd;
    if (token.market_cap_usd != null) current.market_cap_usd = token.market_cap_usd;
    if (token.price_change_h24 != null) current.price_change_h24 = token.price_change_h24;
    if (token.name) current.name = token.name;
    if (token.symbol) current.symbol = token.symbol;
    map.set(key, current);
  }
  for (const row of [...profiles, ...boosts]) {
    upsert({
      chain: row.chainId,
      address: row.tokenAddress,
      name: "",
      symbol: "",
      description: row.description || "",
      volume_usd: null,
      market_cap_usd: null,
      price_change_h24: null,
      dexscreener_url: row.url || (row.chainId && row.tokenAddress ? `https://dexscreener.com/${row.chainId}/${row.tokenAddress}` : ""),
    });
  }
  for (const row of gecko.data || []) {
    const id = row.relationships?.base_token?.data?.id || "";
    const split = id.indexOf("_");
    if (split < 0) continue;
    const attrs = row.attributes || {};
    const base = (attrs.name || "").split("/")[0].trim();
    upsert({
      chain: id.slice(0, split),
      address: id.slice(split + 1),
      name: base,
      symbol: base,
      description: "",
      volume_usd: num(attrs.volume_usd?.h24),
      market_cap_usd: num(attrs.market_cap_usd ?? attrs.fdv_usd),
      price_change_h24: num(attrs.price_change_percentage?.h24),
      dexscreener_url: `https://dexscreener.com/${id.slice(0, split)}/${id.slice(split + 1)}`,
    });
  }
  const addresses = [...map.values()].slice(0, 30).map((token) => token.address).filter(Boolean);
  if (addresses.length) {
    const pairs = await getJson(`https://api.dexscreener.com/latest/dex/tokens/${addresses.join(",")}`).catch((error) => {
      errors.push(String(error));
      return { pairs: [] };
    });
    for (const pair of pairs.pairs || []) {
      const base = pair.baseToken || {};
      upsert({
        chain: pair.chainId,
        address: base.address,
        name: base.name || "",
        symbol: base.symbol || "",
        description: "",
        volume_usd: num(pair.volume?.h24),
        market_cap_usd: num(pair.marketCap ?? pair.fdv),
        price_change_h24: num(pair.priceChange?.h24),
        dexscreener_url: pair.url || "",
      });
    }
  }

  const tokens = [...map.values()];
  const buckets = new Map();
  for (const token of tokens) {
    for (const word of new Set(words(`${token.name} ${token.symbol}`))) {
      if (!buckets.has(word)) buckets.set(word, []);
      buckets.get(word).push(token);
    }
  }
  const groups = [];
  const used = new Set();
  for (const [word, members] of buckets) {
    const unique = [];
    for (const token of members) {
      const key = `${token.chain}:${token.address}`;
      if (unique.some((item) => `${item.chain}:${item.address}` === key)) continue;
      unique.push(token);
    }
    if (unique.length < 2) continue;
    groups.push({ classification: "META", theme: word, tokens: unique });
    unique.forEach((token) => used.add(`${token.chain}:${token.address}`));
  }
  for (const token of tokens) {
    if (used.has(`${token.chain}:${token.address}`)) continue;
    groups.push({ classification: "LAUNCHPAD", theme: "", tokens: [token] });
  }

  const ideas = groups.map((group) => {
    const volume = group.tokens.reduce((sum, token) => sum + (token.volume_usd || 0), 0);
    const description = group.tokens.map((token) => token.description).find(Boolean) || "";
    const sourced = Boolean(description.trim());
    const raw = Math.min(100, Math.log10(volume + 1) * 8 + Math.min(25, (group.tokens.length - 1) * 8));
    const score = Math.round((sourced ? raw : raw * 0.45) * 10) / 10;
    const theme = group.theme && !BRANDS.has(group.theme) ? group.theme : words(group.tokens[0].name).find((word) => !BRANDS.has(word)) || "";
    const seed = hash(`${group.classification}:${group.theme}:${group.tokens[0].address}`);
    const head = theme ? theme[0].toUpperCase() + theme.slice(1) : "Pebble";
    const name = `${head} ${NOUNS[seed % NOUNS.length]}`;
    const ticker = (name.replace(/[aeiou\s]/gi, "").slice(0, 5) || "XCON").toUpperCase();
    const id = `b_${seed.toString(16)}`;
    return {
      id,
      classification: group.classification,
      concept_kind: group.classification === "META" ? "beta coin" : "launchpad",
      trend_name: group.classification === "META" ? `${group.theme} meta` : `${group.tokens[0].name || group.tokens[0].symbol || "token"} launchpad`,
      name,
      token_name: name,
      ticker,
      description: sourced
        ? `Browser-scan concept. Riffs on the DexScreener profile: "${description.slice(0, 140)}"`
        : "Browser-scan concept. Trend context: trend unclear.",
      cluster_note: group.classification === "META"
        ? `${group.tokens.length} tokens share '${group.theme}' in this browser pass.`
        : "Single token in this browser pass.",
      score,
      trend_context: {
        status: sourced ? "sourced" : "trend unclear",
        why: sourced ? `DexScreener profile: "${description.slice(0, 320)}"` : "trend unclear",
        meme_or_story: sourced ? `DexScreener profile: "${description.slice(0, 320)}"` : "trend unclear",
        driver: "driver unclear — browser scan does not read profile links",
        freshness: {
          phase: "unclear",
          basis: "Browser scan does not compute pool age. See the published 30-minute scan.",
          started_at: null,
        },
        sources: sourced && group.tokens[0].dexscreener_url ? [{
          kind: "dexscreener_profile",
          title: group.tokens[0].name || group.tokens[0].symbol || "profile",
          url: group.tokens[0].dexscreener_url,
          snippet: description.slice(0, 320),
        }] : [],
      },
      source_tokens: group.tokens.slice(0, 6).map((token) => ({
        name: token.name,
        symbol: token.symbol,
        chain: token.chain,
        address: token.address,
        dexscreener_url: token.dexscreener_url,
        volume_usd: token.volume_usd,
        market_cap_usd: token.market_cap_usd,
      })),
      risk_note: "Trademark and impersonation risk: unofficial concept from a manual browser scan. Not affiliated with any person, brand, or source token. This site does not deploy tokens.",
      socials_text: `${name} ($${ticker}) — unofficial browser-scan concept. Not a launched token.`,
      art: { seed: id, palette: seed % 6, body: seed % 4, ears: (seed >> 3) % 4, accent: (seed >> 5) % 4 },
      image_file: "",
    };
  });
  ideas.sort((a, b) => b.score - a.score);
  const now = new Date();
  return {
    schema: "fomo-world.ideas.v1",
    data_origin: "browser-scan",
    label: "Manual browser scan. Not the published 30-minute snapshot.",
    generated_at: now.toISOString(),
    scan_interval_seconds: 1800,
    next_scan_at: new Date(now.getTime() + 1800 * 1000).toISOString(),
    ideas: ideas.slice(0, 10).map((idea, index) => ({ ...idea, rank: index + 1 })),
    feed: [],
    errors,
    sources_skipped: [
      { id: "google-news", reason: "Browser scan does not call Google News. The publisher does." },
      { id: "google-trends", reason: "Browser scan does not call Google Trends. The publisher does." },
      { id: "wikipedia", reason: "Browser scan does not call Wikipedia. The publisher does." },
      { id: "reddit", reason: "Browser scan does not call Reddit. The publisher does." },
    ],
  };
}
