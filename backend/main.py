"""
Project 1 Backend — Log Anomaly Detective (Real Infrastructure)
Pulls REAL logs from LocalStack CloudWatch Logs instead of simulating.
"""
import os, json, time
import boto3
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Log Anomaly Detective — Real Infra", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# ── AWS clients pointing to LocalStack ────────────────────────────────────
AWS_ENDPOINT = os.getenv("AWS_ENDPOINT_URL", "http://localstack:4566")
AWS_KWARGS   = dict(
    endpoint_url=AWS_ENDPOINT,
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test"
)

cw_logs = boto3.client("logs", **AWS_KWARGS)
ec2     = boto3.client("ec2",  **AWS_KWARGS)

LOG_GROUP   = "/aiops/services"
LOG_STREAMS = ["auth-service", "payment-service", "inventory-api"]

# ── OpenAI ─────────────────────────────────────────────────────────────────
openai_client = None
if os.getenv("OPENAI_API_KEY"):
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── CloudWatch log puller ──────────────────────────────────────────────────
def pull_real_logs(minutes_back: int = 5) -> list[dict]:
    """Pull real logs from LocalStack CloudWatch Logs."""
    logs       = []
    start_time = int((time.time() - minutes_back * 60) * 1000)

    for stream in LOG_STREAMS:
        try:
            resp = cw_logs.get_log_events(
                logGroupName=LOG_GROUP,
                logStreamName=stream,
                startTime=start_time,
                limit=200
            )
            for event in resp.get("events", []):
                try:
                    parsed = json.loads(event["message"])
                    logs.append(parsed)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"CloudWatch pull failed for {stream}: {e}")

    return logs


# ── Anomaly detection ──────────────────────────────────────────────────────
def detect_anomalies(logs: list[dict]):
    if len(logs) < 10:
        return pd.DataFrame(), []

    df = pd.DataFrame(logs)
    le = LabelEncoder()
    df["service_enc"] = le.fit_transform(df["service"].fillna("unknown"))
    df["is_error"]    = (df["level"] == "ERROR").astype(int)
    df["status_5xx"]  = (df.get("status_code", pd.Series([200] * len(df))) >= 500).astype(int)
    df["latency_ms"]  = pd.to_numeric(df.get("latency_ms", 0), errors="coerce").fillna(0)

    X = df[["latency_ms", "service_enc", "is_error", "status_5xx"]].values

    model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
    model.fit(X)
    df["anomaly_score"] = model.score_samples(X)
    df["is_anomaly"]    = model.predict(X) == -1

    anomaly_idx = df[df["is_anomaly"]].index.tolist()
    clusters, cur = [], []
    for i in anomaly_idx:
        if not cur or i - cur[-1] <= 5:
            cur.append(i)
        else:
            clusters.append(cur)
            cur = [i]
    if cur:
        clusters.append(cur)

    return df, clusters


# ── RCA chaining ───────────────────────────────────────────────────────────
def build_chains(df, clusters):
    chains = []
    for cluster_indices in clusters:
        rows        = df.iloc[cluster_indices].copy().sort_values("timestamp")
        svc_counts  = rows["service"].value_counts()
        root_svc    = svc_counts.index[0]
        propagation = (rows.drop_duplicates("service")
                           .sort_values("timestamp")["service"].tolist())
        chains.append({
            "cluster_size":   len(cluster_indices),
            "root_cause":     root_svc,
            "propagation":    propagation,
            "avg_latency_ms": round(rows["latency_ms"].mean(), 1),
            "error_count":    int(rows["is_error"].sum()),
            "severity":       "critical" if rows["is_error"].sum() > 3 else "warning",
            "log_sample":     rows[["timestamp", "service", "level",
                                    "latency_ms"]].head(3).to_dict("records")
        })
    return chains


