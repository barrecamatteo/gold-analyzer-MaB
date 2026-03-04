import streamlit as st
import anthropic
from datetime import datetime, timedelta
import json
import hashlib

from gold_data_fetcher import (
    fetch_all_fred_data, fetch_all_yahoo_data, fetch_gld_holdings,
    fetch_fed_history, fetch_gold_news, format_news_for_claude,
    calculate_all_scores, _bias_label
)
from gold_cot_data import get_all_cot_analysis
from gold_claude import run_claude_analysis
from gold_ui import display_scores_table, display_claude_analysis, display_calendar_sidebar, display_data_input_section

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

def save_analysis(user_id, scores, claude_resp, gold_price):
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
            "scores_json": json.dumps({k: v for k, v in scores.items() if k != "TOTAL"}),
            "claude_response": claude_resp,
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



# === FRESHNESS ===
def check_freshness(data_key, last_updated):
    if last_updated is None:
        return {"is_fresh": False, "status": chr(0x1F534), "message": "Mai aggiornato"}
    now = get_italy_now()
    if isinstance(last_updated, str):
        try:
            last_updated = datetime.fromisoformat(last_updated)
        except:
            return {"is_fresh": False, "status": chr(0x1F534), "message": "Data non valida"}
    if last_updated.tzinfo is None and ITALY_TZ:
        last_updated = last_updated.replace(tzinfo=ITALY_TZ)
    age_h = (now - last_updated).total_seconds() / 3600
    thresh = {"fred_data": 24, "yahoo_data": 12, "gld_data": 24, "fed_data": 168,
              "cot_data": 168, "cb_data": 720, "news_data": 12}
    mx = thresh.get(data_key, 24)
    if age_h < mx:
        return {"is_fresh": True, "status": chr(0x1F7E2), "message": f"Aggiornato {int(age_h)}h fa"}
    return {"is_fresh": False, "status": chr(0x1F7E0), "message": f"Da aggiornare ({int(age_h)}h fa)"}

