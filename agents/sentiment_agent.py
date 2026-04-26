import time
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field

import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from .json_llm import invoke_json_llm
from config import get_settings

logger = logging.getLogger(__name__)

try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon", quiet=True)


class SentimentMemo(BaseModel):
    company_name: str = Field(default="Unknown")
    overall_sentiment: str = Field(description="POSITIVE, NEUTRAL, or NEGATIVE")
    sentiment_score: float = Field(description="Compound score from -1.0 to +1.0")
    top_headlines: List[str] = Field(default_factory=list, description="Up to 3 most relevant headlines")
    risk_signal: str = Field(description="One-line plain English risk interpretation for the credit committee")
    news_source: str = Field(default="newsapi", description="newsapi or fallback")
    articles_analysed: int = Field(default=0)


class ExtractedEntity(BaseModel):
    company_name: str = "UNKNOWN"
    industry: str = "UNKNOWN"
    ticker: str = "UNKNOWN"

def extract_entity_from_context(financial_summary: str, raw_context: str) -> dict:
    """
    Use the LLM to extract company_name, industry, and ticker from already-parsed
    financial analysis. Prefer financial_summary; fall back to raw_context[:2000].
    
    Returns: {"company_name": str, "industry": str, "ticker": str or "UNKNOWN"}
    """
    
    source = financial_summary if financial_summary.strip() else raw_context[:2000]
    
    prompt = f"""You are extracting structured entity information from a loan document summary.

Extract:
1. company_name: The full legal name of the borrowing company
2. industry: The industry sector (e.g. "retail", "manufacturing", "technology", "real estate")
3. ticker: Stock ticker symbol if mentioned (NSE/BSE format like "RELIANCE.NS" preferred), 
   else "UNKNOWN"

SOURCE TEXT:
{source}

Return ONLY valid JSON with exactly these three keys. 
If you cannot determine a value, use "UNKNOWN".
{{"company_name": "...", "industry": "...", "ticker": "..."}}"""

    result = invoke_json_llm(
        prompt=prompt,
        default_dict={"company_name": "UNKNOWN", "industry": "UNKNOWN", "ticker": "UNKNOWN"},
        model_class=ExtractedEntity,
    )
    
    # invoke_json_llm returns a pydantic model or dict — handle both
    if hasattr(result, "dict"):
        return result.dict()
    elif hasattr(result, "model_dump"):
        return result.model_dump()
    return result if isinstance(result, dict) else {"company_name": "UNKNOWN", "industry": "UNKNOWN", "ticker": "UNKNOWN"}


def fetch_headlines(company_name: str, ticker: str, api_key: str) -> List[dict]:
    """
    Fetch up to 10 recent articles from NewsAPI.
    Query strategy:
      - Primary: company_name (exact phrase if multi-word, else plain)
      - If company_name returns 0 results AND ticker != "UNKNOWN": retry with ticker
    
    Returns list of {"title": str, "source": str} dicts.
    On any error (no key, rate limit, timeout, no results): returns []
    """
    
    if not api_key:
        return []
    
    seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    def _call(query: str) -> List[dict]:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": f'"{query}"' if " " in query else query,
                    "from": seven_days_ago,
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                    "language": "en",
                    "apiKey": api_key,
                },
                timeout=8,
            )
            if resp.status_code == 429:
                logger.warning("NewsAPI rate limit hit — using fallback")
                return []
            if resp.status_code != 200:
                logger.warning("NewsAPI returned %s", resp.status_code)
                return []
            articles = resp.json().get("articles", [])
            return [{"title": a["title"], "source": a["source"]["name"]} for a in articles if a.get("title")]
        except Exception as e:
            logger.warning("NewsAPI fetch failed: %s", e)
            return []
    
    results = _call(company_name)
    if not results and ticker != "UNKNOWN":
        time.sleep(0.5)  # brief pause before retry
        results = _call(ticker.replace(".NS", "").replace(".BO", ""))
    return results


