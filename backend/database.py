# backend/database.py

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Define the base for declarative models
Base = declarative_base()

# Define the path for the SQLite database
# It will be created in the 'backend' directory
DATABASE_FILE = "receipts.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, DATABASE_FILE)

# SQLite database URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create the SQLAlchemy engine
# connect_args={"check_same_thread": False} is needed for SQLite with FastAPI
# because SQLite does not allow multiple threads to write to the same connection
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define the Receipt model
class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    vendor = Column(String, index=True)
    transaction_date = Column(DateTime, index=True)
    amount = Column(Float)
    category = Column(String, nullable=True) # Optional category
    uploaded_at = Column(DateTime, default=datetime.now)
    extracted_text = Column(String) # Store the full extracted text for debugging/review

    def __repr__(self):
        return (
            f"<Receipt(id={self.id}, vendor='{self.vendor}', "
            f"amount={self.amount}, date='{self.transaction_date.strftime('%Y-%m-%d')}')>"
        )

# Function to create all tables in the database
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Ensure the database file exists and tables are created on startup
if not os.path.exists(DATABASE_PATH):
    print(f"Creating database at: {DATABASE_PATH}")
    create_db_and_tables()
else:
    print(f"Database already exists at: {DATABASE_PATH}")
    # You might want to call create_db_and_tables() here as well
    # in case new tables/columns are added to the models.
    # Base.metadata.create_all(bind=engine) is idempotent.
    create_db_and_tables()

