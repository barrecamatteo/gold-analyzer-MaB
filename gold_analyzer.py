import streamlit as st
from datetime import datetime, timedelta
import json
import hashlib

from gold_data_fetcher import (
    fetch_all_fred_data, fetch_all_yahoo_data, fetch_gld_holdings,
    fetch_fed_history, calculate_all_scores, _bias_label
)
from gold_cot_data import get_all_cot_analysis
from gold_ui import (
    display_indicator_cards, display_scores_table,
    display_calendar_sidebar, display_past_analysis
)

try:
    from zoneinfo import ZoneInfo
    ITALY_TZ = ZoneInfo("Europe/Rome")
except ImportError:
    ITALY_TZ = None

def get_italy_now():
    if ITALY_TZ:
        return datetime.now(ITALY_TZ)
    return datetime.utcnow() + timedelta(hours=1)

# === SUPABASE ===
def get_sb():
    try:
        from supabase import create_client
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.error(f"Supabase error: {e}")
        return None

def save_analysis(user_id, scores, gold_price, raw_data):
    sb = get_sb()
    if not sb:
        return False
    try:
        sb.table("gold_analyses").insert({
            "user_id": user_id,
            "analysis_date": get_italy_now().strftime("%Y-%m-%d"),
            "gold_price": gold_price,
            "total_score": scores.get("TOTAL", {}).get("total_score", 0),
            "bias": scores.get("TOTAL", {}).get("bias", "N/A"),
            "scores_json": json.dumps(scores, default=str),
            "claude_response": json.dumps(raw_data, default=str),
            "created_at": get_italy_now().isoformat(),
        }).execute()
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False

def load_history(user_id, limit=30):
    sb = get_sb()
    if not sb:
        return []
    try:
        r = sb.table("gold_analyses").select("*").eq("user_id", user_id).order("analysis_date", desc=True).limit(limit).execute()
        return r.data or []
    except:
        return []

# === AUTH ===
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def auth_user(username, password):
    sb = get_sb()
    if not sb:
        return None
    try:
        r = sb.table("gold_users").select("*").eq("username", username).execute()
        if r.data and r.data[0]["password_hash"] == hash_pw(password):
            return r.data[0]
    except:
        pass
    return None

# === DATA SOURCES CONFIG ===
DATA_SOURCES = {
    "fred_data": {"label": "FRED (Tassi, Inflazione)", "icon": "\U0001F4C8", "freshness_h": 24},
    "yahoo_data": {"label": "Yahoo (DXY, VIX, Gold)", "icon": "\U0001F4B9", "freshness_h": 12},
    "gld_data": {"label": "GLD Holdings (SPDR)", "icon": "\U0001F947", "freshness_h": 24},
    "fed_data": {"label": "Fed (FOMC History)", "icon": "\U0001F3DB\uFE0F", "freshness_h": 168},
    "cot_data": {"label": "COT (CFTC Gold + USD)", "icon": "\U0001F4CB", "freshness_h": 168},
}

def check_freshness(data_key, last_updated):
    if last_updated is None:
        return {"is_fresh": False, "status": "\U0001F534", "message": "Mai aggiornato", "ago": ""}
    now = get_italy_now()
    if isinstance(last_updated, str):
        try:
            last_updated = datetime.fromisoformat(last_updated)
        except:
            return {"is_fresh": False, "status": "\U0001F534", "message": "Data non valida", "ago": ""}
    if last_updated.tzinfo is None and ITALY_TZ:
        last_updated = last_updated.replace(tzinfo=ITALY_TZ)
    age_h = (now - last_updated).total_seconds() / 3600
    mx = DATA_SOURCES.get(data_key, {}).get("freshness_h", 24)
    date_str = last_updated.strftime("%d/%m %H:%M")
    if age_h < mx:
        return {"is_fresh": True, "status": "\U0001F7E2", "message": f"{date_str}", "ago": f"{int(age_h)}h fa"}
    return {"is_fresh": False, "status": "\U0001F7E0", "message": f"{date_str}", "ago": f"{int(age_h)}h fa"}

def fetch_source(key):
    """Fetch a single data source by key."""
    if key == "fred_data":
        return fetch_all_fred_data(st.secrets["fred"]["api_key"])
    elif key == "yahoo_data":
        return fetch_all_yahoo_data()
    elif key == "gld_data":
        return fetch_gld_holdings()
    elif key == "fed_data":
        return fetch_fed_history()
    elif key == "cot_data":
        return get_all_cot_analysis()
    return None

