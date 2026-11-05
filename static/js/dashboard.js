const source = document.getElementById("dashboard-data");
if (source && window.Chart) {
  const { risks, statuses } = JSON.parse(source.textContent);
  const colors = {
    Low: "#4ade80", Medium: "#facc15", High: "#fb923c", Critical: "#fb7185",
    Open: "#60a5fa", "In Progress": "#facc15", Closed: "#34d399",
  };
  for (const [id, counts] of [["risk-chart", risks], ["status-chart", statuses]]) {
    const labels = Object.keys(colors).filter(label => Object.hasOwn(counts, label));
    new Chart(document.getElementById(id), {
      type: "bar",
      data: {
        labels,
        datasets: [{ data: labels.map(label => counts[label]), backgroundColor: labels.map(label => colors[label]), borderRadius: 5 }],
      },
      options: {
        animation: false,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#c7d2e5" }, grid: { display: false } },
          y: { beginAtZero: true, ticks: { precision: 0, color: "#c7d2e5" }, grid: { color: "#263653" } },
        },
      },
    });
  }
}
