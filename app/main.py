import asyncio, json
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .db import engine, Base, SessionLocal
from .models import Article, UserProfile
from .schemas import ArticleOut, UserProfileIn
from .fetch_news import newsapi_fetch, gdelt_fetch
from .summarize import llm_summary
from .embeddings import embed_text, dumps_embedding
from .reco import recommend_for

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
    items = newsapi_fetch() or gdelt_fetch(query=query, maxrecords=80)
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
