
import os

import sys

import argparse

import time

import speech_recognition as sr

from pydub import AudioSegment

import re

import json

from datetime import datetime

import requests
import subprocess


class StreamTranscriber:

    def __init__(self):

        self.temp_dir = "temp_audio"

        # Create temp directory if it doesn't exist

        if not os.path.exists(self.temp_dir):

            os.makedirs(self.temp_dir)

            

    def validate_youtube_url(self, url):

        """Validate if the URL is a YouTube URL"""

        youtube_regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+'

        return bool(re.match(youtube_regex, url))

    

    def extract_youtube_stream_url(self, youtube_url):

        """Extract m3u8 stream URL from YouTube live video"""

        try:

            print(f"🔍 Extracting stream URL from YouTube: {youtube_url}")

            

            # Using youtube-dl to get the best audio format

            cmd = [

                "youtube-dl", 

                "--format", "bestaudio", 

                "--get-url",

                youtube_url

            ]

            

            result = subprocess.run(cmd, capture_output=True, text=True)

            

            if result.returncode != 0:

                print(f"❌ Error extracting YouTube URL: {result.stderr}")

                return None

                

            stream_url = result.stdout.strip()

            print(f"✅ Successfully extracted stream URL")

            return stream_url

            

        except Exception as e:

            print(f"❌ Error extracting YouTube stream URL: {str(e)}")

            return None

    

    def download_audio_from_stream(self, stream_url, duration=120, output_file=None):

        """Download audio from a stream URL (m3u8) for specified duration"""

        try:

            if output_file is None:

                output_file = os.path.join(self.temp_dir, f"stream_audio_{int(time.time())}.mp3")

                

            print(f"🎤 Recording {duration} seconds of live audio...")

            

            cmd_ffmpeg = [

                "ffmpeg", "-y",

                "-i", stream_url,

                "-t", str(duration),

                "-c:a", "libmp3lame",

                "-q:a", "3",

                output_file

            ]

            

            subprocess.run(cmd_ffmpeg, check=True)

            print(f"✅ Done! Audio saved as {output_file}")

            return output_file

            

        except subprocess.CalledProcessError as e:

            print(f"❌ FFmpeg error: {str(e)}")

            return None

        except Exception as e:

            print(f"❌ Error downloading audio: {str(e)}")

            return None

    

    def download_youtube_video_audio(self, youtube_url, output_file=None):

        """Download audio from a regular YouTube video (non-live)"""

        try:

            if output_file is None:

                output_file = os.path.join(self.temp_dir, f"video_audio_{int(time.time())}.mp3")

                

            print(f"📥 Downloading audio from YouTube video: {youtube_url}")

            

            cmd = [

                "youtube-dl",

                "--extract-audio",

                "--audio-format", "mp3",

                "--audio-quality", "0",

                "--output", output_file,

                youtube_url

            ]

            

            subprocess.run(cmd, check=True)

            print(f"✅ Done! Audio saved as {output_file}")

            return output_file

            

        except subprocess.CalledProcessError as e:

            print(f"❌ youtube-dl error: {str(e)}")

            return None

        except Exception as e:

            print(f"❌ Error downloading video audio: {str(e)}")

            return None

    

    def convert_mp3_to_wav(self, mp3_file):

        """Convert MP3 to WAV format for speech recognition"""

        try:

            wav_file = mp3_file.replace(".mp3", ".wav")

            

            print(f"🔄 Converting MP3 to WAV format...")

            

            # Using pydub for conversion

            audio = AudioSegment.from_mp3(mp3_file)

            audio.export(wav_file, format="wav")

            

            print(f"✅ Conversion complete: {wav_file}")

            return wav_file

            

        except Exception as e:

            print(f"❌ Error converting MP3 to WAV: {str(e)}")

            return None

    

    def transcribe_audio(self, audio_file, use_chunk=False, chunk_size_ms=30000):

        """Transcribe an audio file to text using Google Speech Recognition"""

        try:

            # Check if the file is MP3 and convert if needed

            if audio_file.endswith(".mp3"):

                audio_file = self.convert_mp3_to_wav(audio_file)

                if not audio_file:

                    return None

            

            recognizer = sr.Recognizer()

            

            # Adjust the energy threshold and pause threshold

            recognizer.energy_threshold = 300

            recognizer.pause_threshold = 0.8

            

            full_text = []

            

            if use_chunk:

                # Process large files in chunks

                audio = AudioSegment.from_wav(audio_file)

                duration_ms = len(audio)

                chunks = [audio[i:i+chunk_size_ms] for i in range(0, duration_ms, chunk_size_ms)]

                

                print(f"🔊 Processing audio in {len(chunks)} chunks...")

                

                for i, chunk in enumerate(chunks):

                    # Export chunk to a temporary file

                    chunk_file = os.path.join(self.temp_dir, f"chunk_{i}.wav")

                    chunk.export(chunk_file, format="wav")

                    

                    # Transcribe the chunk

                    with sr.AudioFile(chunk_file) as source:

                        audio_data = recognizer.record(source)

                        

                    try:

                        text = recognizer.recognize_google(audio_data)

                        full_text.append(text)

                        print(f"✓ Chunk {i+1}/{len(chunks)} transcribed")

                    except sr.UnknownValueError:

                        print(f"? Chunk {i+1}/{len(chunks)}: Could not understand audio")

                    except sr.RequestError as e:

                        print(f"❌ Chunk {i+1}/{len(chunks)}: {str(e)}")

                    

                    # Clean up temporary chunk file

                    os.remove(chunk_file)

            else:

                # Process the whole file at once

                print(f"🔊 Processing audio file: {audio_file}")

                

                with sr.AudioFile(audio_file) as source:

                    print("Adjusting for ambient noise...")

                    recognizer.adjust_for_ambient_noise(source)

                    print("Recording audio...")

                    audio_data = recognizer.record(source)

                

                try:

                    print("Transcribing...")

                    text = recognizer.recognize_google(audio_data)

                    full_text.append(text)

                    print("✅ Transcription complete!")

                except sr.UnknownValueError:

                    print("❌ Could not understand the audio")

                    return None

                except sr.RequestError as e:

                    print(f"❌ Google Speech Recognition error: {str(e)}")

                    return None

            

            # Combine all text chunks

            final_text = " ".join(full_text)

            return final_text

            

        except Exception as e:

            print(f"❌ Error during transcription: {str(e)}")

            return None

    

    def save_transcription(self, text, output_file=None):

        """Save transcription to a file"""

        if not text:

            print("❌ No text to save")

            return False

            

        if output_file is None:

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            output_file = f"transcription_{timestamp}.txt"

        

        try:

            with open(output_file, "w", encoding="utf-8") as f:

                f.write(text)

            print(f"📝 Transcription saved to '{output_file}'")

            return True

        except Exception as e:

            print(f"❌ Error saving transcription: {str(e)}")

            return False

    

    def save_with_metadata(self, text, source_url, duration, output_file=None):

        """Save transcription with metadata as JSON"""

        if not text:

            print("❌ No text to save")

            return False

            

        if output_file is None:

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            output_file = f"transcription_{timestamp}.json"

        

        metadata = {

            "source_url": source_url,

            "duration_seconds": duration,

            "transcription_time": datetime.now().isoformat(),

            "text": text

        }

        

        try:

            with open(output_file, "w", encoding="utf-8") as f:

                json.dump(metadata, f, indent=2)

            print(f"📝 Transcription with metadata saved to '{output_file}'")

            return True

        except Exception as e:

            print(f"❌ Error saving transcription with metadata: {str(e)}")

            return False

    

    def process_youtube_live(self, youtube_url, duration=120, output_file=None):

        """Process a YouTube live stream: extract URL, download audio, transcribe"""

        if not self.validate_youtube_url(youtube_url):

            print("❌ Invalid YouTube URL")

            return None

            

        # Extract the stream URL from YouTube

        stream_url = self.extract_youtube_stream_url(youtube_url)

        if not stream_url:

            print("❌ Failed to extract stream URL")

            return None

            

        # Download audio from the stream

        audio_file = self.download_audio_from_stream(stream_url, duration)

        if not audio_file:

            print("❌ Failed to download audio")

            return None

            

        # Transcribe the audio

        text = self.transcribe_audio(audio_file, use_chunk=True if duration > 60 else False)

        if not text:

            print("❌ Failed to transcribe audio")

            return None

            

        # Save the transcription

        if output_file:

            self.save_transcription(text, output_file)

        else:

            self.save_with_metadata(text, youtube_url, duration)

            

        return text

    

    def process_direct_stream(self, stream_url, duration=120, output_file=None):

        """Process a direct M3U8 stream URL: download audio, transcribe"""

        # Download audio from the stream

        audio_file = self.download_audio_from_stream(stream_url, duration)

        if not audio_file:

            print("❌ Failed to download audio")

            return None

            

        # Transcribe the audio

        text = self.transcribe_audio(audio_file, use_chunk=True if duration > 60 else False)

        if not text:

            print("❌ Failed to transcribe audio")

            return None

            

        # Save the transcription

        if output_file:

            self.save_transcription(text, output_file)

        else:

            self.save_with_metadata(text, stream_url, duration)

            

        return text

    

    def process_youtube_video(self, youtube_url, output_file=None):

        """Process a regular YouTube video: download audio, transcribe"""

        if not self.validate_youtube_url(youtube_url):

            print("❌ Invalid YouTube URL")

            return None

            

        # Download audio from the YouTube video

        audio_file = self.download_youtube_video_audio(youtube_url)

        if not audio_file:

            print("❌ Failed to download audio")

            return None

            

        # Get audio duration

        audio = AudioSegment.from_mp3(audio_file)

        duration_seconds = len(audio) / 1000

            

        # Transcribe the audio (use chunking for videos longer than 5 minutes)

        text = self.transcribe_audio(audio_file, use_chunk=True if duration_seconds > 300 else False)

        if not text:

            print("❌ Failed to transcribe audio")

            return None

            

        # Save the transcription

        if output_file:

            self.save_transcription(text, output_file)

        else:

            self.save_with_metadata(text, youtube_url, duration_seconds)

            

        return text

    

    def cleanup(self):

        """Clean up temporary files"""

        try:

            for file in os.listdir(self.temp_dir):

                file_path = os.path.join(self.temp_dir, file)

                if os.path.isfile(file_path):

                    os.remove(file_path)

            print("🧹 Cleaned up temporary files")

        except Exception as e:

            print(f"⚠️ Error cleaning up: {str(e)}")



