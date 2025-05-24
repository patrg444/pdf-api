from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List
import time
import tempfile
import os
import uuid
from io import BytesIO

from app.core.dependencies import (
    verify_api_key,
    validate_pdf_file,
    validate_multiple_pdf_files,
    validate_image_file,
    get_file_url,
    require_pro_plan
)
from app.models.requests import (
    MergePDFRequest,
    SplitPDFRequest,
    CompressPDFRequest,
    RotatePDFRequest,
    WatermarkPDFRequest,
    SecurePDFRequest,
    PDFToImagesRequest,
    ImagesToPDFRequest
)
from app.models.responses import (
    MergePDFResponse,
    SplitPDFResponse,
    CompressPDFResponse,
    PDFResponse,
    PDFToImagesResponse,
    ErrorResponse
)
from app.services.pdf_service import pdf_service
from app.core.config import settings

router = APIRouter(prefix="/pdf", tags=["PDF Manipulation"])


@router.post("/merge", response_model=MergePDFResponse)
async def merge_pdfs(
    files: List[UploadFile] = File(...),
    order: Optional[str] = Form(None),
    api_key: str = Depends(verify_api_key)
):
    """
    Merge multiple PDF files into one.
    
    - **files**: List of PDF files to merge (max 20 files)
    - **order**: Optional comma-separated indices for custom order (e.g., "2,0,1")
    """
    start_time = time.time()
    
    try:
        # Validate files
        pdf_contents = await validate_multiple_pdf_files(files)
        
        # Parse order if provided
        order_list = None
        if order:
            try:
                order_list = [int(x.strip()) for x in order.split(',')]
                if len(order_list) != len(files):
                    raise ValueError("Order list must match number of files")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Merge PDFs
        merged_pdf = await pdf_service.merge_pdfs(pdf_contents, order_list)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            dir=settings.TEMP_DIR,
            suffix=".pdf",
            prefix="merged_"
        )
        temp_file.write(merged_pdf)
        temp_file.close()
        
        # Get metadata
        metadata = await pdf_service.get_pdf_metadata(merged_pdf)
        
        processing_time = time.time() - start_time
        
        return MergePDFResponse(
            file_url=get_file_url(temp_file.name),
            file_size=len(merged_pdf),
            pages=metadata["pages"],
            processing_time=processing_time,
            source_files=[f.filename for f in files],
            total_pages=metadata["pages"],
            message="PDFs merged successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/merge-urls", response_model=MergePDFResponse)
async def merge_pdfs_from_urls(
    request: MergePDFRequest,
    api_key: str = Depends(verify_api_key)
):
    """Merge PDFs from URLs"""
    start_time = time.time()
    
    try:
        if not request.urls:
            raise HTTPException(status_code=400, detail="No URLs provided")
        
        # Download PDFs
        pdf_contents = []
        for url in request.urls:
            pdf_data = await pdf_service.download_file(url)
            pdf_contents.append(pdf_data)
        
        # Merge PDFs
        merged_pdf = await pdf_service.merge_pdfs(pdf_contents, request.order)
        
        # Save and return response
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            dir=settings.TEMP_DIR,
            suffix=".pdf",
            prefix="merged_"
        )
        temp_file.write(merged_pdf)
        temp_file.close()
        
        metadata = await pdf_service.get_pdf_metadata(merged_pdf)
        processing_time = time.time() - start_time
        
        return MergePDFResponse(
            file_url=get_file_url(temp_file.name),
            file_size=len(merged_pdf),
            pages=metadata["pages"],
            processing_time=processing_time,
            source_files=request.urls,
            total_pages=metadata["pages"],
            message="PDFs merged successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/split", response_model=SplitPDFResponse)
