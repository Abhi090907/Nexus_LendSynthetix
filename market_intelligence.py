import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import yfinance as yf
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# =========================================================================
# SECTION 1 — DATA FETCHING (yfinance + free APIs)
# =========================================================================
def fetch_equity_data(ticker: str) -> dict:
    if not ticker or ticker == "UNKNOWN":
        return {"error": "Invalid ticker", "ticker": ticker}

    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        
        if hist.empty and not ticker.endswith(".NS"):
            time.sleep(1)
            ticker_ns = ticker + ".NS"
            t = yf.Ticker(ticker_ns)
            hist = t.history(period="1y")
            if not hist.empty:
                ticker = ticker_ns
        
        info = {}
        try:
            info = t.info
        except Exception:
            pass

        if hist.empty:
            return {"error": "No price data found", "ticker": ticker}

        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        price_change_pct = ((current_price - prev_close) / prev_close) * 100

        week_52_high = hist['High'].max()
        week_52_low = hist['Low'].min()
        
        dist_52w_high_pct = None
        if week_52_high and week_52_high > 0:
            dist_52w_high_pct = ((week_52_high - current_price) / week_52_high) * 100

        sma200 = hist['Close'].rolling(window=200).mean().iloc[-1] if len(hist) >= 200 else None
        price_vs_200dma = None
        if sma200 is not None:
            price_vs_200dma = "ABOVE" if current_price > sma200 else "BELOW"

        # RSI 14
        rsi_14 = None
        if len(hist) >= 15:
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_14 = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

        # Volume ratio
        vol_today = hist['Volume'].iloc[-1]
        vol_30d_avg = hist['Volume'].rolling(window=30).mean().iloc[-1] if len(hist) >= 30 else vol_today
        volume_ratio = float(vol_today / vol_30d_avg) if vol_30d_avg and vol_30d_avg > 0 else 1.0

        # Target Price
        target_mean = info.get("targetMeanPrice")
        target_price_upside_pct = None
        if target_mean and current_price and current_price > 0:
            target_price_upside_pct = ((target_mean - current_price) / current_price) * 100

        # Debt to equity
        debt_to_equity = None
        try:
            bs = t.balance_sheet
            if not bs.empty and 'Total Debt' in bs.index and 'Stockholders Equity' in bs.index:
                total_debt = bs.loc['Total Debt'].iloc[0]
                equity = bs.loc['Stockholders Equity'].iloc[0]
                if equity and equity != 0:
                    debt_to_equity = float(total_debt / equity)
        except Exception:
            pass

        # FCF
        free_cash_flow = info.get("freeCashflow")
        if free_cash_flow is None:
            try:
                cf = t.cashflow
                if not cf.empty and 'Free Cash Flow' in cf.index:
                    free_cash_flow = float(cf.loc['Free Cash Flow'].iloc[0])
            except Exception:
                pass

        return {
            "ticker": ticker,
            "current_price": float(current_price),
            "prev_close": float(prev_close),
            "price_change_pct": float(price_change_pct),
            "week_52_high": float(week_52_high),
            "week_52_low": float(week_52_low),
            "distance_from_52w_high_pct": dist_52w_high_pct,
            "price_vs_200dma": price_vs_200dma,
            "rsi_14": rsi_14,
            "volume_ratio": volume_ratio,
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "ev_to_ebitda": info.get("enterpriseToEbitda"),
            "dividend_yield": info.get("dividendYield"),
            "payout_ratio": info.get("payoutRatio"),
            "debt_to_equity": debt_to_equity,
            "return_on_equity": info.get("returnOnEquity"),
            "return_on_assets": info.get("returnOnAssets"),
            "free_cash_flow": free_cash_flow,
            "insider_ownership_pct": info.get("heldPercentInsiders", 0) * 100 if info.get("heldPercentInsiders") else None,
            "institutional_ownership_pct": info.get("heldPercentInstitutions", 0) * 100 if info.get("heldPercentInstitutions") else None,
            "analyst_recommendation": info.get("recommendationKey"),
            "analyst_count": info.get("numberOfAnalystOpinions"),
            "target_price_upside_pct": target_price_upside_pct
        }
    except Exception as e:
        logger.warning(f"Error fetching equity data for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}

# =========================================================================
# SECTION 2 — SECTOR & MACRO CONTEXT
# =========================================================================
def fetch_macro_indicators() -> dict:
    indicators = {}
    macro_flags = []
    
    def get_last_price(symbol: str) -> Optional[float]:
        try:
            time.sleep(1)
            t = yf.Ticker(symbol)
            return t.fast_info.last_price
        except Exception:
            return None

    # India 10Y Yield
    in10y = get_last_price("IN10YT=RR")
    if in10y is None:
        in10y = get_last_price("^TNX")
    indicators["india_10y_yield"] = in10y

    usd_inr = get_last_price("USDINR=X")
    indicators["usd_inr"] = usd_inr
    if usd_inr and usd_inr > 84:
        macro_flags.append("Weak INR — import-heavy companies face margin pressure")

    crude = get_last_price("BZ=F")
    indicators["crude_oil_brent"] = crude
    if crude and crude > 90:
        macro_flags.append("Elevated crude — logistics/manufacturing cost risk")

    indicators["gold_price"] = get_last_price("GC=F")

    try:
        time.sleep(1)
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="1mo")
        if not hist.empty and len(hist) > 1:
            nifty_last = hist['Close'].iloc[-1]
            nifty_start = hist['Close'].iloc[0]
            nifty_change = ((nifty_last - nifty_start) / nifty_start) * 100
            indicators["nifty50_level"] = nifty_last
            indicators["nifty50_change_pct"] = nifty_change
            if nifty_change < -5:
                macro_flags.append("Broad market weakness — risk-off environment")
    except Exception:
        indicators["nifty50_level"] = None
        indicators["nifty50_change_pct"] = None

    indicators["vix_india"] = get_last_price("^NSEBANK")
    
    return {
        "indicators": indicators,
        "macro_flags": macro_flags,
        "macro_summary": f"Macro context computed with {len(macro_flags)} risk flags."
    }