def main():

    parser = argparse.ArgumentParser(description="Transcribe audio from YouTube videos or live streams")

    

    # Input source arguments

    source_group = parser.add_mutually_exclusive_group(required=True)

    source_group.add_argument("--youtube", help="YouTube video or live stream URL")

    source_group.add_argument("--stream", help="Direct M3U8 stream URL")

    source_group.add_argument("--audio", help="Local audio file path")

    

    # Processing options

    parser.add_argument("--live", action="store_true", help="Treat YouTube URL as live stream")

    parser.add_argument("--duration", type=int, default=120, help="Duration to record in seconds (for live streams)")

    parser.add_argument("--output", help="Output file path for transcription")

    parser.add_argument("--json", action="store_true", help="Save output as JSON with metadata")

    parser.add_argument("--no-cleanup", action="store_true", help="Don't clean up temporary files after processing")

    

    args = parser.parse_args()

    

    transcriber = StreamTranscriber()

    

    try:

        text = None

        

        if args.youtube:

            if args.live:

                print(f"🎥 Processing YouTube live stream: {args.youtube}")

                text = transcriber.process_youtube_live(args.youtube, args.duration)

            else:

                print(f"🎬 Processing YouTube video: {args.youtube}")

                text = transcriber.process_youtube_video(args.youtube)

        elif args.stream:

            print(f"📡 Processing direct stream: {args.stream}")

            text = transcriber.process_direct_stream(args.stream, args.duration)

        elif args.audio:

            print(f"🔊 Processing local audio file: {args.audio}")

            text = transcriber.transcribe_audio(args.audio, use_chunk=True)

            

        if text:

            output_file = args.output

            

            if args.json:

                # Ensure JSON extension

                if output_file and not output_file.endswith('.json'):

                    output_file = output_file.replace('.txt', '.json') if output_file.endswith('.txt') else f"{output_file}.json"

                

                source = args.youtube or args.stream or args.audio

                duration = args.duration if args.youtube and args.live else None

                transcriber.save_with_metadata(text, source, duration, output_file)

            else:

                transcriber.save_transcription(text, output_file)

                

            print("\nTranscription:")

            print("-" * 40)

            print(text[:500] + "..." if len(text) > 500 else text)

            print("-" * 40)

        

        if not args.no_cleanup:

            transcriber.cleanup()

            

    except KeyboardInterrupt:

        print("\n⏹️ Process interrupted by user")

        if not args.no_cleanup:

            transcriber.cleanup()

    except Exception as e:

        print(f"\n❌ Error: {str(e)}")

        if not args.no_cleanup:

            transcriber.cleanup()



