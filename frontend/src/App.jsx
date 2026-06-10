import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";

const API = "http://localhost:8001";

export default function App() {
  const [data, setData]         = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [svcStatus, setSvcStatus] = useState({});

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${API}/services/status`);
        if (r.ok) setSvcStatus(await r.json());
      } catch {}
    };
    poll();
    const t = setInterval(poll, 5000);
    return () => clearInterval(t);
  }, []);

  const runAnalysis = async () => {
    setLoading(true); setError(null);
    try {
      const r = await fetch(`${API}/analyze?minutes_back=5&max_reports=8`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const injectCrash = async (svc) => {
    await fetch(`${API}/services/${svc}/crash`, { method: "POST" });
    setTimeout(runAnalysis, 3000);
  };

  const chartData = data?.logs ? Object.entries(
    data.logs.reduce((acc, l) => {
      const k = l.service?.replace("-service","").replace("-api","") || "unknown";
      if (!acc[k]) acc[k] = { normal: 0, anomaly: 0 };
      l.is_anomaly ? acc[k].anomaly++ : acc[k].normal++;
      return acc;
    }, {})
  ).map(([name, v]) => ({ name, ...v })) : [];

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "1.5rem", fontFamily: "system-ui" }}>
      <h1 style={{ color: "#1A56A0", marginBottom: 4 }}>Log Anomaly Detective</h1>
      <p style={{ color: "#666", marginBottom: 16 }}>
        LocalStack CloudWatch · Real log ingestion from 3 Flask microservices
      </p>

      {/* Service status */}
      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        {Object.entries(svcStatus).map(([svc, status]) => (
          <div key={svc} style={{
            padding: "6px 14px", borderRadius: 20, fontSize: 12, fontWeight: 600,
            background: status === "healthy" ? "#D5F5E3" : "#FADBD8",
            color: status === "healthy" ? "#0B6B3A" : "#7B241C"
          }}>
            {svc.replace("-service","").replace("-api","")} · {status}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <button onClick={runAnalysis} disabled={loading}
          style={{ padding: "10px 24px", background: "#1A56A0", color: "#fff",
                   border: "none", borderRadius: 6, cursor: "pointer", fontSize: 15 }}>
          {loading ? "Analyzing..." : "Run Analysis (Real Logs)"}
        </button>
        {["auth-service","payment-service","inventory-api"].map(svc => (
          <button key={svc} onClick={() => injectCrash(svc)}
            style={{ padding: "10px 16px", background: "#D85A30", color: "#fff",
                     border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 }}>
            Crash {svc.replace("-service","").replace("-api","")}
          </button>
        ))}
      </div>

      {error && <p style={{ color: "red" }}>Error: {error}</p>}

      {data && (
        <>
          <div style={{ background: "#E8F4FD", padding: 10, borderRadius: 6,
                        marginBottom: 16, fontSize: 13, color: "#1A56A0" }}>
            Source: <strong>{data.source}</strong> · Log group: <strong>{data.log_group}</strong>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 20 }}>
            {[["Total Logs", data.total_logs], ["Anomalies", data.anomaly_count],
              ["Anomaly Rate", `${data.anomaly_rate}%`], ["Chains", data.chain_count]]
              .map(([label, val]) => (
              <div key={label} style={{ background: "#F5F8FF", borderRadius: 8,
                                        padding: "1rem", textAlign: "center" }}>
                <div style={{ fontSize: 12, color: "#777" }}>{label}</div>
                <div style={{ fontSize: 26, fontWeight: 600, color: "#1A56A0" }}>{val}</div>
              </div>
            ))}
          </div>

          {chartData.length > 0 && (
            <>
              <h3>Anomalies by Service (Real CloudWatch Logs)</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData}>
                  <XAxis dataKey="name"/><YAxis/><Tooltip/><Legend/>
                  <Bar dataKey="normal"  name="Normal"  fill="#1D9E75"/>
                  <Bar dataKey="anomaly" name="Anomaly" fill="#D85A30"/>
                </BarChart>
              </ResponsiveContainer>
            </>
          )}

          <h3 style={{ marginTop: 20 }}>Incident Chains</h3>
          {data.chains.map((c, i) => (
            <div key={i} style={{ border: "1px solid #ddd", borderRadius: 8,
                                  marginBottom: 10, overflow: "hidden" }}>
              <div style={{ padding: "10px 16px", fontWeight: 600, fontSize: 14,
                            background: c.severity === "critical" ? "#FADBD8" : "#FEF9E7",
                            display: "flex", justifyContent: "space-between" }}>
                <span>{c.report?.title || `Chain #${i+1}: ${c.root_cause}`}</span>
                <span style={{ fontSize: 12 }}>{c.severity.toUpperCase()} · {c.error_count} errors</span>
              </div>
              <div style={{ padding: "12px 16px", fontSize: 13 }}>
                <p><strong>Root cause:</strong> {c.root_cause} → {c.propagation.join(" → ")}</p>
                <p><strong>Avg latency:</strong> {c.avg_latency_ms}ms</p>
                {c.report?.summary && <p><strong>Summary:</strong> {c.report.summary}</p>}
                {c.report?.remediation && (
                  <div>
                    <strong>Remediation:</strong>
                    <ol style={{ margin: "4px 0 0 0", paddingLeft: 20 }}>
                      {c.report.remediation.map((r, j) => <li key={j}>{r}</li>)}
                    </ol>
                  </div>
                )}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