# =========================================================================
# SECTION 3 — GEOPOLITICAL RISK SCORING
# =========================================================================
def fetch_geopolitical_headlines(sector: str, api_key: str) -> List[str]:
    """
    Fetch current macro/geopolitical headlines relevant to this sector.
    Uses NewsAPI to search for geopolitical risk terms + sector.
    Returns up to 5 headline strings. Returns [] on any failure.
    """
    if not api_key:
        return []
    
    # Build a sector-aware geopolitical query
    GEO_TERMS = {
        "manufacturing": "supply chain OR tariff OR sanctions OR trade war",
        "technology": "chip ban OR semiconductor OR export control OR China tech",
        "retail": "import tariff OR consumer sentiment OR inflation",
        "real estate": "interest rate OR RBI OR Fed rate",
        "pharma": "drug export ban OR API China OR FDA",
        "logistics": "Red Sea OR Suez OR shipping OR port strike",
    }
    sector_lower = sector.lower()
    query_suffix = next(
        (v for k, v in GEO_TERMS.items() if k in sector_lower),
        "geopolitical risk OR sanctions OR trade war OR war"
    )
    
    query = f"India economy OR {query_suffix}"
    
    try:
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "from": seven_days_ago,
                "sortBy": "publishedAt",
                "pageSize": 5,
                "language": "en",
                "apiKey": api_key,
            },
            timeout=8,
        )
        if resp.status_code != 200:
            return []
        articles = resp.json().get("articles", [])
        return [a["title"] for a in articles if a.get("title")]
    except Exception:
        return []

class GeopoliticalRisk(BaseModel):
    china_supply_chain_exposure: str = Field(description="HIGH | MEDIUM | LOW | NONE")
    china_exposure_reason: str
    sanctions_risk: str = Field(description="HIGH | LOW")
    sanctions_reason: str
    trade_war_sensitivity: str = Field(description="HIGH | MEDIUM | LOW")
    trade_war_reason: str
    commodity_shock_exposure: str = Field(description="HIGH | MEDIUM | LOW")
    commodity_reason: str
    geopolitical_risk_score: int
    geopolitical_flags: List[str]
    geopolitical_summary: str