if __name__ == "__main__":

    main()# =============================

# app.py - Flask Web Application

# =============================


from flask import Flask, render_template, request, jsonify, send_file

import os

import time

import threading

import uuid

from werkzeug.utils import secure_filename

import json


# Import our transcriber module

from transcriber import StreamTranscriber

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'

app.config['RESULT_FOLDER'] = 'results'

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload


# Create necessary folders

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)


# Store active transcription jobs

active_jobs = {}


# Initialize transcriber

transcriber = StreamTranscriber()


@app.route('/')

def index():

    return render_template('index.html')


@app.route('/api/transcribe', methods=['POST'])

def transcribe_api():

    try:

        data = request.json

        url = data.get('url')

        job_type = data.get('type', 'youtube_video')  # youtube_video, youtube_live, direct_stream

        duration = int(data.get('duration', 120))

        

        if not url:

            return jsonify({'error': 'URL is required'}), 400

            

        # Generate a unique job ID

        job_id = str(uuid.uuid4())

        

        # Start transcription in a background thread

        thread = threading.Thread(

            target=process_transcription_job,

            args=(job_id, job_type, url, duration)

        )

        thread.daemon = True

        thread.start()

        

        # Store job information

        active_jobs[job_id] = {

            'id': job_id,

            'status': 'processing',

            'url': url,

            'type': job_type,

            'start_time': time.time(),

            'result': None

        }

        

        return jsonify({

            'job_id': job_id,

            'status': 'processing',

            'message': 'Transcription job started'

        })

        

    except Exception as e:

        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])

