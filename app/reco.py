import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Article, UserProfile
from .embeddings import loads_embedding, embed_text

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a)*np.linalg.norm(b) + 1e-9)
    return float(np.dot(a,b) / denom)

async def recommend_for(session: AsyncSession, user_id: str, k: int = 10):
    # build a user interest vector by embedding interest phrases and averaging
    res = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    prof = res.scalar_one_or_none()
    if not prof or not prof.interests:
        user_vec = None
    else:
        interests = [s.strip() for s in prof.interests.split(",") if s.strip()]
        if not interests: user_vec = None
        else:
            embs = [embed_text(it) for it in interests]
            user_vec = np.mean(np.array(embs), axis=0)

    res = await session.execute(select(Article))
    arts = res.scalars().all()

    scored = []
    if user_vec is None:
        # cold start: rank by recentness (created_at desc) or random
        for a in arts:
            scored.append((0.0, a))
    else:
        u = user_vec
        for a in arts:
            if not a.embedding: continue
            v = loads_embedding(a.embedding)
            scored.append((cosine(u, v), a))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored[:k]]