async def split_pdf(
    file: UploadFile = File(...),
    pages: Optional[str] = Form(None),
    chunks: Optional[int] = Form(None),
    api_key: str = Depends(verify_api_key)
):
    """
    Split a PDF file by page ranges or into equal chunks.
    
    - **file**: PDF file to split
    - **pages**: Page ranges to extract (e.g., "1-3,5,7-10")
    - **chunks**: Number of equal chunks to split into
    
    Either provide 'pages' or 'chunks', not both.
    """
    start_time = time.time()
    
    try:
        if pages and chunks:
            raise HTTPException(
                status_code=400,
                detail="Provide either 'pages' or 'chunks', not both"
            )
        
        if not pages and not chunks:
            raise HTTPException(
                status_code=400,
                detail="Provide either 'pages' or 'chunks'"
            )
        
        # Validate PDF
        pdf_content = await validate_pdf_file(file)
        
        # Split PDF
        split_pdfs = await pdf_service.split_pdf(pdf_content, pages, chunks)
        
        # Save split PDFs
        result_files = []
        for i, pdf_data in enumerate(split_pdfs):
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                dir=settings.TEMP_DIR,
                suffix=".pdf",
                prefix=f"split_{i+1}_"
            )
            temp_file.write(pdf_data)
            temp_file.close()
            
            metadata = await pdf_service.get_pdf_metadata(pdf_data)
            result_files.append({
                "file_url": get_file_url(temp_file.name),
                "file_size": len(pdf_data),
                "pages": metadata["pages"],
                "part": i + 1
            })
        
        processing_time = time.time() - start_time
        
        return SplitPDFResponse(
            files=result_files,
            total_files=len(result_files),
            processing_time=processing_time,
            message="PDF split successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compress", response_model=CompressPDFResponse)
async def compress_pdf(
    file: UploadFile = File(...),
    level: str = Form("medium"),
    dpi: int = Form(150),
    api_key: str = Depends(verify_api_key),
    _: bool = Depends(require_pro_plan)
):
    """
    Compress a PDF file to reduce its size.
    
    - **file**: PDF file to compress
    - **level**: Compression level (low, medium, high, extreme)
    - **dpi**: Target DPI for images (72-300)
    
    This feature requires Pro plan or higher.
    """
    start_time = time.time()
    
    try:
        # Validate inputs
        if level not in ["low", "medium", "high", "extreme"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid compression level"
            )
        
        if dpi < 72 or dpi > 300:
            raise HTTPException(
                status_code=400,
                detail="DPI must be between 72 and 300"
            )
        
        # Validate PDF
        pdf_content = await validate_pdf_file(file)
        original_size = len(pdf_content)
        
        # Compress PDF
        compressed_pdf, compression_ratio = await pdf_service.compress_pdf(
            pdf_content,
            level,
            dpi
        )
        
        # Save compressed PDF
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            dir=settings.TEMP_DIR,
            suffix=".pdf",
            prefix="compressed_"
        )
        temp_file.write(compressed_pdf)
        temp_file.close()
        
        metadata = await pdf_service.get_pdf_metadata(compressed_pdf)
        processing_time = time.time() - start_time
        
        return CompressPDFResponse(
            file_url=get_file_url(temp_file.name),
            file_size=len(compressed_pdf),
            pages=metadata["pages"],
            processing_time=processing_time,
            original_size=original_size,
            compressed_size=len(compressed_pdf),
            compression_ratio=compression_ratio,
            message=f"PDF compressed by {compression_ratio:.1f}%"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rotate", response_model=PDFResponse)
async def rotate_pdf(
    file: UploadFile = File(...),
    angle: int = Form(...),
    pages: Optional[str] = Form(None),
    api_key: str = Depends(verify_api_key)
):
    """
    Rotate PDF pages.
    
    - **file**: PDF file to rotate
    - **angle**: Rotation angle (90, 180, or 270)
    - **pages**: Optional specific pages to rotate (e.g., "1-3,5")
    """
    start_time = time.time()
    
    try:
        # Validate angle
        if angle not in [90, 180, 270]:
            raise HTTPException(
                status_code=400,
                detail="Angle must be 90, 180, or 270"
            )
        
        # Validate PDF
        pdf_content = await validate_pdf_file(file)
        
        # Rotate PDF
        rotated_pdf = await pdf_service.rotate_pdf(pdf_content, angle, pages)
        
        # Save rotated PDF
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            dir=settings.TEMP_DIR,
            suffix=".pdf",
            prefix="rotated_"
        )
        temp_file.write(rotated_pdf)
        temp_file.close()
        
        metadata = await pdf_service.get_pdf_metadata(rotated_pdf)
        processing_time = time.time() - start_time
        
        return PDFResponse(
            file_url=get_file_url(temp_file.name),
            file_size=len(rotated_pdf),
            pages=metadata["pages"],
            processing_time=processing_time,
            message="PDF rotated successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watermark", response_model=PDFResponse)
