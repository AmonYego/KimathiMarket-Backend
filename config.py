from supabase import create_client
import os

SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_SERVICE_KEY = "your-service-role-key"  # IMPORTANT

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

from fastapi import UploadFile, File
import uuid

@app.post("/products/{product_id}/images")
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 1. Validate image
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid image type")

    # 2. Ensure product exists
    product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 3. Generate safe filename
    filename = f"{product.user_id}/{product_id}/{uuid.uuid4()}.jpg"

    # 4. Upload to Supabase Storage
    supabase.storage.from_("product-images").upload(
        filename,
        await file.read(),
        file_options={"content-type": file.content_type},
    )

    # 5. Get public URL
    image_url = supabase.storage.from_("product-images").get_public_url(filename)

    # 6. Save URL in DB (ARRAY column)
    product.images = product.images + [image_url]
    db.commit()

    return {"imageUrl": image_url}
