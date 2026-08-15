import os
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips

def resize_and_crop(clip, target_width, target_height):
    """
    Resizes and crops an image clip to the target dimensions (1080x1920 for Shorts),
    ensuring it fills the frame without stretching.
    """
    clip_ratio = clip.w / clip.h
    target_ratio = target_width / target_height

    if clip_ratio > target_ratio:
        # Clip is wider than target. Resize based on height, then crop width.
        new_height = target_height
        new_width = int(new_height * clip_ratio)
        resized_clip = clip.resize(height=new_height)
        
        # Crop from the center
        x_center = new_width / 2
        y_center = new_height / 2
        cropped_clip = resized_clip.crop(
            x_center=x_center, 
            y_center=y_center, 
            width=target_width, 
            height=target_height
        )
    else:
        # Clip is taller than target (or equal). Resize based on width, then crop height.
        new_width = target_width
        new_height = int(new_width / clip_ratio)
        resized_clip = clip.resize(width=new_width)
        
        # Crop from the center
        x_center = new_width / 2
        y_center = new_height / 2
        cropped_clip = resized_clip.crop(
            x_center=x_center, 
            y_center=y_center, 
            width=target_width, 
            height=target_height
        )
        
    return cropped_clip

def assemble_video(audio_path: str, image_paths: list[str], output_path: str = "final_short.mp4"):
    """
    Assembles the audio and images into a final video.
    """
    print("Starting video assembly...")
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
    for img_path in image_paths:
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image file not found: {img_path}")

    # Load audio
    audio_clip = AudioFileClip(audio_path)
    total_duration = audio_clip.duration
    
    # Calculate duration per image
    num_images = len(image_paths)
    clip_duration = total_duration / num_images
    
    video_clips = []
    
    target_w, target_h = 1080, 1920

    for img_path in image_paths:
        print(f"Processing image: {img_path}")
        img_clip = ImageClip(img_path)
        
        # Resize/Crop to 1080x1920
        processed_clip = resize_and_crop(img_clip, target_w, target_h)
        
        # Set duration
        processed_clip = processed_clip.set_duration(clip_duration)
        
        # Add basic crossfade transition if desired, or just append
        video_clips.append(processed_clip)

    # Concatenate clips
    print("Concatenating clips...")
    final_video = concatenate_videoclips(video_clips, method="compose")
    
    # Set audio
    final_video = final_video.set_audio(audio_clip)
    
    # Write to file
    print(f"Writing final video to {output_path}...")
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast" # faster rendering for CI environments
    )
    
    # Close clips to free resources
    audio_clip.close()
    for clip in video_clips:
        clip.close()
    final_video.close()
    
    print("Video assembly completed successfully!")
    return output_path

if __name__ == "__main__":
    # Test execution assuming assets exist
    # assemble_video("../assets/voiceover.mp3", ["../assets/image_1.jpg", "../assets/image_2.jpg", "../assets/image_3.jpg"])
    pass