async def add_watermark(
    file: UploadFile = File(...),
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    opacity: float = Form(0.5),
    position: str = Form("center"),
    pages: Optional[str] = Form(None),
    api_key: str = Depends(verify_api_key),
    _: bool = Depends(require_pro_plan)
):
    """
    Add text or image watermark to PDF.
    
    - **file**: PDF file to watermark
    - **text**: Text watermark (provide either text or image)
    - **image**: Image watermark file
    - **opacity**: Watermark opacity (0.0 to 1.0)
    - **position**: Position (center, top-left, top-right, bottom-left, bottom-right)
    - **pages**: Optional specific pages to watermark
    
    This feature requires Pro plan or higher.
    """
    start_time = time.time()
    
    try:
        # Validate inputs
        if not text and not image:
            raise HTTPException(
                status_code=400,
                detail="Provide either text or image watermark"
            )
        
        if text and image:
            raise HTTPException(
                status_code=400,
                detail="Provide either text or image watermark, not both"
            )
        
        if opacity < 0 or opacity > 1:
            raise HTTPException(
                status_code=400,
                detail="Opacity must be between 0 and 1"
            )
        
        valid_positions = ["center", "top-left", "top-right", "bottom-left", "bottom-right"]
        if position not in valid_positions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid position. Must be one of: {', '.join(valid_positions)}"
            )
        
        # Validate PDF
        pdf_content = await validate_pdf_file(file)
        
        # Process image watermark if provided
        image_data = None
        if image:
            image_data = await validate_image_file(image)
        
        # Add watermark
        watermarked_pdf = await pdf_service.add_watermark(
            pdf_content,
            text=text,
            image_data=image_data,
            opacity=opacity,
            position=position,
            pages=pages
        )
        
        # Save watermarked PDF
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            dir=settings.TEMP_DIR,
            suffix=".pdf",
            prefix="watermarked_"
        )
        temp_file.write(watermarked_pdf)
        temp_file.close()
        
        metadata = await pdf_service.get_pdf_metadata(watermarked_pdf)
        processing_time = time.time() - start_time
        
        return PDFResponse(
            file_url=get_file_url(temp_file.name),
            file_size=len(watermarked_pdf),
            pages=metadata["pages"],
            processing_time=processing_time,
            message="Watermark added successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/secure", response_model=PDFResponse)
async def secure_pdf(
    file: UploadFile = File(...),
    user_password: Optional[str] = Form(None),
    owner_password: str = Form(...),
    permissions: Optional[str] = Form(None),
    encryption_level: int = Form(128),
    api_key: str = Depends(verify_api_key),
    _: bool = Depends(require_pro_plan)
):
    """
    Add password protection and permissions to PDF.
    
    - **file**: PDF file to secure
    - **user_password**: Password to open PDF (optional)
    - **owner_password**: Password to modify PDF (required)
    - **permissions**: Comma-separated permissions (print,modify,copy,annotate)
    - **encryption_level**: Encryption level (40 or 128)
    
    This feature requires Pro plan or higher.
    """
    start_time = time.time()
    
    try:
        # Validate encryption level
        if encryption_level not in [40, 128]:
            raise HTTPException(
                status_code=400,
                detail="Encryption level must be 40 or 128"
            )
        
        # Parse permissions
        permission_list = []
        if permissions:
            valid_permissions = ["print", "modify", "copy", "annotate"]
            permission_list = [p.strip() for p in permissions.split(',')]
            invalid = [p for p in permission_list if p not in valid_permissions]
            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid permissions: {', '.join(invalid)}"
                )
        
        # Validate PDF
        pdf_content = await validate_pdf_file(file)
        
        # Secure PDF
        secured_pdf = await pdf_service.secure_pdf(
            pdf_content,
            user_password=user_password,
            owner_password=owner_password,
            permissions=permission_list,
            encryption_level=encryption_level
        )
        
        # Save secured PDF
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            dir=settings.TEMP_DIR,
            suffix=".pdf",
            prefix="secured_"
        )
        temp_file.write(secured_pdf)
        temp_file.close()
        
        metadata = await pdf_service.get_pdf_metadata(secured_pdf)
        processing_time = time.time() - start_time
        
        return PDFResponse(
            file_url=get_file_url(temp_file.name),
            file_size=len(secured_pdf),
            pages=metadata["pages"],
            processing_time=processing_time,
            message="PDF secured successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/to/images", response_model=PDFToImagesResponse)
