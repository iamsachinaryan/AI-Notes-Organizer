import os
import google.generativeai as genai

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key nahi mili! .env file check kar.")
    genai.configure(api_key=api_key)

def get_subject_from_text(text):
    if not text.strip():
        return "Unreadable_Document"

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Analyze this handwritten notes text. Tell me ONLY the academic subject name (e.g., Computer Science, Mathematics, Physics, English). NO EXTRA WORDS. NO PUNCTUATION.\n\nText: {text[:1500]}" 
        
        response = model.generate_content(prompt)
        subject = response.text.strip().replace("/", "-")
        return subject
    except Exception as e:
        print(f"Gemini Error: {e}")
        return "Unknown_Subject"