# ── GPT report ─────────────────────────────────────────────────────────────
def generate_report(chain: dict) -> dict:
    if not openai_client:
        return {
            "title":          f"{chain['root_cause']} incident",
            "summary":        f"Anomaly detected in {chain['root_cause']}. "
                              f"Propagated to: {', '.join(chain['propagation'])}.",
            "impact":         f"Services affected: {', '.join(chain['propagation'])}",
            "severity":       "P2" if chain["severity"] == "critical" else "P3",
            "remediation":    ["Check service logs",
                               "Restart affected service",
                               "Monitor error rate"],
            "estimated_cause": "High latency spike detected by Isolation Forest"
        }

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system",
             "content": "You are an AIOps incident analyst. Return JSON only."},
            {"role": "user",
             "content": f"""Analyze this real incident chain from CloudWatch logs:
{json.dumps(chain, indent=2, default=str)}
Return JSON: title, summary, impact, severity (P1/P2/P3),
remediation (list of 3), estimated_cause"""}
        ],
        max_tokens=500,
        temperature=0.3
    )
    return json.loads(resp.choices[0].message.content)


# ── EC2 helpers ────────────────────────────────────────────────────────────
def get_ec2_instances() -> dict:
    try:
        resp      = ec2.describe_instances(
            Filters=[{"Name": "tag:Project", "Values": ["aiops"]}]
        )
        instances = {}
        for reservation in resp["Reservations"]:
            for inst in reservation["Instances"]:
                name = next((t["Value"] for t in inst.get("Tags", [])
                             if t["Key"] == "Name"), inst["InstanceId"])
                instances[name] = {
                    "instance_id": inst["InstanceId"],
                    "state":       inst["State"]["Name"],
                    "type":        inst["InstanceType"]
                }
        return instances
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode":   "real-infrastructure",
        "source": "localstack-cloudwatch"
    }


@app.get("/analyze")
def analyze(
    minutes_back: int = Query(default=5,  ge=1,  le=60),
    max_reports:  int = Query(default=5,  ge=1,  le=10)
):
    logs = pull_real_logs(minutes_back=minutes_back)

    if len(logs) < 5:
        return {
            "error":    "Not enough logs yet. Wait 30s for services to generate logs.",
            "log_count": len(logs),
            "tip":      "Try increasing minutes_back"
        }

    df, clusters = detect_anomalies(logs)
    chains       = build_chains(df, clusters)

    top_chains = sorted(chains, key=lambda c: c["error_count"], reverse=True)
    for chain in top_chains[:max_reports]:
        try:
            chain["report"] = generate_report(chain)
        except Exception as e:
            chain["report"] = {"error": str(e)}

    return {
        "source":        "localstack-cloudwatch",
        "log_group":     LOG_GROUP,
        "total_logs":    len(logs),
        "anomaly_count": int(df["is_anomaly"].sum()) if len(df) > 0 else 0,
        "anomaly_rate":  round(df["is_anomaly"].mean() * 100, 1) if len(df) > 0 else 0,
        "chain_count":   len(chains),
        "chains":        chains,
        "ec2_instances": get_ec2_instances(),
        "logs":          df.to_dict("records") if len(df) > 0 else []
    }


@app.get("/services/status")
def services_status():
    """Real-time health of all microservices."""
    import httpx
    services = {
        "auth-service":    os.getenv("AUTH_URL",      "http://auth-svc:5001"),
        "payment-service": os.getenv("PAYMENT_URL",   "http://payment-svc:5002"),
        "inventory-api":   os.getenv("INVENTORY_URL", "http://inventory-svc:5003"),
    }
    status = {}
    for name, url in services.items():
        try:
            r = httpx.get(f"{url}/health", timeout=2)
            status[name] = "healthy" if r.status_code == 200 else "degraded"
        except Exception:
            status[name] = "down"
    return status


