import asyncio, json, os
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
from .db import engine, Base, SessionLocal
from .models import Article, UserProfile
from .schemas import ArticleOut, UserProfileIn
from .fetch_news import newsapi_fetch, gdelt_fetch
from .summarize import llm_summary
from .embeddings import embed_text, dumps_embedding
from .reco import recommend_for

# Load environment variables
load_dotenv()

app = FastAPI(title="News Aggregator")

async def get_db():
    async with SessionLocal() as session:
        yield session

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/ingest", response_model=int)
async def ingest_news(session: AsyncSession = Depends(get_db), query: str = "technology"):
    # Try NewsAPI first, then fallback to GDELT
    items = newsapi_fetch() or gdelt_fetch(query=query, maxrecords=30)
    count = 0
    for it in items:
        if not it["url"] or not it["title"]:
            continue
        exists = await session.execute(select(Article).where(Article.url == it["url"]))
        if exists.scalar_one_or_none(): 
            continue
        text = " ".join(filter(None, [it["title"], it["description"], it["content"]]))
        summary = llm_summary(text) if text else ""
        emb = embed_text(text) if text else []
        a = Article(
            url=it["url"], title=it["title"], source=it["source"], author=it["author"],
            published_at=it["published_at"], description=it["description"], content=it["content"],
            summary=summary, embedding=dumps_embedding(emb) if emb else None
        )
        session.add(a); count += 1
    await session.commit()
    return count

@app.post("/ingest-for-interests", response_model=dict)
async def ingest_for_interests(interests: List[str], session: AsyncSession = Depends(get_db)):
    """Fetch articles specifically tailored to user interests"""
    from .fetch_news import newsapi_fetch, gdelt_fetch
    
    # Map interests to NewsAPI categories
    category_map = {
        "sports": "sports",
        "football": "sports", 
        "basketball": "sports",
        "soccer": "sports",
        "baseball": "sports",
        "technology": "technology",
        "ai": "technology",
        "tech": "technology",
        "business": "business",
        "finance": "business",
        "economy": "business",
        "entertainment": "entertainment",
        "health": "health",
        "science": "science"
    }
    
    # Get unique categories for these interests
    categories = list(set([category_map.get(interest.lower(), "general") for interest in interests]))
    
    all_items = []
    for category in categories:
        try:
            # Fetch more articles for each category - much more for sports
            if category == "sports":
                items = newsapi_fetch(category=category, page_size=100) or gdelt_fetch(query=category, maxrecords=50)
            else:
                items = newsapi_fetch(category=category, page_size=30) or gdelt_fetch(query=category, maxrecords=20)
            all_items.extend(items)
        except Exception as e:
            print(f"Error fetching {category}: {e}")
            continue
    
    # Remove duplicates and add to database
    seen_urls = set()
    count = 0
    for it in all_items:
        if not it["url"] or not it["title"] or it["url"] in seen_urls:
            continue
        seen_urls.add(it["url"])
        
        # Check if already exists
        exists = await session.execute(select(Article).where(Article.url == it["url"]))
        if exists.scalar_one_or_none(): 
            continue
            
        text = " ".join(filter(None, [it["title"], it["description"], it["content"]]))
        summary = llm_summary(text) if text else ""
        emb = embed_text(text) if text else []
        a = Article(
            url=it["url"], title=it["title"], source=it["source"], author=it["author"],
            published_at=it["published_at"], description=it["description"], content=it["content"],
            summary=summary, embedding=dumps_embedding(emb) if emb else None
        )
        session.add(a)
        count += 1
    
    await session.commit()
    return {"ingested": count, "categories": categories}

@app.post("/profile", response_model=dict)
async def set_profile(p: UserProfileIn, session: AsyncSession = Depends(get_db)):
    exists = await session.execute(select(UserProfile).where(UserProfile.user_id == p.user_id))
    row = exists.scalar_one_or_none()
    interests = ",".join(p.interests)
    if row:
        row.interests = interests
    else:
        row = UserProfile(user_id=p.user_id, interests=interests)
        session.add(row)
    await session.commit()
    return {"ok": True}

@app.get("/recommendations", response_model=List[ArticleOut])
async def get_recs(user_id: str, k: int = 10, session: AsyncSession = Depends(get_db)):
    recs = await recommend_for(session, user_id=user_id, k=k)
    return recs

@app.get("/test-newsapi")
async def test_newsapi():
    """Test if NewsAPI is working"""
    from .fetch_news import newsapi_fetch
    articles = newsapi_fetch(category="sports", page_size=5)
    return {"articles_found": len(articles), "sample_titles": [a["title"] for a in articles[:3]]}

@app.post("/daily-update", response_model=dict)
async def daily_update(session: AsyncSession = Depends(get_db)):
    """Fetch fresh content for daily highlights - focuses on recent articles from last 36 hours"""
    from .fetch_news import newsapi_fetch, gdelt_fetch
    from datetime import datetime, timedelta
    
    # Get diverse recent content
    categories = ["technology", "sports", "business", "entertainment", "health"]
    all_items = []
    
    for category in categories:
        try:
            # Fetch recent articles with higher page size for better selection
            items = newsapi_fetch(category=category, page_size=20) or gdelt_fetch(query=category, maxrecords=15)
            all_items.extend(items)
        except Exception as e:
            print(f"Error fetching {category}: {e}")
            continue
    
    # Remove duplicates and add to database - only articles from last 36 hours
    seen_urls = set()
    count = 0
    cutoff_time = datetime.now() - timedelta(hours=36)
    
    for it in all_items:
        if not it["url"] or not it["title"] or it["url"] in seen_urls:
            continue
        seen_urls.add(it["url"])
        
        # Check if already exists
        exists = await session.execute(select(Article).where(Article.url == it["url"]))
        if exists.scalar_one_or_none(): 
            continue
        
        # Only add articles from the last 7 days (with timezone fix)
        if it["published_at"]:
            try:
                from datetime import datetime
                pub_time = datetime.fromisoformat(it["published_at"].replace('Z', '+00:00'))
                # Use 7 days for ingestion, 36 hours for display
                week_cutoff = datetime.now() - timedelta(days=7)
                # Make week_cutoff timezone-aware for comparison
                week_cutoff_aware = week_cutoff.replace(tzinfo=pub_time.tzinfo)
                if pub_time < week_cutoff_aware:
                    continue  # Skip articles older than 7 days
            except:
                # If we can't parse the date, skip it to be safe
                continue
            
        text = " ".join(filter(None, [it["title"], it["description"], it["content"]]))
        summary = llm_summary(text) if text else ""
        emb = embed_text(text) if text else []
        a = Article(
            url=it["url"], title=it["title"], source=it["source"], author=it["author"],
            published_at=it["published_at"], description=it["description"], content=it["content"],
            summary=summary, embedding=dumps_embedding(emb) if emb else None
        )
        session.add(a)
        count += 1
    
    await session.commit()
    return {"ingested": count, "message": "Daily update completed"}
