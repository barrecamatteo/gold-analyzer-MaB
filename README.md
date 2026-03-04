# Gold XAU/USD Macro Analyzer

Analizzatore macro settimanale per l'oro (XAU/USD) con scoring automatico (-18 / +18) e sintesi Claude AI.

## Struttura File

```
gold_analyzer/
├── .streamlit/
│   ├── config.toml              # Tema e config Streamlit
│   ├── secrets.toml.example     # Template secrets (da copiare)
│   └── secrets.toml             # LE TUE CHIAVI (non su git!)
├── gold_analyzer.py             # App principale Streamlit
├── gold_data_fetcher.py         # Fetch dati + scoring engine
├── gold_cot_data.py             # Modulo COT CFTC (contratto 088691)
├── gold_claude.py               # Modulo analisi Claude AI
├── gold_ui.py                   # Componenti UI
├── supabase_schema.sql          # Schema database
├── requirements.txt             # Dipendenze Python
├── .gitignore                   # File esclusi da git
└── README.md                    # Questa guida
```

## 11 Indicatori

| # | Indicatore | Range | Fonte |
|---|-----------|-------|-------|
| 1 | Tasso Reale 10Y (DFII10) | +/-2 | FRED API |
| 2 | DXY (US Dollar Index) | +/-3 | Yahoo Finance |
| 3 | Breakeven Inflation (T10YIE) | +/-2 | FRED API |
| 4 | GLD Holdings (SPDR) | +/-1 | SPDR CSV |
| 5 | COT Oro Non-Commercial | +/-2 | CFTC API |
| 6 | Banche Centrali | +/-1 | IMF/Manuale |
| 7 | Fed Trend (FOMC) | +/-1 | Investing.com |
| 8 | Fed Expectations (FFR-2Y) | +/-2 | FRED API |
| 9 | VIX (Risk Sentiment) | +/-2 | Yahoo Finance |
| 10 | Stagionalita | +/-1 | Hardcoded |
| 11 | News/Geopolitica | +/-1 | Claude AI |

**Totale: -18 / +18**

## Interpretazione Bias

- **+10 a +18**: Forte bias rialzista
- **+4 a +9**: Moderatamente rialzista
- **-3 a +3**: Neutro / Range
- **-9 a -4**: Moderatamente ribassista
- **-18 a -10**: Forte bias ribassista
