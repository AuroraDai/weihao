import csv
import io
import os
import re
from typing import Optional, List, Dict
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from finvizfinance.quote import finvizfinance
from newspaper import Article
from deep_translator import GoogleTranslator
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from collections import defaultdict


load_dotenv()


def create_better_summary(text: str, max_sentences: int = 5) -> str:
    """
    Create an improved extractive summary using sentence scoring.
    Scores sentences based on word frequency (excluding stopwords).
    """
    try:
        # Tokenize into sentences
        sentences = sent_tokenize(text)
        if len(sentences) <= max_sentences:
            return text
        
        # Tokenize words and remove stopwords
        stop_words = set(stopwords.words('english'))
        words = word_tokenize(text.lower())
        words = [w for w in words if w.isalnum() and w not in stop_words]
        
        # Calculate word frequencies
        word_freq = defaultdict(int)
        for word in words:
            word_freq[word] += 1
        
        # Score sentences based on word frequency
        sentence_scores = defaultdict(int)
        for sentence in sentences:
            sentence_words = word_tokenize(sentence.lower())
            for word in sentence_words:
                if word in word_freq:
                    sentence_scores[sentence] += word_freq[word]
        
        # Get top sentences
        sorted_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)
        top_sentences = [sent for sent, score in sorted_sentences[:max_sentences]]
        
        # Maintain original order of sentences
        summary_sentences = []
        for sentence in sentences:
            if sentence in top_sentences:
                summary_sentences.append(sentence)
                if len(summary_sentences) >= max_sentences:
                    break
        
        return ' '.join(summary_sentences)
    except Exception:
        # Fallback to simple truncation
        sentences = sent_tokenize(text)
        return ' '.join(sentences[:max_sentences])


# Download NLTK data required for article summarization
try:
    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)
    nltk.download("punkt_tab", quiet=True)
except Exception:
    pass  # May already be downloaded

app = FastAPI(title="Finviz Proxy API", version="0.1.0")

# Allow the Svelte frontend to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/market/overview")
def get_market_overview() -> dict:
    """
    Get market overview data including:
    - Trading session (Pre / Regular / After)
    - Major indices status (SPY / QQQ / DIA)
    - VIX (fear index)
    - Advance/Decline ratio
    """
    try:
        import datetime
        
        # Get current time in EST (Eastern Time)
        from datetime import timezone, timedelta
        est = timezone(timedelta(hours=-5))  # EST is UTC-5
        now = datetime.datetime.now(est)
        current_hour = now.hour
        current_minute = now.minute
        weekday = now.weekday()  # 0 = Monday, 6 = Sunday
        
        # Determine trading session (EST timezone)
        # Pre-market: 4:00 AM - 9:30 AM EST (weekdays only)
        # Regular: 9:30 AM - 4:00 PM EST (weekdays only)
        # After-hours: 4:00 PM - 8:00 PM EST (weekdays only)
        # Closed: weekends or outside trading hours
        if weekday >= 5:  # Saturday or Sunday
            session = "Closed"
        elif 4 <= current_hour < 9 or (current_hour == 9 and current_minute < 30):
            session = "Pre"
        elif (current_hour == 9 and current_minute >= 30) or (9 < current_hour < 16):
            session = "Regular"
        elif 16 <= current_hour < 20:
            session = "After"
        else:
            session = "Closed"
        
        # Get major indices data
        indices_data = {}
        for ticker in ["SPY", "QQQ", "DIA"]:
            try:
                quote = finvizfinance(ticker)
                quote_data = quote.ticker_fundament()
                price = quote_data.get("Price", "N/A")
                change = quote_data.get("Change", "N/A")
                change_pct = quote_data.get("Change %", "N/A")
                indices_data[ticker] = {
                    "price": price,
                    "change": change,
                    "change_pct": change_pct
                }
            except Exception:
                indices_data[ticker] = {"price": "N/A", "change": "N/A", "change_pct": "N/A"}
        
        # Get VIX data
        vix_data = {}
        try:
            vix_quote = finvizfinance("VIX")
            vix_fundament = vix_quote.ticker_fundament()
            vix_data = {
                "value": vix_fundament.get("Price", "N/A"),
                "change": vix_fundament.get("Change", "N/A"),
                "change_pct": vix_fundament.get("Change %", "N/A")
            }
        except Exception:
            vix_data = {"value": "N/A", "change": "N/A", "change_pct": "N/A"}
        
        # Get advance/decline ratio
        # Try to get from NYSE/NASDAQ data via Finviz screener or use a proxy
        adv_decl_ratio = "N/A"
        adv_count = "N/A"
        decl_count = "N/A"
        try:
            # Get market-wide data from Finviz (simplified approach)
            # In production, you'd use a dedicated market data API
            # For now, we'll calculate a proxy based on major indices
            spy_data = indices_data.get("SPY", {})
            qqq_data = indices_data.get("QQQ", {})
            dia_data = indices_data.get("DIA", {})
            
            # Count how many indices are up vs down
            up_count = 0
            down_count = 0
            for idx_data in [spy_data, qqq_data, dia_data]:
                change_pct = idx_data.get("change_pct", "")
                if change_pct and change_pct != "N/A":
                    if change_pct.startswith("+"):
                        up_count += 1
                    elif change_pct.startswith("-"):
                        down_count += 1
            
            if up_count + down_count > 0:
                adv_decl_ratio = f"{up_count}:{down_count}"
                adv_count = str(up_count)
                decl_count = str(down_count)
        except Exception:
            pass
        
        return {
            "session": session,
            "indices": indices_data,
            "vix": vix_data,
            "adv_decl": {
                "ratio": adv_decl_ratio,
                "advance": adv_count,
                "decline": decl_count
            },
            "timestamp": now.isoformat()
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch market overview: {exc}",
        ) from exc


