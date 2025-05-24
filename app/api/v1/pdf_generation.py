from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, Dict
import time
import tempfile
from io import BytesIO
from datetime import datetime

from app.core.dependencies import (
    verify_api_key,
    get_file_url
)
from app.models.requests import PDFRequest
from app.models.responses import (
    PDFResponse,
    TemplateListResponse
)
from app.core.config import settings
from playwright.async_api import async_playwright

router = APIRouter(prefix="/pdf", tags=["PDF Generation"])


# Templates from original app
TEMPLATES = {
    "invoice": """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { display: flex; justify-content: space-between; margin-bottom: 40px; }
            .invoice-title { font-size: 32px; font-weight: bold; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            .total { font-size: 20px; font-weight: bold; text-align: right; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <div class="invoice-title">INVOICE</div>
                <div>Invoice #: {{invoice_number}}</div>
                <div>Date: {{date}}</div>
            </div>
            <div style="text-align: right;">
                <div><strong>{{company_name}}</strong></div>
                <div>{{company_address}}</div>
            </div>
        </div>
        
        <div style="margin-bottom: 30px;">
            <strong>Bill To:</strong><br>
            {{customer_name}}<br>
            {{customer_address}}
        </div>
        
        <table>
            <tr>
                <th>Description</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>Total</th>
            </tr>
            {{#items}}
            <tr>
                <td>{{description}}</td>
                <td>{{quantity}}</td>
                <td>${{price}}</td>
                <td>${{total}}</td>
            </tr>
            {{/items}}
        </table>
        
        <div class="total">
            Total: ${{total_amount}}
        </div>
    </body>
    </html>
    """,
    
    "report": """
    <html>
    <head>
        <style>
            body { font-family: Georgia, serif; margin: 40px; line-height: 1.6; }
            h1 { color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }
            h2 { color: #666; margin-top: 30px; }
            .meta { color: #999; font-style: italic; margin-bottom: 30px; }
        </style>
    </head>
    <body>
        <h1>{{title}}</h1>
        <div class="meta">{{author}} | {{date}}</div>
        
        {{#sections}}
        <h2>{{heading}}</h2>
        <p>{{content}}</p>
        {{/sections}}
    </body>
    </html>
    """,
    
    "certificate": """
    <html>
    <head>
        <style>
            body { 
                font-family: 'Times New Roman', serif; 
                margin: 0; 
                padding: 40px;
                text-align: center;
                background: linear-gradient(45deg, #f0f0f0 25%, transparent 25%, transparent 75%, #f0f0f0 75%, #f0f0f0),
                            linear-gradient(45deg, #f0f0f0 25%, transparent 25%, transparent 75%, #f0f0f0 75%, #f0f0f0);
                background-size: 20px 20px;
                background-position: 0 0, 10px 10px;
            }
            .certificate {
                background: white;
                border: 10px solid #4a90e2;
                padding: 50px;
                max-width: 800px;
                margin: 0 auto;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
            }
            h1 { 
                font-size: 48px; 
                color: #2c3e50;
                margin-bottom: 20px;
                text-transform: uppercase;
                letter-spacing: 3px;
            }
            .recipient { 
                font-size: 36px; 
                color: #4a90e2;
                margin: 30px 0;
                font-style: italic;
            }
            .description {
                font-size: 20px;
                color: #555;
                margin: 20px 0;
                line-height: 1.5;
            }
            .date {
                font-size: 18px;
                color: #777;
                margin-top: 40px;
            }
            .signatures {
                display: flex;
                justify-content: space-around;
                margin-top: 60px;
            }
            .signature {
                text-align: center;
            }
            .signature-line {
                width: 200px;
                border-bottom: 2px solid #333;
                margin: 0 auto 10px;
            }
        </style>
    </head>
    <body>
        <div class="certificate">
            <h1>Certificate of {{achievement}}</h1>
            <p class="description">This is to certify that</p>
            <p class="recipient">{{recipient_name}}</p>
            <p class="description">{{description}}</p>
            <p class="date">{{date}}</p>
            
            <div class="signatures">
                <div class="signature">
                    <div class="signature-line"></div>
                    <p>{{signature1_name}}<br>{{signature1_title}}</p>
                </div>
                <div class="signature">
                    <div class="signature-line"></div>
                    <p>{{signature2_name}}<br>{{signature2_title}}</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """,
    
    "resume": """
    <html>
    <head>
        <style>
            body { 
                font-family: 'Helvetica Neue', Arial, sans-serif; 
                margin: 0;
                padding: 30px;
                color: #333;
                line-height: 1.6;
            }
            .header {
                border-bottom: 3px solid #2c3e50;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }
            h1 {
                margin: 0;
                color: #2c3e50;
                font-size: 36px;
            }
            .contact {
                color: #666;
                font-size: 14px;
                margin-top: 10px;
            }
            h2 {
                color: #2c3e50;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
                margin-top: 30px;
                font-size: 24px;
            }
            .job {
                margin-bottom: 25px;
            }
            .job-title {
                font-weight: bold;
                font-size: 18px;
                color: #34495e;
            }
            .company {
                color: #7f8c8d;
                font-style: italic;
            }
            .date {
                color: #95a5a6;
                font-size: 14px;
                float: right;
            }
            ul {
                margin: 10px 0;
                padding-left: 20px;
            }
            .skills {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-top: 10px;
            }
            .skill {
                background: #ecf0f1;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{{name}}</h1>
            <div class="contact">{{email}} | {{phone}} | {{location}}</div>
        </div>
        
        <h2>Professional Summary</h2>
        <p>{{summary}}</p>
        
        <h2>Experience</h2>
        {{#experience}}
        <div class="job">
            <div class="date">{{start_date}} - {{end_date}}</div>
            <div class="job-title">{{position}}</div>
            <div class="company">{{company}}</div>
            <ul>
                {{#achievements}}
                <li>{{.}}</li>
                {{/achievements}}
            </ul>
        </div>
        {{/experience}}
        
        <h2>Education</h2>
        {{#education}}
        <div class="job">
            <div class="date">{{graduation_year}}</div>
            <div class="job-title">{{degree}}</div>
            <div class="company">{{institution}}</div>
        </div>
        {{/education}}
        
        <h2>Skills</h2>
        <div class="skills">
            {{#skills}}
            <span class="skill">{{.}}</span>
            {{/skills}}
        </div>
    </body>
    </html>
    """
}


