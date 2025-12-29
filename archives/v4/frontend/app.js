const API_URL = "http://localhost:8000";
const WS_URL = "ws://localhost:8000";

/* ---------------- Chart Setup ---------------- */

const chartContainer = document.getElementById("chart");

const chart = LightweightCharts.createChart(chartContainer, {
    layout: {
        background: { type: 'solid', color: "#111" },
        textColor: "#DDD",
    },
    grid: {
        vertLines: { color: "#222" },
        horzLines: { color: "#222" },
    },
    timeScale: {
        timeVisible: true,
        secondsVisible: false,
    },
});

// FIXED: Use CandlestickSeries class from LightweightCharts namespace
const candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: "#26a69a",
    downColor: "#ef5350",
    borderVisible: false,
    wickUpColor: "#26a69a",
    wickDownColor: "#ef5350",
});

/* ---------------- Resize Observer ---------------- */

const resizeObserver = new ResizeObserver(entries => {
    for (const entry of entries) {
        chart.applyOptions({
            width: entry.contentRect.width,
            height: entry.contentRect.height,
        });
    }
});
resizeObserver.observe(document.getElementById("chart-wrapper"));

/* ---------------- Trade Markers ---------------- */

const tradeMarkers = [];

async function trade(side) {
    const quantity = prompt("Enter quantity:") || 0.01;

    // Get last candle from chart data
    const chartData = candleSeries.data();
    if (!chartData || chartData.length === 0) {
        alert("No price data available yet");
        return;
    }

    const lastCandle = chartData[chartData.length - 1];
    const price = lastCandle.close;

    const res = await fetch(`${API_URL}/trade`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            symbol: "BTCUSDT",
            side,
            price: price,
            quantity: parseFloat(quantity)
        })
    });

    const data = await res.json();
    console.log("Trade placed:", data);

    if (data.success) {
        const marker = {
            time: lastCandle.time,
            position: side === "buy" ? "belowBar" : "aboveBar",
            color: side === "buy" ? "#26a69a" : "#ef5350",
            shape: side === "buy" ? "arrowUp" : "arrowDown",
            text: `${side.toUpperCase()} ${data.trade.quantity}`
        };

        tradeMarkers.push(marker);
        candleSeries.setMarkers(tradeMarkers);
    }
}

/* ---------------- Initialize: Load Historical + WebSocket ---------------- */

async function initialize() {
    const statusEl = document.getElementById("status");
    
    try {
        // 1. Load historical candles first
        statusEl.textContent = "Loading historical data...";
        statusEl.className = "loading";
        
        const response = await fetch(`${API_URL}/candles`);
        const historicalCandles = await response.json();
        
        console.log(`Loaded ${historicalCandles.length} historical candles`);
        
        if (historicalCandles.length === 0) {
            statusEl.textContent = "No historical data available";
            statusEl.className = "disconnected";
            return;
        }
        
        // Set initial data
        candleSeries.setData(historicalCandles);
        
        // Fit content to show all data
        chart.timeScale().fitContent();
        
        statusEl.textContent = "Connecting to live stream...";
        
        // 2. Connect WebSocket for live updates
        connectWebSocket();
        
    } catch (error) {
        console.error("Failed to load historical data:", error);
        statusEl.textContent = "Failed to load data";
        statusEl.className = "disconnected";
    }
}

function connectWebSocket() {
    const statusEl = document.getElementById("status");
    const ws = new WebSocket(`${WS_URL}/ws/candles`);

    ws.onopen = () => {
        console.log("WebSocket connected");
        statusEl.textContent = "● Live";
        statusEl.className = "connected";
    };

    ws.onmessage = (e) => {
        const message = JSON.parse(e.data);
        
        // Handle snapshot (initial data from WebSocket)
        if (message.type === "snapshot") {
            // We already loaded via REST, so we can ignore this
            return;
        }
        
        // Handle real-time candle updates
        const candle = message.type ? message.data : message;
        
        if (candle && candle.time) {
            candleSeries.update(candle);
        }
    };

    ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        statusEl.textContent = "● Connection error";
        statusEl.className = "disconnected";
    };

    ws.onclose = () => {
        console.log("WebSocket closed, reconnecting in 3s...");
        statusEl.textContent = "● Reconnecting...";
        statusEl.className = "disconnected";
        
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };
}

// Start initialization when page loads
initialize();