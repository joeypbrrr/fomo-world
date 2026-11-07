/** Polished procedural coin art. A placeholder until images/<id>.png exists. */

const PALETTES = [
  { bg: ["#fff1d6", "#f08a4b"], rim: ["#fff7df", "#e2b15a", "#a87422"], body: "#ff8d6a", belly: "#ffe3cf", ink: "#3a2418", cheek: "#ffb1a0" },
  { bg: ["#e5f6ff", "#6aa6e4"], rim: ["#f4f7fb", "#c5d0dc", "#7d8b99"], body: "#6dcec0", belly: "#e9fff8", ink: "#14332c", cheek: "#ffd0c8" },
  { bg: ["#fff0f4", "#e36b8a"], rim: ["#fff6ea", "#f0c27a", "#c4893a"], body: "#ffd36a", belly: "#fff6dc", ink: "#3d2a12", cheek: "#ffb4c4" },
  { bg: ["#eef6e4", "#7db86a"], rim: ["#fff8e8", "#d7b56a", "#8d6a2f"], body: "#f2a35a", belly: "#fff0dc", ink: "#2c2416", cheek: "#ffc1ae" },
  { bg: ["#f3e9ff", "#8d74d6"], rim: ["#fff", "#d9c7f5", "#8d74c4"], body: "#ff9eb5", belly: "#fff0f4", ink: "#2c2140", cheek: "#ffc2d1" },
  { bg: ["#fff6e8", "#e07a3d"], rim: ["#fffaf0", "#f0d08a", "#b8863a"], body: "#7eb0e0", belly: "#f3f8ff", ink: "#1c2a3a", cheek: "#ffd0c2" },
];

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function mascot(ctx, cx, cy, r, art, palette) {
  const body = palette.body;
  ctx.save();
  ctx.translate(cx, cy + r * 0.06);
  ctx.fillStyle = "rgba(40, 24, 16, 0.16)";
  ctx.beginPath();
  ctx.ellipse(0, r * 0.42, r * 0.46, r * 0.1, 0, 0, Math.PI * 2);
  ctx.fill();

  if (art.ears === 0) {
    ctx.fillStyle = body;
    ctx.beginPath();
    ctx.ellipse(-r * 0.28, -r * 0.42, r * 0.16, r * 0.22, -0.4, 0, Math.PI * 2);
    ctx.ellipse(r * 0.28, -r * 0.42, r * 0.16, r * 0.22, 0.4, 0, Math.PI * 2);
    ctx.fill();
  } else if (art.ears === 1) {
    ctx.fillStyle = body;
    ctx.beginPath();
    ctx.moveTo(-r * 0.22, -r * 0.2);
    ctx.lineTo(-r * 0.08, -r * 0.62);
    ctx.lineTo(r * 0.02, -r * 0.18);
    ctx.moveTo(r * 0.22, -r * 0.2);
    ctx.lineTo(r * 0.08, -r * 0.62);
    ctx.lineTo(-r * 0.02, -r * 0.18);
    ctx.fill();
  } else if (art.ears === 2) {
    ctx.fillStyle = palette.rim[1];
    ctx.beginPath();
    ctx.arc(-r * 0.34, -r * 0.28, r * 0.16, 0, Math.PI * 2);
    ctx.arc(r * 0.34, -r * 0.28, r * 0.16, 0, Math.PI * 2);
    ctx.fill();
  } else {
    ctx.strokeStyle = palette.ink;
    ctx.lineWidth = r * 0.05;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.arc(-r * 0.16, -r * 0.48, r * 0.16, Math.PI, Math.PI * 1.8);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(r * 0.16, -r * 0.48, r * 0.16, Math.PI * 1.2, Math.PI * 2);
    ctx.stroke();
  }

  const gradient = ctx.createRadialGradient(-r * 0.2, -r * 0.25, r * 0.1, 0, 0, r * 0.62);
  gradient.addColorStop(0, "#fff");
  gradient.addColorStop(0.35, body);
  gradient.addColorStop(1, palette.ink);
  ctx.fillStyle = gradient;
  ctx.beginPath();
  if (art.body === 1) ctx.ellipse(0, 0, r * 0.46, r * 0.4, 0, 0, Math.PI * 2);
  else if (art.body === 2) ctx.ellipse(0, r * 0.04, r * 0.42, r * 0.48, 0, 0, Math.PI * 2);
  else ctx.arc(0, 0, r * 0.42, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = palette.belly;
  ctx.beginPath();
  ctx.ellipse(0, r * 0.12, r * 0.24, r * 0.2, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = palette.cheek;
  ctx.globalAlpha = 0.9;
  ctx.beginPath();
  ctx.arc(-r * 0.2, r * 0.06, r * 0.07, 0, Math.PI * 2);
  ctx.arc(r * 0.2, r * 0.06, r * 0.07, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;

  ctx.fillStyle = palette.ink;
  ctx.beginPath();
  ctx.ellipse(-r * 0.12, -r * 0.04, r * 0.045, r * 0.055, 0, 0, Math.PI * 2);
  ctx.ellipse(r * 0.12, -r * 0.04, r * 0.045, r * 0.055, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#fff";
  ctx.beginPath();
  ctx.arc(-r * 0.11, -r * 0.06, r * 0.016, 0, Math.PI * 2);
  ctx.arc(r * 0.135, -r * 0.06, r * 0.016, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = palette.ink;
  ctx.lineWidth = Math.max(2, r * 0.035);
  ctx.lineCap = "round";
  ctx.beginPath();
  if (art.accent % 2 === 0) ctx.arc(0, r * 0.04, r * 0.1, 0.15 * Math.PI, 0.85 * Math.PI);
  else ctx.arc(0, r * 0.12, r * 0.08, 1.15 * Math.PI, 1.85 * Math.PI);
  ctx.stroke();
  ctx.restore();
}

export function drawCoin(canvas, art = {}, ticker = "") {
  const size = canvas.width;
  const ctx = canvas.getContext("2d");
  const palette = PALETTES[(art.palette || 0) % PALETTES.length];
  const background = ctx.createRadialGradient(size * 0.5, size * 0.42, size * 0.08, size * 0.5, size * 0.5, size * 0.72);
  background.addColorStop(0, palette.bg[0]);
  background.addColorStop(1, palette.bg[1]);
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, size, size);

  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.4;
  ctx.fillStyle = "rgba(48, 28, 12, 0.18)";
  ctx.beginPath();
  ctx.ellipse(cx, cy + radius * 0.95, radius * 0.72, radius * 0.1, 0, 0, Math.PI * 2);
  ctx.fill();

  const rim = ctx.createLinearGradient(cx - radius, cy - radius, cx + radius, cy + radius);
  rim.addColorStop(0, palette.rim[0]);
  rim.addColorStop(0.45, palette.rim[1]);
  rim.addColorStop(1, palette.rim[2]);
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.fillStyle = rim;
  ctx.fill();

  const face = ctx.createRadialGradient(cx - radius * 0.28, cy - radius * 0.32, radius * 0.08, cx, cy, radius * 0.8);
  face.addColorStop(0, "#fffdf8");
  face.addColorStop(0.55, palette.bg[0]);
  face.addColorStop(1, palette.bg[1]);
  ctx.beginPath();
  ctx.arc(cx, cy, radius * 0.84, 0, Math.PI * 2);
  ctx.fillStyle = face;
  ctx.fill();

  ctx.fillStyle = "rgba(255,255,255,0.55)";
  ctx.beginPath();
  ctx.ellipse(cx - radius * 0.12, cy - radius * 0.5, radius * 0.34, radius * 0.12, -0.5, 0, Math.PI * 2);
  ctx.fill();

  mascot(ctx, cx, cy - radius * 0.04, radius, art, palette);

  const label = (ticker || "CONCEPT").slice(0, 6);
  ctx.font = `700 ${Math.round(size * 0.07)}px Georgia, "Times New Roman", serif`;
  const width = Math.min(radius * 1.3, ctx.measureText(label).width + size * 0.08);
  const badgeY = cy + radius * 0.52;
  ctx.fillStyle = palette.ink;
  roundRect(ctx, cx - width / 2, badgeY, width, size * 0.09, size * 0.045);
  ctx.fill();
  ctx.fillStyle = "#fffaf3";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label, cx, badgeY + size * 0.047);

  ctx.font = `600 ${Math.round(size * 0.032)}px Georgia, "Times New Roman", serif`;
  ctx.fillStyle = "rgba(28, 36, 32, 0.62)";
  ctx.textBaseline = "alphabetic";
  ctx.fillText("PLACEHOLDER", cx, size * 0.955);
}

export function mountArt(host, idea) {
  host.replaceChildren();
  host.classList.add("is-placeholder");
  const canvas = document.createElement("canvas");
  canvas.width = 1000;
  canvas.height = 1000;
  canvas.className = "coin-canvas";
  drawCoin(canvas, idea.art || {}, idea.ticker || "");
  host.append(canvas);
  const file = idea.image_file;
  if (!file) return canvas;
  const img = new Image();
  img.alt = `${idea.token_name || "Concept"} coin logo`;
  img.className = "coin-canvas";
  img.onload = () => {
    host.replaceChildren(img);
    host.classList.remove("is-placeholder");
  };
  img.src = file;
  return canvas;
}

export function downloadCoin(idea) {
  const file = idea.image_file;
  const link = document.createElement("a");
  link.download = `${(idea.ticker || "concept").toLowerCase()}-1000.png`;
  if (file) {
    fetch(file).then((res) => {
      if (!res.ok) throw new Error("missing");
      return res.blob();
    }).then((blob) => {
      link.href = URL.createObjectURL(blob);
      link.click();
    }).catch(() => downloadCanvas(idea, link));
    return;
  }
  downloadCanvas(idea, link);
}

function downloadCanvas(idea, link) {
  const canvas = document.createElement("canvas");
  canvas.width = 1000;
  canvas.height = 1000;
  drawCoin(canvas, idea.art || {}, idea.ticker || "");
  link.href = canvas.toDataURL("image/png");
  link.click();
}