async def pdf_to_images(
    file: UploadFile = File(...),
    format: str = Form("png"),
    dpi: int = Form(200),
    pages: Optional[str] = Form(None),
    api_key: str = Depends(verify_api_key)
):
    """
    Convert PDF pages to images.
    
    - **file**: PDF file to convert
    - **format**: Output image format (png, jpeg, jpg)
    - **dpi**: DPI for conversion (72-600)
    - **pages**: Optional specific pages to convert
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
        
        # Validate DPI
        if dpi < 72 or dpi > 600:
            raise HTTPException(
                status_code=400,
                detail="DPI must be between 72 and 600"
            )
        
        # Validate PDF
        pdf_content = await validate_pdf_file(file)
        
        # Convert to images
        images = await pdf_service.pdf_to_images(
            pdf_content,
            dpi=dpi,
            image_format=format,
            pages=pages
        )
        
        # Save images
        image_urls = []
        for i, img_data in enumerate(images):
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                dir=settings.TEMP_DIR,
                suffix=f".{format}",
                prefix=f"page_{i+1}_"
            )
            temp_file.write(img_data)
            temp_file.close()
            image_urls.append(get_file_url(temp_file.name))
        
        processing_time = time.time() - start_time
        
        return PDFToImagesResponse(
            images=image_urls,
            total_pages=len(images),
            format=format,
            processing_time=processing_time,
            message="PDF converted to images successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/from/images", response_model=PDFResponse)
async def images_to_pdf(
    files: List[UploadFile] = File(...),
    page_size: str = Form("A4"),
    margin: int = Form(0),
    auto_orient: bool = Form(True),
    api_key: str = Depends(verify_api_key)
):
    """
    Convert images to PDF.
    
    - **files**: Image files to convert (max 50)
    - **page_size**: Page size (A4, A3, Letter, Legal, Tabloid)
    - **margin**: Page margin in pixels
    - **auto_orient**: Auto-orient images based on EXIF data
    """
    start_time = time.time()
    
    try:
        # Validate page size
        valid_sizes = ["A4", "A3", "Letter", "Legal", "Tabloid"]
        if page_size not in valid_sizes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid page size. Must be one of: {', '.join(valid_sizes)}"
            )
        
        # Validate margin
        if margin < 0 or margin > 100:
            raise HTTPException(
                status_code=400,
                detail="Margin must be between 0 and 100"
            )
        
        # Validate images
        image_contents = []
        for file in files:
            content = await validate_image_file(file)
            image_contents.append(content)
        
        # Convert to PDF
        pdf_data = await pdf_service.images_to_pdf(
            image_contents,
            page_size=page_size,
            margin=margin,
            auto_orient=auto_orient
        )
        
        # Save PDF
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            dir=settings.TEMP_DIR,
            suffix=".pdf",
            prefix="from_images_"
        )
        temp_file.write(pdf_data)
        temp_file.close()
        
        metadata = await pdf_service.get_pdf_metadata(pdf_data)
        processing_time = time.time() - start_time
        
        return PDFResponse(
            file_url=get_file_url(temp_file.name),
            file_size=len(pdf_data),
            pages=metadata["pages"],
            processing_time=processing_time,
            message="Images converted to PDF successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Direct download endpoint for processed files
@router.get("/download/{file_id}")
async def download_pdf(
    file_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Download a processed PDF file"""
    try:
        file_path = os.path.join(settings.TEMP_DIR, file_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        return StreamingResponse(
            BytesIO(content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={file_id}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
