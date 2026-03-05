"""
Gold XAU/USD Data Fetcher Module
Raccoglie dati da: FRED API, Yahoo Finance, SPDR Gold Shares CSV, Investing.com
"""
import requests
from datetime import datetime, timedelta
import time

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {
    "DFII10": "10-Year Real Interest Rate (TIPS)",
    "T10YIE": "10-Year Breakeven Inflation Rate",
    "DFF": "Federal Funds Effective Rate",
    "DGS2": "2-Year Treasury Constant Maturity Rate",
}
YAHOO_TICKERS = {"DXY": "DX-Y.NYB", "VIX": "^VIX", "GOLD": "GC=F"}
FED_EVENT_ID = 168

GOLD_SEASONALITY = {
    1: {"score":1,"label":"Favorevole","reason":"Capodanno lunare + domanda India"},
    2: {"score":1,"label":"Favorevole","reason":"Prosecuzione domanda Q1"},
    3: {"score":-1,"label":"Sfavorevole","reason":"Finestra storicamente debole"},
    4: {"score":-1,"label":"Sfavorevole","reason":"Finestra storicamente debole"},
    5: {"score":-1,"label":"Sfavorevole","reason":"Finestra storicamente debole"},
    6: {"score":-1,"label":"Sfavorevole","reason":"Finestra storicamente debole"},
    7: {"score":0,"label":"Neutro","reason":"Transizione pre-festival"},
    8: {"score":0,"label":"Neutro","reason":"Transizione pre-festival"},
    9: {"score":1,"label":"Favorevole","reason":"Mese storicamente piu forte"},
    10: {"score":0,"label":"Neutro","reason":"Misto post-festival"},
    11: {"score":0,"label":"Neutro","reason":"Misto post-festival"},
    12: {"score":1,"label":"Favorevole","reason":"Ribilanciamento fine anno"},
}

SCORING_THRESHOLDS = {
    "DFII10": {"level":[(0.5,1),(1.5,0),(999,-1)],"mom_thresh":0.15},
    "DXY": {"level":[(98,2),(101,1),(105,0),(107,-1),(999,-2)],"mom_thresh":1.5},
    "T10YIE": {"level":[(2.0,-1),(2.5,0),(999,1)],"mom_thresh":0.10},
    "GLD": {"mom_thresh":10.0},
    "FED_SPREAD": {"level":[(-0.25,-1),(0.50,0),(999,1)],"mom_thresh":0.15},
    "VIX": {"level":[(15,-1),(20,0),(999,1)],"mom_thresh":5.0},
}

def fetch_fred_series(series_id, api_key, limit=100):
    obs_start = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
    params = {"series_id":series_id,"api_key":api_key,"file_type":"json",
              "observation_start":obs_start,"sort_order":"desc","limit":limit}
    try:
        r = requests.get(FRED_BASE_URL, params=params, timeout=15)
        if r.status_code != 200:
            return {"error":f"HTTP {r.status_code}","series_id":series_id}
        valid = [{"date":o["date"],"value":float(o["value"])}
                 for o in r.json().get("observations",[])
                 if o.get("value") and o["value"] != "."]
        if not valid:
            return {"error":"No valid data","series_id":series_id}
        return {"series_id":series_id,"description":FRED_SERIES.get(series_id,series_id),
                "latest_value":valid[0]["value"],"latest_date":valid[0]["date"],
                "values":valid[:60],"error":None}
    except Exception as e:
        return {"error":str(e)[:100],"series_id":series_id}

def fetch_all_fred_data(api_key):
    results = {}
    for sid in FRED_SERIES:
        results[sid] = fetch_fred_series(sid, api_key)
        time.sleep(0.3)
    return results

