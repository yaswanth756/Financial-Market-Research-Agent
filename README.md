# 🧠 MarketMind — Financial Market Research Agent

> An AI-powered financial research assistant built with **RAG (Retrieval-Augmented Generation)**, **LangGraph**, and **Gemini 2.5 Flash** that delivers real-time market analysis, stock research, and intelligent portfolio insights.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔀 **10 Smart Query Routes** | Automatic intent classification — stock prices, fundamentals, technicals, comparisons, news, recommendations, portfolio, discovery, general market, and conversational |
| 🔍 **Hybrid Search (BM25 + Vector)** | Combines keyword search (BM25) with semantic search (ChromaDB/Qdrant) using Reciprocal Rank Fusion |
| 💡 **HyDE (Hypothetical Document Embeddings)** | Generates hypothetical ideal answers to improve retrieval accuracy |
| 🏆 **Cross-Encoder Reranking** | Uses `ms-marco-MiniLM-L-6-v2` to rerank search results for precision |
| 📰 **Live News Ingestion** | Streams financial news from RSS feeds (FT, Economist, MoneyControl, Economic Times) into Qdrant vector database |
| 🧠 **Financial Memory** | Persistent memory backed by Qdrant — remembers user preferences, past research, and conversation history |
| 📊 **Market Tools Suite** | 8 professional tools — live prices, price history, fundamentals, technicals, analyst recommendations, stock comparison, portfolio snapshots, and news-vs-price validation |
| 🔄 **LangGraph Multi-Step Pipeline** | 6-node research graph: Router → Clarifier → Data Gatherer → Analyzer → Memo Writer → Memory Saver |
| 📈 **Confidence Scoring** | Transparent confidence levels (HIGH/MEDIUM/LOW) with detailed reasoning |
| 🌐 **Contradiction Detection** | Cross-references news sentiment with actual price action |
| 💬 **Follow-Up Detection** | Maintains conversational context across multi-turn interactions |
| 🌅 **Morning Briefing** | Auto-generated daily market summary for your portfolio |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                         │
│         Chat Interface · Sidebar · Ticker · Settings            │
└───────────────────────────┬──────────────────────────────────────┘
                            │ REST API
┌───────────────────────────▼──────────────────────────────────────┐
│                     Flask API (api.py)                           │
│                    14 REST Endpoints                             │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│              LangGraph Research Agent (research_agent.py)        │
│                                                                  │
│  ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Router  │→ │ Clarifier │→ │ Gatherer │→ │    Analyzer      │ │
│  └─────────┘  └───────────┘  └──────────┘  │  (Gemini 2.5)    │ │
│                                             └────────┬─────────┘ │
│  ┌──────────────┐  ┌─────────────┐                   │          │
│  │ Memory Saver │← │ Memo Writer │←──────────────────┘          │
│  └──────────────┘  └─────────────┘                              │
└──────────┬────────────────┬──────────────────┬──────────────────┘
           │                │                  │
    ┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼───────┐
    │Market Tools │  │Hybrid Search│  │Financial Memory│
    │(yfinance)   │  │(BM25+Vector)│  │   (Qdrant)     │
    └─────────────┘  └──────┬──────┘  └───────────────┘
                            │
                  ┌─────────▼─────────┐
                  │  Smart Retrieval   │
                  │  HyDE + Reranker   │
                  └─────────┬─────────┘
                            │
                  ┌─────────▼─────────┐
                  │    Qdrant Cloud    │
                  │  (Vector Database) │
                  └───────────────────┘
