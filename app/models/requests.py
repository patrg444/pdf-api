from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Union
from enum import Enum


class PDFFormat(str, Enum):
    A4 = "A4"
    A3 = "A3"
    LETTER = "Letter"
    LEGAL = "Legal"
    TABLOID = "Tabloid"


class ImageFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"
    GIF = "gif"
    BMP = "bmp"
    TIFF = "tiff"


class CompressionLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class SecurityPermissions(str, Enum):
    PRINT = "print"
    MODIFY = "modify"
    COPY = "copy"
    ANNOTATE = "annotate"
    FILL_FORMS = "fill_forms"
    EXTRACT = "extract"
    ASSEMBLE = "assemble"
    PRINT_HIGH_QUALITY = "print_high_quality"


# Base PDF Request
class PDFRequest(BaseModel):
    html: Optional[str] = Field(None, description="HTML content to convert")
    url: Optional[str] = Field(None, description="URL to convert")
    template: Optional[str] = Field(None, description="Template name to use")
    data: Optional[Dict] = Field(None, description="Data for template")
    options: Optional[Dict] = Field(default_factory=dict, description="PDF options")


# Merge PDFs
class MergePDFRequest(BaseModel):
    urls: Optional[List[str]] = Field(None, description="URLs of PDFs to merge")
    order: Optional[List[int]] = Field(None, description="Order of PDFs (0-indexed)")
    
    @validator('order')
    def validate_order(cls, v, values):
        if v and 'urls' in values and values['urls']:
            if len(v) != len(values['urls']):
                raise ValueError('Order list must match number of files')
        return v


# Split PDF
class SplitPDFRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL of PDF to split")
    pages: Optional[str] = Field(None, description="Page ranges (e.g., '1-3,5,7-10')")
    chunks: Optional[int] = Field(None, description="Split into N equal chunks")
    
    @validator('pages')
    def validate_pages(cls, v):
        if v:
            # Validate page range format
            import re
            pattern = r'^(\d+(-\d+)?)(,\d+(-\d+)?)*$'
            if not re.match(pattern, v.replace(' ', '')):
                raise ValueError('Invalid page range format')
        return v


# Compress PDF
class CompressPDFRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL of PDF to compress")
    level: CompressionLevel = Field(CompressionLevel.MEDIUM, description="Compression level")
    dpi: Optional[int] = Field(150, description="DPI for images (72-300)")
    
    @validator('dpi')
    def validate_dpi(cls, v):
        if v and (v < 72 or v > 300):
            raise ValueError('DPI must be between 72 and 300')
        return v


# Rotate PDF
class RotatePDFRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL of PDF to rotate")
    angle: int = Field(..., description="Rotation angle (90, 180, 270)")
    pages: Optional[str] = Field(None, description="Specific pages to rotate")
    
    @validator('angle')
    def validate_angle(cls, v):
        if v not in [90, 180, 270]:
            raise ValueError('Angle must be 90, 180, or 270')
        return v


# Watermark PDF
class WatermarkPDFRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL of PDF to watermark")
    text: Optional[str] = Field(None, description="Text watermark")
    image_url: Optional[str] = Field(None, description="Image watermark URL")
    opacity: float = Field(0.5, ge=0.0, le=1.0, description="Watermark opacity")
    position: str = Field("center", description="Position: center, top-left, etc.")
    pages: Optional[str] = Field(None, description="Specific pages to watermark")


# Secure PDF
class SecurePDFRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL of PDF to secure")
    user_password: Optional[str] = Field(None, description="Password to open PDF")
    owner_password: str = Field(..., description="Password to modify PDF")
    permissions: List[SecurityPermissions] = Field(
        default_factory=list,
        description="Allowed permissions"
    )
    encryption_level: int = Field(128, description="Encryption level (40 or 128)")
    
    @validator('encryption_level')
    def validate_encryption(cls, v):
        if v not in [40, 128]:
            raise ValueError('Encryption level must be 40 or 128')
        return v


# Extract from PDF
class ExtractTextRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL of PDF")
    pages: Optional[str] = Field(None, description="Specific pages to extract from")
    format: str = Field("text", description="Output format: text, json, markdown")


class ExtractImagesRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL of PDF")
    pages: Optional[str] = Field(None, description="Specific pages to extract from")
    format: ImageFormat = Field(ImageFormat.PNG, description="Output image format")
    min_width: int = Field(100, description="Minimum image width to extract")
    min_height: int = Field(100, description="Minimum image height to extract")


# Convert PDF to Images
class PDFToImagesRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL of PDF")
    format: ImageFormat = Field(ImageFormat.PNG, description="Output image format")
    dpi: int = Field(200, ge=72, le=600, description="DPI for conversion")
    pages: Optional[str] = Field(None, description="Specific pages to convert")


# Convert Images to PDF
class ImagesToPDFRequest(BaseModel):
    image_urls: List[str] = Field(..., description="URLs of images to convert")
    page_size: PDFFormat = Field(PDFFormat.A4, description="Page size")
    margin: int = Field(0, ge=0, le=100, description="Page margin in pixels")
    auto_orient: bool = Field(True, description="Auto-orient images")


# API Key Management
class APIKeyCreate(BaseModel):
    email: str
    plan: str = Field("basic", description="basic, pro, or enterprise")


# Batch Processing
class BatchPDFRequest(BaseModel):
    operations: List[Dict] = Field(..., description="List of operations to perform")
    webhook_url: Optional[str] = Field(None, description="Webhook for completion")
