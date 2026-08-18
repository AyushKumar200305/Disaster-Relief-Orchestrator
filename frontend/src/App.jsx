import { useEffect, useState } from "react";

const initialHealth = { state: "loading", message: "Checking backend connection…" };

function App() {
  const [health, setHealth] = useState(initialHealth);

  useEffect(() => {
    let active = true;

    fetch("/health")
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Backend returned HTTP ${response.status}`);
        }
        return response.json();
      })
      .then((payload) => {
        if (active) {
          setHealth({
            state: payload.status === "ok" ? "ready" : "warning",
            message: payload.status === "ok" ? "Backend is online" : "Backend responded with a warning",
          });
        }
      })
      .catch((error) => {
        if (active) {
          setHealth({ state: "error", message: error.message });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const isReady = health.state === "ready";

  return (
    <main className="min-h-screen bg-[#071522] px-6 py-10 text-slate-100 sm:px-10 lg:px-16">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl flex-col">
        <header className="flex items-center justify-between border-b border-white/10 pb-6">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-400 text-lg font-black text-[#071522]">
              FR
            </span>
            <div>
              <p className="text-sm font-semibold tracking-[0.18em] text-cyan-300 uppercase">
                Flood Response
              </p>
              <p className="text-xs text-slate-400">System foundation</p>
            </div>
          </div>
          <span className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-400">
            v0.1.0
          </span>
        </header>

        <section className="grid flex-1 items-center gap-12 py-16 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="mb-5 text-sm font-semibold tracking-[0.22em] text-cyan-300 uppercase">
              Prepared for what comes next
            </p>
            <h1 className="max-w-3xl text-5xl leading-[1.02] font-semibold tracking-tight text-white sm:text-7xl">
              A clear foundation for faster flood response.
            </h1>
            <p className="mt-7 max-w-xl text-lg leading-8 text-slate-300">
              The core services are connected and ready for risk prediction,
              infrastructure mapping, and response optimization.
            </p>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/[0.06] p-2 shadow-2xl shadow-cyan-950/20">
            <div className="rounded-[1.35rem] bg-[#0d2538] p-7 sm:p-9">
              <div className="flex items-start justify-between gap-6">
                <div>
                  <p className="text-sm text-slate-400">System status</p>
                  <h2 className="mt-2 text-2xl font-semibold text-white">
                    End-to-end connection
                  </h2>
                </div>
                <span
                  className={`mt-1 h-3 w-3 rounded-full ${
                    isReady
                      ? "bg-emerald-400 shadow-[0_0_16px_rgba(52,211,153,0.8)]"
                      : health.state === "error"
                        ? "bg-rose-400"
                        : "animate-pulse bg-amber-300"
                  }`}
                  aria-label={health.state}
                />
              </div>

              <div className="mt-9 rounded-2xl border border-white/10 bg-[#071522]/60 p-5">
                <p className="text-xs font-semibold tracking-[0.16em] text-slate-500 uppercase">
                  GET /health
                </p>
                <p className="mt-3 text-base text-slate-200">{health.message}</p>
                <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${
                      isReady ? "w-full bg-emerald-400" : health.state === "error" ? "w-1/4 bg-rose-400" : "w-2/3 bg-amber-300"
                    }`}
                  />
                </div>
              </div>

              <div className="mt-7 grid grid-cols-2 gap-3 text-sm">
                {["FastAPI", "React", "SQLAlchemy", "PostgreSQL ready"].map((item) => (
                  <div key={item} className="rounded-xl border border-white/10 px-4 py-3 text-slate-300">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <footer className="flex flex-col gap-2 border-t border-white/10 pt-5 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <span>Starter workspace · Local development ready</span>
          <span>Data, ML, and mapping layers are ready for the next build.</span>
        </footer>
      </div>
    </main>
  );
}

export default App;