def score_headlines(headlines: List[dict]) -> dict:
    """
    Run VADER on each headline title.
    Returns:
    {
        "overall_sentiment": "POSITIVE"|"NEUTRAL"|"NEGATIVE",
        "sentiment_score": float,       # mean compound score
        "scored_headlines": List[dict]  # [{title, score, source}]
    }
    """
    if not headlines:
        return {"overall_sentiment": "NEUTRAL", "sentiment_score": 0.0, "scored_headlines": []}
    
    sia = SentimentIntensityAnalyzer()
    scored = []
    for h in headlines:
        compound = sia.polarity_scores(h["title"])["compound"]
        scored.append({"title": h["title"], "score": compound, "source": h["source"]})
    
    mean_score = sum(s["score"] for s in scored) / len(scored)
    
    if mean_score > 0.05:
        sentiment = "POSITIVE"
    elif mean_score < -0.05:
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"
    
    # Sort by absolute score descending — most extreme headlines first
    scored.sort(key=lambda x: abs(x["score"]), reverse=True)
    
    return {
        "overall_sentiment": sentiment,
        "sentiment_score": round(mean_score, 4),
        "scored_headlines": scored,
    }


def build_risk_signal(sentiment: str, score: float, company_name: str, 
                       articles_count: int) -> str:
    """
    Pure Python — no LLM. Returns a single plain-English sentence
    for the credit committee to reference.
    """
    if articles_count == 0:
        return f"No recent news found for {company_name} — sentiment could not be assessed."
    
    intensity = "strongly" if abs(score) > 0.3 else "mildly"
    
    signals = {
        "POSITIVE": f"Recent news coverage of {company_name} is {intensity} positive (score: {score:+.2f}) — market perception is supportive of this credit.",
        "NEGATIVE": f"Recent news coverage of {company_name} is {intensity} negative (score: {score:+.2f}) — reputational or operational concerns flagged; Risk agent should investigate.",
        "NEUTRAL":  f"Recent news coverage of {company_name} is neutral (score: {score:+.2f}) — no significant market signals detected.",
    }
    return signals.get(sentiment, signals["NEUTRAL"])


def run_sentiment_agent(
    financial_summary: str,
    raw_context: str,
) -> SentimentMemo:
    """
    Full pipeline:
    1. Extract entity → 2. Fetch headlines → 3. Score → 4. Build memo
    
    NEVER raises an exception. All failures resolve to a NEUTRAL fallback memo.
    """
    settings = get_settings()
    
    NEUTRAL_FALLBACK = SentimentMemo(
        company_name="Unknown",
        overall_sentiment="NEUTRAL",
        sentiment_score=0.0,
        top_headlines=[],
        risk_signal="Sentiment analysis unavailable — no API key or extraction failed.",
        news_source="fallback",
        articles_analysed=0,
    )
    
    try:
        # Step 1
        entity = extract_entity_from_context(financial_summary, raw_context)
        company_name = entity.get("company_name", "UNKNOWN")
        ticker = entity.get("ticker", "UNKNOWN")
        
        if company_name == "UNKNOWN":
            logger.info("Could not extract company name — returning neutral fallback")
            return NEUTRAL_FALLBACK
        
        # Step 2
        headlines = fetch_headlines(company_name, ticker, settings.newsapi_key or "")
        
        # Step 3
        scored = score_headlines(headlines)
        
        # Step 4
        top_3 = [h["title"] for h in scored["scored_headlines"][:3]]
        risk_signal = build_risk_signal(
            scored["overall_sentiment"],
            scored["sentiment_score"],
            company_name,
            len(headlines),
        )
        
        return SentimentMemo(
            company_name=company_name,
            overall_sentiment=scored["overall_sentiment"],
            sentiment_score=scored["sentiment_score"],
            top_headlines=top_3,
            risk_signal=risk_signal,
            news_source="newsapi" if headlines else "fallback",
            articles_analysed=len(headlines),
        )
    
    except Exception as e:
        logger.error("Sentiment agent failed unexpectedly: %s", e)
        return NEUTRAL_FALLBACK


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mock_summary = "Vertex Technologies is a mid-sized IT services firm headquartered in Bangalore. Revenue grew 18% YoY to ₹420 Cr."
    
    result = run_sentiment_agent(
        financial_summary=mock_summary,
        raw_context="",
    )
    print(result.dict() if hasattr(result, "dict") else result.model_dump())