```

---

## 🗂️ Project Structure

```
RAG2/
├── api.py                  # Flask REST API — 14 endpoints
├── research_agent.py       # LangGraph multi-step research pipeline
├── analyst.py              # Gemini-powered analyst with 10 query routes
├── market_tools.py         # 8 financial tools (prices, fundamentals, technicals)
├── hybrid_search.py        # BM25 + Vector hybrid search with RRF
├── smart_retrieval.py      # HyDE + Cross-Encoder reranking
├── news_stream.py          # RSS financial news ingestion into Qdrant
├── financial_memory.py     # Persistent memory (preferences, cache, history)
├── user_config.py          # Portfolio & Qdrant configuration
├── portfolio.json          # User portfolio data
├── .env.example            # Environment variable template
│
├── frontend/               # Next.js 16 + React 19 + Tailwind CSS 4
│   ├── app/
│   │   ├── page.tsx             # Main page with session management
│   │   ├── layout.tsx           # Root layout
│   │   ├── globals.css          # Global styles
│   │   └── components/
│   │       ├── ChatInterface.tsx # Chat UI with markdown rendering
│   │       ├── Sidebar.tsx      # Session sidebar navigation
│   │       ├── SettingsModal.tsx # User settings & portfolio config
│   │       └── Ticker.tsx       # Live market ticker
│   └── package.json
│
└── market_mind_db/         # Local vector DB storage
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))
- **Qdrant Cloud** account (free tier available at [qdrant.io](https://qdrant.io/))

### 1. Clone the Repository

```bash
git clone https://github.com/yaswanth756/Financial-Market-Research-Agent.git
cd Financial-Market-Research-Agent
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
GEMINI_API_KEY=your_gemini_api_key_here
QDRANT_URL=your_qdrant_cloud_url_here
QDRANT_API_KEY=your_qdrant_api_key_here
```

### 3. Install Python Dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install flask flask-cors python-dotenv langgraph google-genai \
            yfinance feedparser rank_bm25 sentence-transformers \
            langchain-qdrant qdrant-client duckduckgo-search \
            langchain-core requests httpx
```

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Start the News Stream (Optional)

```bash
python news_stream.py
```

> This ingests live financial news from RSS feeds into Qdrant. Run it in a separate terminal to keep the knowledge base fresh.

### 6. Start the Backend

```bash
python api.py
```

The API server runs on `http://localhost:5000`.

### 7. Start the Frontend

```bash
cd frontend
npm run dev
```

The frontend runs on `http://localhost:3000`.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check & system status |
| `POST` | `/api/analyze` | Main research endpoint (LangGraph pipeline) |
| `GET` | `/api/briefing` | Morning portfolio briefing |
| `GET` | `/api/portfolio` | Get current portfolio |
| `POST` | `/api/portfolio` | Update portfolio |
| `GET` | `/api/market-data` | Live market ticker data |
| `GET` | `/api/stock/<symbol>` | Quick stock price lookup |
| `GET` | `/api/fundamentals/<symbol>` | Stock fundamentals |
| `GET` | `/api/recommendations/<symbol>` | Analyst recommendations |
| `GET` | `/api/technicals/<symbol>` | Technical indicators (RSI, MACD, etc.) |
| `POST` | `/api/compare` | Compare multiple stocks |
| `GET` | `/api/preferences` | Get user preferences |
| `POST` | `/api/preferences` | Update user preferences |
| `GET` | `/api/suggest-next` | AI-powered next analysis suggestions |
| `GET` | `/api/history` | Conversation history |

### Example — Analyze a Stock

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the fundamentals of Reliance Industries?", "mode": "auto"}'
```

---

## 🧰 Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core backend language |
| **Flask** | REST API framework |
| **LangGraph** | Multi-step agent orchestration |
| **Google Gemini 2.5 Flash** | LLM for analysis & synthesis |
| **Qdrant Cloud** | Vector database for semantic search & memory |
| **Sentence Transformers** | Local embeddings (`all-MiniLM-L6-v2`) |
| **Cross-Encoder** | Reranking (`ms-marco-MiniLM-L-6-v2`) |
| **yFinance** | Real-time market data |
| **BM25 (rank_bm25)** | Keyword-based search |
| **DuckDuckGo Search** | Web search fallback |
| **feedparser** | RSS news ingestion |

### Frontend
| Technology | Purpose |
|---|---|
| **Next.js 16** | React framework |
| **React 19** | UI library |
| **Tailwind CSS 4** | Styling |
| **TypeScript** | Type safety |
| **react-markdown** | Markdown rendering in chat |
| **Lucide React** | Icon library |

---

## 🔬 RAG Pipeline Deep Dive

### How a Query Flows Through the System

1. **Router Node** — Classifies the query into one of 10 routes using pattern matching and keyword detection. Detects follow-ups and resolves stock symbols.

2. **Clarifier Node** — Checks if additional context is needed (e.g., time horizon for investment queries). Auto-fills from financial memory when possible.

3. **Data Gatherer Node** — Fetches data from multiple sources in parallel:
   - 📈 **Market Tools** — Live prices, fundamentals, technicals via yFinance
   - 🔍 **Hybrid Search** — BM25 + Vector search on Qdrant knowledge base
   - 💡 **HyDE** — Generates hypothetical documents for better semantic matching
   - 🌐 **Web Search** — DuckDuckGo fallback for real-time information
   - 🧠 **Financial Memory** — Past research and user preferences

4. **Analyzer Node** — Sends all gathered context to Gemini 2.5 Flash with a route-specific prompt template. Detects contradictions between sources.

5. **Memo Writer Node** — Formats the final report with metadata (route, confidence, sources count, symbols).

6. **Memory Saver Node** — Caches the research, saves conversation turn, and tracks interaction patterns for future suggestions.

### Confidence Scoring

| Level | Criteria |
|-------|----------|
| **🟢 HIGH** | ≥3 sources, live market data, no contradictions |
| **🟡 MEDIUM** | 2 sources or minor contradictions |
| **🔴 LOW** | Single source, no live data, or significant contradictions |

---

## 📊 Supported Markets

- 🇮🇳 **Indian Stocks (NSE)** — TCS, Infosys, Reliance, HDFC Bank, Zomato, etc.
- 🇺🇸 **US Stocks** — Apple, Google, Tesla, Microsoft, NVIDIA, etc.
- ₿ **Cryptocurrencies** — Bitcoin, Ethereum, Solana, Dogecoin, etc.
- 🏆 **Commodities** — Gold, Silver, Crude Oil, Natural Gas
- 📈 **Indices** — NIFTY 50, SENSEX

---

## 📝 License

This project is for educational and research purposes.

---

<p align="center">
  Built with ❤️ using RAG, LangGraph & Gemini 2.5
</p>
