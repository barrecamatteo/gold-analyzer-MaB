"""
Gold + USD COT (Commitment of Traders) Data Module
Contratti CFTC: Oro = 088691, USD Index = 098662
"""
import requests
import numpy as np
from datetime import datetime, timedelta
import time

COT_CONTRACTS = {
    "GOLD": {"code": "088691", "name": "Oro", "icon": "🥇"},
    "USD": {"code": "098662", "name": "USD Index", "icon": "💵"},
}
CFTC_BASE_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
LOOKBACK_WEEKS = 52


def fetch_cot_data(contract_code, limit=60):
    """Fetch COT data per un contratto dalla CFTC API."""
    params = {
        "$where": f"cftc_contract_market_code='{contract_code}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": limit,
    }
    try:
        r = requests.get(CFTC_BASE_URL, params=params, timeout=30)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}"}
        data = r.json()
        if not data:
            return {"error": "No COT data"}
        records = []
        for row in data:
            try:
                date = row.get("report_date_as_yyyy_mm_dd", "")[:10]
                nl = int(row.get("noncomm_positions_long_all", 0))
                ns = int(row.get("noncomm_positions_short_all", 0))
                net = nl - ns
                oi = int(row.get("open_interest_all", 0))
                records.append({"date": date, "net_long": net, "long": nl,
                               "short": ns, "open_interest": oi})
            except:
                continue
        if not records:
            return {"error": "No valid COT records"}
        records.sort(key=lambda x: x["date"], reverse=True)
        return {"records": records, "error": None}
    except Exception as e:
        return {"error": str(e)[:100]}


def calculate_cot_score(cot_raw):
    """
    Calcola COT Index e momentum.
    Returns dict con: cot_index, momentum_score, net_long, delta_1w, ecc.
    """
    if cot_raw.get("error") or not cot_raw.get("records"):
        return {"error": cot_raw.get("error", "No data"), "cot_index": 50,
                "momentum_score": 0, "net_long": 0, "delta_1w": 0}

    records = cot_raw["records"]
    if len(records) < 10:
        return {"error": "Insufficient history", "cot_index": 50,
                "momentum_score": 0, "net_long": records[0]["net_long"] if records else 0,
                "delta_1w": 0}

    hist = records[:LOOKBACK_WEEKS]
    nets = [r["net_long"] for r in hist]
    current_net = nets[0]
    max_net, min_net = max(nets), min(nets)

    # COT Index (0-100%)
    if max_net == min_net:
        cot_index = 50.0
    else:
        cot_index = ((current_net - min_net) / (max_net - min_net)) * 100

    # Delta 1 settimana
    delta_1w = current_net - nets[1] if len(nets) >= 2 else 0

    # Momentum: net attuale vs media 4 settimane
    ma_4w = np.mean(nets[1:5]) if len(nets) >= 5 else np.mean(nets[1:])
    delta_vs_ma = current_net - ma_4w
    mom_thresh = (max_net - min_net) * 0.05 if max_net != min_net else 1000

    if delta_vs_ma > mom_thresh:
        momentum_score = 1
    elif delta_vs_ma < -mom_thresh:
        momentum_score = -1
    else:
        momentum_score = 0

    # Posizionamento score
    if cot_index > 75:
        pos_score = 1
    elif cot_index < 25:
        pos_score = -1
    else:
        pos_score = 0

    # Interpretazione testuale
    if pos_score > 0 and momentum_score > 0:
        interp = "Long forte + accelerazione acquisti"
    elif pos_score > 0 and momentum_score == 0:
        interp = "Long forte consolidato"
    elif pos_score > 0 and momentum_score < 0:
        interp = "Long forte ma stanno vendendo"
    elif pos_score == 0 and momentum_score > 0:
        interp = "Long debole, in costruzione"
    elif pos_score == 0 and momentum_score == 0:
        interp = "Long debole, stabile"
    elif pos_score == 0 and momentum_score < 0:
        interp = "Bearish in costruzione"
    elif pos_score < 0 and momentum_score < 0:
        interp = "Short forte consolidato"
    elif pos_score < 0 and momentum_score == 0:
        interp = "Short, stabile"
    else:
        interp = "Short in riduzione"

    total_score = pos_score + momentum_score

    return {
        "cot_index": round(cot_index, 1),
        "pos_score": pos_score,
        "momentum_score": momentum_score,
        "total_score": total_score,
        "net_long": current_net,
        "delta_1w": delta_1w,
        "ma_4w": round(ma_4w, 0),
        "delta_vs_ma": round(delta_vs_ma, 0),
        "max_52w": max_net,
        "min_52w": min_net,
        "latest_date": records[0]["date"],
        "records_count": len(records),
        "interpretation": interp,
        "error": None,
    }


def get_gold_cot_analysis():
    """Fetch + calcolo score per ORO."""
    raw = fetch_cot_data(COT_CONTRACTS["GOLD"]["code"])
    result = calculate_cot_score(raw)
    result["asset"] = "GOLD"
    result["asset_name"] = "Oro"
    return result


def get_usd_cot_analysis():
    """Fetch + calcolo score per USD Index."""
    raw = fetch_cot_data(COT_CONTRACTS["USD"]["code"])
    result = calculate_cot_score(raw)
    result["asset"] = "USD"
    result["asset_name"] = "USD Index"
    return result


def get_all_cot_analysis():
    """Fetch entrambi: Gold + USD. Ritorna dict con entrambi."""
    gold = get_gold_cot_analysis()
    time.sleep(0.5)
    usd = get_usd_cot_analysis()
    return {
        "GOLD": gold,
        "USD": usd,
        "latest_date": gold.get("latest_date", usd.get("latest_date", "N/A")),
        "error": None if not gold.get("error") else gold.get("error"),
    }
