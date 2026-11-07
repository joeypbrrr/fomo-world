import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DObject, CSS2DRenderer } from "three/addons/renderers/CSS2DRenderer.js";
import { AGENTS, AGENT_BY_ID, STATIONS } from "./agents.js";
import { renderCard, renderEmpty, renderFeed } from "./cards.js";
import { loadIdeas, mountClock } from "./data.js";

const shot = new URLSearchParams(location.search).get("shot") === "1";
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const routes = {
  "Trend Scout": ["trend", "radar", "lab"],
  "Token Tracker": ["radar", "trend", "desk"],
  "Meta Spotter": ["lab", "trend", "radar"],
  "Derivative Designer": ["lab", "desk", "trend"],
  "Launchpad Analyst": ["desk", "lab", "radar"],
  Skeptic: ["trend", "radar", "lab", "desk"],
};
const spots = {
  trend: new THREE.Vector3(0, 0, -6.2),
  radar: new THREE.Vector3(6.3, 0, 0.2),
  lab: new THREE.Vector3(0.2, 0, 6.3),
  desk: new THREE.Vector3(-6.3, 0, -0.2),
};

const viewport = document.getElementById("viewport");
const feedList = document.getElementById("feed");
const board = document.getElementById("idea-board");
let published = null;
let showing = null;
let framed = false;
let dataSettled = false;

function markReady() {
  if (framed && dataSettled) document.body.dataset.ready = "1";
}

mountClock({
  scanned: document.getElementById("last-scanned"),
  next: document.getElementById("countdown"),
  banner: document.getElementById("origin-banner"),
}, () => published);

function showDoc(doc) {
  showing = doc;
  renderFeed(feedList, doc.feed || [], AGENT_BY_ID);
  board.replaceChildren();
  if (!doc.ideas?.length) {
    renderEmpty(board, doc);
    return;
  }
  for (const idea of doc.ideas.slice(0, 4)) board.append(renderCard(idea, { compact: true }));
  const more = document.createElement("a");
  more.className = "button ghost";
  more.href = "top10.html";
  more.textContent = "All 10 on the Top 10 Launchable page";
  board.append(more);
}

loadIdeas().then((doc) => {
  published = doc;
  showDoc(doc);
  assignLines(doc.feed || []);
  dataSettled = true;
  markReady();
}).catch((error) => {
  board.replaceChildren();
  const p = document.createElement("p");
  p.className = "empty";
  p.textContent = `Could not read data/ideas.json (${error.message}). Nothing was invented to fill the board.`;
  board.append(p);
  dataSettled = true;
  markReady();
});

document.getElementById("reread")?.addEventListener("click", async () => {
  try {
    published = await loadIdeas();
    showDoc(published);
    assignLines(published.feed || []);
  } catch (error) {
    document.getElementById("origin-banner").hidden = false;
    document.getElementById("origin-banner").textContent = error.message;
  }
});

const scene = new THREE.Scene();
scene.background = new THREE.Color("#f3ecdf");
scene.fog = new THREE.Fog("#f3ecdf", 18, 36);
const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 80);
camera.position.set(7.4, 5.4, 8.6);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
viewport.append(renderer.domElement);
const labels = new CSS2DRenderer();
labels.domElement.className = "label-layer";
viewport.append(labels.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.05, 0);
controls.enableDamping = true;
controls.maxPolarAngle = 1.25;
controls.minDistance = 7;
controls.maxDistance = 24;
controls.update();

scene.add(new THREE.HemisphereLight("#fff4e2", "#8fb56a", 1.15));
const sun = new THREE.DirectionalLight("#fff7ea", 1.1);
sun.position.set(6, 10, 4);
scene.add(sun);

function mesh(geometry, color, x, y, z) {
  const material = new THREE.MeshLambertMaterial({ color });
  const object = new THREE.Mesh(geometry, material);
  object.position.set(x, y, z);
  scene.add(object);
  return object;
}

const water = mesh(new THREE.CircleGeometry(16, 48), "#b7d4ea", 0, -0.72, 0);
water.rotation.x = -Math.PI / 2;
const island = mesh(new THREE.CylinderGeometry(8.6, 9.4, 1.15, 40), "#8fce86", 0, -0.2, 0);
mesh(new THREE.CylinderGeometry(5.4, 5.4, 0.08, 40), "#f0e2c4", 0, 0.42, 0);

function signTexture(title) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fffaf3";
  ctx.fillRect(0, 0, 512, 256);
  ctx.strokeStyle = "#1c2420";
  ctx.lineWidth = 14;
  ctx.strokeRect(10, 10, 492, 236);
  ctx.fillStyle = "#1c2420";
  ctx.font = "700 58px Georgia, serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(title, 256, 128);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function station(id, position, color) {
  const group = new THREE.Group();
  const base = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.7, 1.2), new THREE.MeshLambertMaterial({ color }));
  base.position.y = 0.7;
  const post = new THREE.Mesh(new THREE.BoxGeometry(0.12, 1.1, 0.12), new THREE.MeshLambertMaterial({ color: "#6b4b2a" }));
  post.position.y = 1.55;
  const board = new THREE.Mesh(
    new THREE.PlaneGeometry(2.3, 1.05),
    new THREE.MeshBasicMaterial({ map: signTexture(STATIONS.find((item) => item.id === id).title) }),
  );
  board.position.y = 2.25;
  group.add(base, post, board);
  group.position.copy(position);
  if (id === "radar") group.lookAt(0, 1, 0);
  scene.add(group);
  return group;
}

