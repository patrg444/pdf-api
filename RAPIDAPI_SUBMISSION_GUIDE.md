# 🚀 RapidAPI Submission Guide

## Step 1: Get Your RapidAPI Proxy Secret

1. In RapidAPI Provider Dashboard, look for:
   - **Settings** → **Security** → **Proxy Secret**
   - Or it might be under **API Settings**
2. Copy this secret
3. Go back to Railway → Variables → Add:
   ```
   RAPIDAPI_PROXY_SECRET=your-copied-secret-here
   ```

## Step 2: Add New API

Click "Add New API" and fill in:

### Basic Information:
- **API Name**: Lightning PDF API
- **Category**: Tools
- **Short Description**: 
  ```
  Comprehensive PDF processing API - Generate PDFs from HTML/URLs, merge/split files, compress, watermark, extract text/images, and more.
  ```
- **Base URL**: Your Railway URL (something like `https://peaceful-smile-production.up.railway.app`)

### Tags (Add these):
- pdf
- pdf-api
- pdf-generator
- pdf-converter
- pdf-merger
- document-processing
- html-to-pdf

## Step 3: Add Endpoints

Copy these from `rapidapi-config.json`. Add each one:

### 1. Generate PDF
- **Path**: `/api/v1/pdf/generate`
- **Method**: POST
- **Description**: Generate PDF from HTML, URL, or pre-built templates

### 2. List Templates
- **Path**: `/api/v1/pdf/templates`
- **Method**: GET
- **Description**: Get list of available PDF templates

### 3. Merge PDFs
- **Path**: `/api/v1/pdf/merge`
- **Method**: POST
- **Description**: Merge multiple PDF files into one

### 4. Split PDF
- **Path**: `/api/v1/pdf/split`
- **Method**: POST
- **Description**: Split PDF by page ranges or into chunks

### 5. Compress PDF
- **Path**: `/api/v1/pdf/compress`
- **Method**: POST
- **Description**: Reduce PDF file size with configurable quality

### 6. Rotate PDF
- **Path**: `/api/v1/pdf/rotate`
- **Method**: POST
- **Description**: Rotate PDF pages

### 7. Add Watermark
- **Path**: `/api/v1/pdf/watermark`
- **Method**: POST
- **Description**: Add text or image watermark to PDF

### 8. Secure PDF
- **Path**: `/api/v1/pdf/secure`
- **Method**: POST
- **Description**: Add password protection and permissions to PDF

### 9. Extract Text
- **Path**: `/api/v1/pdf/extract/text`
- **Method**: POST
- **Description**: Extract text content from PDF

### 10. Extract Images
- **Path**: `/api/v1/pdf/extract/images`
- **Method**: POST
- **Description**: Extract images from PDF

### 11. Get Metadata
- **Path**: `/api/v1/pdf/extract/metadata`
- **Method**: POST
- **Description**: Extract metadata from PDF

### 12. PDF to Images
- **Path**: `/api/v1/pdf/to/images`
- **Method**: POST
- **Description**: Convert PDF pages to images

### 13. Images to PDF
- **Path**: `/api/v1/pdf/from/images`
- **Method**: POST
- **Description**: Convert images to PDF

### 14. Check Usage
- **Path**: `/api/v1/usage`
- **Method**: GET
- **Description**: Check API usage and limits

## Step 4: Set Pricing Plans

Configure these tiers:

### Basic (Free)
- **Price**: $0
- **Requests**: 100/day
- **Rate Limit**: 20 requests/minute

### Pro
- **Price**: $29/month
- **Requests**: 3,000/month
- **Rate Limit**: 100 requests/minute

### Ultra
- **Price**: $99/month
- **Requests**: 30,000/month
- **Rate Limit**: 1,000 requests/minute

### Mega
- **Price**: $299/month
- **Requests**: Unlimited
- **Rate Limit**: 10,000 requests/minute

## Step 5: Add Code Examples

For the Generate PDF endpoint, add this Python example:

```python
import requests

url = "https://your-api.p.rapidapi.com/api/v1/pdf/generate"

payload = {
    "html": "<h1>Hello World</h1><p>This is a PDF!</p>",
    "options": {
        "format": "A4",
        "margin": {"top": "2cm", "bottom": "2cm"}
    }
}

headers = {
    "content-type": "application/json",
    "X-RapidAPI-Key": "YOUR-RAPIDAPI-KEY",
    "X-RapidAPI-Host": "your-api.p.rapidapi.com"
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

## Step 6: Submit for Review

1. Review all information
2. Click "Submit for Review"
3. Wait 1-3 business days for approval

## 📋 Quick Checklist:

- [ ] Added RAPIDAPI_PROXY_SECRET to Railway
- [ ] Set correct Base URL from Railway
- [ ] Added all 14 endpoints
- [ ] Set up 4 pricing tiers
- [ ] Added code examples
- [ ] Submitted for review

## 🎉 That's It!

Once approved, your API will be available on RapidAPI marketplace and you'll start getting subscribers!