# === MAIN ===
def main():
    st.set_page_config(page_title="Gold XAU/USD Macro Analyzer", page_icon="\U0001F947",
                       layout="wide", initial_sidebar_state="expanded")
    st.markdown("""<style>
    .stMetricValue {font-size:1.3rem!important}
    .main .block-container {padding-top:1rem;max-width:1200px}
    </style>""", unsafe_allow_html=True)

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "analysis_done" not in st.session_state:
        st.session_state.analysis_done = False
    if "analysis_scores" not in st.session_state:
        st.session_state.analysis_scores = None

    # LOGIN
    if not st.session_state.authenticated:
        st.title("\U0001F947 Gold XAU/USD Macro Analyzer")
        st.markdown("*Analisi macro settimanale con scoring automatico*")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Accedi", type="primary"):
                user = auth_user(u, p)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_id = user.get("id", u)
                    st.session_state.username = u
                    st.rerun()
                else:
                    st.error("Credenziali non valide")
        return

    # MAIN APP
    st.title("\U0001F947 Gold XAU/USD Macro Analyzer")
    st.caption(f"User: {st.session_state.get('username','?')} | {get_italy_now().strftime('%d/%m/%Y %H:%M')}")

    # Sidebar
    history = load_history(st.session_state.user_id)
    sel_hist = display_calendar_sidebar(history)
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    # Se selezionata analisi passata, mostrala
    if sel_hist:
        display_past_analysis(sel_hist)
        st.markdown("---")
        if st.button("\u2B05\uFE0F Torna all'analisi corrente"):
            st.rerun()
        return

    # Init session state per ogni data source
    for dk in DATA_SOURCES:
        if dk not in st.session_state:
            st.session_state[dk] = None
        if f"{dk}_ts" not in st.session_state:
            st.session_state[f"{dk}_ts"] = None

    # === AUTO-LOAD: carica ultimi dati dall'ultima analisi salvata ===
    if "last_analysis_loaded" not in st.session_state:
        st.session_state.last_analysis_loaded = False

    if not st.session_state.last_analysis_loaded and history:
        last = history[0]  # la piu recente
        last_date = last.get("analysis_date", "N/A")
        try:
            raw = json.loads(last.get("claude_response", "{}"))
            last_scores = json.loads(last.get("scores_json", "{}"))
            if raw and last_scores:
                st.session_state.last_analysis_data = raw
                st.session_state.last_analysis_date = last_date
                st.session_state.last_analysis_scores = last_scores
                st.session_state.last_analysis_scores["TOTAL"] = {
                    "total_score": last.get("total_score", 0),
                    "bias": last.get("bias", "N/A"),
                }
                # Mostra anche l'ultimo risultato
                st.session_state.analysis_scores = st.session_state.last_analysis_scores
                st.session_state.analysis_done = True
        except:
            pass
        st.session_state.last_analysis_loaded = True

    # === SEZIONE DATA SOURCES CON BOTTONI ===
    st.markdown("## \U0001F4E5 Fonti Dati")

    # Aggiorna TUTTO
    if st.button("\U0001F504 Aggiorna TUTTO", type="primary"):
        with st.spinner("Aggiornamento completo..."):
            for dk in DATA_SOURCES:
                try:
                    st.session_state[dk] = fetch_source(dk)
                    st.session_state[f"{dk}_ts"] = get_italy_now().isoformat()
                except Exception as e:
                    st.error(f"{DATA_SOURCES[dk]['label']}: {e}")
            st.session_state.analysis_done = False
            st.session_state.analysis_scores = None
            st.rerun()

    st.markdown("")

    # Riga per ogni data source con bottone + stato
    for dk, cfg in DATA_SOURCES.items():
        f = check_freshness(dk, st.session_state.get(f"{dk}_ts"))
        c1, c2, c3, c4 = st.columns([0.5, 3, 2, 1.5])
        c1.markdown(f"### {cfg['icon']}")
        c2.markdown(f"**{cfg['label']}**")
        if f["ago"]:
            c3.markdown(f"{f['status']} {f['message']} ({f['ago']})")
        else:
            c3.markdown(f"{f['status']} Mai aggiornato")
        if c4.button("\U0001F504 Aggiorna", key=f"btn_{dk}"):
            with st.spinner(f"{cfg['label']}..."):
                try:
                    st.session_state[dk] = fetch_source(dk)
                    st.session_state[f"{dk}_ts"] = get_italy_now().isoformat()
                    st.session_state.analysis_done = False
                    st.session_state.analysis_scores = None
                except Exception as e:
                    st.error(f"{cfg['label']}: {e}")
                st.rerun()

    # === SCHEDE INDICATORI (SEMPRE APERTE) ===
    st.markdown("---")

    # Se non ci sono dati live ma c'e un'ultima analisi salvata, mostra quei dati
    has_live_data = st.session_state.fred_data or st.session_state.yahoo_data
    last_raw = st.session_state.get("last_analysis_data")
    last_date = st.session_state.get("last_analysis_date")

    if not has_live_data and last_raw and last_date:
        st.info(f"\U0001F4C5 Ultimi dati disponibili dall'analisi del **{last_date}**. Clicca \"Aggiorna TUTTO\" per dati freschi.")
        st.markdown("## \U0001F4CA Indicatori (da ultima analisi)")
        from gold_ui import display_last_analysis_indicators
        display_last_analysis_indicators(last_raw)
    else:
        st.markdown("## \U0001F4CA Indicatori")
        display_indicator_cards(
            fred_data=st.session_state.fred_data or {},
            yahoo_data=st.session_state.yahoo_data or {},
            gld_data=st.session_state.gld_data or {},
            fed_data=st.session_state.fed_data or {},
            cot_data=st.session_state.cot_data,
        )

    # === AVVIA ANALISI ===
    st.markdown("---")
    required = ["fred_data", "yahoo_data"]
    missing = [DATA_SOURCES[k]["label"] for k in required if not st.session_state.get(k)]

    if missing:
        st.warning(f"Dati mancanti per l'analisi: {', '.join(missing)}")

    if st.button("\U0001F680 Avvia Analisi", type="primary", disabled=bool(missing)):
        scores = calculate_all_scores(
            fred_data=st.session_state.fred_data,
            yahoo_data=st.session_state.yahoo_data,
            gld_data=st.session_state.gld_data or {},
            fed_data=st.session_state.fed_data or {},
            cot_data=st.session_state.cot_data,
        )
        gold_price = scores.get("GOLD_PRICE", {}).get("value_raw", 0)

        # Prepara raw data per salvataggio
        raw_data = {
            "fred_data_summary": {},
            "yahoo_data_summary": {},
            "gld_data_summary": {},
            "fed_data_summary": {},
            "cot_data_summary": {},
            "timestamps": {},
        }
        if st.session_state.fred_data:
            for sid, d in st.session_state.fred_data.items():
                if not d.get("error"):
                    raw_data["fred_data_summary"][sid] = {
                        "value": d.get("latest_value"), "date": d.get("latest_date"),
                    }
        if st.session_state.yahoo_data:
            for tk, d in st.session_state.yahoo_data.items():
                if not d.get("error"):
                    raw_data["yahoo_data_summary"][tk] = {
                        "value": d.get("latest_value"), "date": d.get("latest_date"),
                    }
        if st.session_state.gld_data and not st.session_state.gld_data.get("error"):
            raw_data["gld_data_summary"] = {
                "tonnes": st.session_state.gld_data.get("latest_tonnes"),
                "date": st.session_state.gld_data.get("latest_date"),
            }
        if st.session_state.fed_data and not st.session_state.fed_data.get("error"):
            raw_data["fed_data_summary"] = {
                "rate": st.session_state.fed_data.get("current_rate"),
                "trend": st.session_state.fed_data.get("trend_label"),
                "meetings": st.session_state.fed_data.get("meetings", [])[:5],
            }
        if st.session_state.cot_data and not st.session_state.cot_data.get("error"):
            for asset_key in ["GOLD", "USD"]:
                d = st.session_state.cot_data.get(asset_key, {})
                if d and not d.get("error"):
                    raw_data["cot_data_summary"][asset_key] = {
                        "net_long": d.get("net_long"), "cot_index": d.get("cot_index"),
                        "delta_1w": d.get("delta_1w"), "ma_4w": d.get("ma_4w"),
                        "interpretation": d.get("interpretation"),
                    }
        for dk in DATA_SOURCES:
            raw_data["timestamps"][dk] = st.session_state.get(f"{dk}_ts", "N/A")

        # Salva automaticamente
        save_analysis(st.session_state.user_id, scores, gold_price, raw_data)
        st.session_state.analysis_scores = scores
        st.session_state.analysis_done = True
        st.rerun()

    # === RISULTATI ===
    if st.session_state.analysis_done and st.session_state.analysis_scores:
        scores = st.session_state.analysis_scores
        st.markdown("---")
        st.markdown("## \U0001F3AF Risultati Analisi")
        display_scores_table(scores)
        st.success("Analisi salvata automaticamente!")

if __name__ == "__main__":
    main()
