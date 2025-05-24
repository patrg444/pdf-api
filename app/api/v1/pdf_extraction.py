from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, List
import time
import tempfile
import os
import zipfile
from io import BytesIO

from app.core.dependencies import (
    verify_api_key,
    validate_pdf_file,
    get_file_url
)
from app.models.requests import (
    ExtractTextRequest,
    ExtractImagesRequest
)
from app.models.responses import (
    ExtractTextResponse,
    ExtractImagesResponse,
    PDFMetadataResponse
)
from app.services.pdf_service import pdf_service
from app.core.config import settings

router = APIRouter(prefix="/pdf/extract", tags=["PDF Extraction"])


@router.post("/text", response_model=ExtractTextResponse)
async def extract_text(
    file: UploadFile = File(...),
    pages: Optional[str] = Form(None),
    format: str = Form("text"),
    api_key: str = Depends(verify_api_key)
):
    """
    Extract text content from PDF.
    
    - **file**: PDF file to extract text from
    - **pages**: Optional specific pages to extract from (e.g., "1-3,5,7-10")
    - **format**: Output format (text, json, markdown)
    """
    start_time = time.time()
    
    try:
        # Validate format
        valid_formats = ["text", "json", "markdown"]
        if format not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}"
            )
        
        # Validate PDF
        pdf_content = await validate_pdf_file(file)
        
        # Extract text
        result = await pdf_service.extract_text(
            pdf_content,
            pages=pages,
            output_format=format
        )
        
        processing_time = time.time() - start_time
        
        if format == "json":
            return ExtractTextResponse(
                json=result.get("pages"),
                word_count=result["word_count"],
                page_count=result["page_count"],
                processing_time=processing_time,
                message="Text extracted successfully"
            )
        else:
            return ExtractTextResponse(
                text=result["text"],
                word_count=result["word_count"],
                page_count=result["page_count"],
                processing_time=processing_time,
                message="Text extracted successfully"
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text-url", response_model=ExtractTextResponse)
async def extract_text_from_url(
    request: ExtractTextRequest,
    api_key: str = Depends(verify_api_key)
):
    """Extract text from PDF URL"""
    start_time = time.time()
    
    try:
        if not request.url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        # Download PDF
        pdf_content = await pdf_service.download_file(request.url)
        
        # Extract text
        result = await pdf_service.extract_text(
            pdf_content,
            pages=request.pages,
            output_format=request.format
        )
        
        processing_time = time.time() - start_time
        
        if request.format == "json":
            return ExtractTextResponse(
                json=result.get("pages"),
                word_count=result["word_count"],
                page_count=result["page_count"],
                processing_time=processing_time,
                message="Text extracted successfully"
            )
        else:
            return ExtractTextResponse(
                text=result["text"],
                word_count=result["word_count"],
                page_count=result["page_count"],
                processing_time=processing_time,
                message="Text extracted successfully"
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images", response_model=ExtractImagesResponse)
async def extract_images(
    file: UploadFile = File(...),
    pages: Optional[str] = Form(None),
    format: str = Form("png"),
    min_width: int = Form(100),
    min_height: int = Form(100),
    api_key: str = Depends(verify_api_key)
):
    """
    Extract images from PDF.
    
    - **file**: PDF file to extract images from
    - **pages**: Optional specific pages to extract from
    - **format**: Output image format (png, jpeg, jpg)
    - **min_width**: Minimum image width to extract
    - **min_height**: Minimum image height to extract
    """
    start_time = time.time()
    
    try:
        # Validate format
        valid_formats = ["png", "jpeg", "jpg"]
        if format.lower() not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}"
            )
        
        # Validate dimensions
        if min_width < 1 or min_height < 1:
            raise HTTPException(
                status_code=400,
                detail="Minimum dimensions must be at least 1 pixel"
            )
        
        # Validate PDF
        pdf_content = await validate_pdf_file(file)
        
        # Extract images
        extracted_images = await pdf_service.extract_images(
            pdf_content,
            pages=pages,
            min_width=min_width,
            min_height=min_height,
            image_format=format
        )
        
        if not extracted_images:
            return ExtractImagesResponse(
                images=[],
                total_images=0,
                processing_time=time.time() - start_time,
                message="No images found matching criteria"
            )
        
        # Create ZIP file with all images
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            image_info = []
            
            for i, img_data in enumerate(extracted_images):
                filename = f"page_{img_data['page']}_image_{img_data['index']}.{format}"
                zip_file.writestr(filename, img_data['data'])
                
                # Save individual image for direct access
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    dir=settings.TEMP_DIR,
                    suffix=f".{format}",
                    prefix=f"extracted_img_{i}_"
                )
                temp_file.write(img_data['data'])
                temp_file.close()
                
                image_info.append({
                    "page": img_data['page'],
                    "index": img_data['index'],
                    "width": img_data['width'],
                    "height": img_data['height'],
                    "url": get_file_url(temp_file.name),
                    "filename": filename
                })
        
        # Save ZIP file
        zip_buffer.seek(0)
        zip_file_path = tempfile.NamedTemporaryFile(
            delete=False,
            dir=settings.TEMP_DIR,
            suffix=".zip",
            prefix="extracted_images_"
        )
        zip_file_path.write(zip_buffer.getvalue())
        zip_file_path.close()
        
        processing_time = time.time() - start_time
        
        return ExtractImagesResponse(
            images=image_info,
            total_images=len(extracted_images),
            zip_url=get_file_url(zip_file_path.name),
            processing_time=processing_time,
            message=f"Extracted {len(extracted_images)} images successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images-url", response_model=ExtractImagesResponse)
