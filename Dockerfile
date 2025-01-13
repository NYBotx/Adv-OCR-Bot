FROM python:3.9-slim

# Install required system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-fra \
    tesseract-ocr-spa \
    tesseract-ocr-deu \
    tesseract-ocr-ita \
    tesseract-ocr-por \
    tesseract-ocr-rus \
    tesseract-ocr-chi-sim \
    tesseract-ocr-jpn \
    tesseract-ocr-kor \
    tesseract-ocr-ara \
    tesseract-ocr-tur \
    tesseract-ocr-ben \
    tesseract-ocr-tam \
    tesseract-ocr-tel \
    tesseract-ocr-mar \
    tesseract-ocr-guj \
    tesseract-ocr-kan \
    tesseract-ocr-mal \
    tesseract-ocr-pol \
    tesseract-ocr-swe \
    tesseract-ocr-dut \
    tesseract-ocr-vie \
    tesseract-ocr-ukr \
    tesseract-ocr-hrv \
    tesseract-ocr-ces \
    tesseract-ocr-bul \
    tesseract-ocr-ell \
    tesseract-ocr-tha \
    tesseract-ocr-ind \
    tesseract-ocr-lav \
    tesseract-ocr-lit \
    tesseract-ocr-est \
    tesseract-ocr-slk \
    tesseract-ocr-fin \
    tesseract-ocr-heb \
    tesseract-ocr-mal \
    tesseract-ocr-srp \
    tesseract-ocr-ron \
    tesseract-ocr-mkd \
    tesseract-ocr-swa \
    tesseract-ocr-eng-old \
    tesseract-ocr-yid

# Set environment variables
ENV LANG C.UTF-8

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Set working directory
WORKDIR /app

# Expose necessary ports if needed (depends on your application)
EXPOSE 8080

# Start the application (Modify if needed)
CMD ["python", "main.py"]
