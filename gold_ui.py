import streamlit as st
import json
from datetime import datetime

# ============================================================================
# DESCRIZIONI INDICATORI
# ============================================================================

INDICATOR_INFO = {
    "DFII10": {
        "title": "Tasso Reale 10Y (DFII10)",
        "icon": "📉",
        "description": "Il tasso di interesse reale a 10 anni (Treasury Inflation-Protected Securities). "
            "Misura il rendimento reale dei titoli di stato USA al netto dell\u2019inflazione attesa. "
            "Tassi reali bassi o in calo sono BULLISH per l\u2019oro (costo opportunita basso), "
            "tassi reali alti o in salita sono BEARISH (conviene detenere bond).",
        "scoring": "Livello: <0.5% = +1 | 0.5-1.5% = 0 | >1.5% = -1 | "
            "Momentum (4 sett.): calo >0.15% = +1 | stabile = 0 | salita >0.15% = -1",
        "max_score": "+/-2",
        "source": "FRED (Federal Reserve Economic Data)",
    },
    "DXY": {
        "title": "DXY (US Dollar Index)",
        "icon": "💵",
        "description": "Indice del dollaro USA ponderato contro un paniere di 6 valute principali. "
            "Il dollaro e l\u2019oro hanno correlazione inversa: dollaro debole = oro forte. "
            "DXY sotto 98 e fortemente bullish per l\u2019oro, sopra 107 e fortemente bearish.",
        "scoring": "Livello: <98 = +2 | 98-101 = +1 | 101-105 = 0 | 105-107 = -1 | >107 = -2 | "
            "Momentum (4 sett.): calo >1.5pt = +1 | stabile = 0 | salita >1.5pt = -1",
        "max_score": "+/-3",
        "source": "Yahoo Finance (DX-Y.NYB)",
    },
    "T10YIE": {
        "title": "Breakeven Inflation 10Y (T10YIE)",
        "icon": "📊",
        "description": "Aspettative di inflazione a 10 anni ricavate dalla differenza tra rendimenti nominali e reali. "
            "L\u2019oro e un hedge contro l\u2019inflazione: aspettative di inflazione in salita sono BULLISH, "
            "in calo sono BEARISH.",
        "scoring": "Livello: <2.0% = -1 | 2.0-2.5% = 0 | >2.5% = +1 | "
            "Momentum (4 sett.): salita >0.10% = +1 | stabile = 0 | calo >0.10% = -1",
        "max_score": "+/-2",
        "source": "FRED (Federal Reserve Economic Data)",
    },
    "FED_SPREAD": {
        "title": "Fed Expectations (Spread FFR - Treasury 2Y)",
        "icon": "🏦",
        "description": "Differenza tra il tasso Fed Funds effettivo (DFF) e il rendimento del Treasury a 2 anni (DGS2). "
            "Se il 2Y e molto sotto il FFR, il mercato prezza tagli imminenti (BULLISH oro). "
            "Se il 2Y e sopra il FFR, il mercato prezza rialzi (BEARISH oro).",
        "scoring": "Spread: <-0.25% = -1 (rialzi) | -0.25/+0.50% = 0 | >+0.50% = +1 (tagli) | "
            "Momentum (4 sett.): spread in aumento >0.15% = +1 | stabile = 0 | in calo >0.15% = -1",
        "max_score": "+/-2",
        "source": "FRED (DFF + DGS2)",
    },
    "GLD": {
        "title": "GLD Holdings (SPDR Gold Shares)",
        "icon": "🥇",
        "description": "Tonnellate di oro fisico detenute dall\u2019ETF GLD, il piu grande al mondo. "
            "Afflussi = domanda istituzionale in crescita (BULLISH). "
            "Deflussi = domanda in calo (BEARISH). Solo il momentum conta, non il livello assoluto.",
        "scoring": "Solo momentum: variazione >+10t in 4 sett. = +1 | stabile = 0 | <-10t = -1",
        "max_score": "+/-1",
        "source": "SPDR Gold Shares (CSV ufficiale)",
    },
    "VIX": {
        "title": "VIX (CBOE Volatility Index)",
        "icon": "⚡",
        "description": "Indice di volatilita implicita dell\u2019S&P 500, noto come \u201Cindice della paura\u201D. "
            "VIX alto = risk-off = investitori cercano rifugio nell\u2019oro (BULLISH). "
            "VIX basso = risk-on = meno interesse per l\u2019oro come safe haven (BEARISH).",
        "scoring": "Livello: <15 = -1 | 15-25 = 0 | >25 = +1 | "
            "Momentum (1 sett.): spike >+5pt = +1 | stabile = 0 | calo >5pt = -1",
        "max_score": "+/-2",
        "source": "Yahoo Finance (^VIX)",
    },
    "COT": {
        "title": "COT Oro Non-Commercial (Speculative Positioning)",
        "icon": "📋",
        "description": "Posizionamento netto dei trader non-commerciali (speculativi) sui futures dell\u2019oro. "
            "Il COT Index (0-100%) indica dove si trova il posizionamento rispetto al range delle ultime 52 settimane. "
            "Index alto (>75%) = molto long, BULLISH ma attenzione a eccessi. Index basso (<25%) = BEARISH.",
        "scoring": "Posizionamento: Index >75% = +1 | 25-75% = 0 | <25% = -1 | "
            "Momentum: net long sopra MA 4w e in crescita = +1 | intorno = 0 | sotto e in calo = -1",
        "max_score": "+/-2",
        "source": "CFTC (Commitment of Traders Report, contratto 088691)",
    },
    "FED_TREND": {
        "title": "Fed Trend (Ciclo FOMC)",
        "icon": "🏛️",
        "description": "Direzione della politica monetaria della Federal Reserve basata sulle ultime decisioni. "
            "Ciclo di taglio/easing = BULLISH per l\u2019oro (tassi piu bassi). "
            "Ciclo di rialzo/tightening = BEARISH (tassi piu alti).",
        "scoring": "Easing/Cutting/Pausa post-taglio = +1 | Holding = 0 | Tightening/Hiking/Pausa post-rialzo = -1",
        "max_score": "+/-1",
        "source": "Investing.com (storico decisioni FOMC)",
    },
    "SEASONALITY": {
        "title": "Stagionalita Oro",
        "icon": "📅",
        "description": "Pattern stagionali storici dell\u2019oro. Mesi forti: Gennaio, Febbraio (Capodanno lunare), "
            "Settembre (Diwali), Dicembre (ribilanciamento). Mesi deboli: Marzo-Giugno.",
        "scoring": "Mese favorevole = +1 | Neutro = 0 | Sfavorevole = -1",
        "max_score": "+/-1",
        "source": "Pattern storico hardcoded",
    },
    "NEWS": {
        "title": "News / Geopolitica",
        "icon": "📰",
        "description": "Punteggio assegnato da Claude AI sulla base delle notizie recenti raccolte. "
            "Tensioni geopolitiche, crisi bancarie, sanzioni = BULLISH (flight to safety). "
            "Distensione, risk-on generalizzato = BEARISH.",
        "scoring": "Claude assegna: +1 (bullish news) | 0 (neutro) | -1 (bearish news)",
        "max_score": "+/-1",
        "source": "Claude AI + DuckDuckGo News",
    },
}


