import os
import urllib.parse
import requests
from gtts import gTTS

def generate_audio(text: str, output_path: str):
    """
    Generates an MP3 file using gTTS (Google Text-to-Speech) to bypass network errors.
    """
    print(f"Generating audio for text: '{text}' using gTTS")
    tts = gTTS(text=text, lang='en', tld='us')
    tts.save(output_path)
    print(f"Audio saved to {output_path}")

def download_image(prompt: str, output_path: str):
    """
    Downloads an image from Pollinations.ai based on the prompt.
    """
    # URL encode the prompt
    encoded_prompt = urllib.parse.quote(prompt)
    
    # 1080x1920 (9:16 aspect ratio), nologo=true
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true"
    
    print(f"Downloading image from Pollinations.ai for prompt: '{prompt}'")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status() # Raise an exception for bad status codes
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Image saved to {output_path}")
            return # Success, exit the retry loop
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed to download image from {url}: {e}")
            if attempt == max_retries - 1:
                raise
            else:
                print("Retrying in 5 seconds...")
                import time
                time.sleep(5)

def generate_assets(script_data: dict, output_dir: str = "assets"):
    """
    Orchestrates the generation of all required assets (audio and images).
    Returns a dictionary with paths to the generated files.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    quote = script_data.get("quote", "")
    prompts = script_data.get("prompts", [])

    if not quote or not prompts:
        raise ValueError("Invalid script data provided to asset generator.")

    audio_path = os.path.join(output_dir, "voiceover.mp3")
    image_paths = []

    # 1. Generate Voiceover
    generate_audio(quote, audio_path)

    # 2. Download Images
    for i, prompt in enumerate(prompts):
        image_path = os.path.join(output_dir, f"image_{i+1}.jpg")
        download_image(prompt, image_path)
        image_paths.append(image_path)

    return {
        "audio": audio_path,
        "images": image_paths
    }

if __name__ == "__main__":
    # Test execution with dummy data
    dummy_data = {
        "quote": "Success is not final. Failure is not fatal. It is the courage to continue that counts.",
        "prompts": [
            "A man standing on a peak",
            "A person getting up after falling",
            "A path leading into the bright horizon"
        ]
    }
    generate_assets(dummy_data, output_dir="../assets")