def assess_geopolitical_risk(company_name: str, sector: str, context: str, llm_caller, api_key: str = "") -> dict:
    geo_headlines = fetch_geopolitical_headlines(sector, api_key)
    
    CURRENT_GEO_NEWS_BLOCK = ""
    if geo_headlines:
        headlines_text = "\n".join(f"- {h}" for h in geo_headlines)
        CURRENT_GEO_NEWS_BLOCK = f"""
LIVE GEOPOLITICAL HEADLINES (fetched today — prioritise these over your 
training knowledge when assessing current risk):
{headlines_text}

Use these headlines to UPDATE your assessment. If a headline signals a new 
sanctions event, trade restriction, war escalation, or supply chain shock 
relevant to this company's sector, reflect that in your geopolitical_flags 
and increase the geopolitical_risk_score accordingly.
"""

    prompt = f"""Assess the geopolitical risk for the following company based on its sector and the provided document context.

Company: {company_name}
Sector: {sector}

Context:
{context[:3000]}
{CURRENT_GEO_NEWS_BLOCK}
Base your assessment on the company's sector, any countries mentioned in the document context, and known geopolitical risks as of your training cutoff. Be specific — reference the actual sector risks, not generic statements.

Rules for score:
china_exposure (HIGH=30, MED=15, LOW=5) +
sanctions_risk (HIGH=25, LOW=0) +
trade_war (HIGH=20, MED=10, LOW=3) +
commodity_shock (HIGH=15, MED=8, LOW=2)
Max score = 90. Return the score out of 100.

Return the result strictly as a valid JSON matching the schema."""
    
    default_dict = {
        "china_supply_chain_exposure": "UNKNOWN",
        "china_exposure_reason": "",
        "sanctions_risk": "UNKNOWN",
        "sanctions_reason": "",
        "trade_war_sensitivity": "UNKNOWN",
        "trade_war_reason": "",
        "commodity_shock_exposure": "UNKNOWN",
        "commodity_reason": "",
        "geopolitical_risk_score": 0,
        "geopolitical_flags": [],
        "geopolitical_summary": "Failed to assess risk."
    }
    
    try:
        res = llm_caller(
            prompt=prompt,
            default_dict=default_dict,
            model_class=GeopoliticalRisk
        )
        return res.model_dump() if hasattr(res, "model_dump") else getattr(res, "dict", lambda: default_dict)()
    except Exception as e:
        logger.error(f"Geopolitical risk assessment failed: {e}")
        return default_dict

# =========================================================================
# SECTION 4 — INVESTMENT SIGNAL SYNTHESIS
# =========================================================================
def generate_investment_signals(equity_data: dict, macro_data: dict, geo_risk: dict) -> dict:
    if "error" in equity_data:
        return {
            "technical_signals": {},
            "valuation_signals": {},
            "overall_investment_score": 0,
            "investment_verdict": "UNKNOWN",
            "key_reasons_to_invest": [],
            "key_reasons_to_avoid": ["Equity data could not be fetched."],
            "one_line_summary": "Insufficient data to generate specific technical or fundamental investment signals."
        }

    rsi = equity_data.get("rsi_14")
    if rsi is None:
        rsi_signal = "NEUTRAL"
    elif rsi < 30:
        rsi_signal = "OVERSOLD — potential entry"
    elif rsi > 70:
        rsi_signal = "OVERBOUGHT — caution"
    else:
        rsi_signal = "NEUTRAL"
        
    pvs200 = equity_data.get("price_vs_200dma")
    pct_change = equity_data.get("price_change_pct", 0)
    if pvs200 == "ABOVE" and pct_change > 0:
        trend_signal = "BULLISH TREND"
    elif pvs200 == "BELOW" and pct_change < 0:
        trend_signal = "BEARISH TREND"
    else:
        trend_signal = "MIXED"
        
    vol_ratio = equity_data.get("volume_ratio", 1)
    if vol_ratio > 2.0:
        volume_signal = "HIGH VOLUME — unusual institutional activity"
    else:
        volume_signal = "NORMAL VOLUME"
        
    dist = equity_data.get("distance_from_52w_high_pct")
    if dist is None:
        proximity_signal = "UNKNOWN"
    elif dist < 5:
        proximity_signal = "NEAR 52-WEEK HIGH — breakout or resistance"
    elif dist > 40:
        proximity_signal = "FAR FROM PEAK — significant drawdown"
    else:
        proximity_signal = "MID-RANGE"

    pe = equity_data.get("pe_ratio")
    pb = equity_data.get("pb_ratio")
    if pe is None:
        valuation_signal = "VALUATION UNKNOWN — not profitable or not public"
    elif pe < 15 and pb and pb < 1.5:
        valuation_signal = "UNDERVALUED relative to market norms"
    elif pe > 40:
        valuation_signal = "EXPENSIVE — high growth priced in"
    else:
        valuation_signal = "FAIRLY VALUED"

    fcf = equity_data.get("free_cash_flow")
    if fcf is None:
        fcf_signal = "FCF UNKNOWN"
    elif fcf > 0:
        fcf_signal = "POSITIVE FREE CASH FLOW — healthy"
    else:
        fcf_signal = "NEGATIVE FCF — cash burn risk"

    score = 0
    recc = str(equity_data.get("analyst_recommendation", "")).lower()
    if "strong buy" in recc: score += 20
    elif "buy" in recc: score += 15
    elif "hold" in recc: score += 10
    elif "sell" in recc: score += 3

    if rsi is not None and rsi < 70: score += 10
    if pvs200 == "ABOVE": score += 15
    if pe is not None and pe < 30: score += 15
    if fcf is not None and fcf > 0: score += 20
    
    geo_score = geo_risk.get("geopolitical_risk_score", 50)
    if geo_score < 40: score += 10
    
    if len(macro_data.get("macro_flags", [])) == 0: score += 10
    
    score = min(max(int(score), 0), 100)
    
    if score >= 75: verdict = "STRONG INVEST SIGNAL — fundamentals, technicals, and macro align"
    elif score >= 55: verdict = "CAUTIOUS POSITIVE — worth considering with position sizing discipline"
    elif score >= 35: verdict = "NEUTRAL / WAIT — mixed signals, monitor before committing"
    elif score >= 15: verdict = "CAUTION — multiple red flags present"
    else: verdict = "AVOID — significant risk factors across multiple dimensions"
    
    positives = []
    if fcf_signal.startswith("POSITIVE"): positives.append(fcf_signal)
    if valuation_signal.startswith("UNDERVALUED"): positives.append(valuation_signal)
    if trend_signal == "BULLISH TREND": positives.append(trend_signal)
    
    negatives = []
    if geo_score > 50: negatives.append(f"High geopolitical risk: {geo_score}")
    if fcf_signal.startswith("NEGATIVE"): negatives.append(fcf_signal)
    if rsi_signal.startswith("OVERBOUGHT"): negatives.append(rsi_signal)
    if valuation_signal.startswith("EXPENSIVE"): negatives.append(valuation_signal)

    one_line_summary = f"Score of {score}/100: {verdict}. "
    one_line_summary += f"Positives: {', '.join(positives[:2]) if positives else 'None standing out'}. "
    one_line_summary += f"Risks: {', '.join(negatives[:2]) if negatives else 'No major immediate alarms'}."

    return {
        "technical_signals": {
            "rsi_signal": rsi_signal,
            "trend_signal": trend_signal,
            "volume_signal": volume_signal,
            "proximity_signal": proximity_signal
        },
        "valuation_signals": {
            "valuation_signal": valuation_signal,
            "fcf_signal": fcf_signal
        },
        "overall_investment_score": score,
        "investment_verdict": verdict,
        "key_reasons_to_invest": positives[:3],
        "key_reasons_to_avoid": negatives[:3],
        "one_line_summary": one_line_summary
    }

