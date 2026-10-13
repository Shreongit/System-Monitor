
(function () {
  const statusEl = document.getElementById("status");
  const refreshBtn = document.getElementById("refreshSnapshot");

  // system info elements
  const cpuNameEl = document.getElementById("cpuName");
  const cpuCoresEl = document.getElementById("cpuCores");
  const cpuThreadsEl = document.getElementById("cpuThreads");
  const ramInstalledEl = document.getElementById("ramInstalled");
  const gpuNameEl = document.getElementById("gpuName");
  const osInfoEl = document.getElementById("osInfo");

  let cpuChart = null;
  let memChart = null;
  let netChart = null;

  function bytesToHuman(n) {
    // simple bytes -> human
    const units = ["B", "KB", "MB", "GB", "TB"];
    let i = 0;
    let num = n;
    while (num >= 1024 && i < units.length - 1) {
      num /= 1024;
      i++;
    }
    return `${num.toFixed(2)} ${units[i]}`;
  }

  function makeChart(ctx, label, color) {
    return new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: label,
            data: [],
            borderColor: color,
            backgroundColor: "rgba(0,0,0,0)",
            tension: 0.3,
          },
        ],
      },
      options: {
        animation: false,
        responsive: true,
        plugins: { legend: { display: true } },
        scales: {
          x: { display: false },
          y: { beginAtZero: true },
        },
      },
    });
  }

  function updateSeries(chart, value, maxPoints = 60) {
    const label = new Date().toLocaleTimeString();
    chart.data.labels.push(label);
    chart.data.datasets[0].data.push(value);
    if (chart.data.labels.length > maxPoints) {
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
    }
    chart.update("none");
  }

  function updateProcessesTable(list) {
    const tbody = document.querySelector("#procs tbody");
    tbody.innerHTML = "";
    for (const p of list) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${p.pid}</td><td>${p.name}</td><td>${(p.cpu_percent||0).toFixed(1)}</td><td>${(p.memory_percent||0).toFixed(1)}</td><td>${p.username||""}</td>`;
      tbody.appendChild(tr);
    }
  }

  function updateSystemInfo(system, gpus) {
    if (!system) return;
    cpuNameEl.textContent = system.cpu_name || "-";
    cpuCoresEl.textContent = system.physical_cores != null ? system.physical_cores : "-";
    cpuThreadsEl.textContent = system.logical_cores != null ? system.logical_cores : "-";
    ramInstalledEl.textContent = system.ram_total != null ? bytesToHuman(system.ram_total) : "-";
    osInfoEl.textContent = system.os || "-";
    // GPU name: prefer first GPU name from gpus array, else '-'
    if (Array.isArray(gpus) && gpus.length > 0) {
      const first = gpus[0];
      gpuNameEl.textContent = first.name || "-";
    } else {
      gpuNameEl.textContent = "-";
    }
  }

  window.addEventListener("load", () => {
    const cpuCtx = document.getElementById("cpuChart").getContext("2d");
    const memCtx = document.getElementById("memChart").getContext("2d");
    const netCtx = document.getElementById("netChart").getContext("2d");
    cpuChart = makeChart(cpuCtx, "CPU %", "rgb(75, 192, 192)");
    memChart = makeChart(memCtx, "Memory %", "rgb(255, 99, 132)");
    netChart = makeChart(netCtx, "Network KB/s (sum)", "rgb(54, 162, 235)");

    // websocket
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = protocol + "//" + location.host + "/api/ws/metrics";
    const ws = new WebSocket(wsUrl);

    ws.addEventListener("open", () => {
      statusEl.textContent = "Connected";
    });

    ws.addEventListener("message", (ev) => {
      try {
        const payload = JSON.parse(ev.data);

        // update system info
        updateSystemInfo(payload.system, payload.gpus || []);

        // cpu percent
        const cpuPercent = payload.cpu?.percent ?? 0;
        updateSeries(cpuChart, cpuPercent);

        // memory percent
        const memPercent = payload.memory?.percent ?? 0;
        updateSeries(memChart, memPercent);

        // network: sum of all interfaces bytes per sec -> convert to KB/s
        let netSum = 0;
        const nr = payload.network_rates || {};
        for (const iface in nr) {
          const r = nr[iface];
          netSum += (r.bytes_sent_per_sec || 0) + (r.bytes_recv_per_sec || 0);
        }
        updateSeries(netChart, netSum / 1024);

        // processes
        const procs = payload.processes_summary || [];
        updateProcessesTable(procs);
      } catch (e) {
        console.error("Invalid payload", e);
      }
    });

    ws.addEventListener("close", () => {
      statusEl.textContent = "Disconnected";
    });

    refreshBtn.addEventListener("click", () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("snapshot");
      } else {
        statusEl.textContent = "WS not open";
      }
    });
  });
})();