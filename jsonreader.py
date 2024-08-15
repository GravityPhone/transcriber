import json
import matplotlib.pyplot as plt
import os
from datetime import datetime

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
        print(f"No recognized phrases found in {json_file}")
    
    return transcript, confidence_scores

def process_json_files(input_directory, output_directory):
    for filename in os.listdir(input_directory):
        if filename.endswith('.json'):
            json_file = os.path.join(input_directory, filename)
            
            # Check if a corresponding transcript already exists
            transcript_filename = f"transcript_{os.path.splitext(filename)[0]}.txt"
            if os.path.exists(os.path.join(output_directory, transcript_filename)):
                print(f"Transcript for {filename} already exists. Skipping.")
                continue
            
            transcript, confidence_scores = parse_transcription(json_file)
            
            if transcript:  # Only proceed if there are transcripts
                # Create output file (without timestamp)
                output_file = os.path.join(output_directory, transcript_filename)
                
                with open(output_file, 'w') as out:
                    out.write("\n".join(transcript))
                
                # Plot confidence scores
                plt.figure(figsize=(10, 5))
                plt.plot(confidence_scores)
                plt.title(f'Confidence Scores for {filename}')
                plt.xlabel('Segment Index')
                plt.ylabel('Confidence Score')
                plt.ylim(0, 1)
                plt.savefig(os.path.join(output_directory, f'confidence_scores_{os.path.splitext(filename)[0]}.png'))
                plt.close()
                
                print(f"Readable transcription saved to {output_file}")
                print(f"Confidence score graph saved as confidence_scores_{os.path.splitext(filename)[0]}.png")
            else:
                print(f"No transcription data to save for {filename}")

# Usage (when run standalone)
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    process_json_files(current_dir, current_dir)