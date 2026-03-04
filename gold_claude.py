"""Claude AI Analysis Module for Gold Analyzer"""
import streamlit as st
import anthropic
import json
from datetime import datetime

CLAUDE_SYSTEM = (
    "Sei un analista macro specializzato in oro (XAU/USD). "
    "Ricevi punteggi automatici di 11 indicatori macro/intermarket e notizie recenti.\n\n"
    "COMPITI:\n"
    "1. ASSEGNA punteggio News/Geopolitica (-1, 0 o +1)\n"
    "2. COMMENTO sintetico (5 righe) su cosa spinge il bias\n"
    "3. CHECK COERENZA: se DFII10, DXY e COT divergono, segnalalo\n"
    "4. 3 SCENARI a 3 settimane con range prezzo\n"
    "5. 2-3 TRIGGER operativi\n\n"
    'RISPONDI SOLO in JSON:\n'
    '{"news_score": <-1/0/+1>, "news_comment": "...", "summary": "...", '
    '"coherence_check": "...", '
    '"scenarios": {"bullish": {"conditions":"..","price_range":".."}, '
    '"neutral": {"conditions":"..","price_range":".."}, '
    '"bearish": {"conditions":"..","price_range":".."}}, '
    '"triggers": ["..","..",".."], "confidence": "alta/media/bassa"}'
)

SCORE_KEYS = ["DFII10","DXY","T10YIE","GLD","COT","CB",
              "FED_TREND","FED_EXPECT","VIX","SEASONALITY"]

def build_prompt(scores, news_text, gold_price, now_str):
    lines = ["PUNTEGGI AUTOMATICI CALCOLATI:"]
    for key in SCORE_KEYS:
        s = scores.get(key, {})
        if "total_score" in s:
            lines.append(
                f"- {s['name']}: {s['value']} | D4w: {s['delta_4w']} "
                f"| Score: {s['total_score']:+d}/{s['max_score']} | {s['comment']}"
            )
    total = scores.get("TOTAL", {})
    lines.append(f"\nTOTALE (senza news): {total.get('total_score',0):+d}")
    lines.append(f"BIAS: {total.get('bias','N/A')}")
    if gold_price:
        lines.append(f"PREZZO XAU/USD: ${gold_price:,.2f}")
    lines.append(f"DATA: {now_str}")
    lines.append(f"\nNOTIZIE RECENTI SULL'ORO:\n{news_text}")
    lines.append("\nAnalizza i dati sopra e fornisci la tua analisi in formato JSON.")
    return "\n".join(lines)

def run_claude_analysis(scores, news_text, gold_price, now_str):
    try:
        api_key = st.secrets["anthropic"]["api_key"]
    except Exception:
        return {"error": "API key Anthropic non configurata"}

    prompt = build_prompt(scores, news_text, gold_price, now_str)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        container = st.empty()
        full = ""
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=CLAUDE_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                full += text
                container.markdown(f"```\n{full}\n```")

        js = full.find("{")
        je = full.rfind("}") + 1
        if js >= 0 and je > js:
            return json.loads(full[js:je])
        return {"error": "No JSON found", "raw": full}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON", "raw": full}
    except Exception as e:
        return {"error": str(e)[:200]}