for (const [id, position] of Object.entries(spots)) {
  const colors = { trend: "#e7b15a", radar: "#7eb6d8", lab: "#d98ab0", desk: "#8fce86" };
  station(id, position, colors[id]);
}

for (let i = 0; i < 7; i += 1) {
  const angle = (i / 7) * Math.PI * 2;
  const radius = 7.1;
  mesh(new THREE.ConeGeometry(0.45, 1.3, 8), "#3f7d55", Math.cos(angle) * radius, 1.05, Math.sin(angle) * radius);
  mesh(new THREE.CylinderGeometry(0.1, 0.12, 0.45, 6), "#6b4b2a", Math.cos(angle) * radius, 0.35, Math.sin(angle) * radius);
}

const radarDish = mesh(new THREE.TorusGeometry(0.55, 0.08, 8, 20), "#1c2420", 6.3, 1.35, 0.2);
radarDish.rotation.x = Math.PI / 2.4;

function person(color) {
  const group = new THREE.Group();
  const cloth = new THREE.MeshLambertMaterial({ color });
  const skin = new THREE.MeshLambertMaterial({ color: "#ffd7bf" });
  const ink = new THREE.MeshLambertMaterial({ color: "#1c2420" });
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.38, 16, 12), cloth);
  body.scale.y = 1.18;
  body.position.y = 0.62;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.26, 16, 12), skin);
  head.position.y = 1.22;
  const left = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 8), ink);
  left.position.set(-0.08, 1.26, 0.22);
  const right = left.clone();
  right.position.x = 0.08;
  group.add(body, head, left, right);
  return group;
}

const actors = AGENTS.map((agent, index) => {
  const group = person(agent.color);
  const route = routes[agent.role] || routes.Skeptic;
  const home = spots[route[index % route.length]];
  const spread = ((index % 5) - 2) * 0.45;
  group.position.set(home.x + spread, 0, home.z + ((index % 3) - 1) * 0.4);
  const name = document.createElement("div");
  name.className = "agent-name";
  name.textContent = agent.name;
  const nameLabel = new CSS2DObject(name);
  nameLabel.position.set(0, 1.78, 0);
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.hidden = true;
  const bubbleLabel = new CSS2DObject(bubble);
  bubbleLabel.position.set(0, 2.35, 0);
  group.add(nameLabel, bubbleLabel);
  scene.add(group);
  return {
    agent,
    group,
    bubble,
    route,
    stop: index % route.length,
    pause: index * 0.35,
  };
});

let feedLines = [];
function assignLines(feed) {
  feedLines = feed || [];
  if (shot) {
    actors.forEach((actor, index) => {
      const angle = -0.85 + (index / Math.max(actors.length - 1, 1)) * 1.7;
      const radius = index % 2 === 0 ? 2.8 : 4.4;
      actor.group.position.set(Math.sin(angle) * radius, 0.42, 1.1 + Math.cos(angle) * radius * 0.45);
      actor.group.lookAt(camera.position.x, 1, camera.position.z);
    });
    const speakers = [0, 8, 15];
    speakers.forEach((index, nth) => {
      const line = feedLines[nth];
      const actor = actors[index];
      if (!line || !actor) return;
      actor.bubble.hidden = false;
      actor.bubble.textContent = line.text;
    });
  }
}

let lineCursor = 0;
let talkUntil = 0;
function talk(now) {
  if (!feedLines.length || shot) return;
  if (now < talkUntil) return;
  const line = feedLines[lineCursor % feedLines.length];
  lineCursor += 1;
  for (const actor of actors) {
    const mine = actor.agent.id === line.agent_id;
    actor.bubble.hidden = !mine;
    if (mine) actor.bubble.textContent = line.text;
  }
  talkUntil = now + 4200;
}

function resize() {
  const width = viewport.clientWidth || 320;
  const height = viewport.clientHeight || 320;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height, false);
  labels.setSize(width, height);
}
window.addEventListener("resize", resize);

const clock = new THREE.Clock();
function frame(now) {
  const delta = Math.min(clock.getDelta(), 0.05);
  if (!reduced && !shot) {
    for (const actor of actors) {
      if (actor.pause > 0) {
        actor.pause -= delta;
        actor.group.position.y = Math.sin(now / 280 + actor.stop) * 0.04;
        continue;
      }
      const nextId = actor.route[actor.stop % actor.route.length];
      const goal = spots[nextId];
      const offset = actor.group.position.clone().setY(0);
      const flat = goal.clone();
      const direction = flat.sub(offset);
      const distance = direction.length();
      if (distance < 0.35) {
        actor.stop += 1;
        actor.pause = 1.1;
      } else {
        direction.normalize().multiplyScalar(delta * 1.35);
        actor.group.position.add(direction);
        actor.group.lookAt(actor.group.position.x + direction.x, 0.6, actor.group.position.z + direction.z);
      }
    }
    radarDish.rotation.z += delta * 0.8;
  }
  talk(now);
  controls.update();
  renderer.render(scene, camera);
  labels.render(scene, camera);
  if (!framed) {
    framed = true;
    markReady();
  }
  requestAnimationFrame(frame);
}

resize();
if (!renderer.getContext()) {
  document.getElementById("webgl-fallback").hidden = false;
  framed = true;
  markReady();
} else {
  requestAnimationFrame(frame);
}
