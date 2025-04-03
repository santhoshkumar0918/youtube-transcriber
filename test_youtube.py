#!/usr/bin/env python3
"""
Test script for YouTube Audio Transcription Tool
"""

import os
import sys
import time
from transcriber import StreamTranscriber

def test_youtube_url_validation():
    """Test YouTube URL validation function"""
    transcriber = StreamTranscriber()
    
    # Valid URLs
    valid_urls = [
        "https://www.youtube.com/watch?v=jZLHchwKOVY",
        "https://youtube.com/watch?v=jZLHchwKOVY",
        "https://youtu.be/jZLHchwKOVY",
        "http://www.youtube.com/watch?v=jZLHchwKOVY&feature=featured",
        "https://m.youtube.com/watch?v=jZLHchwKOVY"
    ]
    
    # Invalid URLs
    invalid_urls = [
        "https://www.youtub.com/watch?v=jZLHchwKOVY",  # Typo in domain
        "https://vimeo.com/123456789", 
        "https://example.com",
        "not a url"
    ]
    
    print("Testing YouTube URL validation...\n")
    
    for url in valid_urls:
        result = transcriber.validate_youtube_url(url)
        print(f"{url}: {'✅ Valid' if result else '❌ Invalid'}")
        assert result, f"URL should be valid: {url}"
    
    for url in invalid_urls:
        result = transcriber.validate_youtube_url(url)
        print(f"{url}: {'❌ Valid (ERROR)' if result else '✅ Invalid'}")
        assert not result, f"URL should be invalid: {url}"
    
    print("\nURL validation test passed!\n")

def test_extract_youtube_stream():
    """Test YouTube stream URL extraction"""
    transcriber = StreamTranscriber()
    
    test_url = "https://www.youtube.com/watch?v=jZLHchwKOVY"
    
    print(f"Testing stream URL extraction from: {test_url}\n")
    
    stream_url = transcriber.extract_youtube_stream_url(test_url)
    
    if stream_url:
        print(f"✅ Successfully extracted stream URL:")
        print(f"Stream URL: {stream_url[:60]}...\n")
    else:
        print("❌ Failed to extract stream URL\n")
        sys.exit(1)
    
    print("Stream extraction test passed!\n")
    return stream_url

def test_download_audio(stream_url):
    """Test audio download from stream URL"""
    transcriber = StreamTranscriber()
    
    print("Testing audio download (short 10-second clip)...\n")
    
    audio_file = transcriber.download_audio_from_stream(stream_url, duration=10)
    
    if audio_file and os.path.exists(audio_file):
        print(f"✅ Successfully downloaded audio to: {audio_file}")
        file_size = os.path.getsize(audio_file) / 1024  # KB
        print(f"File size: {file_size:.2f} KB\n")
    else:
        print("❌ Failed to download audio\n")
        sys.exit(1)
    
    print("Audio download test passed!\n")
    return audio_file

def test_transcribe_audio(audio_file):
    """Test audio transcription"""
    transcriber = StreamTranscriber()
    
    print("Testing audio transcription...\n")
    
    text = transcriber.transcribe_audio(audio_file)
    
    if text:
        print(f"✅ Successfully transcribed audio:")
        print(f"Transcription: \"{text}\"\n")
    else:
        print("❌ Failed to transcribe audio\n")
        print("This might be due to unclear audio or Google Speech API issues")
        print("The test will continue, but this step is marked as failed\n")
    
    print("Transcription test completed!\n")
    return text

def test_save_transcription(text):
    """Test saving transcription"""
    if not text:
        print("Skipping save test as no transcription was produced\n")
        return
        
    transcriber = StreamTranscriber()
    
    print("Testing saving transcription...\n")
    
    output_file = "test_transcription.txt"
    result = transcriber.save_transcription(text, output_file)
    
    if result and os.path.exists(output_file):
        print(f"✅ Successfully saved transcription to: {output_file}\n")
    else:
        print("❌ Failed to save transcription\n")
        sys.exit(1)
    
    print("Save transcription test passed!\n")

def main():
    """Run all tests"""
    print("=" * 50)
    print("YouTube Audio Transcription Tool - Test Script")
    print("=" * 50)
    print("\nRunning tests...\n")
    
    # Run tests in sequence
    test_youtube_url_validation()
    stream_url = test_extract_youtube_stream()
    audio_file = test_download_audio(stream_url)
    text = test_transcribe_audio(audio_file)
    test_save_transcription(text)
    
    print("=" * 50)
    print("All tests completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()