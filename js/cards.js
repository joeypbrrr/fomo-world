/** Idea cards shared by the world, the Top 10 page, and the launch kit. */

import { mountArt } from "./art.js";
import { formatET, safeUrl, usd } from "./data.js";

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function sourceList(idea) {
  const list = el("ul", "source-list");
  const sources = idea.trend_context?.sources || [];
  if (!sources.length) {
    list.append(el("li", "", "No cited source."));
    return list;
  }
  for (const source of sources) {
    const item = el("li");
    const href = safeUrl(source.url);
    const label = `${source.kind}: ${source.title || source.snippet || "source"}`;
    if (href) {
      const link = el("a", "", label);
      link.href = href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      item.append(link);
    } else {
      item.textContent = label;
    }
    list.append(item);
  }
  return list;
}

export function whyBlock(idea) {
  const context = idea.trend_context || {};
  const wrap = el("div", "why");
  wrap.append(el("h3", "", "Why this is trending"));
  const unclear = context.status !== "sourced";
  wrap.append(el("p", unclear ? "unclear" : "", context.why || "trend unclear"));
  if (context.meme_or_story && context.meme_or_story !== context.why) {
    wrap.append(el("p", "", context.meme_or_story));
  }
  wrap.append(el("p", "driver", `Who's driving it: ${context.driver || "driver unclear"}`));
  const fresh = context.freshness || {};
  const started = fresh.started_at ? formatET(fresh.started_at) : "start time not in the data";
  wrap.append(el(
    "p",
    "fresh",
    `Freshness: ${fresh.phase || "unclear"}. Started ${started}. ${fresh.basis || ""}`,
  ));
  if (idea.cluster_note) wrap.append(el("p", "cluster", idea.cluster_note));
  wrap.append(sourceList(idea));
  return wrap;
}

function tokenList(idea) {
  const list = el("ul", "token-list");
  for (const token of idea.source_tokens || []) {
    const item = el("li");
    const href = safeUrl(token.dexscreener_url);
    const name = `${token.name || "token"} (${token.symbol || "n/a"})`;
    if (href) {
      const link = el("a", "", name);
      link.href = href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      item.append(link);
    } else {
      item.append(el("span", "", name));
    }
    item.append(el(
      "span",
      "stats",
      ` · vol ${usd(token.volume_usd)} · mcap ${usd(token.market_cap_usd)}`,
    ));
    list.append(item);
  }
  if (!idea.source_tokens?.length) list.append(el("li", "", "No source trending tokens on this concept."));
  return list;
}

export function renderCard(idea, { compact = false } = {}) {
  const card = el("article", compact ? "card compact" : "card");
  card.dataset.id = idea.id;
  const art = el("div", "art");
  mountArt(art, idea);
  art.append(el("p", "art-note", "Placeholder art — polished procedural stand-in, not the final coin logo."));
  const body = el("div", "card-body");
  const pills = el("div", "pills");
  pills.append(el("span", "pill", idea.classification === "META" ? "META · beta coin" : "LAUNCHPAD"));
  pills.append(el("span", "pill score", `Score ${idea.score}`));
  if (idea.trend_context?.status !== "sourced") pills.append(el("span", "pill warn", "trend unclear · down-ranked"));
  body.append(pills);
  body.append(el("p", "kicker", idea.trend_name || ""));
  body.append(el("h2", "token-name", idea.token_name || idea.name || "Unnamed concept"));
  const ticker = el("p", "ticker");
  ticker.append(el("span", "label", "Ticker "));
  ticker.append(el("strong", "", idea.ticker || "—"));
  body.append(ticker);
  body.append(el("p", "desc", idea.description || ""));
  if (!compact) {
    body.append(whyBlock(idea));
    body.append(el("h3", "", "Trending tokens"));
    body.append(tokenList(idea));
    body.append(el("p", "risk", idea.risk_note || ""));
  }
  const launch = el("a", "button", "Launch");
  launch.href = `launch.html?id=${encodeURIComponent(idea.id)}`;
  body.append(launch);
  card.append(art, body);
  return card;
}

export function renderFeed(list, feed, agentsById) {
  list.replaceChildren();
  const rows = feed?.length ? feed : [];
  if (!rows.length) {
    list.append(el("li", "", "No agent notes in this scan."));
    return;
  }
  for (const row of rows.slice(0, 24)) {
    const agent = agentsById[row.agent_id];
    const item = el("li");
    item.append(el("strong", "", agent ? agent.name : row.agent_id));
    item.append(document.createTextNode(` · ${row.role || agent?.role || ""} — ${row.text || ""}`));
    list.append(item);
  }
}

export function renderEmpty(host, doc) {
  host.replaceChildren();
  const box = el("div", "empty");
  box.append(el("h2", "", "No launchable concepts in this scan."));
  box.append(el("p", "", "The pipeline did not invent tokens to fill the board. Source notes are below."));
  const errors = doc?.errors || [];
  const skipped = doc?.sources_skipped || [];
  const reports = (doc?.source_reports || []).filter((report) => report && report.ok === false);
  if (!errors.length && !skipped.length && !reports.length) {
    box.append(el("p", "", "Sources returned no usable tokens."));
  }
  for (const item of skipped) box.append(el("p", "", `${item.id}: ${item.reason}`));
  for (const item of reports) box.append(el("p", "", `${item.id}: ${item.error || "request failed"}`));
  for (const item of errors) box.append(el("p", "", String(item)));
  host.append(box);
}
