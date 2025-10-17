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
    
    # Aggressive keyword-based scoring with comprehensive matching
    scored = []
    for article in arts:
        score = 0.0
        text_to_search = f"{article.title} {article.description} {article.content}".lower()
        
        # Direct keyword matching with higher weights
        for interest in interests:
            if interest in text_to_search:
                score += 3.0  # Much higher weight for direct matches
        
        # Comprehensive technology matching
        if any(tech in interests for tech in ["technology", "ai", "tech", "apple", "google", "microsoft", "computer", "software"]):
            tech_keywords = [
                "ai", "artificial intelligence", "machine learning", "neural network", "algorithm",
                "apple", "google", "microsoft", "amazon", "meta", "facebook", "tesla", "openai",
                "tech", "technology", "software", "computer", "digital", "innovation", "startup",
                "chip", "semiconductor", "cpu", "gpu", "processor", "intel", "nvidia", "amd",
                "smartphone", "iphone", "android", "app", "application", "programming", "code",
                "cybersecurity", "hacking", "data", "cloud", "server", "database", "internet",
                "automation", "robot", "drone", "electric", "battery", "solar", "renewable",
                "crypto", "bitcoin", "blockchain", "nft", "web3", "metaverse", "vr", "ar"
            ]
            for keyword in tech_keywords:
                if keyword in text_to_search:
                    score += 2.0  # High weight for tech keywords
        
        # Comprehensive sports matching
        if any(sport in interests for sport in ["sports", "football", "basketball", "soccer", "baseball", "tennis", "golf"]):
            sports_keywords = [
                "nfl", "nba", "nhl", "mlb", "nascar", "pga", "tennis", "golf", "soccer", "football", 
                "basketball", "baseball", "hockey", "racing", "olympics", "championship", "playoff",
                "panthers", "lakers", "warriors", "cowboys", "patriots", "yankees", "dodgers",
                "game", "team", "player", "coach", "season", "score", "win", "loss", "victory",
                "stadium", "arena", "field", "court", "track", "gym", "training", "fitness"
            ]
            for keyword in sports_keywords:
                if keyword in text_to_search:
                    score += 2.0  # High weight for sports keywords
        
        # Comprehensive business matching
        if any(biz in interests for biz in ["business", "finance", "economy", "market", "stock", "money", "investment"]):
            biz_keywords = [
                "business", "finance", "economy", "market", "stock", "investment", "trading",
                "company", "corporate", "financial", "bank", "banking", "loan", "credit",
                "revenue", "profit", "loss", "earnings", "quarterly", "ipo", "merger", "acquisition",
                "ceo", "executive", "board", "shareholder", "dividend", "portfolio", "fund",
                "startup", "venture", "capital", "funding", "valuation", "unicorn", "ipo"
            ]
            for keyword in biz_keywords:
                if keyword in text_to_search:
                    score += 2.0  # High weight for business keywords
        
        # Health and science matching
        if any(health in interests for health in ["health", "science", "medical", "medicine", "research"]):
            health_keywords = [
                "health", "medical", "medicine", "doctor", "hospital", "patient", "treatment",
                "research", "study", "clinical", "trial", "vaccine", "drug", "therapy",
                "cancer", "diabetes", "heart", "brain", "mental", "psychology", "therapy",
                "fitness", "exercise", "nutrition", "diet", "wellness", "lifestyle"
            ]
            for keyword in health_keywords:
                if keyword in text_to_search:
                    score += 2.0
        
        # Entertainment matching
        if any(ent in interests for ent in ["entertainment", "movie", "music", "celebrity", "hollywood"]):
            ent_keywords = [
                "movie", "film", "cinema", "hollywood", "actor", "actress", "director", "producer",
                "music", "song", "album", "artist", "singer", "band", "concert", "tour",
                "celebrity", "famous", "star", "award", "oscar", "grammy", "emmy", "golden globe",
                "netflix", "disney", "hbo", "streaming", "tv", "television", "series", "show"
            ]
            for keyword in ent_keywords:
                if keyword in text_to_search:
                    score += 2.0
        
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
    
    # If we don't have enough relevant articles, add some recent ones regardless of score
    if len(result) < k:
        print(f"Only found {len(result)} relevant articles, adding recent ones...")
        # Get recent articles that weren't already included
        already_included = {article.id for article in result}
        for score, article in recent_articles:
            if article.id not in already_included and len(result) < k:
                result.append(article)
    
    # Final fallback: if still not enough articles, get any recent articles
    if len(result) < k:
        print(f"Still only {len(result)} articles, using fallback...")
        # Get any articles from the last 7 days
        from datetime import datetime, timedelta
        week_cutoff = datetime.now() - timedelta(days=7)
        fallback_articles = []
        for article in arts:
            if article.published_at:
                try:
                    pub_time = datetime.fromisoformat(article.published_at.replace('Z', '+00:00'))
                    week_cutoff_aware = week_cutoff.replace(tzinfo=pub_time.tzinfo)
                    if pub_time >= week_cutoff_aware and article.id not in {a.id for a in result}:
                        fallback_articles.append(article)
                except:
                    continue
        result.extend(fallback_articles[:k-len(result)])
    
    return result[:k]
