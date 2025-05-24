from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class BaseResponse(BaseModel):
    success: bool = Field(True, description="Operation success status")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now)


class PDFResponse(BaseResponse):
    file_url: Optional[str] = Field(None, description="URL to download the PDF")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    pages: Optional[int] = Field(None, description="Number of pages")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")


class MergePDFResponse(PDFResponse):
    source_files: List[str] = Field(default_factory=list, description="List of merged files")
    total_pages: int = Field(..., description="Total pages in merged PDF")


class SplitPDFResponse(BaseResponse):
    files: List[Dict[str, Any]] = Field(default_factory=list, description="List of split PDF files")
    total_files: int = Field(..., description="Number of files created")


class CompressPDFResponse(PDFResponse):
    original_size: int = Field(..., description="Original file size in bytes")
    compressed_size: int = Field(..., description="Compressed file size in bytes")
    compression_ratio: float = Field(..., description="Compression ratio percentage")


class ExtractTextResponse(BaseResponse):
    text: Optional[str] = Field(None, description="Extracted text content")
    json: Optional[Dict] = Field(None, description="Structured text data")
    word_count: int = Field(0, description="Total word count")
    page_count: int = Field(0, description="Number of pages processed")


class ExtractImagesResponse(BaseResponse):
    images: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="List of extracted images with metadata"
    )
    total_images: int = Field(0, description="Total number of images extracted")


class PDFToImagesResponse(BaseResponse):
    images: List[str] = Field(default_factory=list, description="URLs of generated images")
    total_pages: int = Field(..., description="Total pages converted")
    format: str = Field(..., description="Image format used")


class APIKeyResponse(BaseResponse):
    api_key: str = Field(..., description="Generated API key")
    plan: str = Field(..., description="Subscription plan")
    email: str = Field(..., description="Associated email")
    created_at: datetime = Field(default_factory=datetime.now)


class UsageResponse(BaseResponse):
    plan: str = Field(..., description="Current plan")
    requests_used: int = Field(..., description="Requests used in current period")
    requests_limit: int = Field(..., description="Total requests allowed")
    reset_date: datetime = Field(..., description="When the usage resets")
    percentage_used: float = Field(..., description="Percentage of limit used")


class ErrorResponse(BaseModel):
    success: bool = Field(False)
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code for debugging")
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict] = Field(None, description="Additional error details")


class BatchOperationStatus(BaseModel):
    operation_id: str = Field(..., description="Unique operation ID")
    status: str = Field(..., description="Status: pending, processing, completed, failed")
    progress: float = Field(0.0, description="Progress percentage")
    result: Optional[Dict] = Field(None, description="Operation result when completed")
    error: Optional[str] = Field(None, description="Error message if failed")


class BatchResponse(BaseResponse):
    batch_id: str = Field(..., description="Unique batch ID")
    operations: List[BatchOperationStatus] = Field(
        default_factory=list,
        description="Status of each operation"
    )
    total_operations: int = Field(..., description="Total number of operations")
    completed_operations: int = Field(0, description="Number of completed operations")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")


class HealthCheckResponse(BaseModel):
    status: str = Field("healthy", description="Service health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, bool] = Field(
        default_factory=dict,
        description="Status of dependent services"
    )


class TemplateListResponse(BaseResponse):
    templates: List[str] = Field(default_factory=list, description="Available template names")
    details: Dict[str, str] = Field(
        default_factory=dict,
        description="Template descriptions"
    )


class PDFMetadataResponse(BaseResponse):
    title: Optional[str] = Field(None, description="PDF title")
    author: Optional[str] = Field(None, description="PDF author")
    subject: Optional[str] = Field(None, description="PDF subject")
    creator: Optional[str] = Field(None, description="PDF creator application")
    producer: Optional[str] = Field(None, description="PDF producer")
    creation_date: Optional[datetime] = Field(None, description="Creation date")
    modification_date: Optional[datetime] = Field(None, description="Last modification date")
    pages: int = Field(..., description="Number of pages")
    file_size: int = Field(..., description="File size in bytes")
    encrypted: bool = Field(False, description="Whether PDF is encrypted")
    page_size: Dict[str, float] = Field(
        default_factory=dict,
        description="Page dimensions (width, height)"
    )
