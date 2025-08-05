

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
from dotenv import load_dotenv
import os, base64

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter()

@router.post("/detect-tools")
async def detect_tools(image: UploadFile = File(...)):
    try:
        # Read and encode the image
        image_bytes = await image.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Send to GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What tools do you see in this image? List them clearly."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    ]
                }
            ],
            max_tokens=300
        )

        tools = response.choices[0].message.content
        return JSONResponse(content={"tools": tools})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# tool_name = detected_tool.lower()
# tool_link = tool_links.get(tool_name, "https://www.amazon.com/s?k=" + tool_name)

# return {
#     "tool": detected_tool,
#     "description": tool_info,
#     "link": tool_link
# }
