import os
import json
from google import genai
from pydantic import BaseModel, Field

class ScriptOutput(BaseModel):
    quote: str = Field(description="A 3-sentence script/quote")
    prompts: list[str] = Field(description="Exactly 1 image generation prompt describing the visual for the video")

def generate_script(api_key: str = None, custom_topic: str = None, is_exact: bool = False) -> dict:
    """
    Calls the Gemini API to generate a script and 1 image prompt.
    Uses a custom topic if provided, otherwise picks a random topic (Coding Tips, Motivation, Info).
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing.")
    
    # Using the google-genai client
    client = genai.Client(api_key=api_key)

    if custom_topic and is_exact:
        prompt = (
            "You are an expert YouTube Shorts creator. "
            f"The user has provided the EXACT script they want to use: '{custom_topic}'. "
            "You MUST use this exact script as the `quote` in your output. Do not change it. "
            "Generate exactly 1 short, descriptive image generation prompt that visually matches the script. "
            "The prompt should be suited for a realistic, cinematic aesthetic without any text or logos."
        )
    elif custom_topic and custom_topic.strip():
        prompt = (
            "You are an expert YouTube Shorts creator. "
            f"The user has provided the following custom topic: '{custom_topic}'. "
            "Write a powerful, 3-sentence script about that topic. "
            "Then, generate exactly 1 short, descriptive image generation prompt that visually matches the script. "
            "The prompt should be suited for a realistic, cinematic aesthetic without any text or logos."
        )
    else:
        import random
        topics = [
            "a powerful coding tip for software engineers",
            "a deep motivational quote about discipline and success",
            "an interesting psychological fact",
            "a stoic philosophy quote"
        ]
        chosen_topic = random.choice(topics)
        prompt = (
            "You are an expert YouTube Shorts creator. "
            f"Generate a powerful, 3-sentence script about: {chosen_topic}. "
            "Also generate exactly 1 short, descriptive image generation prompt that visually matches the overall script. "
            "The prompt should be suited for a realistic, cinematic, moody aesthetic (e.g., 'cinematic shot of a lone wolf on a snowy mountain, dark moody lighting')."
        )

    print("Calling Gemini API for script generation...")
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ScriptOutput,
            temperature=0.7
        )
    )

    # Parse the output
    try:
        output_data = json.loads(response.text)
        if len(output_data.get("prompts", [])) != 1:
            raise ValueError("Gemini did not return exactly 1 prompt.")
        print("Script and prompts generated successfully.")
        return output_data
    except Exception as e:
        print(f"Failed to parse Gemini output: {response.text}")
        raise e

if __name__ == "__main__":
    # Test execution
    res = generate_script()
    print(json.dumps(res, indent=2))