def render_template(template_name: str, data: dict) -> str:
    """Simple template rendering"""
    template = TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"Template '{template_name}' not found")
    
    # Deep copy template to avoid modifying original
    rendered = template
    
    # Handle arrays/lists
    import re
    array_pattern = r'\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}'
    matches = re.findall(array_pattern, rendered, re.DOTALL)
    
    for key, content in matches:
        if key in data and isinstance(data[key], list):
            array_html = ""
            for item in data[key]:
                item_html = content
                if isinstance(item, dict):
                    for k, v in item.items():
                        item_html = item_html.replace(f"{{{{{k}}}}}", str(v))
                else:
                    item_html = item_html.replace("{{.}}", str(item))
                array_html += item_html
            
            rendered = rendered.replace(f"{{{{#{key}}}}}{content}{{{{/{key}}}}}", array_html)
    
    # Handle simple replacements
    for key, value in data.items():
        if not isinstance(value, list):
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    
    return rendered


async def generate_pdf(content: str, options: dict = None) -> bytes:
    """Generate PDF using Playwright"""
    options = options or {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Load content
        if content.startswith(('http://', 'https://')):
            await page.goto(content, wait_until='networkidle')
        else:
            await page.set_content(content, wait_until='networkidle')
        
        # PDF options
        pdf_options = {
            'format': options.get('format', 'A4'),
            'print_background': options.get('print_background', True),
            'margin': options.get('margin', {'top': '1cm', 'bottom': '1cm', 'left': '1cm', 'right': '1cm'}),
            'scale': options.get('scale', 1),
        }
        
        if 'header_template' in options:
            pdf_options['display_header_footer'] = True
            pdf_options['header_template'] = options['header_template']
        
        if 'footer_template' in options:
            pdf_options['display_header_footer'] = True
            pdf_options['footer_template'] = options['footer_template']
        
        # Generate PDF
        pdf_bytes = await page.pdf(**pdf_options)
        await browser.close()
        
        return pdf_bytes


@router.post("/generate", response_model=PDFResponse)
async def create_pdf(
    request: PDFRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Generate a PDF from HTML, URL, or template.
    
    - **html**: HTML content to convert to PDF
    - **url**: URL to convert to PDF
    - **template**: Template name to use (invoice, report, certificate, resume)
    - **data**: Data to populate the template
    - **options**: PDF generation options (format, margins, etc.)
    """
    start_time = time.time()
    
    try:
        # Determine content source
        if request.html:
            content = request.html
        elif request.url:
            content = request.url
        elif request.template and request.data:
            content = render_template(request.template, request.data)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Provide either 'html', 'url', or 'template' with 'data'"
            )
        
        # Generate PDF
        pdf_bytes = await generate_pdf(content, request.options)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            dir=settings.TEMP_DIR,
            suffix=".pdf",
            prefix="generated_"
        )
        temp_file.write(pdf_bytes)
        temp_file.close()
        
        # Get page count (simplified)
        import PyPDF2
        with open(temp_file.name, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            page_count = len(pdf_reader.pages)
        
        processing_time = time.time() - start_time
        
        return PDFResponse(
            file_url=get_file_url(temp_file.name),
            file_size=len(pdf_bytes),
            pages=page_count,
            processing_time=processing_time,
            message="PDF generated successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(api_key: str = Depends(verify_api_key)):
    """
    List available PDF templates.
    
    Returns a list of template names and their descriptions.
    """
    return TemplateListResponse(
        templates=list(TEMPLATES.keys()),
        details={
            "invoice": "Professional invoice template with itemized billing",
            "report": "Business report template with sections",
            "certificate": "Achievement certificate with signatures",
            "resume": "Modern resume/CV template"
        },
        message="Templates retrieved successfully"
    )


@router.get("/templates/{template_name}")
async def get_template_preview(
    template_name: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get template HTML preview and sample data structure.
    
    Returns the template HTML and a sample data structure that can be used
    to populate the template.
    """
    if template_name not in TEMPLATES:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template_name}' not found"
        )
    
    # Sample data structures for each template
    sample_data = {
        "invoice": {
            "invoice_number": "INV-001",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "company_name": "Your Company",
            "company_address": "123 Business St, City, Country",
            "customer_name": "Customer Name",
            "customer_address": "456 Client Ave, City, Country",
            "items": [
                {
                    "description": "Product/Service 1",
                    "quantity": 2,
                    "price": 100.00,
                    "total": 200.00
                },
                {
                    "description": "Product/Service 2",
                    "quantity": 1,
                    "price": 150.00,
                    "total": 150.00
                }
            ],
            "total_amount": 350.00
        },
        "report": {
            "title": "Annual Report 2024",
            "author": "John Doe",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "sections": [
                {
                    "heading": "Executive Summary",
                    "content": "This report provides an overview of our achievements..."
                },
                {
                    "heading": "Financial Performance",
                    "content": "Our financial results for the year show..."
                }
            ]
        },
        "certificate": {
            "achievement": "Excellence",
            "recipient_name": "Jane Smith",
            "description": "has successfully completed the Advanced Training Program with distinction",
            "date": datetime.now().strftime("%B %d, %Y"),
            "signature1_name": "Dr. John Doe",
            "signature1_title": "Program Director",
            "signature2_name": "Jane Johnson",
            "signature2_title": "CEO"
        },
        "resume": {
            "name": "John Doe",
            "email": "john.doe@email.com",
            "phone": "+1 (555) 123-4567",
            "location": "New York, NY",
            "summary": "Experienced software engineer with 5+ years...",
            "experience": [
                {
                    "position": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "start_date": "2020",
                    "end_date": "Present",
                    "achievements": [
                        "Led development of microservices architecture",
                        "Improved system performance by 40%"
                    ]
                }
            ],
            "education": [
                {
                    "degree": "Bachelor of Computer Science",
                    "institution": "University Name",
                    "graduation_year": "2018"
                }
            ],
            "skills": ["Python", "JavaScript", "Docker", "AWS", "React"]
        }
    }
    
    return {
        "template_name": template_name,
        "template_html": TEMPLATES[template_name],
        "sample_data": sample_data.get(template_name, {}),
        "description": f"Template for creating {template_name} PDFs"
    }


# Direct streaming endpoint
@router.post("/generate/stream")
async def create_pdf_stream(
    request: PDFRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Generate a PDF and return it as a direct stream (no file storage).
    
    Same parameters as /generate but returns the PDF directly for download.
    """
    try:
        # Determine content source
        if request.html:
            content = request.html
        elif request.url:
            content = request.url
        elif request.template and request.data:
            content = render_template(request.template, request.data)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Provide either 'html', 'url', or 'template' with 'data'"
            )
        
        # Generate PDF
        pdf_bytes = await generate_pdf(content, request.options)
        
        # Return as stream
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=document_{int(time.time())}.pdf"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
