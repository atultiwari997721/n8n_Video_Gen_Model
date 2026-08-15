import os
import json
from google import genai
from pydantic import BaseModel, Field

class ScriptOutput(BaseModel):
    quote: str = Field(description="A 3-sentence motivational quote")
    prompts: list[str] = Field(description="Exactly 3 image generation prompts describing the visuals for the quote")

def generate_script(api_key: str = None) -> dict:
    """
    Calls the Gemini API to generate a motivational quote and 3 image prompts.
    Returns the result as a dictionary.
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing.")
    
    # Using the google-genai client
    client = genai.Client(api_key=api_key)

    prompt = (
        "You are an expert YouTube Shorts creator. "
        "Generate a powerful, 3-sentence motivational quote about success, discipline, or mindset. "
        "Also generate exactly 3 short, descriptive image generation prompts that visually match each sentence of the quote. "
        "The prompts should be suited for a realistic, cinematic, moody aesthetic (e.g., 'cinematic shot of a lone wolf on a snowy mountain, dark moody lighting')."
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
        if len(output_data.get("prompts", [])) != 3:
            raise ValueError("Gemini did not return exactly 3 prompts.")
        print("Script and prompts generated successfully.")
        return output_data
    except Exception as e:
        print(f"Failed to parse Gemini output: {response.text}")
        raise e

if __name__ == "__main__":
    # Test execution
    res = generate_script()
    print(json.dumps(res, indent=2))
