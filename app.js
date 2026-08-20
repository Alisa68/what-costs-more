const state = {
  period: 7,
  data: null,
  metrics: []
};

const fmtPct = value => {
  const sign = value > 0.004 ? "+" : value < -0.004 ? "−" : "";
  return sign + Math.abs(value).toLocaleString("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }) + "%";
};

const fmtDate = iso => {
  const [y,m,d] = iso.split("-");
  return `${d}.${m}.${y}`;
};

function cumulativeChange(indices, period) {
  if (period === 7) return indices.at(-1) - 100;
  const intervals = indices.slice(-4);
  const factor = intervals.reduce((acc, idx) => acc * (idx / 100), 1);
  return (factor - 1) * 100;
}

function getMetrics(period) {
  return state.data.items.map(item => ({...item, change: cumulativeChange(item.indices, period)})).sort((a,b) => b.change - a.change);
}

function maxAbs(metrics) { return Math.max(...metrics.map(d => Math.abs(d.change)), 0.01); }
function statusText(value) {
  if (value > 0.15) return "цена выросла";
  if (value < -0.15) return "цена снизилась";
  return "почти без изменений";
}

function buildSummary(metrics, period) {
  const leader = metrics[0];
  const decline = [...metrics].sort((a,b) => a.change - b.change)[0];
  const stable = [...metrics].sort((a,b) => Math.abs(a.change) - Math.abs(b.change))[0];
  const falling = metrics.filter(d => d.change < -0.15);
  const periodText = period === 7 ? "за неделю" : "за четыре недели";
  let text = `${leader.shortName} показал максимальный рост ${periodText}: ${fmtPct(leader.change)}. `;
  if (decline.change < -0.15) text += `Сильнее всего снизился ${decline.shortName.toLowerCase()}: ${fmtPct(decline.change)}. `;
  text += `Самая стабильная категория — ${stable.shortName.toLowerCase()} (${fmtPct(stable.change)}).`;
  if (falling.length >= 3) text += ` В ${falling.length} из 6 категорий за период зафиксировано снижение.`;
  return {leader, decline, stable, text};
}

function renderBars(metrics, containerId, share = false) {
  const max = maxAbs(metrics), el = document.getElementById(containerId); el.innerHTML = "";
  metrics.forEach(item => {
    const width = Math.min(Math.abs(item.change) / max * 48, 48), row = document.createElement("div");
    row.className = share ? "share-bar" : "bar-row";
    const name = document.createElement("div"); name.className = share ? "share-bar-name" : "bar-name"; name.textContent = item.shortName;
    const track = document.createElement("div"); track.className = share ? "share-bar-track" : "bar-track";
    const bar = document.createElement("div"); bar.className = share ? (item.change >= 0 ? "share-bar-pos" : "share-bar-neg") : (item.change >= 0 ? "bar-positive" : "bar-negative"); bar.style.width = `${width}%`; track.appendChild(bar);
    const val = document.createElement("div"); val.className = share ? "share-bar-value" : "bar-value"; val.textContent = fmtPct(item.change);
    row.append(name, track, val); el.appendChild(row);
  });
}

function renderCards(metrics) {
  const el = document.getElementById("cards"); el.innerHTML = "";
  metrics.forEach(item => {
    const card = document.createElement("article"); card.className = "metric-card";
    const cls = item.change > 0.15 ? "positive" : item.change < -0.15 ? "negative" : "";
    card.innerHTML = `<div><div class="metric-top"><span>${item.unit}</span><span>${state.period === 7 ? "7 дней" : "4 недели"}</span></div><h3>${item.name}</h3></div><div><div class="metric-change ${cls}">${fmtPct(item.change)}</div><div class="metric-status">${statusText(item.change)}</div></div>`;
    el.appendChild(card);
  });
}

function render() {
  const metrics = getMetrics(state.period); state.metrics = metrics;
  const {leader, decline, stable, text} = buildSummary(metrics, state.period), max = maxAbs(metrics);
  const ringDeg = Math.max(35, Math.min(Math.abs(leader.change) / max, 1) * 300);
  document.documentElement.style.setProperty("--ringDeg", `${ringDeg}deg`); document.documentElement.style.setProperty("--shareDeg", `${ringDeg}deg`);
  document.getElementById("leaderValue").textContent = fmtPct(leader.change); document.getElementById("leaderName").textContent = leader.shortName;
  document.getElementById("headline").textContent = leader.change > 0.15 ? `${leader.shortName} — лидер роста` : "Рост цен за период минимален";
  document.getElementById("summary").textContent = text;
  document.getElementById("declineChip").textContent = decline.change < -0.15 ? `${decline.shortName} ${fmtPct(decline.change)}` : "нет заметного снижения";
  document.getElementById("stableChip").textContent = `${stable.shortName} ${fmtPct(stable.change)}`;
  document.getElementById("autoInsight").textContent = text; document.getElementById("updatedDate").textContent = fmtDate(state.data.updated);
  renderBars(metrics, "bars"); renderCards(metrics);
  document.getElementById("shareDate").textContent = fmtDate(state.data.updated);
  document.getElementById("sharePeriod").textContent = `Россия · ${state.period === 7 ? "последние 7 дней" : "последние 4 недели"}`;
  document.getElementById("shareLeaderValue").textContent = fmtPct(leader.change); document.getElementById("shareLeaderName").textContent = leader.shortName;
  document.getElementById("shareLeaderText").textContent = `${leader.shortName}: максимальный рост среди шести выбранных категорий.`;
  document.getElementById("shareStable").textContent = `${stable.shortName} ${fmtPct(stable.change)}`;
  document.getElementById("shareDecline").textContent = decline.change < -0.15 ? `${decline.shortName} ${fmtPct(decline.change)}` : "нет заметного снижения";
  renderBars(metrics, "shareBars", true);
}

async function downloadPng() {
  const button = document.getElementById("downloadPng"), old = button.textContent; button.textContent = "Готовим PNG…"; button.disabled = true;
  try {
    const canvas = await html2canvas(document.getElementById("shareCard"), {scale:1, backgroundColor:"#f4f3ee", useCORS:true, logging:false});
    const link = document.createElement("a"); link.download = `chto-dorozhaet-${state.period}d-${state.data.updated}.png`; link.href = canvas.toDataURL("image/png"); link.click();
  } finally { button.textContent = old; button.disabled = false; }
}

async function init() {
  try {
    const response = await fetch("data/prices.json"); if (!response.ok) throw new Error("Не удалось загрузить data/prices.json"); state.data = await response.json();
    document.querySelectorAll(".period-btn").forEach(btn => btn.addEventListener("click", () => {document.querySelectorAll(".period-btn").forEach(b => b.classList.remove("active")); btn.classList.add("active"); state.period = Number(btn.dataset.period); render();}));
    document.getElementById("downloadPng").addEventListener("click", downloadPng); render();
  } catch (error) {
    console.error(error); document.getElementById("headline").textContent = "Не удалось загрузить данные"; document.getElementById("summary").textContent = "Запускайте проект через локальный сервер или GitHub Pages, а не двойным кликом по index.html.";
  }
}
init();