def upload_api():

    try:

        if 'audio_file' not in request.files:

            return jsonify({'error': 'No file part'}), 400

            

        file = request.files['audio_file']

        

        if file.filename == '':

            return jsonify({'error': 'No selected file'}), 400

            

        if file:

            filename = secure_filename(file.filename)

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file.save(file_path)

            

            # Generate a unique job ID

            job_id = str(uuid.uuid4())

            

            # Start transcription in a background thread

            thread = threading.Thread(

                target=process_audio_file,

                args=(job_id, file_path)

            )

            thread.daemon = True

            thread.start()

            

            # Store job information

            active_jobs[job_id] = {

                'id': job_id,

                'status': 'processing',

                'file': filename,

                'type': 'audio_file',

                'start_time': time.time(),

                'result': None

            }

            

            return jsonify({

                'job_id': job_id,

                'status': 'processing',

                'message': 'Audio file uploaded and processing started'

            })

            

    except Exception as e:

        return jsonify({'error': str(e)}), 500


@app.route('/api/job/<job_id>', methods=['GET'])

def get_job_status(job_id):

    if job_id not in active_jobs:

        return jsonify({'error': 'Job not found'}), 404

        

    job = active_jobs[job_id]

    

    # Calculate elapsed time

    elapsed = time.time() - job['start_time']

    

    response = {

        'job_id': job_id,

        'status': job['status'],

        'elapsed_seconds': int(elapsed)

    }

    

    # Include result location if completed

    if job['status'] == 'completed' and job.get('result_file'):

        response['result_file'] = job['result_file']

        

    return jsonify(response)