def _make_history_table(values, n_weeks=8, value_label="Valore", fmt=".2f"):
    """Crea una tabella con gli ultimi N dati settimanali dalla serie storica."""
    if not values or len(values) < 2:
        st.caption("Dati storici insufficienti")
        return

    # Prendi un dato per settimana circa (ogni 5 giorni di trading)
    step = max(1, len(values) // n_weeks) if len(values) > n_weeks else 1
    selected = values[::step][:n_weeks]

    rows = []
    for i, v in enumerate(selected):
        val = v["value"]
        delta = ""
        if i < len(selected) - 1:
            prev = selected[i + 1]["value"]
            d = val - prev
            delta = f"{d:+{fmt}}"
        rows.append({"Data": v["date"], value_label: f"{val:{fmt}}", "Variazione": delta})

    import pandas as pd
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _show_indicator_card(key, info, score_data, hist_values=None, extra_content=None,
                          value_label="Valore", fmt=".2f", n_weeks=8):
    """Mostra card completa per un indicatore."""
    with st.expander(f"{info['icon']} **{info['title']}** — Score: {score_data.get('total_score', 0):+d}/{info['max_score']}", expanded=False):
        # Descrizione
        st.markdown(f"**Cos\u2019e:** {info['description']}")
        st.markdown(f"**Scoring:** `{info['scoring']}`")
        st.markdown(f"**Fonte:** {info['source']}")
        st.markdown("---")

        # Valore attuale e score
        c1, c2, c3, c4 = st.columns([2, 2, 1, 3])
        c1.metric("Valore attuale", score_data.get("value", "N/A"))
        c2.metric("Delta 4 sett.", score_data.get("delta_4w", "N/A"))
        sv = score_data.get("total_score", 0)
        emoji = "\U0001F7E2" if sv > 0 else ("\U0001F534" if sv < 0 else "\u26AA")
        c3.metric("Score", f"{emoji} {sv:+d}")
        c4.markdown(f"**Dettaglio:** {score_data.get('comment', '')}")

        # Contenuto extra (es. tabella spread, meeting Fed)
        if extra_content:
            st.markdown("---")
            extra_content()

        # Tabella storica
        if hist_values and len(hist_values) > 1:
            st.markdown("---")
            st.markdown(f"**Serie storica (ultimi {n_weeks} punti):**")
            _make_history_table(hist_values, n_weeks=n_weeks, value_label=value_label, fmt=fmt)


# ============================================================================
# MAIN DISPLAY FUNCTIONS
# ============================================================================

def display_data_input_section(fred_data, yahoo_data, gld_data, fed_data, cot_data, scores):
    """Mostra la sezione completa dati di input con tabelle dettagliate."""
    st.markdown("## 📥 Dati di Input — Dettaglio Indicatori")

    if not scores:
        st.info("Clicca \u201CAggiorna TUTTO\u201D per caricare i dati.")
        return

    # Gold price in evidenza
    gp = scores.get("GOLD_PRICE", {})
    if gp.get("value_raw"):
        st.metric("💰 Prezzo XAU/USD attuale", gp["value"])

    st.markdown("---")

    # 1. DFII10
    if fred_data and fred_data.get("DFII10", {}).get("values"):
        _show_indicator_card("DFII10", INDICATOR_INFO["DFII10"], scores.get("DFII10", {}),
            hist_values=fred_data["DFII10"]["values"], value_label="Tasso Reale %", fmt=".4f")

    # 2. DXY
    if yahoo_data and yahoo_data.get("DXY", {}).get("values"):
        _show_indicator_card("DXY", INDICATOR_INFO["DXY"], scores.get("DXY", {}),
            hist_values=yahoo_data["DXY"]["values"], value_label="DXY", fmt=".2f")

    # 3. T10YIE
    if fred_data and fred_data.get("T10YIE", {}).get("values"):
        _show_indicator_card("T10YIE", INDICATOR_INFO["T10YIE"], scores.get("T10YIE", {}),
            hist_values=fred_data["T10YIE"]["values"], value_label="Breakeven %", fmt=".4f")

    # 4. Fed Expectations (spread FFR - 2Y)
    if fred_data and fred_data.get("DFF", {}).get("values") and fred_data.get("DGS2", {}).get("values"):
        def fed_spread_extra():
            st.markdown("**Componenti dello spread:**")
            dff = fred_data["DFF"]
            dgs2 = fred_data["DGS2"]
            c1, c2, c3 = st.columns(3)
            c1.metric("FFR (Fed Funds Rate)", f"{dff['latest_value']:.4f}%",
                      help="Tasso effettivo dei Fed Funds")
            c2.metric("Treasury 2Y", f"{dgs2['latest_value']:.4f}%",
                      help="Rendimento Treasury a 2 anni")
            spread = dff["latest_value"] - dgs2["latest_value"]
            c3.metric("Spread (FFR - 2Y)", f"{spread:+.4f}%",
                      help="Positivo = mercato prezza tagli, Negativo = prezza rialzi")

            # Costruisci serie spread storica
            spread_hist = []
            dff_dict = {v["date"]: v["value"] for v in dff.get("values", [])}
            for v in dgs2.get("values", []):
                if v["date"] in dff_dict:
                    sp = dff_dict[v["date"]] - v["value"]
                    spread_hist.append({"date": v["date"], "value": round(sp, 4)})
            if spread_hist:
                st.markdown("**Serie storica dello spread FFR - 2Y:**")
                _make_history_table(spread_hist, n_weeks=8, value_label="Spread %", fmt=".4f")

        _show_indicator_card("FED_SPREAD", INDICATOR_INFO["FED_SPREAD"], scores.get("FED_EXPECT", {}),
            extra_content=fed_spread_extra)

    # 5. GLD Holdings
    if gld_data and gld_data.get("values"):
        _show_indicator_card("GLD", INDICATOR_INFO["GLD"], scores.get("GLD", {}),
            hist_values=gld_data["values"], value_label="Tonnellate", fmt=".2f")

    # 6. VIX
    if yahoo_data and yahoo_data.get("VIX", {}).get("values"):
        _show_indicator_card("VIX", INDICATOR_INFO["VIX"], scores.get("VIX", {}),
            hist_values=yahoo_data["VIX"]["values"], value_label="VIX", fmt=".2f")

    # 7. COT
    if cot_data and not cot_data.get("error"):
        def cot_extra():
            st.markdown("**Dettaglio posizionamento:**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("COT Index", f"{cot_data.get('cot_index', 0):.1f}%",
                      help="0% = minimo 52 sett., 100% = massimo 52 sett.")
            c2.metric("Net Long attuale", f"{cot_data.get('net_long', 0):,}",
                      help="Contratti long - short dei non-commercial")
            c3.metric("Media 4 sett.", f"{cot_data.get('ma_4w', 0):,.0f}")
            c4.metric("Delta vs MA", f"{cot_data.get('delta_vs_ma', 0):+,.0f}")
            st.markdown(f"**Range 52 sett.:** Min {cot_data.get('min_52w', 0):,} — Max {cot_data.get('max_52w', 0):,}")
            if cot_data.get("cot_index", 50) < 5:
                st.warning("⚠️ COT Index molto basso: posizionamento al minimo storico 52 settimane. Possibile segnale contrarian bullish.")
            elif cot_data.get("cot_index", 50) > 95:
                st.warning("⚠️ COT Index molto alto: posizionamento al massimo storico. Possibile segnale contrarian bearish.")

        _show_indicator_card("COT", INDICATOR_INFO["COT"], scores.get("COT", {}),
            extra_content=cot_extra)

    # 8. Fed Trend
    if fed_data and not fed_data.get("error"):
        def fed_extra():
            st.markdown("**Ultimi meeting FOMC:**")
            for m in fed_data.get("meetings", []):
                decision_emoji = "🔴 ▼" if m["decision"] == "cut" else ("🟢 ▲" if m["decision"] == "hike" else "➖")
                st.markdown(f"- **{m['date_formatted']}**: {decision_emoji} {m['change']} — Tasso: {m['rate']}")

        _show_indicator_card("FED_TREND", INDICATOR_INFO["FED_TREND"], scores.get("FED_TREND", {}),
            extra_content=fed_extra)

    # 9. Stagionalita
    _show_indicator_card("SEASONALITY", INDICATOR_INFO["SEASONALITY"], scores.get("SEASONALITY", {}))

    # 10. News
    _show_indicator_card("NEWS", INDICATOR_INFO["NEWS"], scores.get("NEWS", {}))


def display_scores_table(scores):
    """Mostra la tabella riassuntiva dei punteggi."""
    st.markdown("### 📊 Tabella Riassuntiva Punteggi")

    gp = scores.get("GOLD_PRICE", {})
    if gp.get("value"):
        st.metric("💰 Prezzo XAU/USD", gp["value"])

    keys = ["DFII10", "DXY", "T10YIE", "GLD", "COT", "CB", "FED_TREND", "FED_EXPECT", "VIX", "SEASONALITY", "NEWS"]

    import pandas as pd
    rows = []
    for key in keys:
        s = scores.get(key, {})
        if "total_score" not in s:
            continue
        sv = s.get("total_score", 0)
        emoji = chr(0x1F7E2) if sv > 0 else (chr(0x1F534) if sv < 0 else chr(0x26AA))
        rows.append({
            "Indicatore": s.get("name", key),
            "Valore": str(s.get("value", "N/A")),
            "Delta 4w": str(s.get("delta_4w", "N/A")),
            "Score": f"{emoji} {sv:+d}",
            "Commento": s.get("comment", ""),
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    total = scores.get("TOTAL", {})
    c1, c2 = st.columns(2)
    c1.metric("PUNTEGGIO TOTALE", f"{total.get('total_score', 0):+d} / +/-18")
    c2.metric("BIAS", total.get("bias", "N/A"))


def display_claude_analysis(analysis):
    """Mostra analisi Claude."""
    if analysis.get("error"):
        st.error(f"Errore: {analysis['error']}")
        if analysis.get("raw"):
            with st.expander("Risposta grezza"):
                st.code(analysis["raw"])
        return

    st.markdown("### 🤖 Analisi Claude AI")

    ns = analysis.get("news_score", 0)
    nc = analysis.get("news_comment", "")
    if ns > 0:
        st.success(f"📰 News Score: **{ns:+d}** — {nc}")
    elif ns < 0:
        st.error(f"📰 News Score: **{ns:+d}** — {nc}")
    else:
        st.info(f"📰 News Score: **{ns:+d}** — {nc}")

    st.markdown("#### 📝 Commento Sintetico")
    st.markdown(analysis.get("summary", "N/A"))

    st.markdown("#### 🔄 Check Coerenza Intermarket")
    st.markdown(analysis.get("coherence_check", "N/A"))

    st.markdown("#### 🎯 Scenari 3 Settimane")
    scenarios = analysis.get("scenarios", {})
    c1, c2, c3 = st.columns(3)
    for col, key, title, emoji in [(c1,"bullish","Rialzista","🟢"),(c2,"neutral","Laterale","⚪"),(c3,"bearish","Ribassista","🔴")]:
        with col:
            st.markdown(f"**{emoji} {title}**")
            sc = scenarios.get(key, {})
            st.markdown(f"_{sc.get('conditions', 'N/A')}_")
            st.markdown(f"**{sc.get('price_range', 'N/A')}**")

    st.markdown("#### ⚡ Trigger Operativi")
    for t in analysis.get("triggers", []):
        st.markdown(f"- {t}")

    st.markdown(f"**Confidenza: {analysis.get('confidence', 'media')}**")


def display_calendar_sidebar(history):
    """Mostra calendario nella sidebar."""
    st.sidebar.markdown("### 📅 Storico Analisi")
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
