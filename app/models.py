from sqlalchemy import Column, Integer, String, Text, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from .db import Base

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, index=True)
    title = Column(String)
    source = Column(String)
    author = Column(String)
    published_at = Column(String)
    description = Column(Text)
    content = Column(Text)
    summary = Column(Text)
    embedding = Column(Text)  # store as json string (list[float])
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)  # simple string identifier
    interests = Column(Text)  # comma-separated interests
    __table_args__ = (UniqueConstraint('user_id', name='uix_user'),)
