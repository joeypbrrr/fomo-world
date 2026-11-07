import { renderCard, renderEmpty } from "./cards.js";
import { loadExample, loadIdeas, mountClock } from "./data.js";
import { browserScan } from "./scan.js";

const grid = document.getElementById("grid");
const banner = document.getElementById("origin-banner");
let published = null;
let view = null;

const paint = mountClock({
  scanned: document.getElementById("last-scanned"),
  next: document.getElementById("countdown"),
  banner,
}, () => published);

function draw(doc) {
  view = doc;
  grid.replaceChildren();
  if (!doc.ideas?.length) {
    renderEmpty(grid, doc);
    return;
  }
  for (const idea of doc.ideas.slice(0, 10)) grid.append(renderCard(idea));
}

async function pull() {
  published = await loadIdeas();
  draw(published);
  paint();
}

pull().catch((error) => {
  banner.hidden = false;
  banner.textContent = `Could not read data/ideas.json (${error.message}).`;
  renderEmpty(grid, { errors: [error.message], sources_skipped: [], ideas: [] });
  document.body.dataset.ready = "1";
});

document.getElementById("reread").addEventListener("click", () => {
  pull().catch((error) => {
    banner.hidden = false;
    banner.textContent = error.message;
  });
});

document.getElementById("scan-now").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  banner.hidden = false;
  banner.textContent = "Scanning DexScreener and GeckoTerminal…";
  try {
    const doc = await browserScan();
    draw(doc);
    banner.hidden = false;
    banner.textContent = "Manual browser scan. News, Google Trends, Wikipedia, and Reddit run on the 30-minute publisher. This pass is not published. The countdown still follows the last published scan.";
  } catch (error) {
    banner.textContent = `Browser scan failed: ${error.message}`;
  }
  setTimeout(() => {
    button.disabled = false;
  }, 20000);
});

document.getElementById("show-example").addEventListener("click", async () => {
  try {
    const doc = await loadExample();
    draw(doc);
    banner.hidden = false;
    banner.textContent = doc.label;
  } catch (error) {
    banner.hidden = false;
    banner.textContent = error.message;
  }
});

setInterval(() => {
  if (view?.data_origin === "browser-scan" || view?.data_origin === "example") return;
  pull().catch(() => {});
}, 60000);

const ready = new MutationObserver(() => {
  if (grid.childElementCount) {
    document.body.dataset.ready = "1";
    ready.disconnect();
  }
});
ready.observe(grid, { childList: true });
