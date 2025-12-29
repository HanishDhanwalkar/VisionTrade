const chart = LightweightCharts.createChart(document.getElementById('chart'));
const series = chart.addCandlestickSeries();
let symbol = "BTCUSDT";

async function loadHistory() {
  const r = await fetch(`/candles/${symbol}`);
  const data = await r.json();
  series.setData(data);
}

document.getElementById("symbol").onchange = e => {
  symbol = e.target.value;
  loadHistory();
};

const ws = new WebSocket(`ws://${location.host}/ws`);
ws.onmessage = e => {
  const msg = JSON.parse(e.data);
  if (msg.symbol === symbol) {
    series.update(msg.data);
  }
};

loadHistory();
