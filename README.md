# Finviz Trading Dashboard

A full-stack trading dashboard that displays Finviz stock data with bilingual news summaries (English/Chinese).

## Features

- 📈 Real-time stock quotes and data from Finviz
- 📊 Daily stock charts
- 📰 News articles with AI-generated summaries
- 🌐 Bilingual summaries (English/Chinese)
- 🔍 Stock screener integration

## Tech Stack

- **Backend**: Python, FastAPI
- **Frontend**: SvelteKit, TypeScript
- **APIs**: Finviz (web scraping), Google Translate (via deep-translator)

## Setup

### Backend

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
FINVIZ_EXPORT_URL="your_finviz_export_url_here"
```

5. Run backend:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env` file:
```bash
VITE_API_BASE=http://localhost:8000
```

4. Run frontend:
```bash
npm run dev -- --host
```

## Usage

1. Start both backend and frontend servers
2. Open browser to `http://localhost:5173` (or the URL shown in terminal)
3. Enter a stock ticker (e.g., AAPL) and click "Get quote"
4. View news articles and click "Show summary" to see bilingual summaries

## Project Structure

```
trading/
├── backend/
│   ├── app/
│   │   └── main.py       # FastAPI backend
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   └── routes/
│   │       └── +page.svelte  # Main Svelte component
│   └── package.json
└── README.md

```

## License

MIT

