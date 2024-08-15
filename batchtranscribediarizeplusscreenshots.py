#!/usr/bin/env python
# coding: utf-8

import logging
import sys
import requests
import time
import pyaudio
import wave
import signal
import os
import swagger_client
from azure.storage.blob import BlobServiceClient, BlobClient
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import threading
from screenshotter import create_session_folder, select_monitors, take_screenshot
from jsonreader import process_json_files

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
        format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p %Z")

# Your subscription key and region for the speech service
SUBSCRIPTION_KEY = "4dd8f0c6af564bac959370fd1b9df04d"
SERVICE_REGION = "eastus"

# Update these constants with the new information
STORAGE_CONNECTION_STRING = "BlobEndpoint=https://daytranscriber.blob.core.windows.net/;QueueEndpoint=https://daytranscriber.queue.core.windows.net/;FileEndpoint=https://daytranscriber.file.core.windows.net/;TableEndpoint=https://daytranscriber.table.core.windows.net/;SharedAccessSignature=sv=2022-11-02&ss=bfqt&srt=sco&sp=rwdlacupiytfx&se=2024-08-16T16:53:42Z&st=2024-08-10T08:53:42Z&spr=https,http&sig=Pttd6BmGyCFm%2FRx1rQ5dtdtFjY%2BUFWmkgsnR5zVPzK8%3D"

STORAGE_CONTAINER_NAME = "audio-recordings"  # Make sure this is correct

# Add this new constant for the container SAS URL
STORAGE_CONTAINER_SAS_URL = "https://daytranscriber.blob.core.windows.net/audio-recordings?sp=racwdl&st=2024-08-10T08:56:50Z&se=2024-08-16T16:56:50Z&sv=2022-11-02&sr=c&sig=e50nb7KCAOzvRhjMp7ZaCPeWbiW1jQj54kfcf7Q7M%2FE%3D"

NAME = "Simple transcription"
DESCRIPTION = "Simple transcription description"

LOCALE = "en-US"

# Audio recording parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
WAVE_OUTPUT_FILENAME = "output.wav"

# Global flag to control recording
recording = True

# Global flag to control screenshot capture
capturing_screenshots = True

def signal_handler(sig, frame):
    global recording, capturing_screenshots
    print("Ctrl+C pressed. Stopping recording and screenshot capture...")
    recording = False
    capturing_screenshots = False

