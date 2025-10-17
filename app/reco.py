import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Article, UserProfile
from .embeddings import loads_embedding, embed_text

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a)*np.linalg.norm(b) + 1e-9)
    return float(np.dot(a,b) / denom)

async def recommend_for(session: AsyncSession, user_id: str, k: int = 10):
    # Get user profile
    res = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    prof = res.scalar_one_or_none()
    
    if not prof or not prof.interests:
        # No profile - return recent articles
        res = await session.execute(select(Article).order_by(Article.created_at.desc()))
        arts = res.scalars().all()
        return arts[:k]
    
    interests = [s.strip().lower() for s in prof.interests.split(",") if s.strip()]
    if not interests:
        res = await session.execute(select(Article).order_by(Article.created_at.desc()))
        arts = res.scalars().all()
        return arts[:k]
    
    # Get all articles
    res = await session.execute(select(Article))
    arts = res.scalars().all()
    
    # Simple keyword-based scoring (more reliable than hash embeddings)
    scored = []
    for article in arts:
        score = 0.0
        text_to_search = f"{article.title} {article.description} {article.content}".lower()
        
        # Direct keyword matching
        for interest in interests:
            if interest in text_to_search:
                score += 1.0
        
        # Sports-specific matching
        if any(sport in interests for sport in ["sports", "football", "basketball", "soccer", "baseball"]):
            sports_keywords = ["nfl", "nba", "nhl", "mlb", "soccer", "football", "basketball", "baseball", 
                             "panthers", "lakers", "warriors", "cowboys", "patriots", "game", "team", "player"]
            for keyword in sports_keywords:
                if keyword in text_to_search:
                    score += 0.5
        
        # Tech-specific matching
        if any(tech in interests for tech in ["technology", "ai", "tech", "apple", "google", "microsoft"]):
            tech_keywords = ["ai", "artificial intelligence", "apple", "google", "microsoft", "tech", 
                           "software", "computer", "digital", "innovation", "startup"]
            for keyword in tech_keywords:
                if keyword in text_to_search:
                    score += 0.5
        
        # Business-specific matching
        if any(biz in interests for biz in ["business", "finance", "economy", "market", "stock"]):
            biz_keywords = ["business", "finance", "economy", "market", "stock", "investment", 
                          "company", "corporate", "financial", "trading"]
            for keyword in biz_keywords:
                if keyword in text_to_search:
                    score += 0.5
        
        scored.append((score, article))
    
    # Sort by score (highest first), then by recency (most recent first)
    scored.sort(key=lambda x: (x[0], x[1].created_at), reverse=True)
    
    # For daily highlights, prioritize recent articles even if they have lower scores
    # Get articles from the last 36 hours
    from datetime import datetime, timedelta
    recent_cutoff = datetime.now() - timedelta(hours=36)
    
    recent_articles = []
    older_articles = []
    
    for score, article in scored:
        # Must have a published_at date to be considered
        if not article.published_at:
            continue
            
        # Check published_at timestamp - this is the primary filter
        try:
            from datetime import datetime
            pub_time = datetime.fromisoformat(article.published_at.replace('Z', '+00:00'))
            # Make recent_cutoff timezone-aware for comparison
            recent_cutoff_aware = recent_cutoff.replace(tzinfo=pub_time.tzinfo)
            if pub_time >= recent_cutoff_aware:
                recent_articles.append((score, article))
            else:
                # Debug: print articles being filtered out
                print(f"Filtering out old article: {article.title[:50]}... from {article.published_at}")
        except Exception as e:
            # If we can't parse the date, skip the article to be safe
            print(f"Error parsing date {article.published_at}: {e}")
            continue
    
    # Only return articles from the last 36 hours
    result = []
    for score, article in recent_articles[:k]:
        result.append(article)
    
    return result
