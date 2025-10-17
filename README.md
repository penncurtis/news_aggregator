# Personalized News Aggregator

A local FastAPI + Streamlit app that fetches news (NewsAPI/GDELT), embeds with MiniLM, recommends by cosine similarity to a user interest profile, and summarizes articles (extractive fallback or OpenAI).

## Features

- **News Fetching**: Fetches news from NewsAPI and GDELT
- **AI Summarization**: Uses OpenAI GPT-4o-mini for article summarization
- **Personalized Recommendations**: Cosine similarity-based recommendations using embeddings
- **User Profiles**: Track user interests for personalized content
- **Modern UI**: Clean Streamlit interface for easy interaction

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create a `.env` file with your API keys:
   ```
   NEWSAPI_KEY=your_newsapi_key_here
   OPENAI_API_KEY=sk-your_openai_key_here
   ```

3. **Run the Backend**:
   ```bash
   uvicorn app.main:app --reload --port 8008
   ```

4. **Run the Frontend** (in a new terminal):
   ```bash
   streamlit run app_ui.py --server.port 8501
   ```

## Usage

1. **Ingest News**: Click "Ingest Latest" to fetch new articles
2. **Set Profile**: Enter your user ID and interests in the sidebar
3. **Get Recommendations**: View personalized news recommendations

## API Endpoints

- `POST /ingest` - Fetch and store new articles
- `POST /profile` - Set user interests
- `GET /recommendations?user_id=X&k=Y` - Get personalized recommendations

## Architecture

- **Backend**: FastAPI with SQLAlchemy (SQLite)
- **Frontend**: Streamlit
- **AI**: OpenAI GPT-4o-mini for summarization
- **Embeddings**: Hash-based embeddings (can be upgraded to sentence-transformers)
- **Database**: SQLite with async support
