# Lightning PDF API 🚀

A comprehensive, high-performance PDF API service that provides PDF generation, manipulation, extraction, and conversion capabilities. Built with FastAPI and designed for scalability.

## Features ✨

### PDF Generation
- Convert HTML to PDF
- Convert URLs to PDF
- Use pre-built templates (Invoice, Report, Certificate, Resume)
- Custom headers and footers
- Full control over page size, margins, and formatting

### PDF Manipulation
- **Merge** - Combine multiple PDFs into one
- **Split** - Extract pages or split into chunks
- **Compress** - Reduce file size with configurable quality
- **Rotate** - Rotate pages at any angle
- **Watermark** - Add text or image watermarks
- **Secure** - Password protection and permissions

### PDF Extraction
- Extract text (plain text, JSON, or Markdown format)
- Extract images with filtering options
- Extract metadata (title, author, creation date, etc.)

### PDF Conversion
- Convert PDF pages to images (PNG, JPEG)
- Convert images to PDF
- Batch processing support

## Tech Stack 🛠️

- **FastAPI** - Modern, fast web framework
- **Redis** - Caching and rate limiting
- **Playwright** - HTML to PDF conversion
- **PyPDF2** - PDF manipulation
- **PyMuPDF** - Advanced PDF processing
- **pdf2image** - PDF to image conversion
- **Stripe** - Payment processing
- **Docker** - Containerization

## Quick Start 🏃‍♂️

### Prerequisites
- Python 3.8+
- Redis
- Docker (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pdf-api.git
cd pdf-api
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

5. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. Start Redis:
```bash
docker run -d -p 6379:6379 redis:alpine
```

7. Run the application:
```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

## API Documentation 📚

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication 🔐

All API endpoints require authentication using an API key. Include your API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your_api_key_here" http://localhost:8000/api/v1/pdf/generate
```

## Usage Examples 💡

### Generate PDF from HTML
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/pdf/generate",
    headers={"X-API-Key": "your_api_key"},
    json={
        "html": "<h1>Hello World</h1><p>This is a PDF!</p>",
        "options": {
            "format": "A4",
            "margin": {"top": "2cm", "bottom": "2cm"}
        }
    }
)
```

### Merge Multiple PDFs
```python
import requests

files = [
    ('files', open('doc1.pdf', 'rb')),
    ('files', open('doc2.pdf', 'rb')),
    ('files', open('doc3.pdf', 'rb'))
]

response = requests.post(
    "http://localhost:8000/api/v1/pdf/merge",
    headers={"X-API-Key": "your_api_key"},
    files=files,
    data={"order": "2,0,1"}  # Optional: reorder files
)
```

### Split PDF by Pages
```python
response = requests.post(
    "http://localhost:8000/api/v1/pdf/split",
    headers={"X-API-Key": "your_api_key"},
    files={"file": open("document.pdf", "rb")},
    data={"pages": "1-3,5,7-10"}  # Extract specific pages
)
```

### Compress PDF
```python
response = requests.post(
    "http://localhost:8000/api/v1/pdf/compress",
    headers={"X-API-Key": "your_api_key"},
    files={"file": open("large.pdf", "rb")},
    data={
        "level": "high",  # low, medium, high, extreme
        "dpi": 150
    }
)
```

### Extract Text from PDF
```python
response = requests.post(
    "http://localhost:8000/api/v1/pdf/extract/text",
    headers={"X-API-Key": "your_api_key"},
    files={"file": open("document.pdf", "rb")},
    data={
        "format": "json",  # text, json, or markdown
        "pages": "1-5"
    }
)
```

### Convert PDF to Images
```python
response = requests.post(
    "http://localhost:8000/api/v1/pdf/to/images",
    headers={"X-API-Key": "your_api_key"},
    files={"file": open("document.pdf", "rb")},
    data={
        "format": "png",
        "dpi": 300
    }
)
```

## Pricing Plans 💰

- **Basic** - $29/month
  - 100 PDFs per hour
  - Core features
  
- **Pro** - $99/month
  - 1,000 PDFs per hour
  - All features including compression, watermarking, and security
  
- **Enterprise** - $299/month
  - 10,000 PDFs per hour
  - Priority support
  - Custom features

## Docker Deployment 🐳

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t pdf-api .
docker run -p 8000:8000 --env-file .env pdf-api
```

## Environment Variables 🔧

```env
# API Settings
SECRET_KEY=your-secret-key-here

# Redis
REDIS_URL=redis://localhost:6379

# Stripe (for payments)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# AWS S3 (optional, for file storage)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
S3_BUCKET=your-bucket

# Rate Limits
RATE_LIMIT_BASIC=100
RATE_LIMIT_PRO=1000
RATE_LIMIT_ENTERPRISE=10000
```

## Development 🛠️

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black app/
flake8 app/
```

### Project Structure
```
PDF-API/
├── app/
│   ├── api/v1/         # API endpoints
│   ├── core/           # Core configuration
│   ├── models/         # Pydantic models
│   ├── services/       # Business logic
│   └── main.py         # Application entry
├── tests/              # Test files
├── docs/               # Additional documentation
├── requirements.txt    # Dependencies
├── Dockerfile         # Docker configuration
└── README.md          # This file
```

## API Endpoints 🔌

### PDF Generation
- `POST /api/v1/pdf/generate` - Generate PDF from HTML/URL/template
- `GET /api/v1/pdf/templates` - List available templates
- `GET /api/v1/pdf/templates/{name}` - Get template details

### PDF Manipulation
- `POST /api/v1/pdf/merge` - Merge multiple PDFs
- `POST /api/v1/pdf/split` - Split PDF
- `POST /api/v1/pdf/compress` - Compress PDF
- `POST /api/v1/pdf/rotate` - Rotate pages
- `POST /api/v1/pdf/watermark` - Add watermark
- `POST /api/v1/pdf/secure` - Add password/permissions

### PDF Extraction
- `POST /api/v1/pdf/extract/text` - Extract text
- `POST /api/v1/pdf/extract/images` - Extract images
- `POST /api/v1/pdf/extract/metadata` - Get metadata

### PDF Conversion
- `POST /api/v1/pdf/to/images` - Convert to images
- `POST /api/v1/pdf/from/images` - Create from images

### Account Management
- `POST /api/v1/keys` - Create API key
- `GET /api/v1/usage` - Check usage/limits
- `GET /health` - Health check

## Contributing 🤝

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Support 💬

- Documentation: [https://docs.pdfapi.example.com](https://docs.pdfapi.example.com)
- Email: support@pdfapi.example.com
- Issues: [GitHub Issues](https://github.com/yourusername/pdf-api/issues)

---

Made with ❤️ by the Lightning PDF API Team
