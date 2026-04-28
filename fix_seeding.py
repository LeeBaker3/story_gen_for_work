from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.database import Base, DynamicList, DynamicListItem
from backend.database_seeding import seed_database
import os

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print(f"Empty DB count: {db.query(DynamicList).count()}")

try:
    seed_database(db=db)
    print("Seed database called.")
except Exception as e:
    print(f"Error calling seed_database: {e}")

genres_count = db.query(DynamicListItem).filter_by(list_name='genres').count()
print(f"Genres count: {genres_count}")

db.close()
