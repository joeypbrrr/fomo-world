/** Load the published scan and keep the 30-minute clock in ET. */

export async function loadIdeas() {
  const response = await fetch(`data/ideas.json?ts=${Date.now()}`);
  if (!response.ok) throw new Error(`ideas.json returned ${response.status}`);
  return response.json();
}

export async function loadExample() {
  const response = await fetch(`data/example-ideas.json?ts=${Date.now()}`);
  if (!response.ok) throw new Error(`example-ideas.json returned ${response.status}`);
  return response.json();
}

export function formatET(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(date);
}

export function countdown(doc, now = new Date()) {
  if (!doc?.next_scan_at) return { text: "—", overdue: false };
  const next = new Date(doc.next_scan_at);
  if (Number.isNaN(next.getTime())) return { text: "—", overdue: false };
  const ms = next.getTime() - now.getTime();
  if (ms <= 0) return { text: "overdue", overdue: true };
  const total = Math.floor(ms / 1000);
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return { text: `${minutes}m ${String(seconds).padStart(2, "0")}s`, overdue: false };
}

export function usd(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "n/a";
  const number = Number(value);
  const abs = Math.abs(number);
  const sign = number < 0 ? "-" : "";
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

export function safeUrl(value) {
  try {
    const url = new URL(value);
    if (url.protocol === "https:" || url.protocol === "http:") return url.href;
  } catch {
    return null;
  }
  return null;
}

export function mountClock({ scanned, next, banner }, getDoc) {
  function paint() {
    const doc = getDoc();
    if (!doc) return;
    if (scanned) scanned.textContent = formatET(doc.generated_at);
    if (next) {
      const left = countdown(doc);
      next.textContent = left.overdue ? "overdue — waiting on the 30-minute publisher" : left.text;
    }
    if (banner) {
      banner.hidden = doc.data_origin === "live";
      if (doc.data_origin === "example") {
        banner.textContent = doc.label || "Example data — not a live scan.";
      } else if (doc.data_origin === "browser-scan") {
        banner.textContent = "Manual browser scan. News, Google Trends, Wikipedia, and Reddit run on the 30-minute publisher. This pass uses DexScreener and GeckoTerminal only, and it is not published.";
      } else if (doc.data_origin !== "live") {
        banner.textContent = doc.label || doc.data_origin;
      }
    }
  }
  paint();
  setInterval(paint, 1000);
  return paint;
}