def fetch_yahoo_finance(ticker_key):
    ticker = YAHOO_TICKERS.get(ticker_key, ticker_key)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"range":"3mo","interval":"1d","includePrePost":"false"}
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code != 200:
            return {"error":f"HTTP {r.status_code}","ticker":ticker_key}
        chart = r.json().get("chart",{}).get("result",[])
        if not chart:
            return {"error":"No data","ticker":ticker_key}
        ts = chart[0].get("timestamp",[])
        closes = chart[0].get("indicators",{}).get("quote",[{}])[0].get("close",[])
        values = []
        for t, c in zip(ts, closes):
            if c is not None:
                values.append({"date":datetime.fromtimestamp(t).strftime("%Y-%m-%d"),"value":round(c,4)})
        values.reverse()
        if not values:
            return {"error":"No valid prices","ticker":ticker_key}
        return {"ticker":ticker_key,"latest_value":values[0]["value"],
                "latest_date":values[0]["date"],"values":values[:60],"error":None}
    except Exception as e:
        return {"error":str(e)[:100],"ticker":ticker_key}

def fetch_all_yahoo_data():
    results = {}
    for key in YAHOO_TICKERS:
        results[key] = fetch_yahoo_finance(key)
        time.sleep(0.3)
    return results

def fetch_fed_history():
    headers = {"User-Agent":"Mozilla/5.0","Accept":"application/json","Referer":"https://www.investing.com/"}
    url = f"https://sbcharts.investing.com/events_charts/us/{FED_EVENT_ID}.json"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return {"error":f"HTTP {r.status_code}"}
        attr = r.json().get("attr",[])
        if not attr or len(attr)<2:
            return {"error":"Insufficient data"}
        recent = attr[-3:] if len(attr)>=3 else attr
        recent.reverse()
        meetings = []
        for i, m in enumerate(recent):
            ts, actual = m.get("timestamp",0), m.get("actual")
            actual_fmt = m.get("actual_formatted","")
            try:
                dt = datetime.fromtimestamp(ts/1000)
                date_str, date_fmt = dt.strftime("%Y-%m-%d"), dt.strftime("%b %d, %Y")
            except: date_str, date_fmt = "N/A", "N/A"
            change, decision = None, "hold"
            if i < len(recent)-1:
                prev = recent[i+1].get("actual")
                if actual is not None and prev is not None:
                    try:
                        diff = float(actual)-float(prev)
                        if abs(diff)<0.001: decision,change = "hold","0bp"
                        elif diff>0: decision,change = "hike",f"+{int(diff*100)}bp"
                        else: decision,change = "cut",f"{int(diff*100)}bp"
                    except: pass
            meetings.append({"date":date_str,"date_formatted":date_fmt,
                           "rate":actual_fmt or f"{actual}%","decision":decision,"change":change or "N/A"})
        trend = _calc_fed_trend(meetings)
        return {"current_rate":meetings[0]["rate"] if meetings else "N/A",
                "meetings":meetings[:3],"trend":trend["trend"],
                "trend_label":trend["trend_label"],"trend_emoji":trend["trend_emoji"],"error":None}
    except Exception as e:
        return {"error":str(e)[:100]}

def _calc_fed_trend(meetings):
    if len(meetings)<2:
        return {"trend":"unknown","trend_label":"Sconosciuto","trend_emoji":"?"}
    d1, d2 = meetings[0].get("decision","hold"), meetings[1].get("decision","hold")
    t = {("hike","hike"):("hiking","Hiking","▲"),("cut","cut"):("cutting","Cutting","▼"),
         ("hold","hold"):("holding","Holding","➖"),("hike","hold"):("tightening","Tightening","▲"),
         ("hold","hike"):("pause_after_hike","Pausa (post-rialzo)","⏸"),
         ("cut","hold"):("easing","Easing","▼"),("hold","cut"):("pause_after_cut","Pausa (post-taglio)","⏸")}
    r = t.get((d1,d2),("mixed","Misto","?"))
    return {"trend":r[0],"trend_label":r[1],"trend_emoji":r[2]}



# === SCORING ENGINE ===

def _calc_level(value, thresholds):
    for thresh, score in thresholds:
        if value < thresh: return score
    return thresholds[-1][1]

