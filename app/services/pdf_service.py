import os
import io
import tempfile
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse
import aiohttp
import aiofiles
from datetime import datetime

# PDF Libraries
import PyPDF2
import fitz  # PyMuPDF
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3, letter, legal, tabloid
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.core.config import settings


class PDFService:
    """Core service for PDF operations"""
    
    def __init__(self):
        self.temp_dir = settings.TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def download_file(self, url: str) -> bytes:
        """Download file from URL"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to download file from {url}")
                return await response.read()
    
    async def save_temp_file(self, content: bytes, suffix: str = ".pdf") -> str:
        """Save content to temporary file"""
        with tempfile.NamedTemporaryFile(
            delete=False,
            dir=self.temp_dir,
            suffix=suffix
        ) as tmp_file:
            tmp_file.write(content)
            return tmp_file.name
    
    def parse_page_ranges(self, pages: str, total_pages: int) -> List[int]:
        """Parse page range string (e.g., '1-3,5,7-10') into list of page numbers"""
        if not pages:
            return list(range(total_pages))
        
        page_list = []
        ranges = pages.replace(' ', '').split(',')
        
        for range_str in ranges:
            if '-' in range_str:
                start, end = map(int, range_str.split('-'))
                page_list.extend(range(start - 1, min(end, total_pages)))
            else:
                page_num = int(range_str) - 1
                if 0 <= page_num < total_pages:
                    page_list.append(page_num)
        
        return sorted(set(page_list))
    
    async def merge_pdfs(
        self, 
        pdf_files: List[bytes], 
        order: Optional[List[int]] = None
    ) -> bytes:
        """Merge multiple PDF files into one"""
        merger = PyPDF2.PdfMerger()
        
        try:
            # Apply custom order if provided
            if order:
                pdf_files = [pdf_files[i] for i in order]
            
            # Add each PDF to the merger
            for pdf_data in pdf_files:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
                merger.append(pdf_reader)
            
            # Write merged PDF to bytes
            output = io.BytesIO()
            merger.write(output)
            output.seek(0)
            
            return output.getvalue()
        finally:
            merger.close()
    
    async def split_pdf(
        self,
        pdf_data: bytes,
        pages: Optional[str] = None,
        chunks: Optional[int] = None
    ) -> List[bytes]:
        """Split PDF by page ranges or into chunks"""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
        total_pages = len(pdf_reader.pages)
        results = []
        
        if chunks:
            # Split into equal chunks
            pages_per_chunk = total_pages // chunks
            remainder = total_pages % chunks
            
            start = 0
            for i in range(chunks):
                end = start + pages_per_chunk + (1 if i < remainder else 0)
                
                writer = PyPDF2.PdfWriter()
                for page_num in range(start, end):
                    writer.add_page(pdf_reader.pages[page_num])
                
                output = io.BytesIO()
                writer.write(output)
                output.seek(0)
                results.append(output.getvalue())
                
                start = end
        else:
            # Split by page ranges
            page_list = self.parse_page_ranges(pages, total_pages)
            
            writer = PyPDF2.PdfWriter()
            for page_num in page_list:
                writer.add_page(pdf_reader.pages[page_num])
            
            output = io.BytesIO()
            writer.write(output)
            output.seek(0)
            results.append(output.getvalue())
        
        return results
    
    async def compress_pdf(
        self,
        pdf_data: bytes,
        compression_level: str = "medium",
        target_dpi: int = 150
    ) -> Tuple[bytes, float]:
        """Compress PDF by reducing image quality"""
        # Save original size
        original_size = len(pdf_data)
        
        # Open PDF with PyMuPDF for better compression
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        
        # Compression settings based on level
        compression_settings = {
            "low": {"image_quality": 85, "remove_duplication": True},
            "medium": {"image_quality": 70, "remove_duplication": True},
            "high": {"image_quality": 50, "remove_duplication": True},
            "extreme": {"image_quality": 30, "remove_duplication": True}
        }
        
        settings = compression_settings.get(compression_level, compression_settings["medium"])
        
        # Create new PDF with compression
        output = io.BytesIO()
        
        # Process each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Get images on page
            image_list = page.get_images()
            
            # Process images
            for img_index, img in enumerate(image_list):
                xref = img[0]
                pix = fitz.Pixmap(pdf_document, xref)
                
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    # Reduce resolution
                    if pix.width > target_dpi or pix.height > target_dpi:
                        pix = fitz.Pixmap(pix, 0)  # Remove alpha
                        factor = min(target_dpi / pix.width, target_dpi / pix.height)
                        pix = pix.rescale(factor, factor)
                    
                    # Convert to PIL Image and compress
                    img_data = pix.tobytes("jpeg", quality=settings["image_quality"])
                    
                    # Replace image in PDF
                    pdf_document.xref_set_key(xref, "Filter", "[/DCTDecode]")
                    pdf_document.xref_stream(xref, img_data)
                
                pix = None
        
        # Save compressed PDF
        pdf_document.save(output, garbage=4, deflate=True, clean=True)
        pdf_document.close()
        
        compressed_data = output.getvalue()
        compression_ratio = (1 - len(compressed_data) / original_size) * 100
        
        return compressed_data, compression_ratio
    
    async def rotate_pdf(
        self,
        pdf_data: bytes,
        angle: int,
        pages: Optional[str] = None
    ) -> bytes:
        """Rotate PDF pages"""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
        pdf_writer = PyPDF2.PdfWriter()
        total_pages = len(pdf_reader.pages)
        
        # Determine which pages to rotate
        pages_to_rotate = self.parse_page_ranges(pages, total_pages) if pages else range(total_pages)
        
        # Process each page
        for page_num in range(total_pages):
            page = pdf_reader.pages[page_num]
            
            if page_num in pages_to_rotate:
                page.rotate(angle)
            
            pdf_writer.add_page(page)
        
        # Write rotated PDF
        output = io.BytesIO()
        pdf_writer.write(output)
        output.seek(0)
        
        return output.getvalue()
    
    async def add_watermark(
        self,
        pdf_data: bytes,
        text: Optional[str] = None,
        image_data: Optional[bytes] = None,
        opacity: float = 0.5,
        position: str = "center",
        pages: Optional[str] = None
    ) -> bytes:
        """Add text or image watermark to PDF"""
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        total_pages = len(pdf_document)
        
        # Determine which pages to watermark
        pages_to_watermark = self.parse_page_ranges(pages, total_pages) if pages else range(total_pages)
        
        for page_num in pages_to_watermark:
            page = pdf_document[page_num]
            rect = page.rect
            
            if text:
                # Add text watermark
                font_size = min(rect.width, rect.height) / 10
                text_length = len(text) * font_size * 0.5
                
                # Calculate position
                if position == "center":
                    x = (rect.width - text_length) / 2
                    y = rect.height / 2
                elif position == "top-left":
                    x, y = 50, 50
                elif position == "top-right":
                    x = rect.width - text_length - 50
                    y = 50
                elif position == "bottom-left":
                    x = 50
                    y = rect.height - 50
                else:  # bottom-right
                    x = rect.width - text_length - 50
                    y = rect.height - 50
                
                # Insert text
                page.insert_text(
                    (x, y),
                    text,
                    fontsize=font_size,
                    color=(0.5, 0.5, 0.5),
                    overlay=True,
                    rotate=45 if position == "center" else 0,
                    opacity=opacity
                )
            
            elif image_data:
                # Add image watermark
                img = fitz.open(stream=image_data, filetype="png")
                img_rect = img[0].rect
                
                # Scale image to fit
                scale = min(rect.width / img_rect.width, rect.height / img_rect.height) * 0.3
                mat = fitz.Matrix(scale, scale)
                
                # Calculate position
                if position == "center":
                    x = (rect.width - img_rect.width * scale) / 2
                    y = (rect.height - img_rect.height * scale) / 2
                else:
                    x, y = 50, 50
                
                # Insert image
                page.insert_image(
                    fitz.Rect(x, y, x + img_rect.width * scale, y + img_rect.height * scale),
                    stream=image_data,
                    overlay=True,
                    opacity=opacity
                )
        
        # Save watermarked PDF
        output = io.BytesIO()
        pdf_document.save(output)
        pdf_document.close()
        
        return output.getvalue()
    
    async def secure_pdf(
        self,
        pdf_data: bytes,
        user_password: Optional[str] = None,
        owner_password: str = None,
        permissions: List[str] = None,
        encryption_level: int = 128
    ) -> bytes:
        """Add password protection and permissions to PDF"""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
        pdf_writer = PyPDF2.PdfWriter()
        
        # Copy all pages
        for page in pdf_reader.pages:
            pdf_writer.add_page(page)
        
        # Set permissions
        permission_flags = 0
        if permissions:
            permission_mapping = {
                "print": PyPDF2.constants.UserAccessPermissions.PRINT,
                "modify": PyPDF2.constants.UserAccessPermissions.MODIFY,
                "copy": PyPDF2.constants.UserAccessPermissions.EXTRACT,
                "annotate": PyPDF2.constants.UserAccessPermissions.ADD_OR_MODIFY,
            }
            
            for perm in permissions:
                if perm in permission_mapping:
                    permission_flags |= permission_mapping[perm]
        
        # Encrypt PDF
        pdf_writer.encrypt(
            user_password=user_password,
            owner_password=owner_password,
            use_128bit=(encryption_level == 128),
            permissions_flag=permission_flags
        )
        
        # Write encrypted PDF
        output = io.BytesIO()
        pdf_writer.write(output)
        output.seek(0)
        
        return output.getvalue()
    
    async def extract_text(
        self,
        pdf_data: bytes,
        pages: Optional[str] = None,
        output_format: str = "text"
    ) -> Dict[str, Any]:
        """Extract text from PDF"""
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        total_pages = len(pdf_document)
        
        # Determine which pages to extract from
        pages_to_extract = self.parse_page_ranges(pages, total_pages) if pages else range(total_pages)
        
        extracted_text = []
        word_count = 0
        
        for page_num in pages_to_extract:
            page = pdf_document[page_num]
            text = page.get_text()
            extracted_text.append({
                "page": page_num + 1,
                "text": text,
                "words": len(text.split())
            })
            word_count += len(text.split())
        
        pdf_document.close()
        
        # Format output
        if output_format == "text":
            result_text = "\n\n".join([f"Page {item['page']}:\n{item['text']}" for item in extracted_text])
            return {
                "text": result_text,
                "word_count": word_count,
                "page_count": len(pages_to_extract)
            }
        elif output_format == "json":
            return {
                "pages": extracted_text,
                "word_count": word_count,
                "page_count": len(pages_to_extract)
            }
        else:  # markdown
            result_text = "\n\n".join([f"## Page {item['page']}\n\n{item['text']}" for item in extracted_text])
            return {
                "text": result_text,
                "word_count": word_count,
                "page_count": len(pages_to_extract)
            }
    
    async def extract_images(
        self,
        pdf_data: bytes,
        pages: Optional[str] = None,
        min_width: int = 100,
        min_height: int = 100,
        image_format: str = "png"
    ) -> List[Dict[str, Any]]:
        """Extract images from PDF"""
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        total_pages = len(pdf_document)
        
        # Determine which pages to extract from
        pages_to_extract = self.parse_page_ranges(pages, total_pages) if pages else range(total_pages)
        
        extracted_images = []
        
        for page_num in pages_to_extract:
            page = pdf_document[page_num]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                pix = fitz.Pixmap(pdf_document, xref)
                
                # Check minimum size
                if pix.width >= min_width and pix.height >= min_height:
                    # Convert to desired format
                    if image_format.lower() in ["jpg", "jpeg"]:
                        img_data = pix.tobytes("jpeg")
                    else:
                        img_data = pix.tobytes("png")
                    
                    extracted_images.append({
                        "page": page_num + 1,
                        "index": img_index,
                        "width": pix.width,
                        "height": pix.height,
                        "data": img_data,
                        "format": image_format
                    })
                
                pix = None
        
        pdf_document.close()
        return extracted_images
    
    async def pdf_to_images(
        self,
        pdf_data: bytes,
        dpi: int = 200,
        image_format: str = "png",
        pages: Optional[str] = None
    ) -> List[bytes]:
        """Convert PDF pages to images"""
        # Save PDF to temporary file (pdf2image requires file path)
        temp_path = await self.save_temp_file(pdf_data)
        
        try:
            # Convert PDF to images
            if pages:
                # Get total pages first
                with open(temp_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    total_pages = len(pdf_reader.pages)
                
                page_list = self.parse_page_ranges(pages, total_pages)
                images = []
                
                for page_num in page_list:
                    page_images = convert_from_path(
                        temp_path,
                        dpi=dpi,
                        first_page=page_num + 1,
                        last_page=page_num + 1,
                        fmt=image_format
                    )
                    images.extend(page_images)
            else:
                images = convert_from_path(temp_path, dpi=dpi, fmt=image_format)
            
            # Convert PIL images to bytes
            image_bytes = []
            for img in images:
                output = io.BytesIO()
                img.save(output, format=image_format.upper())
                output.seek(0)
                image_bytes.append(output.getvalue())
            
            return image_bytes
        finally:
            # Clean up temporary file
            os.unlink(temp_path)
    
    async def images_to_pdf(
        self,
        image_data_list: List[bytes],
        page_size: str = "A4",
        margin: int = 0,
        auto_orient: bool = True
    ) -> bytes:
        """Convert images to PDF"""
        # Page size mapping
        page_sizes = {
            "A4": A4,
            "A3": A3,
            "Letter": letter,
            "Legal": legal,
            "Tabloid": tabloid
        }
        
        page_dims = page_sizes.get(page_size, A4)
        
        # Create PDF
        output = io.BytesIO()
        c = canvas.Canvas(output, pagesize=page_dims)
        
        for img_data in image_data_list:
            # Open image
            img = Image.open(io.BytesIO(img_data))
            
            # Auto-orient if needed
            if auto_orient:
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif:
                        orientation = exif.get(0x0112)
                        if orientation:
                            rotations = {
                                3: 180,
                                6: 270,
                                8: 90
                            }
                            if orientation in rotations:
                                img = img.rotate(rotations[orientation], expand=True)
            
            # Calculate dimensions to fit page
            img_width, img_height = img.size
            page_width, page_height = page_dims
            
            # Apply margins
            available_width = page_width - (2 * margin)
            available_height = page_height - (2 * margin)
            
            # Scale image to fit
            scale = min(available_width / img_width, available_height / img_height)
            new_width = img_width * scale
            new_height = img_height * scale
            
            # Center image on page
            x = margin + (available_width - new_width) / 2
            y = margin + (available_height - new_height) / 2
            
            # Draw image
            img_reader = ImageReader(img)
            c.drawImage(img_reader, x, y, width=new_width, height=new_height)
            c.showPage()
        
        c.save()
        output.seek(0)
        return output.getvalue()
    
    async def get_pdf_metadata(self, pdf_data: bytes) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
        metadata = pdf_reader.metadata if pdf_reader.metadata else {}
        
        # Get page information
        first_page = pdf_reader.pages[0]
        page_box = first_page.mediabox
        
        return {
            "title": metadata.get('/Title', ''),
            "author": metadata.get('/Author', ''),
            "subject": metadata.get('/Subject', ''),
            "creator": metadata.get('/Creator', ''),
            "producer": metadata.get('/Producer', ''),
            "creation_date": metadata.get('/CreationDate', ''),
            "modification_date": metadata.get('/ModDate', ''),
            "pages": len(pdf_reader.pages),
            "file_size": len(pdf_data),
            "encrypted": pdf_reader.is_encrypted,
            "page_size": {
                "width": float(page_box.width),
                "height": float(page_box.height)
            }
        }


# Singleton instance
pdf_service = PDFService()
