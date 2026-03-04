"""
Gold COT (Commitment of Traders) Data Module
Codice contratto oro CFTC: 088691
"""
import requests
import numpy as np
from datetime import datetime, timedelta
import time

GOLD_CONTRACT_CODE = "088691"
CFTC_BASE_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
LOOKBACK_WEEKS = 52

def fetch_gold_cot_data(limit=60):
    params = {
        "$where": f"cftc_contract_market_code='{GOLD_CONTRACT_CODE}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": limit,
    }
    try:
        r = requests.get(CFTC_BASE_URL, params=params, timeout=30)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}"}
        data = r.json()
        if not data:
            return {"error": "No COT data for gold"}
        records = []
        for row in data:
            try:
                date = row.get("report_date_as_yyyy_mm_dd", "")[:10]
                nl = int(row.get("noncomm_positions_long_all", 0))
                ns = int(row.get("noncomm_positions_short_all", 0))
                net = nl - ns
                oi = int(row.get("open_interest_all", 0))
                records.append({"date":date,"net_long":net,"long":nl,"short":ns,"open_interest":oi})
            except:
                continue
        if not records:
            return {"error": "No valid COT records"}
        records.sort(key=lambda x: x["date"], reverse=True)
        return {"records": records, "error": None}
    except Exception as e:
        return {"error": str(e)[:100]}


def calculate_gold_cot_score(cot_raw):
    if cot_raw.get("error") or not cot_raw.get("records"):
        return {"error":cot_raw.get("error","No data"),"cot_index":50,"momentum_score":0,"net_long":0}
    records = cot_raw["records"]
    if len(records) < 10:
        return {"error":"Insufficient history","cot_index":50,"momentum_score":0,"net_long":records[0]["net_long"] if records else 0}
    hist = records[:LOOKBACK_WEEKS]
    nets = [r["net_long"] for r in hist]
    current_net = nets[0]
    max_net, min_net = max(nets), min(nets)
    cot_index = ((current_net - min_net) / (max_net - min_net)) * 100 if max_net != min_net else 50.0
    ma_4w = np.mean(nets[1:5]) if len(nets) >= 5 else np.mean(nets[1:])
    delta_vs_ma = current_net - ma_4w
    mom_thresh = (max_net - min_net) * 0.05 if max_net != min_net else 1000
    if delta_vs_ma > mom_thresh: momentum_score = 1
    elif delta_vs_ma < -mom_thresh: momentum_score = -1
    else: momentum_score = 0
    return {"cot_index":round(cot_index,1),"momentum_score":momentum_score,
            "net_long":current_net,"ma_4w":round(ma_4w,0),"delta_vs_ma":round(delta_vs_ma,0),
            "max_52w":max_net,"min_52w":min_net,"latest_date":records[0]["date"],
            "records_count":len(records),"error":None}


def get_gold_cot_analysis():
    raw = fetch_gold_cot_data()
    return calculate_gold_cot_score(raw)
