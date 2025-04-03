from transcriber import StreamTranscriber

# Initialize the transcriber
transcriber = StreamTranscriber()

# Test URL validation
youtube_url = "https://www.youtube.com/watch?v=jZLHchwKOVY"
is_valid = transcriber.validate_youtube_url(youtube_url)
print(f"URL validation result: {is_valid}")

# Test stream extraction
if is_valid:
    print("Attempting to extract stream URL...")
    stream_url = transcriber.extract_youtube_stream_url(youtube_url)
    if stream_url:
        print(f"Successfully extracted stream URL: {stream_url[:60]}...")
    else:
        print("Failed to extract stream URL")