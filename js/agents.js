/** FOMO agents. Ids match research/roster.py. */
export const AGENTS = [
  { id: "nib", name: "Nib", role: "Trend Scout", color: "#e07a3d", line: "Checks the trend board twice before calling it a theme." },
  { id: "pico", name: "Pico", role: "Trend Scout", color: "#ef9a55", line: "Listens for volume first." },
  { id: "kip", name: "Kip", role: "Trend Scout", color: "#c46a3a", line: "Watches how fresh a pool is." },
  { id: "mara", name: "Mara", role: "Token Tracker", color: "#3d7ea6", line: "Wants the DexScreener link, not the vibe." },
  { id: "jun", name: "Jun", role: "Token Tracker", color: "#5aa0c4", line: "Reads market cap and says n/a when it is missing." },
  { id: "ada", name: "Ada", role: "Token Tracker", color: "#2f6d8f", line: "Stays on the token radar." },
  { id: "solene", name: "Solene", role: "Meta Spotter", color: "#7a6bb5", line: "Counts tokens that share a word." },
  { id: "bex", name: "Bex", role: "Meta Spotter", color: "#9a86d4", line: "Names the meta in one word." },
  { id: "fizz", name: "Fizz", role: "Meta Spotter", color: "#6554a0", line: "Looks for cousin tickers." },
  { id: "otis", name: "Otis", role: "Derivative Designer", color: "#d45d7a", line: "A beta coin is a riff, not a clone." },
  { id: "luma", name: "Luma", role: "Derivative Designer", color: "#e7899e", line: "The ticker has to fit on a badge." },
  { id: "vee", name: "Vee", role: "Derivative Designer", color: "#b84568", line: "Wants a real coin logo, not a copied mark." },
  { id: "hank", name: "Hank", role: "Launchpad Analyst", color: "#3f7d55", line: "Wants the launch kit fast to paste." },
  { id: "rae", name: "Rae", role: "Launchpad Analyst", color: "#6aaa78", line: "Lines up token name, ticker, and image." },
  { id: "dot", name: "Dot", role: "Launchpad Analyst", color: "#2f6848", line: "Freshness belongs on the card." },
  { id: "quill", name: "Quill", role: "Skeptic", color: "#8a6a3b", line: "Puts trademark and impersonation risk on every idea." },
  { id: "moss", name: "Moss", role: "Skeptic", color: "#a88858", line: "Will not fill in a volume that was not returned." },
  { id: "rue", name: "Rue", role: "Skeptic", color: "#6e5430", line: "Says trend unclear rather than invent a story." },
];

export const AGENT_BY_ID = Object.fromEntries(AGENTS.map((agent) => [agent.id, agent]));

export const STATIONS = [
  { id: "trend", title: "Trend board", blurb: "Themes and headlines" },
  { id: "radar", title: "Token radar", blurb: "Volume and market cap" },
  { id: "lab", title: "Idea lab", blurb: "Beta coins and derivatives" },
  { id: "desk", title: "Launchpad desk", blurb: "Name, ticker, image" },
];
