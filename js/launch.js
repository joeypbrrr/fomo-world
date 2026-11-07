import { downloadCoin, mountArt } from "./art.js";
import { whyBlock } from "./cards.js";
import { loadIdeas, mountClock, safeUrl, usd } from "./data.js";

const root = document.getElementById("kit");
const banner = document.getElementById("origin-banner");
let published = null;

mountClock({
  scanned: document.getElementById("last-scanned"),
  next: document.getElementById("countdown"),
  banner,
}, () => published);

function field(label, value) {
  const wrap = document.createElement("label");
  wrap.className = "field";
  const title = document.createElement("span");
  title.textContent = label;
  const row = document.createElement("div");
  row.className = "field-row";
  const text = document.createElement("textarea");
  text.readOnly = true;
  text.value = value || "";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "button ghost";
  button.textContent = "Copy";
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(text.value);
      button.textContent = "Copied";
    } catch {
      text.select();
      document.execCommand("copy");
      button.textContent = "Copied";
    }
    setTimeout(() => {
      button.textContent = "Copy";
    }, 1200);
  });
  row.append(text, button);
  wrap.append(title, row);
  return wrap;
}

function render(doc, idea) {
  root.replaceChildren();
  const art = document.createElement("div");
  art.className = "kit-art";
  mountArt(art, idea);
  const copy = document.createElement("div");
  copy.className = "kit-copy";
  const kicker = document.createElement("p");
  kicker.className = "kicker";
  kicker.textContent = `${idea.classification === "META" ? "META · beta coin" : "LAUNCHPAD"} · score ${idea.score}`;
  const title = document.createElement("h1");
  title.textContent = idea.token_name || idea.name;
  copy.append(kicker, title);
  copy.append(field("Token name", idea.token_name || idea.name || ""));
  copy.append(field("Ticker", idea.ticker || ""));
  copy.append(field("Description", idea.description || ""));
  copy.append(field("Suggested socials", idea.socials_text || ""));
  const actions = document.createElement("div");
  actions.className = "actions";
  const download = document.createElement("button");
  download.type = "button";
  download.className = "button";
  download.textContent = "Download 1000×1000 PNG";
  download.addEventListener("click", () => downloadCoin(idea));
  const open = document.createElement("a");
  open.className = "button";
  open.href = "https://pump.fun/create";
  open.target = "_blank";
  open.rel = "noopener noreferrer";
  open.textContent = "Open pump.fun create";
  actions.append(download, open);
  copy.append(actions);
  const fine = document.createElement("p");
  fine.className = "fine";
  fine.textContent = "FOMO World never creates, deploys, or launches a token. It does not connect a wallet, hold keys, or sign or send transactions. You launch it yourself, in your own wallet, on pump.fun. This page only copies concept text and opens their site.";
  copy.append(fine);
  copy.append(whyBlock(idea));
  const tokens = document.createElement("div");
  tokens.className = "token-list";
  const heading = document.createElement("h3");
  heading.textContent = "Trending tokens";
  tokens.append(heading);
  for (const token of idea.source_tokens || []) {
    const line = document.createElement("p");
    const href = safeUrl(token.dexscreener_url);
    const label = `${token.name || "token"} (${token.symbol || "n/a"}) · vol ${usd(token.volume_usd)} · mcap ${usd(token.market_cap_usd)}`;
    if (href) {
      const link = document.createElement("a");
      link.href = href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = label;
      line.append(link);
    } else {
      line.textContent = label;
    }
    tokens.append(line);
  }
  copy.append(tokens);
  const risk = document.createElement("p");
  risk.className = "risk";
  risk.textContent = idea.risk_note || "";
  copy.append(risk);
  root.append(art, copy);
  document.body.dataset.ready = "1";
}

loadIdeas().then((doc) => {
  published = doc;
  const id = new URLSearchParams(location.search).get("id");
  const idea = doc.ideas?.find((item) => item.id === id) || doc.ideas?.[0];
  if (!idea) {
    root.textContent = "This scan has no concepts to put in a launch kit.";
    document.body.dataset.ready = "1";
    return;
  }
  if (!id) history.replaceState(null, "", `launch.html?id=${encodeURIComponent(idea.id)}`);
  render(doc, idea);
}).catch((error) => {
  banner.hidden = false;
  banner.textContent = error.message;
  root.textContent = "Could not read data/ideas.json.";
  document.body.dataset.ready = "1";
});

setInterval(() => {
  loadIdeas().then((doc) => {
    published = doc;
  }).catch(() => {});
}, 60000);
