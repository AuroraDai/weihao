import csv
import io
import os
import re
from typing import Optional

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
        chart_url = quote.ticker_charts()
        news_raw = quote.ticker_news()
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

