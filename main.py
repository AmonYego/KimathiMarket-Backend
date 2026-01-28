from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, Text, ARRAY, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import datetime
import uuid
from supabase import create_client
from fastapi import UploadFile, File
import os

SUPABASE_URL = "https://nufeuxdqjfithhleezox.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im51ZmV1eGRxamZpdGhobGVlem94Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTU3NTc1MSwiZXhwIjoyMDg1MTUxNzUxfQ.chhcC-Cv1p4SI5fk2gJgCgmGhkGnXc_crDkDP32Bd8g"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# Database URL provided for your local PostgreSQL instance
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Arusei14@localhost:5432/Marketplace"

# Initialize SQLAlchemy with PostgreSQL engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- Database Models ---

class ProfileDB(Base):
    __tablename__ = "profiles"
    id = Column(String, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    course = Column(String)
    year_of_study = Column(Integer)
    phone = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Relationship: One User can have many Products
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


# Create tables in PostgreSQL
Base.metadata.create_all(bind=engine)

app = FastAPI(title="DeKUT Marketplace - PostgreSQL Powered")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Pydantic Schemas ---

class ProfileSchema(BaseModel):
    id: str
    fullName: str
    email: str
    course: str
    yearOfStudy: int
    phone: str
    model_config = ConfigDict(extra='ignore')


class ProductCreate(BaseModel):
    userId: str
    title: str
    description: str
    price: float
    category: str
    condition: str
    images: List[str]


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
            "createdAt": p.created_at.isoformat() if p.created_at else datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
            "updatedAt": p.updated_at.isoformat() if p.updated_at else datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
            "sellerName": p.seller.full_name if p.seller else "Unknown",
            "sellerCourse": p.seller.course if p.seller else "N/A",
            "sellerYear": p.seller.year_of_study if p.seller else 0,
            "sellerPhone": p.seller.phone if p.seller else "",
        })
    return result


@app.post("/products")
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    # Check if user exists before creating product
    user = db.query(ProfileDB).filter(ProfileDB.id == product.userId).first()
    if not user:
        raise HTTPException(status_code=400, detail="User profile must exist to list a product")

    db_product = ProductDB(
        user_id=product.userId,
        title=product.title,
        description=product.description,
        price=product.price,
        category=product.category,
        condition=product.condition,
        images=product.images if product.images else []
    )

    for image in db_product.images:
        if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(status_code=400, detail="Invalid image type")
        # 3️⃣ Create unique filename
        filename = f"{product.user_id}/{uuid.uuid4()}.jpg"

        # 4️⃣ Upload to Supabase Storage
        supabase.storage.from_("product-images").upload(
            filename,
            await image.read(),
            file_options={"content-type": image.content_type}
        )

        # 5️⃣ Get public URL
        image_url = supabase.storage.from_("product-images").get_public_url(filename)

       # 6️⃣ Save URL to database
        db_product.images = product.images + [image_url]

        return {"imageUrl": image_url}
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return {"status": "success", "id": db_product.id}


@app.patch("/products/{id}/sold")
def mark_sold(id: str, db: Session = Depends(get_db)):
    db_product = db.query(ProductDB).filter(ProductDB.id == id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db_product.is_sold = True
    db.commit()
    return {"status": "ok"}


@app.delete("/products/{id}")
def delete_product(id: str, db: Session = Depends(get_db)):
    product = db.query(ProductDB).filter(ProductDB.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # delete images from Supabase
    for url in product.images:
        path = url.split("/product-images/")[1]
        supabase.storage.from_("product-images").remove([path])

    db.delete(product)
    db.commit()
    return {"status": "ok"}



@app.get("/profiles/{email}")
def get_profile_by_email(email: str, db: Session = Depends(get_db)):
    p = db.query(ProfileDB).filter(ProfileDB.email.ilike(email)).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "id": p.id,
        "email": p.email,
        "fullName": p.full_name,
        "course": p.course,
        "yearOfStudy": p.year_of_study,
        "phone": p.phone,
        "createdAt": p.created_at.isoformat()
    }


@app.post("/profiles")
def upsert_profile(profile: ProfileSchema, db: Session = Depends(get_db)):
    existing = db.query(ProfileDB).filter(ProfileDB.id == profile.id).first()
    if existing:
        existing.full_name = profile.fullName
        existing.course = profile.course
        existing.year_of_study = profile.yearOfStudy
        existing.phone = profile.phone
    else:
        db_profile = ProfileDB(
            id=profile.id,
            full_name=profile.fullName,
            email=profile.email.lower(),
            course=profile.course,
            year_of_study=profile.yearOfStudy,
            phone=profile.phone
        )
        db.add(db_profile)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok"}




