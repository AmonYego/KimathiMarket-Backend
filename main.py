# --- main.py ---
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Float, Boolean, Text, ARRAY, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, ConfigDict
from typing import List
import datetime
import uuid
import os
from dotenv import load_dotenv
from supabase import create_client
from urllib.parse import urlparse

# --- Load Environment Variables ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

# --- Supabase Client ---
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# --- Database Setup ---
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Database Models ---
class ProfileDB(Base):
    __tablename__ = "profiles"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    products = relationship("ProductDB", back_populates="seller", cascade="all, delete-orphan")


class ProductDB(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    condition = Column(String, nullable=False)
    images = Column(ARRAY(String), default=[])
    is_sold = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc),
                        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    seller = relationship("ProfileDB", back_populates="products")

# Create tables
Base.metadata.create_all(bind=engine)

# --- FastAPI App ---
app = FastAPI(title="DeKUT Marketplace - PostgreSQL Powered")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Schema ---
class ProfileSchema(BaseModel):
    email: str
    phone: str
    model_config = ConfigDict(extra='ignore')

# --- API Endpoints ---
@app.get("/health")
def health_check():
    return {"status": "online", "database": "postgresql"}


@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(ProductDB).order_by(ProductDB.created_at.desc()).all()
    result = []
    for p in products:
        result.append({
            "id": p.id,
            "userId": p.user_id,
            "title": p.title,
            "description": p.description if p.description else "",
            "price": p.price,
            "category": p.category,
            "condition": p.condition,
            "images": p.images if p.images else [],
            "isSold": p.is_sold,
            "createdAt": p.created_at.isoformat() if p.created_at else datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updatedAt": p.updated_at.isoformat() if p.updated_at else datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "sellerEmail": p.seller.email if p.seller else "",
            "sellerPhone": p.seller.phone if p.seller else "",
        })
    return result


@app.post("/products")
async def create_product(
    db: Session = Depends(get_db),
    userId: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    condition: str = Form(...),
    images: List[UploadFile] = File(...)
):
    user = db.query(ProfileDB).filter(ProfileDB.id == userId).first()
    if not user:
        raise HTTPException(status_code=400, detail="User profile must exist to list a product")

    image_urls = []
    if images:
        for image in images:
            if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
                raise HTTPException(status_code=400, detail=f"Invalid image type: {image.content_type}")
            file_extension = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
            filename = f"{userId}/{uuid.uuid4()}.{file_extension}"
            try:
                contents = await image.read()
                supabase.storage.from_("product-images").upload(
                    path=filename,
                    file=contents,
                    file_options={"content-type": image.content_type}
                )
                SUPABASE_PROJECT_ID = "nufeuxdqjfithhleezox"
                image_url = f"https://{SUPABASE_PROJECT_ID}.supabase.co/storage/v1/object/public/product-images/{filename}"
                image_urls.append(image_url)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

    db_product = ProductDB(
        user_id=userId,
        title=title,
        description=description,
        price=price,
        category=category,
        condition=condition,
        images=image_urls
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return {"status": "success", "id": db_product.id}


@app.get("/profiles/{email}")
def get_profile(email: str, db: Session = Depends(get_db)):
    p = db.query(ProfileDB).filter(ProfileDB.email.ilike(email)).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"email": p.email, "phone": p.phone}


@app.post("/profiles")
def upsert_profile(profile: ProfileSchema, db: Session = Depends(get_db)):
    existing = db.query(ProfileDB).filter(ProfileDB.email.ilike(profile.email)).first()
    if existing:
        existing.phone = profile.phone
    else:
        db_profile = ProfileDB(
            id=str(uuid.uuid4()),
            email=profile.email.lower(),
            phone=profile.phone
        )
        db.add(db_profile)
    db.commit()
    return {"status": "ok"}
