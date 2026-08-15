import os
import sys
import shutil
import traceback
from src.script_generator import generate_script
from src.asset_generator import generate_assets
from src.video_editor import assemble_video
from src.youtube_uploader import upload_video

def run_pipeline(api_key=None, youtube_token_json=None, callback=print, custom_topic=None, is_exact=False):
    callback("Starting Automated YouTube Shorts Pipeline...")
    
    # Define directories
    assets_dir = "assets"
    output_video_path = "final_short.mp4"
    
    try:
        # Step 1: Generate Script
        callback("\n--- STEP 1: Generating Script ---")
        script_data = generate_script(api_key=api_key, custom_topic=custom_topic, is_exact=is_exact)
        quote = script_data.get("quote", "Stay hard.")
        
        # Determine a title from the quote (first sentence)
        first_sentence = quote.split('.')[0] + "."
        title = f"{first_sentence} #shorts #motivation"
        
        # Prepare description
        description = f"{quote}\n\nGenerated entirely by AI.\n#shorts #motivation #mindset #success"
        
        # Step 2: Generate Assets (Images + Audio)
        callback("\n--- STEP 2: Generating Assets ---")
        callback(f"Quote: {script_data.get('quote')}")
        asset_paths = generate_assets(script_data, output_dir=assets_dir, callback=callback)
        audio_path = asset_paths["audio"]
        image_paths = asset_paths["images"]
        
        # Step 3: Edit Video
        callback("\n--- STEP 3: Editing Video ---")
        assemble_video(audio_path, image_paths, output_path=output_video_path)
        callback("Video assembly completed successfully!")
        
        # Step 4: Upload to YouTube
        callback("\n--- STEP 4: Uploading to YouTube ---")
        if youtube_token_json:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_token_file:
                temp_token_file.write(youtube_token_json)
                temp_token_path = temp_token_file.name
            
            try:
                video_id = upload_video(output_video_path, title, description, token_file=temp_token_path, callback=callback)
                callback(f"\nPipeline completed successfully! Video ID: {video_id}")
                callback(f"URL: https://youtu.be/{video_id}")
                return f"https://youtu.be/{video_id}"
            finally:
                if os.path.exists(temp_token_path):
                    os.remove(temp_token_path)
        else:
            callback(f"\nPipeline completed successfully! (YouTube upload skipped because no token was provided)")
            return "Upload Skipped"
        
    except Exception as e:
        callback(f"\nPipeline failed due to an error: {e}")
        callback(traceback.format_exc())
        raise e
    finally:
        # Cleanup
        callback("\n--- Cleanup ---")
        if os.path.exists(assets_dir):
            shutil.rmtree(assets_dir)
            callback(f"Removed {assets_dir} directory.")

if __name__ == "__main__":
    run_pipeline()
