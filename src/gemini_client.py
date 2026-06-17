import os
import httpx
import logging

logger = logging.getLogger(__name__)

# In-memory session history: channel_id -> list of {"role": "user"|"model", "parts": [{"text": ...}]}
chat_histories = {}

async def generate_response(channel_id: int, user_message: str, system_instruction: str = None) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ **Error:** `GEMINI_API_KEY` is not configured in `.env` file!"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # Initialize history for this channel if not exists
    if channel_id not in chat_histories:
        chat_histories[channel_id] = []
        
    # Append user message to history
    chat_histories[channel_id].append({
        "role": "user",
        "parts": [{"text": user_message}]
    })
    
    # Keep only the last 15 messages (15 user + model messages total) to manage context window size
    if len(chat_histories[channel_id]) > 30:
        chat_histories[channel_id] = chat_histories[channel_id][-30:]
        
    payload = {
        "contents": chat_histories[channel_id]
    }
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
        if response.status_code != 200:
            logger.error(f"Gemini API returned status {response.status_code}: {response.text}")
            return f"❌ **Error from Gemini API:** Status code {response.status_code}"
            
        result = response.json()
        candidates = result.get("candidates", [])
        if not candidates:
            return "❌ **Error:** No response candidate returned from Gemini."
            
        model_text = candidates[0]["content"]["parts"][0]["text"]
        
        # Append model response to history
        chat_histories[channel_id].append({
            "role": "model",
            "parts": [{"text": model_text}]
        })
        
        return model_text
        
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return f"❌ **Error:** Failed to connect to Gemini API. Details: {e}"

def clear_chat_history(channel_id: int):
    if channel_id in chat_histories:
        chat_histories[channel_id] = []
