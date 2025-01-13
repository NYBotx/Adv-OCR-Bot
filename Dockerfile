# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables to avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory inside the container
WORKDIR /app

# Install dependencies for Tesseract OCR and the required languages
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
    tesseract-ocr-yid \
    && apt-get clean

# Copy requirements.txt to the container and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . /app/

# Expose the application port (optional, if you're using Flask or another web server)
EXPOSE 8080

# Command to run the application (if using a script as entry point)
CMD ["python", "main.py"]
