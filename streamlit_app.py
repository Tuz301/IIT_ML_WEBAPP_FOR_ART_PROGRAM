import streamlit as st
import requests
import time
import pandas as pd
from typing import Dict, Any

st.set_page_config(page_title="IIT Predictor", layout="wide", initial_sidebar_state="collapsed")

API_BASE = st.sidebar.text_input("Backend URL", value="http://localhost:8000")
API_KEY = st.sidebar.text_input("API Key (optional)", value="", type="password")
HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY

# --- Style ---
st.markdown(
    """
    <style>
      :root{
        --prim:#0ea5e9; --accent:#7c3aed; --card-bg:#ffffff; --muted:#6b7280;
      }
      .topbar{display:flex;align-items:center;justify-content:space-between;padding:18px 24px;border-radius:12px;
        background:linear-gradient(90deg,var(--prim),var(--accent));color:white;margin-bottom:18px;}
      .nav a{color:rgba(255,255,255,0.95);text-decoration:none;margin:0 12px;font-weight:600}
      .hero-sub{opacity:.95;color:rgba(255,255,255,0.95)}
      .stat-card{padding:16px;border-radius:12px;background:linear-gradient(180deg,#f7fdff,#eef9ff);box-shadow:0 6px 18px rgba(12,30,60,0.06)}
      .muted{color:var(--muted)}
      .small{font-size:0.85rem}
      .risk-bar {height:14px;border-radius:8px;margin-top:6px}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Helpers ---
@st.cache_data(ttl=8)
def fetch_dashboard() -> Dict[str, Any]:
    try:
        r = requests.get(f"{API_BASE}/api/dashboard", headers=HEADERS, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

@st.cache_data(ttl=30)
def fetch_model() -> Dict[str, Any]:
    try:
        r = requests.get(f"{API_BASE}/model", headers=HEADERS, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

def post_predict(payload: Dict) -> Dict:
    try:
        r = requests.post(f"{API_BASE}/predict", json=payload, headers=HEADERS, timeout=15)
        if r.status_code >= 500:
            return {"error": f"server {r.status_code}"}
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# --- Navigation via query params ---
params = st.query_params
page = params.get("page", ["Dashboard"])[0]

def nav_to(p: str):
    st.query_params["page"] = p

# --- Top bar with nav ---
top_col1, top_col2 = st.columns([1, 3])
with top_col1:
    st.markdown("<div style='font-weight:700;color:#fff'><img src='https://via.placeholder.com/36' style='vertical-align:middle;border-radius:6px;margin-right:8px'/> IIT Predictor</div>", unsafe_allow_html=True)
with top_col2:
    st.markdown(
        f"<div class='topbar'><div><h2 style='margin:0;color:#fff'>Predict Patient Treatment Risk</h2><div class='hero-sub small'>Early intervention improves retention & outcomes</div></div>"
        f"<div class='nav'>"
        f"<a href='?page=Dashboard'>Dashboard</a>"
        f"<a href='?page=New%20Prediction'>New Prediction</a>"
        f"<a href='?page=Model%20Metrics'>Model Metrics</a>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

# session storage for recents
if "recent_local" not in st.session_state:
    st.session_state.recent_local = []

# --- Pages ---
def render_dashboard():
    st.markdown("### Overview")
    dash = fetch_dashboard()
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='stat-card'><div class='small muted'>Total Predictions</div><h2 style='margin:6px 0'>{dash.get('total_predictions', 0)}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-card'><div class='small muted'>High Risk Patients</div><h2 style='margin:6px 0;color:#ff6b6b'>{dash.get('high_risk_patients', 0)}</h2></div>", unsafe_allow_html=True)
    avg = dash.get("avg_risk_score", 0.0)
    c3.markdown(f"<div class='stat-card'><div class='small muted'>Avg Risk Score</div><h2 style='margin:6px 0'>{round(avg*100,1)}%</h2></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='stat-card'><div class='small muted'>Predictions Today</div><h2 style='margin:6px 0'>{dash.get('predictions_today',0)}</h2></div>", unsafe_allow_html=True)

    st.markdown("### Risk Distribution")
    risk = dash.get("by_risk", [])
    if risk:
        total = sum([int(r.get("value",0)) for r in risk]) or 1
        for r in risk:
            name = r.get("name")
            count = int(r.get("value",0))
            pct = round(count/total*100)
            color = {
                "LOW":"#66bb6a","MEDIUM":"#ffca28","HIGH":"#ff8a65","CRITICAL":"#ef5350"
            }.get(name, "#1976d2")
            st.markdown(f"<div style='display:flex;justify-content:space-between'><div>{name}</div><div class='small muted'>{count} patients · {pct}%</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='risk-bar' style='background:linear-gradient(90deg,{color}, {color}bb);width:{pct}%' ></div>", unsafe_allow_html=True)
    else:
        st.info("No risk data available")

    st.markdown("### Recent Predictions")
    recent = dash.get("recent_predictions") or []
    combined = (recent if isinstance(recent, list) else []) + st.session_state.recent_local
    if combined:
        rows = []
        for r in combined[:20]:
            rows.append({
                "patient": r.get("patient_uuid") or r.get("patient") or "n/a",
                "score %": (r.get("iit_risk_score") and round(r.get("iit_risk_score")*100,1)) or None,
                "risk": r.get("risk_level") or "UNKNOWN",
                "ts": r.get("timestamp") or r.get("timeAgo") or ""
            })
        st.table(pd.DataFrame(rows))
    else:
        st.write("No recent predictions yet.")

def render_new_prediction():
    st.markdown("### New Assessment")
    with st.form("predict_form"):
        pid = st.text_input("Patient UUID", value=f"p-{int(time.time())}")
        birth = st.date_input("Birth date")
        gender = st.selectbox("Gender", ["MALE", "FEMALE", "OTHER", "UNKNOWN"])
        state = st.text_input("State / Location", value="")
        phone = st.text_input("Phone Number", value="")
        st.markdown("#### Clinical Information (optional)")
        last_visit = st.date_input("Last Visit Date", value=None)
        days_supply = st.number_input("Days Supply", min_value=0, value=30)
        extra_json = st.text_area("Additional features (JSON)", value="{}")
        submit = st.form_submit_button("Calculate Risk Score")
        if submit:
            payload = {
                "patient_uuid": pid,
                "demographics": {"birth_date": birth.isoformat(), "gender": gender, "state": state, "phone_number": phone},
                "visits": [],
                "metadata": {}
            }
            try:
                if last_visit:
                    payload["visits"].append({"start_date": last_visit.isoformat()})
                payload.setdefault("metadata", {})["days_supply"] = int(days_supply)
                import json as _json
                extra = _json.loads(extra_json) if extra_json.strip() else {}
                if isinstance(extra, dict):
                    payload["metadata"].update(extra)
            except Exception as e:
                st.error(f"Invalid additional data: {e}")
                return
            st.info("Sending request...")
            res = post_predict(payload)
            if res.get("error"):
                st.error(f"Prediction failed: {res['error']}")
            else:
                st.success("Prediction received")
                st.json(res)
                st.session_state.recent_local.insert(0, {
                    "patient_uuid": res.get("patient_uuid", pid),
                    "iit_risk_score": res.get("iit_risk_score"),
                    "risk_level": res.get("risk_level"),
                    "timestamp": res.get("timestamp")
                })
                fetch_dashboard.clear()
                st.rerun()

def render_model_metrics():
    st.markdown("### Model & Runtime Metrics")
    meta = fetch_model()
    if meta:
        st.subheader("Model metadata")
        st.json(meta)
    else:
        st.info("No model metadata returned from backend (GET /model).")

    st.subheader("Prometheus /metrics (raw)")
    try:
        r = requests.get(f"{API_BASE}/metrics", headers=HEADERS, timeout=5)
        if r.status_code == 200:
            st.text_area("metrics", value=r.text, height=240)
        else:
            st.write(f"Metrics endpoint returned {r.status_code}")
    except Exception as e:
        st.write(f"Metrics fetch error: {e}")

# Router
if page == "Dashboard":
    render_dashboard()
elif page == "New Prediction":
    render_new_prediction()
else:
    render_model_metrics()