def _calc_momentum(current, past, threshold, invert=False):
    delta = current - past
    if abs(delta) < threshold: return 0
    d = 1 if delta > 0 else -1
    return -d if invert else d

def _get_past_value(values, weeks=4):
    target = datetime.now() - timedelta(weeks=weeks)
    closest, min_diff = None, float("inf")
    for v in values:
        try:
            vd = datetime.strptime(v["date"], "%Y-%m-%d")
            diff = abs((vd - target).days)
            if diff < min_diff: min_diff, closest = diff, v["value"]
        except: continue
    return closest

def _make_score(name, value, value_raw, date, delta_4w, delta_raw,
                level_score, momentum_score, max_score, source, comment):
    return {"name":name,"value":value,"value_raw":value_raw,"date":date,
            "delta_4w":delta_4w,"delta_raw":delta_raw,
            "level_score":level_score,"momentum_score":momentum_score,
            "total_score":level_score+momentum_score,"max_score":max_score,
            "source":source,"comment":comment}

def _empty(name, error, max_score):
    return _make_score(name,"N/A",None,"N/A","N/A",None,0,0,max_score,"N/A",
                       f"⚠️ {error}" if error else "⚠️ Non disponibile")

def _bias_label(total):
    if total >= 10: return "FORTE BULLISH"
    if total >= 4: return "MODERATO BULLISH"
    if total >= -3: return "NEUTRO"
    if total >= -9: return "MODERATO BEARISH"
    return "FORTE BEARISH"

