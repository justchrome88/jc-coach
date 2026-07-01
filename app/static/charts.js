const data = window.coachChartData || { labels: [], kd: [], adr: [], kast: [], rating: [] };
const trendCanvas = document.getElementById("trendChart");

if (trendCanvas) {
  new Chart(trendCanvas, {
    type: "line",
    data: {
      labels: data.labels,
      datasets: [
        { label: "K/D", data: data.kd, borderColor: "#5eead4", backgroundColor: "rgba(94,234,212,.12)", tension: 0.28, yAxisID: "y" },
        { label: "Rating", data: data.rating, borderColor: "#facc15", backgroundColor: "rgba(250,204,21,.12)", tension: 0.28, yAxisID: "y" },
        { label: "ADR", data: data.adr, borderColor: "#fb7185", backgroundColor: "rgba(251,113,133,.10)", tension: 0.28, yAxisID: "y1" },
        { label: "KAST", data: data.kast, borderColor: "#60a5fa", backgroundColor: "rgba(96,165,250,.10)", tension: 0.28, yAxisID: "y1" },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { labels: { color: "#cbd5e1" } } },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,.12)" } },
        y: { position: "left", ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,.12)" } },
        y1: { position: "right", ticks: { color: "#94a3b8" }, grid: { drawOnChartArea: false } },
      },
    },
  });
}
