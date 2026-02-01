# --- NEW VERSION ---
# This version includes a definitive check to ensure 'images' are file uploads.
# If the error persists, the client is not sending 'multipart/form-data' correctly.

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
from fastapi import UploadFile, File, Form
import os
from dotenv import load_dotenv
from urllib.parse import urlparse
from passlib.hash import bcrypt

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Database URL provided for your local PostgreSQL instance
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
    password = Column(String)
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
    phone: str
    password: Optional[str] = None
    model_config = ConfigDict(extra='ignore')


class LoginSchema(BaseModel):
    email: str
    password: str
    model_config = ConfigDict(extra='ignore')


# --- API Endpoints ---

@app.get("/debug/test-image-url/{image_path:path}")
def debug_test_image_url(image_path: str):
    """Test if an image URL is accessible"""
    SUPABASE_PROJECT_ID = "nufeuxdqjfithhleezox"
    image_url = f"https://{SUPABASE_PROJECT_ID}.supabase.co/storage/v1/object/public/product-images/{image_path}"
    return {
        "image_path": image_path,
        "full_url": image_url,
        "test_accessible": "Try visiting this URL in your browser",
    }


@app.get("/health")
def health_check():
    return {"status": "online", "database": "postgresql"}


@app.get("/debug/supabase-files")
def debug_supabase_files():
    """Debug endpoint to check what files are in Supabase"""
    try:
        # List all files in the product-images bucket
        files = supabase.storage.from_("product-images").list()
        return {
            "success": True,
            "bucket": "product-images",
            "files_count": len(files),
            "files": files,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "bucket": "product-images",
        }


@app.get("/debug/products")
def debug_products(db: Session = Depends(get_db)):
    """Debug endpoint to see raw database content"""
    products = db.query(ProductDB).all()
    debug_data = []
    for p in products:
        debug_data.append({
            "id": p.id,
            "title": p.title,
            "raw_images_field": p.images,
            "images_type": str(type(p.images)),
            "images_is_none": p.images is None,
            "images_length": len(p.images) if p.images else 0,
        })
    return {
        "total": len(products),
        "products": debug_data
    }


@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(ProductDB).order_by(ProductDB.created_at.desc()).all()
    print(f"DEBUG: Retrieved {len(products)} products from database")
    result = []
    for p in products:
        print(f"\nDEBUG: Processing product {p.id} - {p.title}")
        print(f"  - images field value: {p.images}")
        print(f"  - images type: {type(p.images)}")
        print(f"  - images length: {len(p.images) if p.images else 'None/Empty'}")
        
        images_to_return = p.images if p.images else []
        if images_to_return:
            for i, img_url in enumerate(images_to_return):
                print(f"    - Image {i}: {img_url}")
        
        result.append({
            "id": p.id,
            "userId": p.user_id,
            "title": p.title,
            "description": p.description if p.description else "",
            "price": p.price,
            "category": p.category,
            "condition": p.condition,
            "images": images_to_return,  # This is the critical line
            "isSold": p.is_sold,
            "createdAt": p.created_at.isoformat() if p.created_at else datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
            "updatedAt": p.updated_at.isoformat() if p.updated_at else datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
            "sellerName": p.seller.full_name if p.seller else "Unknown",
            "sellerPhone": p.seller.phone if p.seller else "",
        })
    
    print(f"\nDEBUG: Returning {len(result)} products to client")
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
    # Check if user exists
    user = db.query(ProfileDB).filter(ProfileDB.id == userId).first()
    if not user:
        raise HTTPException(status_code=400, detail="User profile must exist to list a product")

    image_urls = []
    if images:
        # Process uploaded images directly - they're already validated as UploadFile by FastAPI
        print(f"DEBUG: Processing {len(images)} images for product")
        for image in images:
            print(f"DEBUG: Processing image: {image.filename}, type: {image.content_type}")
            # Validate image type
            if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
                raise HTTPException(status_code=400, detail=f"Invalid image type: {image.content_type}")

            # Create unique filename - NO "product-images/" prefix because bucket is already named that
            file_extension = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
            filename = f"{userId}/{uuid.uuid4()}.{file_extension}"  # Just userId/uuid.ext
            print(f"DEBUG: Upload path: {filename}")

            try:
                # Upload to Supabase Storage
                contents = await image.read()
                print(f"DEBUG: Image size: {len(contents)} bytes")
                upload_response = supabase.storage.from_("product-images").upload(
                    path=filename,
                    file=contents,
                    file_options={"content-type": image.content_type}
                )
                print(f"DEBUG: Upload response: {upload_response}")

                # Construct public URL manually (more reliable than get_public_url)
                # Format: https://projectId.supabase.co/storage/v1/object/public/bucket/path
                SUPABASE_PROJECT_ID = "nufeuxdqjfithhleezox"  # Extract from SUPABASE_URL
                image_url = f"https://{SUPABASE_PROJECT_ID}.supabase.co/storage/v1/object/public/product-images/{filename}"
                print(f"DEBUG: Constructed Image URL: {image_url}")
                image_urls.append(image_url)

            except Exception as e:
                print(f"ERROR uploading image: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")
    
    print(f"DEBUG: Total image URLs to save: {image_urls}")

    # Create ProductDB instance
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
    
    print(f"DEBUG: Product created with ID: {db_product.id}")
    print(f"DEBUG: Saved images to DB: {db_product.images}")

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

    # Delete images from Supabase
    if product.images:
        image_paths_to_delete = []
        for url in product.images:
            parsed_url = urlparse(url)
            if parsed_url.path and "/product-images/" in parsed_url.path:
                path_in_bucket = parsed_url.path.split("/product-images/", 1)[-1]
                image_paths_to_delete.append(path_in_bucket)

        if image_paths_to_delete:
            try:
                supabase.storage.from_("product-images").remove(image_paths_to_delete)
            except Exception as e:
                print(f"Failed to delete images from Supabase: {e}")

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
        "phone": p.phone,
        "createdAt": p.created_at.isoformat(),
    }
    


@app.post("/profiles")
def upsert_profile(profile: ProfileSchema, db: Session = Depends(get_db)):
    existing = db.query(ProfileDB).filter(ProfileDB.id == profile.id).first()
    if existing:
        existing.full_name = profile.fullName
        existing.phone = profile.phone
        if profile.password:
            existing.password = bcrypt.hash(profile.password)
    else:
        db_profile = ProfileDB(
            id=profile.id,
            full_name=profile.fullName,
            email=profile.email.lower(),
            phone=profile.phone,
            password=bcrypt.hash(profile.password) if profile.password else None
        )
        db.add(db_profile)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok"}


@app.post("/login")
def login(data: LoginSchema, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    p = db.query(ProfileDB).filter(ProfileDB.email.ilike(email)).first()
    if not p:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not p.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    try:
        if not bcrypt.verify(data.password, p.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "id": p.id,
        "email": p.email,
        "fullName": p.full_name,
        "phone": p.phone,
        "createdAt": p.created_at.isoformat()
    }