# === MAIN ===
def main():
    st.set_page_config(page_title="Gold XAU/USD Macro Analyzer", page_icon=chr(0x1F947),
                       layout="wide", initial_sidebar_state="expanded")
    st.markdown("""<style>
    .stMetricValue {font-size:1.5rem!important}
    div[data-testid="stSidebar"] {background-color:#1a1a2e}
    .main .block-container {padding-top:1rem;max-width:1200px}
    </style>""", unsafe_allow_html=True)

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    # LOGIN
    if not st.session_state.authenticated:
        st.title(chr(0x1F947) + " Gold XAU/USD Macro Analyzer")
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
    st.title(chr(0x1F947) + " Gold XAU/USD Macro Analyzer")
    st.caption(f"User: {st.session_state.get('username','?')} | {get_italy_now().strftime('%d/%m/%Y %H:%M')}")

    # Sidebar
    history = load_history(st.session_state.user_id)
    sel_hist = display_calendar_sidebar(history)
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    if sel_hist:
        st.markdown(f"### Analisi del {sel_hist['analysis_date']}")
        st.markdown(f"**Score: {sel_hist['total_score']:+d} | {sel_hist['bias']}**")
        if sel_hist.get("claude_response"):
            try:
                display_claude_analysis(json.loads(sel_hist["claude_response"]))
            except:
                st.markdown(sel_hist["claude_response"])
        st.markdown("---")

    # DATA INPUT
    st.markdown("## Dati di Input")
    data_keys = ["fred_data","yahoo_data","gld_data","fed_data","cot_data","cb_data","news_data"]
    for dk in data_keys:
        if dk not in st.session_state:
            st.session_state[dk] = None
        if f"{dk}_ts" not in st.session_state:
            st.session_state[f"{dk}_ts"] = None

    # Update all button
    if st.button(chr(0x1F504) + " Aggiorna TUTTO", type="primary"):
        with st.spinner("Aggiornamento..."):
            try:
                st.session_state.fred_data = fetch_all_fred_data(st.secrets["fred"]["api_key"])
                st.session_state.fred_data_ts = get_italy_now().isoformat()
            except Exception as e:
                st.error(f"FRED: {e}")
            st.session_state.yahoo_data = fetch_all_yahoo_data()
            st.session_state.yahoo_data_ts = get_italy_now().isoformat()
            st.session_state.gld_data = fetch_gld_holdings()
            st.session_state.gld_data_ts = get_italy_now().isoformat()
            st.session_state.fed_data = fetch_fed_history()
            st.session_state.fed_data_ts = get_italy_now().isoformat()
            st.session_state.cot_data = get_all_cot_analysis()
            st.session_state.cot_data_ts = get_italy_now().isoformat()
            st.session_state.news_data = fetch_gold_news()
            st.session_state.news_data_ts = get_italy_now().isoformat()
            st.success("Dati aggiornati!")
            st.rerun()

    # Status
    st.markdown("### Stato Dati")
    labels = {"fred_data":"FRED","yahoo_data":"Yahoo","gld_data":"GLD",
              "fed_data":"Fed","cot_data":"COT","cb_data":"BC","news_data":"News"}
    scols = st.columns(7)
    for i,(dk,lb) in enumerate(labels.items()):
        f = check_freshness(dk, st.session_state.get(f"{dk}_ts"))
        scols[i].markdown(f"{f['status']} **{lb}**")
        scols[i].caption(f["message"])

    # Single update buttons
    st.markdown("#### Aggiorna singolarmente:")
    bc = st.columns(7)
    if bc[0].button("FRED"):
        with st.spinner("FRED..."):
            st.session_state.fred_data = fetch_all_fred_data(st.secrets["fred"]["api_key"])
            st.session_state.fred_data_ts = get_italy_now().isoformat()
            st.rerun()
    if bc[1].button("Yahoo"):
        with st.spinner("Yahoo..."):
            st.session_state.yahoo_data = fetch_all_yahoo_data()
            st.session_state.yahoo_data_ts = get_italy_now().isoformat()
            st.rerun()
    if bc[2].button("GLD"):
        with st.spinner("GLD..."):
            st.session_state.gld_data = fetch_gld_holdings()
            st.session_state.gld_data_ts = get_italy_now().isoformat()
            st.rerun()
    if bc[3].button("Fed"):
        with st.spinner("Fed..."):
            st.session_state.fed_data = fetch_fed_history()
            st.session_state.fed_data_ts = get_italy_now().isoformat()
            st.rerun()
    if bc[4].button("COT"):
        with st.spinner("COT..."):
            st.session_state.cot_data = get_all_cot_analysis()
            st.session_state.cot_data_ts = get_italy_now().isoformat()
            st.rerun()
    if bc[5].button("BC"):
        st.info("Banche centrali: aggiornamento manuale trimestrale.")
    if bc[6].button("News"):
        with st.spinner("News..."):
            st.session_state.news_data = fetch_gold_news()
            st.session_state.news_data_ts = get_italy_now().isoformat()
            st.rerun()

    # Calcola punteggi parziali per mostrare dettaglio indicatori
    preview_scores = None
    if st.session_state.fred_data and st.session_state.yahoo_data:
        preview_scores = calculate_all_scores(
            fred_data=st.session_state.fred_data,
            yahoo_data=st.session_state.yahoo_data,
            gld_data=st.session_state.gld_data or {},
            fed_data=st.session_state.fed_data or {},
            cot_data=st.session_state.cot_data,
            cb_data=st.session_state.get("cb_data"),
            news_score=0
        )

    # Mostra dettaglio indicatori con tabelle
    display_data_input_section(
        fred_data=st.session_state.fred_data or {},
        yahoo_data=st.session_state.yahoo_data or {},
        gld_data=st.session_state.gld_data or {},
        fed_data=st.session_state.fed_data or {},
        cot_data=st.session_state.cot_data,
        scores=preview_scores or {}
    )

    # CLAUDE ANALYSIS
    st.markdown("---")
    st.markdown("## Analisi Claude AI")
    required = ["fred_data","yahoo_data","gld_data","fed_data","cot_data","news_data"]
    missing = [k for k in required if not st.session_state.get(k)]
    if missing:
        st.warning(f"Dati mancanti: {', '.join(missing)}")

    if st.button(chr(0x1F680) + " Lancia Analisi Claude", type="primary", disabled=bool(missing)):
        with st.spinner("Claude sta analizzando..."):
            scores = calculate_all_scores(
                fred_data=st.session_state.fred_data,
                yahoo_data=st.session_state.yahoo_data,
                gld_data=st.session_state.gld_data,
                fed_data=st.session_state.fed_data,
                cot_data=st.session_state.cot_data,
                cb_data=st.session_state.get("cb_data"),
                news_score=0
            )
            display_scores_table(scores)
            news_text = format_news_for_claude(st.session_state.news_data)
            gold_price = scores.get("GOLD_PRICE", {}).get("value_raw", 0)
            now_str = get_italy_now().strftime("%Y-%m-%d %H:%M")
            analysis = run_claude_analysis(scores, news_text, gold_price, now_str)

            if not analysis.get("error"):
                ns = analysis.get("news_score", 0)
                scores["NEWS"]["total_score"] = ns
                scores["NEWS"]["level_score"] = ns
                scores["NEWS"]["comment"] = analysis.get("news_comment", "")
                total = sum(s.get("total_score", 0) for k, s in scores.items()
                           if k not in ["GOLD_PRICE", "TOTAL"] and "total_score" in s)
                scores["TOTAL"] = {"total_score": total, "bias": _bias_label(total)}
                st.markdown("---")
                st.markdown("### Punteggi Finali")
                display_scores_table(scores)
                display_claude_analysis(analysis)
                save_analysis(st.session_state.user_id, scores, json.dumps(analysis), gold_price)
                st.success("Analisi salvata!")
            else:
                st.error(f"Errore Claude: {analysis.get('error')}")

if __name__ == "__main__":
    main()