def calculate_all_scores(fred_data, yahoo_data, fed_data,
                          cot_data=None):
    scores = {}
    now = datetime.now()

    # 1. DFII10
    d = fred_data.get("DFII10",{})
    if d.get("latest_value") is not None and not d.get("error"):
        cv, pv = d["latest_value"], _get_past_value(d.get("values",[]),4)
        lv = _calc_level(cv, SCORING_THRESHOLDS["DFII10"]["level"])
        mv = _calc_momentum(cv,pv,SCORING_THRESHOLDS["DFII10"]["mom_thresh"],invert=True) if pv else 0
        scores["DFII10"] = _make_score("Tasso Reale 10Y (DFII10)",f"{cv:.2f}%",cv,
            d.get("latest_date"),f"{cv-pv:+.2f}%" if pv else "N/A",cv-pv if pv else None,
            lv,mv,2,"FRED",f"Livello {'basso' if lv>0 else 'neutro' if lv==0 else 'alto'} ({lv:+d}), tassi reali {'in calo' if mv>0 else 'in salita' if mv<0 else 'stabili'} ({mv:+d})")
    else: scores["DFII10"] = _empty("Tasso Reale 10Y (DFII10)",d.get("error"),2)

    # 2. DXY
    d = yahoo_data.get("DXY",{})
    if d.get("latest_value") is not None and not d.get("error"):
        cv, pv = d["latest_value"], _get_past_value(d.get("values",[]),4)
        lv = _calc_level(cv, SCORING_THRESHOLDS["DXY"]["level"])
        mv = _calc_momentum(cv,pv,SCORING_THRESHOLDS["DXY"]["mom_thresh"],invert=True) if pv else 0
        dl = {2:"Molto debole",1:"Debole",0:"Neutro",-1:"Forte",-2:"Molto forte"}
        scores["DXY"] = _make_score("DXY (US Dollar Index)",f"{cv:.2f}",cv,
            d.get("latest_date"),f"{cv-pv:+.2f}" if pv else "N/A",cv-pv if pv else None,
            lv,mv,3,"Yahoo Finance",f"Dollaro {dl.get(lv,'?')} ({lv:+d}), {'in calo' if mv>0 else 'in salita' if mv<0 else 'stabile'} ({mv:+d})")
    else: scores["DXY"] = _empty("DXY (US Dollar Index)",d.get("error"),3)

    # 3. T10YIE
    d = fred_data.get("T10YIE",{})
    if d.get("latest_value") is not None and not d.get("error"):
        cv, pv = d["latest_value"], _get_past_value(d.get("values",[]),4)
        lv = _calc_level(cv, SCORING_THRESHOLDS["T10YIE"]["level"])
        mv = _calc_momentum(cv,pv,SCORING_THRESHOLDS["T10YIE"]["mom_thresh"],invert=False) if pv else 0
        scores["T10YIE"] = _make_score("Breakeven Inflation 10Y",f"{cv:.2f}%",cv,
            d.get("latest_date"),f"{cv-pv:+.2f}%" if pv else "N/A",cv-pv if pv else None,
            lv,mv,2,"FRED",f"Inflazione attesa {'alta' if lv>0 else 'neutra' if lv==0 else 'bassa'} ({lv:+d}), {'in salita' if mv>0 else 'in calo' if mv<0 else 'stabile'} ({mv:+d})")
    else: scores["T10YIE"] = _empty("Breakeven Inflation 10Y",d.get("error"),2)

    # 5. COT
    # Gestisci sia formato vecchio (flat) che nuovo (GOLD/USD)
    _cot = cot_data.get("GOLD", cot_data) if cot_data else {}
    if _cot and not _cot.get("error"):
        ci, cm = _cot.get("cot_index",50), _cot.get("momentum_score",0)
        ps = 1 if ci>75 else (-1 if ci<25 else 0)
        warn = " ⚠️ Eccesso" if ci>90 else (" ⚠️ Molto basso" if ci<10 else "")
        scores["COT"] = _make_score("COT Oro Non-Commercial",f"Index: {ci:.0f}%",ci,
            _cot.get("latest_date"),f"Net: {_cot.get('net_long',0):+,.0f}",
            _cot.get("net_long",0),ps,cm,2,"CFTC",
            f"{'Bullish' if ps>0 else 'Bearish' if ps<0 else 'Neutro'} ({ps:+d}), mom {'↑' if cm>0 else '↓' if cm<0 else '→'} ({cm:+d}){warn}")
    else: scores["COT"] = _empty("COT Oro Non-Commercial",_cot.get("error") if _cot else "Non caricato",2)

    # 5b. COT USD (invertito: USD long = bearish oro)
    _cot_usd = cot_data.get("USD", {}) if cot_data else {}
    if _cot_usd and not _cot_usd.get("error"):
        ci_u, cm_u = _cot_usd.get("cot_index",50), _cot_usd.get("momentum_score",0)
        ps_u = 1 if ci_u>75 else (-1 if ci_u<25 else 0)
        # Inverti: USD bullish = oro bearish
        ps_u_inv = -ps_u
        cm_u_inv = -cm_u
        scores["COT_USD"] = _make_score("COT USD Index",f"Index: {ci_u:.0f}%",ci_u,
            _cot_usd.get("latest_date"),f"Net: {_cot_usd.get('net_long',0):+,.0f}",
            _cot_usd.get("net_long",0),ps_u_inv,cm_u_inv,2,"CFTC",
            f"USD {'Long' if ps_u>0 else 'Short' if ps_u<0 else 'Neutro'} ({ps_u_inv:+d} inv.), mom {'\u2191' if cm_u_inv>0 else '\u2193' if cm_u_inv<0 else '\u2192'} ({cm_u_inv:+d})")
    else: scores["COT_USD"] = _empty("COT USD Index",_cot_usd.get("error") if _cot_usd else "Non caricato",2)

    # 5. Fed Trend
    if fed_data and not fed_data.get("error"):
        t = fed_data.get("trend","unknown")
        fs = {"cutting":1,"easing":1,"pause_after_cut":1,"holding":0,
              "pause_after_hike":-1,"tightening":-1,"hiking":-1,"mixed":0,"unknown":0}
        fsc = fs.get(t,0)
        mtgs = ", ".join(f"{m['change']} ({m['date']})" for m in fed_data.get("meetings",[])[:2])
        scores["FED_TREND"] = _make_score("Fed Trend (ciclo FOMC)",
            f"{fed_data.get('current_rate','N/A')} - {fed_data.get('trend_label','N/A')}",
            fed_data.get("current_rate"),fed_data.get("meetings",[{}])[0].get("date","N/A"),
            mtgs,None,fsc,0,1,"Investing.com",
            f"{fed_data.get('trend_emoji','')} {fed_data.get('trend_label','N/A')} — {mtgs}")
    else: scores["FED_TREND"] = _empty("Fed Trend (ciclo FOMC)",fed_data.get("error") if fed_data else "Non caricato",1)

    # 6. Fed Expectations
    dff, dgs2 = fred_data.get("DFF",{}), fred_data.get("DGS2",{})
    if dff.get("latest_value") is not None and dgs2.get("latest_value") is not None:
        ffr, t2y = dff["latest_value"], dgs2["latest_value"]
        sp = ffr - t2y
        fp, tp = _get_past_value(dff.get("values",[]),4), _get_past_value(dgs2.get("values",[]),4)
        sp_past = (fp-tp) if fp and tp else None
        lv = _calc_level(sp, SCORING_THRESHOLDS["FED_SPREAD"]["level"])
        mv = _calc_momentum(sp,sp_past,SCORING_THRESHOLDS["FED_SPREAD"]["mom_thresh"],invert=False) if sp_past else 0
        lt = "Tagli prezzati" if sp>0.5 else ("Neutro" if sp>-0.25 else "Rialzi prezzati")
        scores["FED_EXPECT"] = _make_score("Fed Expectations (FFR-2Y)",
            f"FFR {ffr:.2f}% - 2Y {t2y:.2f}% = {sp:+.2f}%",sp,dff.get("latest_date"),
            f"{sp-sp_past:+.2f}%" if sp_past else "N/A",sp-sp_past if sp_past else None,
            lv,mv,2,"FRED",f"{lt} ({lv:+d}), {'piu tagli' if mv>0 else 'meno tagli' if mv<0 else 'stabile'} ({mv:+d})")
    else: scores["FED_EXPECT"] = _empty("Fed Expectations (FFR-2Y)","Dati mancanti",2)

    # 7. VIX
    d = yahoo_data.get("VIX",{})
    if d.get("latest_value") is not None and not d.get("error"):
        cv, pv = d["latest_value"], _get_past_value(d.get("values",[]),1)
        lv = _calc_level(cv, SCORING_THRESHOLDS["VIX"]["level"])
        mv = _calc_momentum(cv,pv,SCORING_THRESHOLDS["VIX"]["mom_thresh"],invert=False) if pv else 0
        scores["VIX"] = _make_score("VIX (Risk Sentiment)",f"{cv:.2f}",cv,
            d.get("latest_date"),f"{cv-pv:+.2f}" if pv else "N/A",cv-pv if pv else None,
            lv,mv,2,"Yahoo Finance",f"{'Risk-off' if lv>0 else 'Risk-on' if lv<0 else 'Neutro'} ({lv:+d}), {'spike' if mv>0 else 'calo' if mv<0 else 'stabile'} ({mv:+d})")
    else: scores["VIX"] = _empty("VIX (Risk Sentiment)",d.get("error"),2)

    # 8. Stagionalita
    s = GOLD_SEASONALITY.get(now.month,{"score":0,"label":"Neutro","reason":""})
    scores["SEASONALITY"] = _make_score("Stagionalita",now.strftime("%B"),now.month,
        now.strftime("%Y-%m-%d"),"N/A",None,s["score"],0,1,"Pattern storico",f"{s['label']} — {s['reason']}")

    # Gold price
    g = yahoo_data.get("GOLD",{})
    if g.get("latest_value"):
        scores["GOLD_PRICE"] = {"name":"Prezzo XAU/USD","value":f"${g['latest_value']:,.2f}",
                                 "value_raw":g["latest_value"],"date":g.get("latest_date","N/A")}

    total = sum(s.get("total_score",0) for k,s in scores.items() if k not in ["GOLD_PRICE","TOTAL"] and "total_score" in s)
    scores["TOTAL"] = {"total_score":total,"bias":_bias_label(total)}
    return scores
