"""
Модуль models.py

Определяет модели базы данных.
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Float

Base = declarative_base()

class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True) 
    url = Column(String, nullable=False, unique=True)
    embedding = Column(ARRAY(Float), nullable=False)