@app.route('/api/jobs', methods=['GET'])

def list_jobs():

    # Return list of active jobs (limit to last 10)

    recent_jobs = {k: v for k, v in sorted(

        active_jobs.items(), 

        key=lambda item: item[1]['start_time'], 

        reverse=True

    )[:10]}

    

    return jsonify({'jobs': list(recent_jobs.values())})


@app.route('/api/download/<job_id>', methods=['GET'])

def download_result(job_id):

    if job_id not in active_jobs or active_jobs[job_id]['status'] != 'completed':

        return jsonify({'error': 'Result not available'}), 404

        

    job = active_jobs[job_id]

    result_file = job.get('result_file')

    

    if not result_file or not os.path.exists(result_file):

        return jsonify({'error': 'Result file not found'}), 404

        

    return send_file(

        result_file,

        as_attachment=True,

        download_name=os.path.basename(result_file)

    )


# Background processing functions

def process_transcription_job(job_id, job_type, url, duration):

    try:

        text = None

        

        if job_type == 'youtube_video':

            text = transcriber.process_youtube_video(url)

        elif job_type == 'youtube_live':

            text = transcriber.process_youtube_live(url, duration)

        elif job_type == 'direct_stream':

            text = transcriber.process_direct_stream(url, duration)

            

        if text:

            # Save result to file

            result_file = os.path.join(app.config['RESULT_FOLDER'], f"result_{job_id}.json")

            

            # Create metadata

            metadata = {

                'job_id': job_id,

                'url': url,

                'type': job_type,

                'completion_time': time.time(),

                'duration': duration if job_type in ['youtube_live', 'direct_stream'] else None,

                'text': text

            }

            

            # Save to file

            with open(result_file, 'w', encoding='utf-8') as f:

                json.dump(metadata, f, indent=2)

                

            # Update job status

            active_jobs[job_id]['status'] = 'completed'

            active_jobs[job_id]['result'] = text

            active_jobs[job_id]['result_file'] = result_file

        else:

            active_jobs[job_id]['status'] = 'failed'

            active_jobs[job_id]['error'] = 'Failed to transcribe audio'

            

    except Exception as e:

        active_jobs[job_id]['status'] = 'failed'

        active_jobs[job_id]['error'] = str(e)


def process_audio_file(job_id, file_path):

    try:

        # Transcribe the audio file

        text = transcriber.transcribe_audio(file_path, use_chunk=True)

        

        if text:

            # Save result to file

            result_file = os.path.join(app.config['RESULT_FOLDER'], f"result_{job_id}.json")

            

            # Create metadata

            metadata = {

                'job_id': job_id,

                'file': os.path.basename(file_path),

                'type': 'audio_file',

                'completion_time': time.time(),

                'text': text

            }

            

            # Save to file

            with open(result_file, 'w', encoding='utf-8') as f:

                json.dump(metadata, f, indent=2)

                

            # Update job status

            active_jobs[job_id]['status'] = 'completed'

            active_jobs[job_id]['result'] = text

            active_jobs[job_id]['result_file'] = result_file

        else:

            active_jobs[job_id]['status'] = 'failed'

            active_jobs[job_id]['error'] = 'Failed to transcribe audio'

            

    except Exception as e:

        active_jobs[job_id]['status'] = 'failed'

        active_jobs[job_id]['error'] = str(e)

    finally:

        # Clean up the uploaded file

        if os.path.exists(file_path):

            os.remove(file_path)


# =============================

# templates/index.html