async def extract_images_from_url(
    request: ExtractImagesRequest,
    api_key: str = Depends(verify_api_key)
):
    """Extract images from PDF URL"""
    start_time = time.time()
    
    try:
        if not request.url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        # Download PDF
        pdf_content = await pdf_service.download_file(request.url)
        
        # Extract images
        extracted_images = await pdf_service.extract_images(
            pdf_content,
            pages=request.pages,
            min_width=request.min_width,
            min_height=request.min_height,
            image_format=request.format.value
        )
        
        if not extracted_images:
            return ExtractImagesResponse(
                images=[],
                total_images=0,
                processing_time=time.time() - start_time,
                message="No images found matching criteria"
            )
        
        # Create ZIP file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            image_info = []
            
            for i, img_data in enumerate(extracted_images):
                filename = f"page_{img_data['page']}_image_{img_data['index']}.{request.format.value}"
                zip_file.writestr(filename, img_data['data'])
                
                # Save individual image
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    dir=settings.TEMP_DIR,
                    suffix=f".{request.format.value}",
                    prefix=f"extracted_img_{i}_"
                )
                temp_file.write(img_data['data'])
                temp_file.close()
                
                image_info.append({
                    "page": img_data['page'],
                    "index": img_data['index'],
                    "width": img_data['width'],
                    "height": img_data['height'],
                    "url": get_file_url(temp_file.name),
                    "filename": filename
                })
        
        # Save ZIP file
        zip_buffer.seek(0)
        zip_file_path = tempfile.NamedTemporaryFile(
            delete=False,
            dir=settings.TEMP_DIR,
            suffix=".zip",
            prefix="extracted_images_"
        )
        zip_file_path.write(zip_buffer.getvalue())
        zip_file_path.close()
        
        processing_time = time.time() - start_time
        
        return ExtractImagesResponse(
            images=image_info,
            total_images=len(extracted_images),
            zip_url=get_file_url(zip_file_path.name),
            processing_time=processing_time,
            message=f"Extracted {len(extracted_images)} images successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metadata", response_model=PDFMetadataResponse)
async def get_pdf_metadata(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Extract metadata from PDF file.
    
    Returns information about:
    - Title, author, subject, creator
    - Creation and modification dates
    - Number of pages
    - File size
    - Encryption status
    - Page dimensions
    """
    start_time = time.time()
    
    try:
        # Validate PDF
        pdf_content = await validate_pdf_file(file)
        
        # Get metadata
        metadata = await pdf_service.get_pdf_metadata(pdf_content)
        
        processing_time = time.time() - start_time
        
        # Convert datetime objects to strings if present
        if metadata.get("creation_date"):
            try:
                metadata["creation_date"] = str(metadata["creation_date"])
            except:
                pass
        
        if metadata.get("modification_date"):
            try:
                metadata["modification_date"] = str(metadata["modification_date"])
            except:
                pass
        
        return PDFMetadataResponse(
            title=metadata.get("title"),
            author=metadata.get("author"),
            subject=metadata.get("subject"),
            creator=metadata.get("creator"),
            producer=metadata.get("producer"),
            creation_date=metadata.get("creation_date"),
            modification_date=metadata.get("modification_date"),
            pages=metadata["pages"],
            file_size=metadata["file_size"],
            encrypted=metadata["encrypted"],
            page_size=metadata["page_size"],
            processing_time=processing_time,
            message="Metadata extracted successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata-url")
async def get_pdf_metadata_from_url(
    url: str,
    api_key: str = Depends(verify_api_key)
):
    """Extract metadata from PDF URL"""
    start_time = time.time()
    
    try:
        # Download PDF
        pdf_content = await pdf_service.download_file(url)
        
        # Get metadata
        metadata = await pdf_service.get_pdf_metadata(pdf_content)
        
        processing_time = time.time() - start_time
        
        # Convert datetime objects to strings
        if metadata.get("creation_date"):
            try:
                metadata["creation_date"] = str(metadata["creation_date"])
            except:
                pass
        
        if metadata.get("modification_date"):
            try:
                metadata["modification_date"] = str(metadata["modification_date"])
            except:
                pass
        
        return PDFMetadataResponse(
            title=metadata.get("title"),
            author=metadata.get("author"),
            subject=metadata.get("subject"),
            creator=metadata.get("creator"),
            producer=metadata.get("producer"),
            creation_date=metadata.get("creation_date"),
            modification_date=metadata.get("modification_date"),
            pages=metadata["pages"],
            file_size=metadata["file_size"],
            encrypted=metadata["encrypted"],
            page_size=metadata["page_size"],
            processing_time=processing_time,
            message="Metadata extracted successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Download endpoints for extracted content
@router.get("/download/text/{file_id}")
async def download_extracted_text(
    file_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Download extracted text file"""
    try:
        file_path = os.path.join(settings.TEMP_DIR, file_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Determine content type based on extension
        ext = os.path.splitext(file_id)[1].lower()
        if ext == ".json":
            media_type = "application/json"
        elif ext == ".md":
            media_type = "text/markdown"
        else:
            media_type = "text/plain"
        
        return StreamingResponse(
            BytesIO(content),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_id}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/images/{file_id}")
async def download_extracted_images(
    file_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Download extracted images (ZIP or individual image)"""
    try:
        file_path = os.path.join(settings.TEMP_DIR, file_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Determine content type based on extension
        ext = os.path.splitext(file_id)[1].lower()
        media_types = {
            ".zip": "application/zip",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff"
        }
        
        media_type = media_types.get(ext, "application/octet-stream")
        
        return StreamingResponse(
            BytesIO(content),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_id}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
