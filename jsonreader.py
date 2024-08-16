import json
import matplotlib.pyplot as plt
import os
import logging
from datetime import datetime
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

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

def parse_transcription(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    confidence_scores = []
    transcript = []
    
    if 'recognizedPhrases' in data:
        for segment in data['recognizedPhrases']:
            speaker = segment['speaker']
            start_time = segment['offset']
            text = segment['nBest'][0]['display']
            confidence = segment['nBest'][0]['confidence']
            
            transcript.append(f"Speaker {speaker} ({start_time}): {text}")
            confidence_scores.append(confidence)
    else:
        logging.warning(f"No recognized phrases found in {json_file}")
    
    return transcript, confidence_scores

def process_json_files(input_directory, output_directory):
    json_files = [f for f in os.listdir(input_directory) if f.endswith('contenturl_0.json')]
    if not json_files:
        logging.warning("No contenturl_0.json files found in the input directory.")
        return None

    # Get the most recent contenturl_0.json file
    latest_json = max(json_files, key=lambda x: os.path.getctime(os.path.join(input_directory, x)))
    json_file_path = os.path.join(input_directory, latest_json)
    
    logging.info(f"Processing most recent JSON file: {latest_json}")

    transcript, confidence_scores = parse_transcription(json_file_path)
    
    if not transcript:
        logging.warning(f"No transcription data found in {latest_json}")
        return None

    # Create transcript file
    transcript_filename = f"transcript_{os.path.splitext(latest_json)[0]}.txt"
    output_file = os.path.join(output_directory, transcript_filename)
    
    with open(output_file, 'w') as out:
        out.write("\n".join(transcript))
    
    logging.info(f"Readable transcription saved to {output_file}")

    # Create and save PDF
    pdf_filename = f"transcript_{os.path.splitext(latest_json)[0]}.pdf"
    pdf_path = os.path.join(output_directory, pdf_filename)
    pdf_content = text_to_pdf("\n".join(transcript), pdf_filename)
    
    with open(pdf_path, 'wb') as pdf_file:
        pdf_file.write(pdf_content)
    
    logging.info(f"PDF transcription saved to {pdf_path}")

    # Plot confidence scores
    plt.figure(figsize=(10, 5))
    plt.plot(confidence_scores)
    plt.title(f'Confidence Scores for {latest_json}')
    plt.xlabel('Segment Index')
    plt.ylabel('Confidence Score')
    plt.ylim(0, 1)
    plt.savefig(os.path.join(output_directory, f'confidence_scores_{os.path.splitext(latest_json)[0]}.png'))
    plt.close()
    
    logging.info(f"Confidence score graph saved as confidence_scores_{os.path.splitext(latest_json)[0]}.png")

    return pdf_path

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    current_dir = os.path.dirname(os.path.abspath(__file__))
    latest_transcript = process_json_files(current_dir, current_dir)
    logging.info(f"Latest transcript file: {latest_transcript}")