@app.post("/services/{service}/crash")
def inject_crash(service: str, duration: int = 60):
    """Inject a real failure into a running service — for demo."""
    import httpx
    urls = {
        "auth-service":    os.getenv("AUTH_URL",      "http://auth-svc:5001"),
        "payment-service": os.getenv("PAYMENT_URL",   "http://payment-svc:5002"),
        "inventory-api":   os.getenv("INVENTORY_URL", "http://inventory-svc:5003"),
    }
    if service not in urls:
        return {"error": f"Unknown service: {service}"}
    try:
        r = httpx.post(f"{urls[service]}/crash",
                       json={"duration": duration}, timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── AWS Console-style endpoints ────────────────────────────────────────────

@app.get("/aws/ec2")
def aws_ec2():
    """EC2 instances — mirrors AWS Console EC2 dashboard."""
    try:
        resp      = ec2.describe_instances(
            Filters=[{"Name": "tag:Project", "Values": ["aiops"]}]
        )
        instances = []
        for r in resp["Reservations"]:
            for i in r["Instances"]:
                name = next((t["Value"] for t in i.get("Tags", [])
                             if t["Key"] == "Name"), "unnamed")
                svc  = next((t["Value"] for t in i.get("Tags", [])
                             if t["Key"] == "Service"), "")
                instances.append({
                    "instance_id":  i["InstanceId"],
                    "name":         name,
                    "service":      svc,
                    "state":        i["State"]["Name"],
                    "type":         i["InstanceType"],
                    "region":       "us-east-1",
                    "ami":          i.get("ImageId", "ami-mock"),
                    "launch_time":  str(i.get("LaunchTime", ""))
                })
        return {
            "instances": instances,
            "total":     len(instances),
            "running":   sum(1 for i in instances if i["state"] == "running"),
            "stopped":   sum(1 for i in instances if i["state"] == "stopped"),
            "region":    "us-east-1",
            "account":   "000000000000 (LocalStack)"
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/aws/logs")
def aws_logs():
    """CloudWatch log groups + streams — mirrors AWS Console CloudWatch."""
    try:
        groups = cw_logs.describe_log_groups(logGroupNamePrefix="/aiops")
        result = []
        for g in groups["logGroups"]:
            streams = cw_logs.describe_log_streams(
                logGroupName=g["logGroupName"],
                orderBy="LastEventTime",
                descending=True
            )
            stream_list = streams.get("logStreams", [])
            recent      = pull_real_logs(minutes_back=60)
            result.append({
                "log_group":       g["logGroupName"],
                "stored_bytes":    g.get("storedBytes", 0),
                "retention_days":  g.get("retentionInDays", "Never expire"),
                "stream_count":    len(stream_list),
                "streams": [
                    {
                        "name":              s["logStreamName"],
                        "last_event_time":   s.get("lastEventTimestamp", 0),
                        "first_event_time":  s.get("firstEventTimestamp", 0),
                    }
                    for s in stream_list
                ],
                "recent_event_count": len(recent)
            })
        return {
            "log_groups":   result,
            "total_groups": len(result),
            "region":       "us-east-1",
            "account":      "000000000000 (LocalStack)"
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/aws/overview")
def aws_overview():
    """Full AWS resource overview for both projects."""
    try:
        # EC2
        ec2_resp  = ec2.describe_instances(
            Filters=[{"Name": "tag:Project", "Values": ["aiops"]}]
        )
        instances = []
        for r in ec2_resp["Reservations"]:
            for i in r["Instances"]:
                name = next((t["Value"] for t in i.get("Tags", [])
                             if t["Key"] == "Name"), i["InstanceId"])
                instances.append({
                    "id":    i["InstanceId"],
                    "name":  name,
                    "state": i["State"]["Name"],
                    "type":  i["InstanceType"]
                })

        # CloudWatch log groups
        groups     = cw_logs.describe_log_groups(logGroupNamePrefix="/aiops")
        log_groups = [g["logGroupName"] for g in groups.get("logGroups", [])]

        # Recent logs summary
        recent = pull_real_logs(minutes_back=5)
        errors = [l for l in recent if l.get("level") == "ERROR"]

        return {
            "region":          "us-east-1",
            "account":         "000000000000 (LocalStack)",
            "ec2": {
                "total":       len(instances),
                "running":     sum(1 for i in instances if i["state"] == "running"),
                "instances":   instances
            },
            "cloudwatch": {
                "log_groups":  log_groups,
                "recent_logs": len(recent),
                "recent_errors": len(errors),
                "error_rate":  round(len(errors) / max(len(recent), 1) * 100, 1)
            },
            "services": {
                "auth-service":    "running",
                "payment-service": "running",
                "inventory-api":   "running"
            }
        }
    except Exception as e:
        return {"error": str(e)}