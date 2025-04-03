# =============================
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