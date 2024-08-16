import requests
import base64
import os
import logging
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def text_to_pdf(text, filename):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40
    for line in text.split('\n'):
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(40, y, line)
        y -= 15
    c.save()
    return buffer.getvalue()

def file_to_base64(file_content):
    return base64.b64encode(file_content).decode('utf-8')

def send_to_api(file_path, bot_id):
    api_url = "https://api.ohanapay.app/api/1.1/wf/add_from_transcriber"
    headers = {
        "Content-Type": "application/json",
        "api_key": "6e1526da85f6ac33b8f71cddb55480c2"
    }
    
    if not os.path.exists(file_path):
        logging.error(f"File does not exist: {file_path}")
        return None
    
    logging.info(f"Reading PDF file: {file_path}")
    with open(file_path, 'rb') as file:
        pdf_content = file.read()
    
    logging.info(f"PDF file read. Size: {len(pdf_content)} bytes")
    
    base64_content = file_to_base64(pdf_content)
    logging.info(f"Base64 encoding completed. Encoded size: {len(base64_content)} characters")
    
    pdf_filename = os.path.basename(file_path)
    payload = {
        "transcription_file": {
            "filename": pdf_filename,
            "contents": base64_content
        },
        "bot_id": bot_id
    }
    
    logging.info(f"Sending PDF data to API. Filename: {pdf_filename}")
    logging.info(f"Bot ID: {bot_id}")
    
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        logging.info(f"Data sent successfully to API for {pdf_filename}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending data to API for {pdf_filename}: {e}")
        if hasattr(e.response, 'text'):
            logging.error(f"Response content: {e.response.text}")
        return None

if __name__ == "__main__":
    logging.warning("This script is not meant to be run directly. It should be imported and used by batchtranscribediarizeplusscreenshots.py")