def record_audio():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("Recording... Press Ctrl+C to stop.")
    frames = []

    while recording:
        data = stream.read(CHUNK)
        frames.append(data)

    print("Recording stopped.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    print(f"Audio saved as {WAVE_OUTPUT_FILENAME}")

def upload_to_blob_storage(local_file_path):
    blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(STORAGE_CONTAINER_NAME)
    blob_name = os.path.basename(local_file_path)
    blob_client = container_client.get_blob_client(blob_name)

    with open(local_file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    return blob_client.url

def download_transcription_results(transcription_id, local_dir="transcription_results"):
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    # Generate timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    base_url = f"https://{SERVICE_REGION}.api.cognitive.microsoft.com/speechtotext/v3.2"
    headers = {"Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY}

    # Get transcription files
    files_url = f"{base_url}/transcriptions/{transcription_id}/files"
    response = requests.get(files_url, headers=headers)
    
    logging.info(f"API Response Status Code: {response.status_code}")
    logging.info(f"API Response Content: {response.text}")

    if response.status_code != 200:
        logging.error(f"Failed to get transcription files. Status code: {response.status_code}")
        return

    files = response.json().get('values', [])
    if not files:
        logging.warning("No files found in the transcription results.")
        return

    for file in files:
        file_url = file['links']['contentUrl']
        original_file_name = file['name']
        
        # Create a new filename with the timestamp only for JSON files
        if original_file_name.endswith('.json'):
            file_name = f"{timestamp}_{original_file_name}"
        else:
            file_name = original_file_name
        file_path = os.path.join(local_dir, file_name)

        # Construct the full SAS URL
        sas_url = f"{file_url}?{STORAGE_CONTAINER_SAS_URL.split('?')[1]}"

        # Download file content using BlobClient
        blob_client = BlobClient.from_blob_url(sas_url)
        
        try:
            with open(file_path, "wb") as file:
                blob_data = blob_client.download_blob()
                blob_data.readinto(file)
            logging.info(f"Downloaded file: {file_name}")

            # If it's a JSON file, let's print its content
            if file_name.endswith('.json'):
                with open(file_path, 'r') as f:
                    content = json.load(f)
                logging.info(f"Content of {file_name}:")
                logging.info(json.dumps(content, indent=2))
        except Exception as e:
            logging.error(f"Failed to download {file_name}. Error: {str(e)}")

    logging.info("Finished downloading transcription results")

def download_json_from_blob(sas_url):
    # Create a BlobClient
    blob_client = BlobClient.from_blob_url(sas_url)

    # Download the blob content
    blob_data = blob_client.download_blob()

    # Read the content as text
    json_content = blob_data.content_as_text()

    # Parse the JSON
    data = json.loads(json_content)

    # Now you can work with your JSON data
    return data

def get_max_speakers():
    while True:
        try:
            max_speakers = int(input("How many speakers? "))
            if max_speakers > 0:
                return max_speakers
            else:
                print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")

def transcribe(blob_uri, max_speakers):
    logging.info("Starting transcription client...")

    # configure API key authorization: subscription_key
    configuration = swagger_client.Configuration()
    configuration.api_key["Ocp-Apim-Subscription-Key"] = SUBSCRIPTION_KEY
    configuration.host = f"https://{SERVICE_REGION}.api.cognitive.microsoft.com/speechtotext/v3.2"

    # create the client object and authenticate
    client = swagger_client.ApiClient(configuration)

    # create an instance of the transcription api class
    api = swagger_client.CustomSpeechTranscriptionsApi(api_client=client)

    # Specify transcription properties
    properties = swagger_client.TranscriptionProperties(
        diarization_enabled=True,
        diarization=swagger_client.DiarizationProperties(
            speakers=swagger_client.DiarizationSpeakersProperties(min_count=1, max_count=max_speakers)
        ),
        word_level_timestamps_enabled=True,
        display_form_word_level_timestamps_enabled=True,
        punctuation_mode="DictatedAndAutomatic",
        profanity_filter_mode="Masked",
        destination_container_url=STORAGE_CONTAINER_SAS_URL,
        time_to_live="PT1H"
    )

    transcription_definition = swagger_client.Transcription(
        content_urls=[blob_uri],
        locale=LOCALE,
        display_name=NAME,
        properties=properties
    )

    created_transcription, status, headers = api.transcriptions_create_with_http_info(transcription=transcription_definition)

    # get the transcription Id from the location URI
    transcription_id = headers["location"].split("/")[-1]

    logging.info(f"Created new transcription with id '{transcription_id}' in region {SERVICE_REGION}")

    logging.info("Checking status.")

    completed = False

    while not completed:
        time.sleep(5)
        transcription = api.transcriptions_get(transcription_id)
        logging.info(f"Transcriptions status: {transcription.status}")

        if transcription.status in ("Failed", "Succeeded"):
            completed = True

        if transcription.status == "Succeeded":
            logging.info("Transcription succeeded. Downloading results...")
            download_transcription_results(transcription_id)
            break
        elif transcription.status == "Failed":
            logging.error(f"Transcription failed: {transcription.properties.error.message}")

def screenshot_thread(session_folder, selected_monitors):
    global capturing_screenshots
    while capturing_screenshots:
        take_screenshot(session_folder, selected_monitors)
        time.sleep(10)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start screenshot capture
    screenshot_session_folder = create_session_folder()
    print(f"Saving screenshots to: {screenshot_session_folder}")
    selected_monitors = select_monitors()
    print(f"Selected monitors: {[i+1 for i in selected_monitors]}")
    
    screenshot_thread = threading.Thread(target=screenshot_thread, args=(screenshot_session_folder, selected_monitors))
    screenshot_thread.start()
    
    max_speakers = get_max_speakers()
    
    record_audio()
    
    # Stop screenshot capture
    capturing_screenshots = False
    screenshot_thread.join()
    
    if os.path.exists(WAVE_OUTPUT_FILENAME):
        try:
            blob_uri = upload_to_blob_storage(WAVE_OUTPUT_FILENAME)
            logging.info(f"Audio file uploaded. URI: {blob_uri}")
            transcribe(blob_uri, max_speakers)
            
            # Process JSON files and save transcriptions to screenshot folder
            process_json_files("transcription_results", screenshot_session_folder)
        except Exception as e:
            logging.error(f"An error occurred during transcription process: {e}")
            logging.exception("Exception details:")
    else:
        logging.error("No audio file recorded. Exiting.")

    print("Screenshot capture, audio recording, and transcription processing completed.")