# Fallback ticker list for watchlist when screener data is unavailable
WATCHLIST_FALLBACK_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "NFLX", "SMCI",
    "PLTR", "COIN", "MSTR", "GME", "AMC", "SPY", "QQQ", "DIA", "IWM", "VIX",
    "SOXL", "TQQQ", "SQQQ", "SPXL", "SPXS", "FNGU", "FNGD",
    "ARKK", "ARKQ", "ARKW", "ARKG", "ARKF", "BABA", "JD", "PDD", "NIO", "XPEV",
    "RIVN", "LCID", "F", "GM", "RBLX", "HOOD", "SOFI", "AFRM", "UPST", "PYPL"
]

@app.get("/watchlist")
def get_watchlist(limit: Optional[int] = 20) -> dict:
    """
    Get smart watchlist - automatically filtered stocks worth watching.
    Criteria for inclusion:
    - Volume > 2x average
    - Recent news (24h)
    - Price change > 3%
    - High volatility
    """
    try:
        # Try to get stocks from Finviz screener export (full market scan)
        # If not available, fall back to predefined list
        export_url = os.getenv("FINVIZ_EXPORT_URL")
        candidate_tickers = []
        
        if export_url:
            try:
                # Get full market data from Finviz screener
                response = requests.get(export_url, timeout=15)
                response.raise_for_status()
                reader = csv.DictReader(io.StringIO(response.text))
                all_stocks = list(reader)
                
                # Extract tickers from screener data (limit to first 200 for performance)
                for stock in all_stocks[:200]:
                    ticker = stock.get("Ticker", "").strip()
                    if ticker and len(ticker) <= 5:  # Valid ticker format
                        candidate_tickers.append(ticker)
                
                print(f"Using screener data: {len(candidate_tickers)} tickers found")
            except Exception as e:
                print(f"Failed to fetch screener data: {e}, using fallback list")
                # Fall back to predefined list if screener fails
                candidate_tickers = WATCHLIST_FALLBACK_TICKERS.copy()
        else:
            # No FINVIZ_EXPORT_URL configured, use predefined list
            candidate_tickers = WATCHLIST_FALLBACK_TICKERS.copy()
            print(f"Using predefined list: {len(candidate_tickers)} tickers")
        
        watchlist_items = []
        now = datetime.now()
        
        # Analyze each stock for watchlist criteria
        # Limit processing to avoid timeout (process up to 100 stocks or until we have enough results)
        max_to_process = min(100, len(candidate_tickers))
        for ticker in candidate_tickers[:max_to_process]:
            # Skip if we already have enough items
            if len(watchlist_items) >= limit:
                break
            
            try:
                # Get detailed quote data
                quote = finvizfinance(ticker)
                quote_data = quote.ticker_fundament()
                
                # Get news (may fail, so make it optional)
                news_raw = None
                news_count = 0
                try:
                    news_raw = quote.ticker_news()
                except Exception:
                    pass  # News is optional
                
                # Calculate score and reasons
                score = 0
                reasons = []
                
                # 1. Check price change
                change_pct_str = quote_data.get("Change %", "0%")
                try:
                    change_pct = float(change_pct_str.replace("%", "").replace("+", ""))
                    if abs(change_pct) > 3:
                        score += 2
                        reasons.append(f"价格变化 {change_pct_str}")
                except:
                    pass
                
                # 2. Check volume (if available)
                volume_str = quote_data.get("Volume", "")
                avg_volume_str = quote_data.get("Avg Volume", "")
                volume_ratio = 0.0
                try:
                    if volume_str and avg_volume_str:
                        volume = float(str(volume_str).replace(",", ""))
                        avg_volume = float(str(avg_volume_str).replace(",", ""))
                        if avg_volume > 0:
                            volume_ratio = volume / avg_volume
                            if volume_ratio > 2:
                                score += 3
                                reasons.append("成交量异常")
                except:
                    pass
                
                # 3. Check recent news (last 24 hours) - optional
                last_catalyst_time = None
                event_types = []
                if news_raw is not None:
                    try:
                        if hasattr(news_raw, "to_dict"):
                            news_list = news_raw.to_dict(orient="records")
                        else:
                            news_list = news_raw if isinstance(news_raw, list) else []
                        
                        # Parse news dates and categorize events
                        # datetime and timedelta are already imported at the top of the file
                        # Use the outer scope 'now' variable or create a new one for news parsing
                        news_now = datetime.now()
                        one_day_ago = news_now - timedelta(days=1)
                        
                        for news_item in news_list[:20]:  # Check more news items
                            if isinstance(news_item, dict):
                                news_date_str = news_item.get("Date", "") or news_item.get("date", "")
                                news_title = news_item.get("Title", "") or news_item.get("title", "") or ""
                                
                                # Count news in last 24h
                                if news_date_str:
                                    try:
                                        # Try to parse date (format may vary)
                                        if 'T' in news_date_str or ' ' in news_date_str:
                                            news_date = datetime.fromisoformat(news_date_str.replace('Z', '+00:00').replace(' ', 'T'))
                                        else:
                                            # Try other formats
                                            news_date = datetime.strptime(news_date_str, "%Y-%m-%d")
                                        
                                        if news_date >= one_day_ago:
                                            news_count += 1
                                            # Track most recent catalyst time
                                            if last_catalyst_time is None or news_date > last_catalyst_time:
                                                last_catalyst_time = news_date
                                            
                                            # Simple AI-like event classification based on keywords
                                            title_lower = news_title.lower()
                                            if any(word in title_lower for word in ['earnings', '财报', 'q1', 'q2', 'q3', 'q4', 'results']):
                                                if 'earnings' not in event_types:
                                                    event_types.append('earnings')
                                            elif any(word in title_lower for word in ['fda', 'approval', '批准', 'approve']):
                                                if 'fda' not in event_types:
                                                    event_types.append('fda')
                                            elif any(word in title_lower for word in ['merger', 'acquisition', '收购', '并购', 'm&a']):
                                                if 'm&a' not in event_types:
                                                    event_types.append('m&a')
                                            elif any(word in title_lower for word in ['partnership', '合作', 'deal', 'agreement']):
                                                if 'partnership' not in event_types:
                                                    event_types.append('partnership')
                                            elif any(word in title_lower for word in ['lawsuit', '诉讼', 'legal', 'court']):
                                                if 'legal' not in event_types:
                                                    event_types.append('legal')
                                            elif any(word in title_lower for word in ['upgrade', 'downgrade', 'rating', '评级', 'upgrade']):
                                                if 'rating' not in event_types:
                                                    event_types.append('rating')
                                    except:
                                        # If date parsing fails, still count it
                                        news_count += 1
                                        if last_catalyst_time is None:
                                            last_catalyst_time = news_now  # Use current time as fallback
                                else:
                                    # No date, but has title - count it
                                    news_count += 1
                        
                        if news_count >= 2:
                            score += 2
                            reasons.append(f"📰{news_count}条新闻")
                    except Exception:
                        pass  # News check failed, continue
                
                # 4. Check volatility (if available)
                volatility_str = quote_data.get("Volatility", "")
                try:
                    if volatility_str:
                        volatility = float(str(volatility_str).replace("%", ""))
                        if volatility > 30:
                            score += 1
                            reasons.append("高波动")
                except:
                    pass
                
                # Only include if score >= 2 (lower threshold to get more results)
                # Score >= 2 means at least one criterion is met
                if score >= 2:
                    price = quote_data.get("Price", "N/A")
                    change = quote_data.get("Change", "0")
                    change_pct = quote_data.get("Change %", "0%")
                    
                    # Risk assessment - automatically generate risk flags
                    risk_flags = []
                    risk_level = "low"
                    
                    # 1. 高 IV (High Implied Volatility)
                    volatility_str = quote_data.get("Volatility", "")
                    try:
                        if volatility_str:
                            volatility = float(str(volatility_str).replace("%", ""))
                            if volatility > 40:
                                risk_flags.append("高IV")
                                risk_level = "high" if risk_level != "high" else "high"
                            elif volatility > 30:
                                risk_flags.append("高IV")
                                risk_level = "medium" if risk_level == "low" else risk_level
                    except:
                        pass
                    
                    # 2. 临近财报 (Earnings approaching)
                    earnings_date_str = quote_data.get("Earnings", "") or quote_data.get("Earnings Date", "")
                    if earnings_date_str and earnings_date_str != "N/A":
                        try:
                            # Try to parse earnings date (format may vary: "Feb 05" or "2024-02-05")
                            # datetime is already imported at the top of the file
                            current_date = datetime.now()
                            
                            # Try different date formats
                            earnings_date = None
                            for fmt in ["%b %d", "%B %d", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"]:
                                try:
                                    earnings_date = datetime.strptime(earnings_date_str.strip(), fmt)
                                    # If year is not specified, assume current year
                                    if earnings_date.year == 1900 or earnings_date.year < 2000:
                                        earnings_date = earnings_date.replace(year=current_date.year)
                                    break
                                except:
                                    continue
                            
                            if earnings_date:
                                days_until_earnings = (earnings_date - current_date).days
                                if 0 <= days_until_earnings <= 7:
                                    risk_flags.append("临近财报")
                                    risk_level = "high" if risk_level != "high" else "high"
                                elif 8 <= days_until_earnings <= 14:
                                    risk_flags.append("临近财报")
                                    risk_level = "medium" if risk_level == "low" else risk_level
                        except:
                            pass
                    
                    # 3. 异常放量 (Abnormal volume - already detected, but add as risk flag)
                    if volume_ratio > 3:
                        risk_flags.append("异常放量")
                        risk_level = "high" if risk_level != "high" else "high"
                    elif volume_ratio > 2:
                        risk_flags.append("异常放量")
                        risk_level = "medium" if risk_level == "low" else risk_level
                    
                    # 4. 新闻不确定性高 (High news uncertainty)
                    # Check for negative keywords in news titles
                    news_uncertainty_score = 0
                    if news_raw is not None:
                        try:
                            if hasattr(news_raw, "to_dict"):
                                news_list = news_raw.to_dict(orient="records")
                            else:
                                news_list = news_raw if isinstance(news_raw, list) else []
                            
                            uncertainty_keywords = [
                                'lawsuit', '诉讼', 'investigation', '调查', 'warning', '警告',
                                'decline', '下降', 'loss', '亏损', 'cut', '削减', 'delay', '延迟',
                                'uncertain', '不确定', 'risk', '风险', 'concern', '担忧',
                                'volatility', '波动', 'crash', '暴跌', 'plunge', '急跌'
                            ]
                            
                            for news_item in news_list[:10]:
                                if isinstance(news_item, dict):
                                    news_title = (news_item.get("Title", "") or news_item.get("title", "") or "").lower()
                                    if any(keyword in news_title for keyword in uncertainty_keywords):
                                        news_uncertainty_score += 1
                            
                            if news_uncertainty_score >= 3:
                                risk_flags.append("新闻不确定性高")
                                risk_level = "high" if risk_level != "high" else "high"
                            elif news_uncertainty_score >= 2:
                                risk_flags.append("新闻不确定性高")
                                risk_level = "medium" if risk_level == "low" else risk_level
                        except:
                            pass
                    
                    # Determine risk flag icon based on risk level and flags
                    risk_flag = ""
                    if risk_level == "high":
                        risk_flag = "🔴"
                    elif risk_level == "medium":
                        risk_flag = "⚠️"
                    elif risk_flags:
                        risk_flag = "⚠️"  # Show warning even if low risk but has flags
                    
                    # Format volume ratio
                    volume_ratio_str = f"{volume_ratio:.2f}x" if volume_ratio > 0 else "N/A"
                    
                    # Format event types
                    event_type_str = ", ".join(event_types[:3]) if event_types else "None"
                    
                    # Format last catalyst time
                    last_catalyst_str = "N/A"
                    if last_catalyst_time:
                        try:
                            time_diff = now - last_catalyst_time
                            if time_diff.total_seconds() < 3600:
                                mins = int(time_diff.total_seconds() / 60)
                                last_catalyst_str = f"{mins}m ago"
                            elif time_diff.total_seconds() < 86400:
                                hours = int(time_diff.total_seconds() / 3600)
                                last_catalyst_str = f"{hours}h ago"
                            else:
                                days = int(time_diff.total_seconds() / 86400)
                                last_catalyst_str = f"{days}d ago"
                        except:
                            last_catalyst_str = "Recent"
                    
                    watchlist_items.append({
                        "ticker": ticker,
                        "price": price,
                        "change": change,
                        "change_pct": change_pct,
                        "volume_alert": "🔥" if score >= 3 and "成交量" in " ".join(reasons) else "",
                        "volume_ratio": volume_ratio_str,  # NEW: Volume/AvgVolume ratio
                        "news_count": news_count,  # Already exists, but ensure it's 24h count
                        "event_type": event_type_str,  # NEW: Event type (AI classification)
                        "risk_flag": risk_flag,  # Risk flag icon (🔴/⚠️)
                        "risk_level": risk_level,  # Risk level (low/medium/high)
                        "risk_flags": risk_flags,  # List of risk flags (高IV, 临近财报, 异常放量, 新闻不确定性高)
                        "last_catalyst_time": last_catalyst_str,  # NEW: Last catalyst time
                        "reasons": reasons,
                        "score": score,
                        "last_update": now.isoformat()
                    })
            
            except Exception as e:
                # Log error but continue processing other stocks
                print(f"Error processing {ticker}: {str(e)}")
                continue  # Skip stocks that fail to fetch
        
        # Sort by score (highest first) and limit
        watchlist_items.sort(key=lambda x: x["score"], reverse=True)
        watchlist_items = watchlist_items[:limit]
        
        return {
            "count": len(watchlist_items),
            "items": watchlist_items,
            "timestamp": now.isoformat()
        }
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as exc:
        import traceback
        error_detail = str(exc)
        print(f"Watchlist error: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=502,
            detail=f"Failed to generate watchlist: {error_detail}",
        ) from exc


@app.get("/quote/{ticker}")
def get_quote(ticker: str) -> dict:
    """
    Fetch quote data for the given ticker from Finviz.
    """
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    try:
        quote = finvizfinance(ticker.upper())
        quote_data = quote.ticker_fundament()
        news_raw = quote.ticker_news()
        
        # Get chart URL - construct Finviz URL directly to avoid library download
        # This is a real-time chart URL, no local download needed
        chart_url = f"https://finviz.com/chart.ashx?t={ticker.upper()}&ty=c&ta=1&p=d"
        news_records = (
            news_raw.to_dict(orient="records")
            if hasattr(news_raw, "to_dict")
            else news_raw
        )
        # Normalize keys to lowercase for the Svelte UI (expects date/title/link/source).
        news = [
            {k.lower(): v for k, v in row.items()} if isinstance(row, dict) else row
            for row in news_records or []
        ]
    except Exception as exc:  # pragma: no cover - upstream/network errors
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch data from Finviz: {exc}",
        ) from exc

    return {
        "ticker": ticker.upper(),
        "quote": quote_data,
        "news": news,
        "chart_url": chart_url,
    }


