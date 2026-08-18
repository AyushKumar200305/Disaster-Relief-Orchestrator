import { useEffect, useMemo, useState } from "react";

const BASELINE_RAINFALL = 100;
const initialHealth = { state: "loading", message: "Checking backend connection" };

function villageName(village) {
  return village.name || `Village ${village.id || ""}`;
}

function priorityScore(village) {
  return typeof village.priority_score === "number" ? village.priority_score.toFixed(1) : "—";
}

function movementFor(id, baseline) {
  const baselineIndex = baseline.findIndex((village) => village.id === id);
  return baselineIndex;
}

function PriorityLane({ title, subtitle, data, baseline, simulated }) {
  return (
    <section
      className={`lane ${simulated ? "after" : ""}`}
      data-testid={`lane-${simulated ? "simulated" : "baseline"}`}
    >
      <div className="lane-header">
        <div>
          <div className="lane-title">{title}</div>
          <div className="lane-kicker">{subtitle}</div>
        </div>
        <div className="lane-badge">{data.length} LOCATIONS</div>
      </div>
      {data.length === 0 ? (
        <div className="empty-state">No priority data returned.</div>
      ) : (
        data.map((village, index) => {
          const previousIndex = movementFor(village.id, baseline);
          const delta = previousIndex < 0 ? 0 : previousIndex - index;
          const movementLabel =
            delta === 0
              ? "No rank change"
              : delta > 0
                ? `Moved up ${delta}`
                : `Moved down ${Math.abs(delta)}`;
          return (
            <div
              className={`priority-row ${simulated && delta !== 0 ? "moved" : ""}`}
              key={village.id}
              data-testid={`priority-row-${village.id}-${simulated ? "simulated" : "baseline"}`}
            >
              <span className="rank">{String(index + 1).padStart(2, "0")}</span>
              <div className="village-copy">
                <div className="village" data-testid={`text-village-${village.id}`}>
                  {villageName(village)}
                </div>
                <div className="village-meta">
                  {village.risk_bucket} risk · {village.nearest_hospital_name}
                </div>
              </div>
              <span
                className={`risk-value ${
                  village.priority_score > 70 ? "high" : village.priority_score < 35 ? "low" : ""
                }`}
                data-testid={`text-priority-score-${village.id}-${simulated ? "simulated" : "baseline"}`}
              >
                {priorityScore(village)}
              </span>
              <span
                className={`move ${delta === 0 ? "same" : delta < 0 ? "down" : ""}`}
                aria-label={movementLabel}
                data-testid={`text-movement-${village.id}`}
              >
                {delta === 0 ? "—" : delta > 0 ? `↑${delta}` : `↓${Math.abs(delta)}`}
              </span>
            </div>
          );
        })
      )}
    </section>
  );
}

function RoutePane({ route, label, changed }) {
  const roads = route?.roads || [];
  const status = route?.status || "AWAITING SCENARIO";
  return (
    <div
      className={`route-pane ${changed ? "changed" : ""}`}
      data-testid={`route-pane-${label.toLowerCase().replaceAll(" ", "-")}`}
    >
      <div className="route-pane-head">
        <span>{label}</span>
        <span className={status !== "CLEAR" ? "route-alert" : ""}>{status}</span>
      </div>
      <div className="route-line">
        <span className="route-node" />
        {route?.origin_label || "Origin"}
      </div>
      <div className="route-path">
        {roads.length ? (
          roads.map((road) => (
            <span className={`road-chip ${road.blocked ? "blocked" : ""}`} key={road.id}>
              {road.name}
              {road.blocked ? " / BLOCKED" : ""}
            </span>
          ))
        ) : (
          <span>No connected road segments</span>
        )}
      </div>
      <div className="route-line">
        <span className="route-node end" />
        {route?.destination_label || "Destination"}
      </div>
      <div className="route-foot">
        <span>{route?.message || "Run a scenario to compare corridors"}</span>
        <strong>{route?.total_distance_km == null ? "—" : `${route.total_distance_km} km`}</strong>
      </div>
    </div>
  );
}

