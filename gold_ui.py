"""
Gold XAU/USD Macro Analyzer - UI Module
Visualizzazione indicatori, punteggi e storico analisi.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

# ============================================================================
# DESCRIZIONI INDICATORI
# ============================================================================

INDICATOR_INFO = {
    "DFII10": {
        "title": "Tasso Reale 10Y (DFII10)",
        "icon": "\U0001F4C9",
        "what": "Il tasso di interesse reale a 10 anni (TIPS). Misura il rendimento reale dei titoli di stato USA al netto dell\u2019inflazione attesa.",
        "why": "Tassi reali bassi o in calo sono BULLISH per l\u2019oro (basso costo opportunit\u00E0 nel detenere oro). Tassi reali alti o in salita sono BEARISH (conviene detenere bond).",
        "scoring": "Livello: <0.5% = +1 | 0.5-1.5% = 0 | >1.5% = -1 \u2014 Momentum 4w: calo >0.15% = +1 | stabile = 0 | salita >0.15% = -1",
        "max": "\u00B12",
    },
    "DXY": {
        "title": "DXY (US Dollar Index)",
        "icon": "\U0001F4B5",
        "what": "Indice del dollaro USA ponderato contro 6 valute principali (EUR, JPY, GBP, CAD, SEK, CHF).",
        "why": "Correlazione inversa con l\u2019oro. Dollaro debole = oro forte. DXY sotto 98 \u00E8 fortemente bullish per l\u2019oro.",
        "scoring": "Livello: <98 = +2 | 98-101 = +1 | 101-105 = 0 | 105-107 = -1 | >107 = -2 \u2014 Momentum 4w: calo >1.5pt = +1 | stabile = 0 | salita >1.5pt = -1",
        "max": "\u00B13",
    },
    "T10YIE": {
        "title": "Breakeven Inflation 10Y (T10YIE)",
        "icon": "\U0001F4CA",
        "what": "Aspettative di inflazione a 10 anni (differenza tra rendimenti nominali e reali).",
        "why": "L\u2019oro \u00E8 un hedge contro l\u2019inflazione. Aspettative in salita = BULLISH, in calo = BEARISH.",
        "scoring": "Livello: <2.0% = -1 | 2.0-2.5% = 0 | >2.5% = +1 \u2014 Momentum 4w: salita >0.10% = +1 | stabile = 0 | calo >0.10% = -1",
        "max": "\u00B12",
    },
    "FED_SPREAD": {
        "title": "Fed Expectations (Spread FFR - Treasury 2Y)",
        "icon": "\U0001F3E6",
        "what": "Differenza tra il tasso Fed Funds effettivo (DFF) e il rendimento del Treasury 2Y (DGS2).",
        "why": "Se il 2Y \u00E8 molto sotto il FFR, il mercato prezza tagli (BULLISH oro). Se sopra, prezza rialzi (BEARISH).",
        "scoring": "Spread: >+0.50% = +1 (tagli) | -0.25/+0.50% = 0 | <-0.25% = -1 (rialzi) \u2014 Momentum 4w: spread in aumento >0.15% = +1 | stabile = 0 | in calo = -1",
        "max": "\u00B12",
    },
    "GLD": {
        "title": "GLD Holdings (SPDR Gold Shares)",
        "icon": "\U0001F947",
        "what": "Tonnellate di oro fisico detenute dall\u2019ETF SPDR Gold Shares, il pi\u00F9 grande al mondo.",
        "why": "Afflussi = domanda istituzionale in crescita (BULLISH). Deflussi = domanda in calo (BEARISH). Conta solo il momentum.",
        "scoring": "Solo momentum: variazione >+10t in 4 sett. = +1 | stabile = 0 | <-10t = -1",
        "max": "\u00B11",
    },
    "VIX": {
        "title": "VIX (CBOE Volatility Index)",
        "icon": "\u26A1",
        "what": "Indice di volatilit\u00E0 implicita dell\u2019S&P 500, noto come \u201Cindice della paura\u201D.",
        "why": "VIX alto = risk-off = investitori cercano rifugio nell\u2019oro (BULLISH). VIX basso = risk-on (BEARISH).",
        "scoring": "Livello: <15 = -1 | 15-20 = 0 | >20 = +1 \u2014 Momentum 1w: spike >+5pt = +1 | stabile = 0 | calo >5pt = -1",
        "max": "\u00B12",
    },
    "COT": {
        "title": "COT Non-Commercial (Speculative Positioning)",
        "icon": "\U0001F4CB",
        "what": "Posizionamento netto dei trader speculativi sui futures oro e USD (CFTC, report settimanale).",
        "why": "COT Index alto (>75%) = molto long, BULLISH ma attenzione a eccessi. Index basso (<25%) = BEARISH. Confronto Gold vs USD per coerenza.",
        "scoring": "Posizionamento: Index >75% = +1 | 25-75% = 0 | <25% = -1 \u2014 Momentum: net long sopra MA 4w = +1 | intorno = 0 | sotto = -1",
        "max": "\u00B12",
    },
    "FED_TREND": {
        "title": "Fed Trend (Ciclo FOMC)",
        "icon": "\U0001F3DB\uFE0F",
        "what": "Direzione della politica monetaria della Federal Reserve basata sulle ultime decisioni FOMC.",
        "why": "Ciclo di taglio/easing = BULLISH (tassi pi\u00F9 bassi, costo opportunit\u00E0 basso). Ciclo di rialzo = BEARISH.",
        "scoring": "Easing/Pausa post-taglio = +1 | Holding = 0 | Tightening/Pausa post-rialzo = -1",
        "max": "\u00B11",
    },
    "SEASONALITY": {
        "title": "Stagionalit\u00E0 Oro",
        "icon": "\U0001F4C5",
        "what": "Pattern stagionali storici dell\u2019oro. Mesi forti: Gen, Feb (Capodanno lunare), Set (Diwali), Dic. Mesi deboli: Mar-Giu.",
        "why": "La domanda fisica di oro ha pattern ricorrenti legati a festivit\u00E0 e ribilanciamenti di portafoglio.",
        "scoring": "Mese favorevole = +1 | Neutro = 0 | Sfavorevole = -1",
        "max": "\u00B11",
    },
}


# ============================================================================
# INDICATOR CARDS (sempre aperte, solo dati, no punteggio)
# ============================================================================

def display_indicator_cards(fred_data, yahoo_data, gld_data, fed_data, cot_data):
    """Mostra tutte le schede indicatori sempre aperte, con descrizione e valore."""

    if not fred_data and not yahoo_data:
        st.info("Carica i dati per visualizzare gli indicatori.")
        return

    # 1. DFII10
    _card_header("DFII10")
    if fred_data.get("DFII10") and not fred_data["DFII10"].get("error"):
        d = fred_data["DFII10"]
        c1, c2 = st.columns(2)
        c1.metric("Valore attuale", f"{d['latest_value']:.4f}%", help="Tasso reale 10Y TIPS")
        c2.metric("Data", d["latest_date"])
        if d.get("values") and len(d["values"]) >= 2:
            _show_mini_history(d["values"], "Tasso Reale %", ".4f")
    else:
        st.caption("\U0001F534 Dati non disponibili")
    st.markdown("---")

    # 2. T10YIE
    _card_header("T10YIE")
    if fred_data.get("T10YIE") and not fred_data["T10YIE"].get("error"):
        d = fred_data["T10YIE"]
        c1, c2 = st.columns(2)
        c1.metric("Valore attuale", f"{d['latest_value']:.4f}%", help="Breakeven Inflation 10Y")
        c2.metric("Data", d["latest_date"])
        if d.get("values") and len(d["values"]) >= 2:
            _show_mini_history(d["values"], "Breakeven %", ".4f")
    else:
        st.caption("\U0001F534 Dati non disponibili")
    st.markdown("---")

    # 3. DXY
    _card_header("DXY")
    if yahoo_data.get("DXY") and not yahoo_data["DXY"].get("error"):
        d = yahoo_data["DXY"]
        c1, c2 = st.columns(2)
        c1.metric("Valore attuale", f"{d['latest_value']:.2f}", help="US Dollar Index")
        c2.metric("Data", d["latest_date"])
        if d.get("values") and len(d["values"]) >= 2:
            _show_mini_history(d["values"], "DXY", ".2f")
    else:
        st.caption("\U0001F534 Dati non disponibili")
    st.markdown("---")

    # 4. Fed Expectations (spread)
    _card_header("FED_SPREAD")
    if fred_data.get("DFF") and fred_data.get("DGS2"):
        dff = fred_data["DFF"]
        dgs2 = fred_data["DGS2"]
        if not dff.get("error") and not dgs2.get("error"):
            spread = dff["latest_value"] - dgs2["latest_value"]
            c1, c2, c3 = st.columns(3)
            c1.metric("FFR (Fed Funds)", f"{dff['latest_value']:.4f}%")
            c2.metric("Treasury 2Y", f"{dgs2['latest_value']:.4f}%")
            c3.metric("Spread (FFR - 2Y)", f"{spread:+.4f}%",
                      help="Positivo = mercato prezza tagli, Negativo = prezza rialzi")
            # Spread history
            dff_dict = {v["date"]: v["value"] for v in dff.get("values", [])}
            spread_hist = []
            for v in dgs2.get("values", []):
                if v["date"] in dff_dict:
                    spread_hist.append({"date": v["date"], "value": round(dff_dict[v["date"]] - v["value"], 4)})
            if len(spread_hist) >= 2:
                _show_mini_history(spread_hist, "Spread %", ".4f")
        else:
            st.caption("\U0001F534 Dati non disponibili")
    else:
        st.caption("\U0001F534 Dati non disponibili")
    st.markdown("---")

    # 5. GLD Holdings
    _card_header("GLD")
    if gld_data and not gld_data.get("error"):
        c1, c2 = st.columns(2)
        c1.metric("Tonnellate attuali", f"{gld_data.get('latest_tonnes', 0):.2f}t")
        c2.metric("Data", gld_data.get("latest_date", "N/A"))
        if gld_data.get("values") and len(gld_data["values"]) >= 2:
            _show_mini_history(gld_data["values"], "Tonnellate", ".2f")
    else:
        st.caption("\U0001F534 Dati non disponibili")
    st.markdown("---")

    # 6. VIX
    _card_header("VIX")
    if yahoo_data.get("VIX") and not yahoo_data["VIX"].get("error"):
        d = yahoo_data["VIX"]
        c1, c2 = st.columns(2)
        c1.metric("Valore attuale", f"{d['latest_value']:.2f}", help="CBOE Volatility Index")
        c2.metric("Data", d["latest_date"])
        if d.get("values") and len(d["values"]) >= 2:
            _show_mini_history(d["values"], "VIX", ".2f")
    else:
        st.caption("\U0001F534 Dati non disponibili")
    st.markdown("---")

    # 7. COT
    _card_header("COT")
    if cot_data and not cot_data.get("error"):
        _display_cot_table(cot_data)
    else:
        st.caption("\U0001F534 Dati non disponibili")
    st.markdown("---")

    # 8. Fed Trend
    _card_header("FED_TREND")
    if fed_data and not fed_data.get("error"):
        c1, c2 = st.columns(2)
        c1.metric("Tasso attuale", fed_data.get("current_rate", "N/A"))
        c2.metric("Trend", f"{fed_data.get('trend_emoji', '')} {fed_data.get('trend_label', 'N/A')}")
        st.markdown("**Ultimi meeting FOMC:**")
        for m in fed_data.get("meetings", [])[:5]:
            decision_emoji = "\U0001F534" if m.get("decision") == "cut" else ("\U0001F7E2" if m.get("decision") == "hike" else "\u2796")
            st.markdown(f"- **{m['date_formatted']}**: {decision_emoji} {m['change']} \u2014 Tasso: {m['rate']}")
    else:
        st.caption("\U0001F534 Dati non disponibili")
    st.markdown("---")

    # 9. Stagionalita
    _card_header("SEASONALITY")
    now = datetime.now()
    month_names = {1:"Gennaio",2:"Febbraio",3:"Marzo",4:"Aprile",5:"Maggio",6:"Giugno",
                   7:"Luglio",8:"Agosto",9:"Settembre",10:"Ottobre",11:"Novembre",12:"Dicembre"}
    st.markdown(f"**Mese corrente:** {month_names.get(now.month, '?')} \u2014 pattern storico basato su domanda fisica e ribilanciamenti")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _card_header(key):
    """Header di una card indicatore con descrizione."""
    info = INDICATOR_INFO.get(key, {})
    st.markdown(f"### {info.get('icon', '')} {info.get('title', key)}")
    st.markdown(f"**Cos\u2019\u00E8:** {info.get('what', '')}")
    st.markdown(f"**Perch\u00E9 conta:** {info.get('why', '')}")
    st.caption(f"Scoring: {info.get('scoring', '')} | Max: {info.get('max', '')}")


def _show_mini_history(values, label, fmt, n=6):
    """Mostra mini-tabella con ultimi N valori e variazione."""
    if not values or len(values) < 2:
        return
    step = max(1, len(values) // n) if len(values) > n else 1
    selected = values[::step][:n]
    rows = []
    for i, v in enumerate(selected):
        delta = ""
        if i < len(selected) - 1:
            d = v["value"] - selected[i + 1]["value"]
            delta = f"{d:+{fmt}}"
        rows.append({"Data": v["date"], label: f"{v['value']:{fmt}}", "\u0394": delta})
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True, height=min(250, 35 * (len(rows) + 1)))


def _net_emoji(val):
    return "\U0001F7E2" if val > 0 else ("\U0001F534" if val < 0 else "\u26AA")

def _index_emoji(val):
    if val >= 75: return "\U0001F535"
    if val >= 50: return "\U0001F7E2"
    if val >= 25: return "\u26AA"
    return "\U0001F534"

def _score_emoji(val):
    if val > 0: return "\U0001F7E2"
    if val < 0: return "\U0001F534"
    return "\u26AA"


def _display_cot_table(cot_data):
    """Tabella COT stile forex con Gold e USD."""
    st.markdown("**COT Non-Commercial (Speculatori)**")
    assets = []
    for key in ["GOLD", "USD"]:
        d = cot_data.get(key, {})
        if d and not d.get("error"):
            assets.append({"key": key, "name": "Oro" if key == "GOLD" else "USD Index",
                          "icon": "\U0001F947" if key == "GOLD" else "\U0001F4B5", "data": d})

    if not assets:
        if cot_data.get("cot_index") is not None:
            assets.append({"key": "GOLD", "name": "Oro", "icon": "\U0001F947", "data": cot_data})

    if not assets:
        st.warning("Dati COT non disponibili")
        return

    rows = []
    for a in assets:
        d = a["data"]
        net = d.get("net_long", 0)
        ci = d.get("cot_index", 50)
        d1w = d.get("delta_1w", 0)
        ts = d.get("total_score", d.get("pos_score", 0) + d.get("momentum_score", 0))
        interp = d.get("interpretation", "N/A")
        rows.append({
            "Asset": f"{a['icon']} {a['name']}",
            "Net Position": f"{_net_emoji(net)} {net:+,}",
            "COT Index": f"{_index_emoji(ci)} {ci:.0f}%",
            "Delta Sett.": f"{_net_emoji(d1w)} {d1w:+,}",
            "Interpretazione": interp,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    report_date = cot_data.get("latest_date", "")
    if not report_date:
        for key in ["GOLD", "USD"]:
            d = cot_data.get(key, {})
            if d.get("latest_date"):
                report_date = d["latest_date"]
                break
    if report_date:
        st.caption(f"Dati report: {report_date}")

    # Dettaglio per asset
    for a in assets:
        d = a["data"]
        with st.expander(f"Dettaglio {a['name']}", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Net Long", f"{d.get('net_long', 0):+,}")
            c2.metric("Media 4 sett.", f"{d.get('ma_4w', 0):,.0f}")
            c3.metric("Delta vs MA", f"{d.get('delta_vs_ma', 0):+,.0f}")
            c4.metric("COT Index", f"{d.get('cot_index', 50):.1f}%")
            st.markdown(f"**Range 52 sett.:** Min {d.get('min_52w', 0):,} | Max {d.get('max_52w', 0):,}")
            ci = d.get("cot_index", 50)
            if ci < 5:
                st.warning("Posizionamento al minimo 52 sett. Possibile segnale contrarian bullish.")
            elif ci > 95:
                st.warning("Posizionamento al massimo 52 sett. Possibile segnale contrarian bearish.")

    # Convergenza Gold vs USD
    gold_d = cot_data.get("GOLD", {})
    usd_d = cot_data.get("USD", {})
    if gold_d and usd_d and not gold_d.get("error") and not usd_d.get("error"):
        gold_mom = gold_d.get("momentum_score", 0)
        usd_mom = usd_d.get("momentum_score", 0)
        if gold_mom > 0 and usd_mom < 0:
            st.success("\u2705 Convergenza: speculatori comprano oro e vendono dollaro. Segnale coerente BULLISH.")
        elif gold_mom < 0 and usd_mom > 0:
            st.error("\u274C Convergenza: speculatori vendono oro e comprano dollaro. Segnale coerente BEARISH.")
        elif gold_mom > 0 and usd_mom > 0:
            st.info("\u2194\uFE0F Divergenza: comprano sia oro che dollaro. Possibile flight to safety.")
        elif gold_mom < 0 and usd_mom < 0:
            st.info("\u2194\uFE0F Divergenza: vendono sia oro che dollaro. Risk-on su altri asset.")


# ============================================================================
# TABELLA RIEPILOGO PUNTEGGI
# ============================================================================

def display_scores_table(scores):
    """Tabella riassuntiva punteggi finale con legenda."""
    # Gold price in evidenza
    gp = scores.get("GOLD_PRICE", {})
    if gp.get("value"):
        st.metric("💰 Prezzo XAU/USD", gp["value"])

    keys = ["DFII10", "T10YIE", "DXY", "FED_EXPECT", "GLD", "VIX", "COT", "FED_TREND", "SEASONALITY"]
    rows = []
    for key in keys:
        s = scores.get(key, {})
        if "total_score" not in s:
            continue
        sv = s.get("total_score", 0)
        emoji = "🟢" if sv > 0 else ("🔴" if sv < 0 else "⚪")
        lv = s.get("level_score", 0)
        mv = s.get("momentum_score", 0)
        rows.append({
            "Indicatore": s.get("name", key),
            "Valore": str(s.get("value", "N/A")),
            "Livello": f"{lv:+d}",
            "Momentum": f"{mv:+d}",
            "Score Totale": f"{emoji} {sv:+d}",
            "Commento": s.get("comment", ""),
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Totale + Bias con emoji
    total = scores.get("TOTAL", {})
    ts = total.get("total_score", 0)
    bias = total.get("bias", "N/A")
    if ts >= 9:
        bias_emoji = "🟢🟢"
    elif ts >= 4:
        bias_emoji = "🟢"
    elif ts >= -3:
        bias_emoji = "🟡"
    elif ts >= -8:
        bias_emoji = "🔴"
    else:
        bias_emoji = "🔴🔴"

    c1, c2, c3 = st.columns(3)
    c1.metric("PUNTEGGIO TOTALE", f"{ts:+d}")
    c2.metric("BIAS", f"{bias_emoji} {bias}")
    # Barra visuale
    pct = max(0.01, min(0.99, (ts + 16) / 32))
    c3.markdown("**Forza segnale**")
    c3.progress(pct)

    # Legenda
    st.markdown("---")
    st.markdown(
        "**Legenda:** "
        "🟢🟢 = Forte BULLISH (+9 a +16) | "
        "🟢 = Moderato BULLISH (+4 a +8) | "
        "🟡 = Neutro / Range (-3 a +3) | "
        "🔴 = Moderato BEARISH (-8 a -4) | "
        "🔴🔴 = Forte BEARISH (-16 a -9)"
    )


# ============================================================================
# SIDEBAR CALENDARIO
# ============================================================================

def display_calendar_sidebar(history):
    """Calendario sidebar stile forex con HTML."""
    import calendar as cal_module
    from datetime import date as date_type

    st.sidebar.markdown("### 📁 Storico Analisi")

    if not history:
        st.sidebar.info("Nessuna analisi salvata")
        return None

    # Mappa date analisi -> score
    analysis_map = {}
    for h in history:
        d = h.get("analysis_date", "")
        if d:
            analysis_map[d] = h

    today = date_type.today()
    if "cal_year" not in st.session_state:
        st.session_state.cal_year = today.year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = today.month

    year = st.session_state.cal_year
    month = st.session_state.cal_month

    month_names = {1:"Gen",2:"Feb",3:"Mar",4:"Apr",5:"Mag",6:"Giu",
                   7:"Lug",8:"Ago",9:"Set",10:"Ott",11:"Nov",12:"Dic"}

    # Navigazione
    nav1, nav2, nav3 = st.sidebar.columns([1, 3, 1])
    if nav1.button("◀", key="cal_prev"):
        if month == 1:
            st.session_state.cal_month = 12
            st.session_state.cal_year = year - 1
        else:
            st.session_state.cal_month = month - 1
        st.rerun()
    nav2.markdown(f"<p style='text-align:center;font-weight:bold;margin:0'>{month_names[month]} {year}</p>", unsafe_allow_html=True)
    if nav3.button("▶", key="cal_next"):
        if month == 12:
            st.session_state.cal_month = 1
            st.session_state.cal_year = year + 1
        else:
            st.session_state.cal_month = month + 1
        st.rerun()

    # Build HTML calendar
    c = cal_module.Calendar(firstweekday=0)
    weeks = c.monthdayscalendar(year, month)

    html = '<table style="width:100%;border-collapse:collapse;text-align:center;font-size:14px;">'
    html += '<tr>'
    for day_name in ["Lu","Ma","Me","Gi","Ve","Sa","Do"]:
        html += f'<th style="padding:4px;color:#888;font-weight:600;font-size:12px;">{day_name}</th>'
    html += '</tr>'

    for week in weeks:
        html += '<tr>'
        for d in week:
            if d == 0:
                html += '<td style="padding:4px;"></td>'
            else:
                date_str = f"{year}-{month:02d}-{d:02d}"
                is_today = (d == today.day and month == today.month and year == today.year)
                has_analysis = date_str in analysis_map

                if has_analysis:
                    html += f'<td style="padding:4px;"><span style="color:#22c55e;font-weight:bold;">{d}</span></td>'
                elif is_today:
                    html += f'<td style="padding:4px;"><span style="background:#3b82f6;color:white;border-radius:50%;padding:2px 6px;font-weight:bold;">{d}</span></td>'
                else:
                    html += f'<td style="padding:4px;color:#555;">{d}</td>'
        html += '</tr>'
    html += '</table>'

    st.sidebar.markdown(html, unsafe_allow_html=True)
    st.sidebar.caption("🟢 Analisi salvata | 🔵 Oggi")

    # Dropdown per selezionare analisi
    st.sidebar.markdown("---")
    st.sidebar.markdown("📅 **Carica analisi:**")
    dates_with_analysis = [h.get("analysis_date", "") for h in history if h.get("analysis_date")]
    selected_date = st.sidebar.selectbox("Seleziona data", ["-- Seleziona data --"] + dates_with_analysis, key="sel_date", label_visibility="collapsed")

    selected = None
    if selected_date and selected_date != "-- Seleziona data --":
        selected = analysis_map.get(selected_date)

    if st.sidebar.button("📅 Vai a Oggi"):
        st.session_state.cal_year = today.year
        st.session_state.cal_month = today.month
        st.rerun()

    return selected


# ============================================================================
# VISUALIZZAZIONE ANALISI PASSATA
# ============================================================================

def display_past_analysis(hist):
    """Mostra analisi passata con punteggi + dati completi incluse serie storiche."""
    date = hist.get("analysis_date", "N/A")
    score = hist.get("total_score", 0)
    bias = hist.get("bias", "N/A")
    gold_price = hist.get("gold_price", 0)

    st.markdown(f"## 📅 Analisi del {date}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{score:+d}")
    c2.metric("Bias", bias)
    c3.metric("Gold Price", f"${gold_price:,.2f}" if gold_price else "N/A")

    # Tabella punteggi
    st.markdown("### 🎯 Punteggi")
    try:
        scores = json.loads(hist.get("scores_json", "{}"))
        if scores:
            scores["TOTAL"] = {"total_score": score, "bias": bias}
            display_scores_table(scores)
    except:
        pass

    # Dati completi
    st.markdown("### 📊 Dati Utilizzati")
    try:
        raw = json.loads(hist.get("claude_response", "{}"))
        if not raw:
            st.info("Dati grezzi non disponibili per questa analisi")
            return
    except:
        st.info("Dati grezzi non disponibili per questa analisi")
        return

    # Supporta sia formato nuovo (fred/yahoo/gld/fed/cot) che vecchio (fred_data_summary etc)
    fred = raw.get("fred", raw.get("fred_data_summary", {}))
    yahoo = raw.get("yahoo", raw.get("yahoo_data_summary", {}))
    gld = raw.get("gld", raw.get("gld_data_summary", {}))
    fed = raw.get("fed", raw.get("fed_data_summary", {}))
    cot = raw.get("cot", raw.get("cot_data_summary", {}))

    # DFII10
    d = fred.get("DFII10", {})
    if d:
        info = INDICATOR_INFO.get("DFII10", {})
        st.markdown(f"#### {info.get('icon', '')} {info.get('title', 'DFII10')}")
        c1, c2 = st.columns(2)
        c1.metric("Valore", f"{d.get('latest_value', d.get('value', 'N/A'))}")
        c2.metric("Data", d.get("latest_date", d.get("date", "N/A")))
        if d.get("values") and len(d["values"]) >= 2:
            _show_mini_history(d["values"], "Tasso Reale %", ".4f")
        st.markdown("---")

    # T10YIE
    d = fred.get("T10YIE", {})
    if d:
        info = INDICATOR_INFO.get("T10YIE", {})
        st.markdown(f"#### {info.get('icon', '')} {info.get('title', 'T10YIE')}")
        c1, c2 = st.columns(2)
        c1.metric("Valore", f"{d.get('latest_value', d.get('value', 'N/A'))}")
        c2.metric("Data", d.get("latest_date", d.get("date", "N/A")))
        if d.get("values") and len(d["values"]) >= 2:
            _show_mini_history(d["values"], "Breakeven %", ".4f")
        st.markdown("---")

    # DXY
    d = yahoo.get("DXY", {})
    if d:
        info = INDICATOR_INFO.get("DXY", {})
        st.markdown(f"#### {info.get('icon', '')} {info.get('title', 'DXY')}")
        c1, c2 = st.columns(2)
        c1.metric("Valore", f"{d.get('latest_value', d.get('value', 'N/A'))}")
        c2.metric("Data", d.get("latest_date", d.get("date", "N/A")))
        if d.get("values") and len(d["values"]) >= 2:
            _show_mini_history(d["values"], "DXY", ".2f")
        st.markdown("---")

    # Fed Spread
    dff = fred.get("DFF", {})
    dgs2 = fred.get("DGS2", {})
    if dff and dgs2:
        info = INDICATOR_INFO.get("FED_SPREAD", {})
        st.markdown(f"#### {info.get('icon', '')} {info.get('title', 'Fed Spread')}")
        dff_val = dff.get("latest_value", dff.get("value", 0))
        dgs2_val = dgs2.get("latest_value", dgs2.get("value", 0))
        try:
            spread = float(dff_val) - float(dgs2_val)
            c1, c2, c3 = st.columns(3)
            c1.metric("FFR", f"{dff_val}%")
            c2.metric("Treasury 2Y", f"{dgs2_val}%")
            c3.metric("Spread", f"{spread:+.4f}%")
        except:
            pass
        # Spread history if available
        if dff.get("values") and dgs2.get("values"):
            dff_dict = {v["date"]: v["value"] for v in dff["values"]}
            spread_hist = []
            for v in dgs2["values"]:
                if v["date"] in dff_dict:
                    spread_hist.append({"date": v["date"], "value": round(dff_dict[v["date"]] - v["value"], 4)})
            if len(spread_hist) >= 2:
                _show_mini_history(spread_hist, "Spread %", ".4f")
        st.markdown("---")

    # GLD
    if gld and (gld.get("latest_tonnes") or gld.get("tonnes")):
        info = INDICATOR_INFO.get("GLD", {})
        st.markdown(f"#### {info.get('icon', '')} {info.get('title', 'GLD')}")
        c1, c2 = st.columns(2)
        c1.metric("Tonnellate", f"{gld.get('latest_tonnes', gld.get('tonnes', 'N/A'))}t")
        c2.metric("Data", gld.get("latest_date", gld.get("date", "N/A")))
        if gld.get("values") and len(gld["values"]) >= 2:
            _show_mini_history(gld["values"], "Tonnellate", ".2f")
        st.markdown("---")

    # VIX
    d = yahoo.get("VIX", {})
    if d:
        info = INDICATOR_INFO.get("VIX", {})
        st.markdown(f"#### {info.get('icon', '')} {info.get('title', 'VIX')}")
        c1, c2 = st.columns(2)
        c1.metric("Valore", f"{d.get('latest_value', d.get('value', 'N/A'))}")
        c2.metric("Data", d.get("latest_date", d.get("date", "N/A")))
        if d.get("values") and len(d["values"]) >= 2:
            _show_mini_history(d["values"], "VIX", ".2f")
        st.markdown("---")

    # COT
    if cot:
        info = INDICATOR_INFO.get("COT", {})
        st.markdown(f"#### {info.get('icon', '')} {info.get('title', 'COT')}")
        rows = []
        for asset_key in ["GOLD", "USD"]:
            d = cot.get(asset_key, {})
            if d:
                net = d.get("net_long", 0)
                ci = d.get("cot_index", 0)
                rows.append({
                    "Asset": "🥇 Oro" if asset_key == "GOLD" else "💵 USD Index",
                    "Net Position": f"{_net_emoji(net)} {net:+,}",
                    "COT Index": f"{_index_emoji(ci)} {ci:.0f}%",
                    "Interpretazione": d.get("interpretation", "N/A"),
                })
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        if cot.get("latest_date"):
            st.caption(f"Dati report: {cot['latest_date']}")
        st.markdown("---")

    # Fed Trend
    if fed:
        info = INDICATOR_INFO.get("FED_TREND", {})
        st.markdown(f"#### {info.get('icon', '')} {info.get('title', 'Fed Trend')}")
        c1, c2 = st.columns(2)
        c1.metric("Tasso", fed.get("current_rate", fed.get("rate", "N/A")))
        c2.metric("Trend", f"{fed.get('trend_emoji', '')} {fed.get('trend_label', fed.get('trend', 'N/A'))}")
        for m in fed.get("meetings", []):
            st.markdown(f"- **{m.get('date_formatted', 'N/A')}**: {m.get('change', 'N/A')}")

import json