# =========================================================================
# SECTION 5 — MAIN ORCHESTRATOR FUNCTION
# =========================================================================
class MarketIntelligenceReport(BaseModel):
    ticker: Optional[str]
    equity_data: dict
    macro_context: dict
    geopolitical_risk: dict
    investment_signals: dict
    market_intelligence_summary: str

def _run_market_intelligence_internal(company_name: str, sector: str, context: str, ticker: Optional[str], llm_caller) -> MarketIntelligenceReport:
    from config import get_settings
    settings = get_settings()
    
    macro = fetch_macro_indicators()
    geo = assess_geopolitical_risk(company_name, sector, context, llm_caller, settings.newsapi_key or "")
    
    equity = {}
    if ticker and ticker != "UNKNOWN":
        equity = fetch_equity_data(ticker)
    else:
        equity = {"error": "No ticker provided"}
        
    signals = generate_investment_signals(equity, macro, geo)
    
    summary = signals.get("one_line_summary", "No clear investment signals generated.")
    if macro.get("macro_flags"):
        summary += f" Macro context is challenging: {', '.join(macro['macro_flags'])}."
    summary += f" Geopolitical risk is assessed at {geo.get('geopolitical_risk_score', 'Unknown')}/100."

    return MarketIntelligenceReport(
        ticker=ticker,
        equity_data=equity,
        macro_context=macro,
        geopolitical_risk=geo,
        investment_signals=signals,
        market_intelligence_summary=summary
    )

def run_market_intelligence(company_name: str, sector: str, context: str, ticker: Optional[str], llm_caller) -> MarketIntelligenceReport:
    """Wrapper to ensure it never throws an unhandled exception."""
    try:
        return _run_market_intelligence_internal(company_name, sector, context, ticker, llm_caller)
    except Exception as e:
        logger.error(f"Fatal error in market intelligence orchestration: {e}")
        return MarketIntelligenceReport(
            ticker=ticker,
            equity_data={"error": str(e)},
            macro_context={},
            geopolitical_risk={},
            investment_signals={},
            market_intelligence_summary="Market intelligence assembly failed due to an error."
        )
