import streamlit as st
import json

def display_scores_table(scores):
    st.markdown("### Tabella Punteggi XAU/USD")
    gp = scores.get("GOLD_PRICE", {})
    if gp.get("value"):
        st.metric("Prezzo XAU/USD", gp["value"])
    keys = ["DFII10","DXY","T10YIE","GLD","COT","CB","FED_TREND","FED_EXPECT","VIX","SEASONALITY","NEWS"]
    for key in keys:
        s = scores.get(key, {})
        if "total_score" not in s:
            continue
        sv = s.get("total_score", 0)
        emoji = chr(0x1F7E2) if sv > 0 else (chr(0x1F534) if sv < 0 else chr(0x26AA))
        cols = st.columns([3, 2, 1.5, 1, 4])
        cols[0].markdown(f"**{s.get('name', key)}**")
        cols[1].markdown(str(s.get("value", "N/A")))
        cols[2].markdown(str(s.get("delta_4w", "N/A")))
        cols[3].markdown(f"{emoji} **{sv:+d}**")
        cols[4].markdown(f"_{s.get('comment', '')}_")
    st.markdown("---")
    total = scores.get("TOTAL", {})
    c1, c2 = st.columns(2)
    c1.metric("PUNTEGGIO TOTALE", f"{total.get('total_score', 0):+d} / +/-18")
    c2.metric("BIAS", total.get("bias", "N/A"))


def display_claude_analysis(analysis):
    if analysis.get("error"):
        st.error(f"Errore: {analysis['error']}")
        if analysis.get("raw"):
            with st.expander("Risposta grezza"):
                st.code(analysis["raw"])
        return
    st.markdown("### Analisi Claude AI")
    ns = analysis.get("news_score", 0)
    nc = analysis.get("news_comment", "")
    if ns > 0:
        st.success(f"News Score: **{ns:+d}** - {nc}")
    elif ns < 0:
        st.error(f"News Score: **{ns:+d}** - {nc}")
    else:
        st.info(f"News Score: **{ns:+d}** - {nc}")
    st.markdown("#### Commento Sintetico")
    st.markdown(analysis.get("summary", "N/A"))
    st.markdown("#### Check Coerenza Intermarket")
    st.markdown(analysis.get("coherence_check", "N/A"))
    st.markdown("#### Scenari 3 Settimane")
    scenarios = analysis.get("scenarios", {})
    c1, c2, c3 = st.columns(3)
    for col, key, title in [(c1,"bullish","Rialzista"),(c2,"neutral","Laterale"),(c3,"bearish","Ribassista")]:
        with col:
            st.markdown(f"**{title}**")
            sc = scenarios.get(key, {})
            st.markdown(f"_{sc.get('conditions', 'N/A')}_")
            st.markdown(f"**{sc.get('price_range', 'N/A')}**")
    st.markdown("#### Trigger Operativi")
    for t in analysis.get("triggers", []):
        st.markdown(f"- {t}")
    st.markdown(f"**Confidenza: {analysis.get('confidence', 'media')}**")


def display_calendar_sidebar(history):
    st.sidebar.markdown("### Storico Analisi")
    if not history:
        st.sidebar.info("Nessuna analisi precedente")
        return None
    selected = None
    for h in history[:20]:
        date = h.get("analysis_date", "N/A")
        score = h.get("total_score", 0)
        emoji = chr(0x1F7E2) if score > 3 else (chr(0x1F534) if score < -3 else chr(0x26AA))
        if st.sidebar.button(f"{emoji} {date} | {score:+d}", key=f"h_{date}"):
            selected = h
    return selected