@app.get("/screener")
def get_screener(limit: Optional[int] = 100) -> dict:
    """
    Fetch screener/export data using a Finviz export URL stored in FINVIZ_EXPORT_URL.
    The export URL should already include any auth token and column selection.
    """
    export_url = os.getenv("FINVIZ_EXPORT_URL")
    if not export_url:
        raise HTTPException(
            status_code=500,
            detail="FINVIZ_EXPORT_URL is not configured on the server",
        )

    safe_limit = max(limit or 0, 0)

    try:
        response = requests.get(export_url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - network dependent
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch screener export: {exc}",
        ) from exc

    reader = csv.DictReader(io.StringIO(response.text))
    rows = list(reader)
    if safe_limit:
        rows = rows[:safe_limit]

    return {"count": len(rows), "rows": rows}


@app.get("/news/summary")
def get_news_summary(url: str = Query(..., description="News article URL to summarize")) -> dict:
    """
    Fetch and summarize a news article from the given URL.
    Handles both absolute URLs and relative URLs (prepends https://finviz.com).
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Handle relative URLs (e.g., /news/266645/...)
    if url.startswith("/"):
        url = f"https://finviz.com{url}"

    try:
        article = Article(url, language="en")
        article.download()
        article.parse()
        
        # Generate a better summary using extractive summarization
        try:
            article.nlp()
            raw_summary = article.summary
            
            # If we have article text, use improved extractive summarization
            if article.text and len(article.text) > 200:
                summary = create_better_summary(article.text, max_sentences=5)
            else:
                summary = raw_summary
        except Exception:
            # If NLP fails, try to create summary from article text
            if article.text and len(article.text) > 200:
                try:
                    summary = create_better_summary(article.text, max_sentences=5)
                except Exception:
                    summary = article.text[:500] + "..." if len(article.text) > 500 else article.text
            else:
                summary = article.text[:500] + "..." if len(article.text) > 500 else article.text

        # Limit summary to 500 words maximum for better conciseness, ensuring it ends at a complete sentence
        summary_en = summary or "Unable to generate summary for this article."
        if summary_en and summary_en != "Unable to generate summary for this article.":
            words = summary_en.split()
            if len(words) > 500:
                # Take first 500 words and join them
                truncated = " ".join(words[:500])
                # Find the last complete sentence ending (. ! or ?) within the truncated text
                # Search backwards from the end to find the last sentence boundary
                sentence_endings = list(re.finditer(r'[.!?]\s+', truncated))
                if sentence_endings:
                    # Use the last sentence ending found
                    last_ending = sentence_endings[-1]
                    summary_en = truncated[:last_ending.end()].rstrip() + "..."
                else:
                    # If no sentence ending found, just truncate and add ellipsis
                    summary_en = truncated + "..."
        
        # Translate to Chinese (Simplified)
        summary_zh = summary_en
        try:
            translator = GoogleTranslator(source='en', target='zh-CN')
            summary_zh = translator.translate(summary_en)
        except Exception as trans_exc:
            # If translation fails, use English as fallback
            print(f"Translation error: {trans_exc}")
            summary_zh = summary_en
        
        return {
            "url": url,
            "title": article.title or "No title available",
            "summary_en": summary_en,
            "summary_zh": summary_zh,
            "authors": article.authors,
            "publish_date": article.publish_date.isoformat() if article.publish_date else None,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch or summarize article: {str(exc)}",
        ) from exc


def cleanup_chart_files():
    """Clean up chart image files downloaded by finvizfinance library"""
    try:
        # Get the backend directory
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Find all .jpg files in backend directory
        chart_files = glob.glob(os.path.join(backend_dir, "*.jpg"))
        for chart_file in chart_files:
            try:
                os.remove(chart_file)
            except Exception:
                pass  # Ignore errors when deleting
    except Exception:
        pass  # Ignore cleanup errors


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