function App() {
  const [health, setHealth] = useState(initialHealth);
  const [baseline, setBaseline] = useState([]);
  const [roads, setRoads] = useState([]);
  const [rainfall, setRainfall] = useState(BASELINE_RAINFALL);
  const [blockedRoad, setBlockedRoad] = useState("");
  const [blockEnabled, setBlockEnabled] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadInitial = async () => {
    setLoading(true);
    setError("");
    try {
      const [healthResponse, priorityResponse, roadsResponse] = await Promise.all([
        fetch("/health"),
        fetch("/api/priority"),
        fetch("/api/roads"),
      ]);
      if (!healthResponse.ok || !priorityResponse.ok || !roadsResponse.ok) {
        throw new Error("The decision layer did not respond. Check the backend workflow.");
      }
      const [healthPayload, priorityPayload, roadsPayload] = await Promise.all([
        healthResponse.json(),
        priorityResponse.json(),
        roadsResponse.json(),
      ]);
      setHealth({
        state: healthPayload.status === "ok" ? "ready" : "warning",
        message: healthPayload.status === "ok" ? "Decision layer online" : "Backend responded with a warning",
      });
      setBaseline(priorityPayload);
      setRoads(roadsPayload);
      setResult(null);
    } catch (requestError) {
      setHealth({ state: "error", message: requestError.message });
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitial();
  }, []);

  const runSimulation = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rainfall_percent: Number(rainfall),
          blocked_road_id: blockEnabled ? blockedRoad || null : null,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Simulation could not be completed.");
      }
      setResult(payload);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setRainfall(BASELINE_RAINFALL);
    setBlockedRoad("");
    setBlockEnabled(false);
    setResult(null);
    setError("");
  };

  const active = result || {
    baseline: { priority: baseline, route: null },
    simulated: { priority: baseline, route: null },
    changes: { priority_order_changed: false, route_changed: false },
  };
  const hasChanges =
    Boolean(active.changes?.priority_order_changed) || Boolean(active.changes?.route_changed);
  const topPriority = active.simulated.priority?.[0];
  const blockedRoadName = roads.find((road) => road.id === blockedRoad)?.name;
  const rankChanges = useMemo(() => {
    if (!result) return 0;
    return result.simulated.priority.reduce((count, village, index) => {
      return count + (result.baseline.priority[index]?.id === village.id ? 0 : 1);
    }, 0);
  }, [result]);

  const setRainfallValue = (value) => {
    const next = Math.max(0, Math.min(300, Number(value) || 0));
    setRainfall(next);
  };

  return (
    <main className="app">
      <div className="shell">
        <header className="topbar">
          <div className="brand">
            <span className="mark">FR</span>
            <div>
              <div className="brand-name">FLOOD RESPONSE</div>
              <div className="brand-sub">Scenario command center</div>
            </div>
          </div>
          <div className="health" data-testid="status-health">
            <span className={`health-dot ${health.state}`} />
            <span>{health.message}</span>
          </div>
        </header>

        <section className="hero">
          <div>
            <div className="eyebrow section-label">What-if simulator / 01</div>
            <h1>
              See the response order <em>move.</em>
            </h1>
          </div>
          <p className="hero-copy">
            Stress-test flood response priorities against changing rainfall and road access.
            Every scenario is compared to the live operating baseline.
          </p>
        </section>

        <section className="controls" aria-label="Simulation controls">
          <div className="rain-control">
            <div className="control-label">
              <span>Rainfall intensity</span>
              <span className="rain-value" data-testid="text-rainfall-value">
                {rainfall}%
              </span>
            </div>
            <input
              data-testid="input-rainfall-slider"
              className="range"
              type="range"
              min="0"
              max="300"
              value={rainfall}
              onChange={(event) => setRainfallValue(event.target.value)}
              aria-label="Rainfall percentage"
            />
            <div className="range-labels">
              <span>0%</span>
              <span>baseline 100%</span>
              <span>300%</span>
            </div>
          </div>
          <div>
            <div className="control-label">
              <span>Exact rainfall</span>
              <span className="mono">PERCENT</span>
            </div>
            <input
              data-testid="input-rainfall-number"
              className="number-input"
              type="number"
              min="0"
              max="300"
              value={rainfall}
              onChange={(event) => setRainfallValue(event.target.value)}
              aria-label="Exact rainfall percentage"
            />
          </div>
          <div className="road-control">
            <div className="control-label">
              <span>Block a road</span>
              <span className="mono">OPTIONAL</span>
            </div>
            <label className="toggle-row">
              <input
                data-testid="toggle-block-road"
                className="toggle-input"
                type="checkbox"
                checked={blockEnabled}
                onChange={(event) => {
                  const enabled = event.target.checked;
                  setBlockEnabled(enabled);
                  if (enabled && !blockedRoad && roads[0]) {
                    setBlockedRoad(roads[0].id);
                  }
                }}
              />
              <span className="toggle-track" aria-hidden="true">
                <span className="toggle-thumb" />
              </span>
              <span>{blockEnabled ? "Closure enabled" : "No closure"}</span>
            </label>
            <div className="select-wrap">
              <select
                data-testid="select-blocked-road"
                className="road-select"
                value={blockedRoad}
                onChange={(event) => setBlockedRoad(event.target.value)}
                disabled={!blockEnabled}
                aria-label="Road to mark blocked"
              >
                <option value="">No road closure</option>
                {roads.map((road) => (
                  <option key={road.id} value={road.id}>
                    {road.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="control-actions">
            <button
              data-testid="button-run-simulation"
              className="btn"
              onClick={runSimulation}
              disabled={loading || baseline.length === 0}
            >
              {loading ? "Running…" : "Run simulation"}
            </button>
            <button data-testid="button-reset-simulation" className="btn secondary" onClick={reset}>
              Reset
            </button>
          </div>
        </section>

        {blockEnabled && blockedRoadName && (
          <div className="scenario-note" data-testid="text-blocked-road">
            Scenario closure: <strong>{blockedRoadName}</strong> will be treated as impassable.
          </div>
        )}
        {error && (
          <div className="alert" data-testid="status-error">
            {error}
            <button data-testid="button-retry" className="btn secondary retry" onClick={loadInitial}>
              Retry connection
            </button>
          </div>
        )}

        <div className="results-head">
          <div>
            <div className="eyebrow section-label">Priority movement / 02</div>
            <h2>Response order</h2>
          </div>
          <div className={`scenario-tag ${hasChanges ? "active" : ""}`} data-testid="text-scenario">
            {result ? `${active.changes.rainfall_percent}% rainfall scenario` : "Baseline loaded"}
            {hasChanges ? " · CHANGES DETECTED" : ""}
          </div>
        </div>

        {loading && baseline.length === 0 ? (
          <div className="loading-card" data-testid="status-loading">
            Loading live priorities and road network…
          </div>
        ) : (
          <div className="lanes">
            <PriorityLane
              title="Current baseline"
              subtitle="Live priority order"
              data={active.baseline.priority || []}
              baseline={active.baseline.priority || []}
              simulated={false}
            />
            <PriorityLane
              title="Simulated response"
              subtitle={result ? `${rankChanges} positions changed` : "Run a scenario to compare"}
              data={active.simulated.priority || []}
              baseline={active.baseline.priority || []}
              simulated
            />
          </div>
        )}

        <section className="route-card">
          <div className="route-title">
            <div>
              <div className="eyebrow section-label">Evacuation corridor / 03</div>
              <h2>Route comparison</h2>
            </div>
            <span
              className={`route-status ${
                active.simulated.route?.status !== "CLEAR" ? "blocked" : ""
              }`}
              data-testid="status-route"
            >
              {active.simulated.route?.status || "AWAITING SCENARIO"}
            </span>
          </div>
          {!result ? (
            <div className="route-prompt" data-testid="text-route-prompt">
              Run a what-if scenario to see the dispatch corridor recalculate here.
            </div>
          ) : (
            <div className="route-grid">
              <RoutePane route={active.baseline.route} label="Baseline route" changed={false} />
              <RoutePane
                route={active.simulated.route}
                label="Simulated route"
                changed={Boolean(active.changes?.route_changed)}
              />
            </div>
          )}
        </section>

        <footer className="footer">
          <span>Flood Response System · planner workspace</span>
          <span className="mono">
            {topPriority ? `NEXT: ${villageName(topPriority).toUpperCase()}` : "Connected to FastAPI"}
          </span>
        </footer>
      </div>
    </main>
  );
}

export default App;