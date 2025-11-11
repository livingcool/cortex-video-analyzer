# --- !! CRITICAL FIX v29 !! ---
import os
os.environ["GOOGLE_AUTH_SUPPRESS_DEFAULT_CREDS"] = "true"
# --- END FIX ---

import json
import logging
import base64 
import io 
import whisper  # Module 1 dependency
import cv2  # Module 2 dependency
import pytesseract # Module 2 dependency
from PIL import Image # Module 2 dependency
import numpy as np 
import google.generativeai as genai # For Module 3 (Vision)
from langchain_groq import ChatGroq # For Module 5 (Text)
from langchain_core.messages import HumanMessage
from celery import chain
from celery_app import celery  # Absolute import

# --- Tesseract Path Fix ---
try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\tesseract.exe'
except Exception:
    logging.warning("Could not set Tesseract path. Assuming it's in the system PATH.")
# --- END FIX ---


# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Processing Directory ---
PROCESSING_DIR = "video_processing_storage"
os.makedirs(PROCESSING_DIR, exist_ok=True)


# --- Module 1: Whisper Model Loading (Lazy) ---
WHISPER_MODEL = None
def get_whisper_model():
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        log.info("Loading Whisper model (tiny)...")
        WHISPER_MODEL = whisper.load_model("tiny") 
        log.info("Whisper model loaded.")
    return WHISPER_MODEL

# --- Module 2: Tesseract (No pre-loading needed!) ---


# --- Task Definitions ---

@celery.task(name="tasks.transcribe_video")
def transcribe_video(context: dict):
    video_path = context["paths"]["original"]
    processing_id = context["processing_id"]
    log.info(f"[{processing_id}] Module 1: Transcribing video (REAL)...")
    
    try:
        model = get_whisper_model()
        result = model.transcribe(video_path, word_timestamps=True)
        
        output_path = os.path.join(PROCESSING_DIR, f"{processing_id}_transcription.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
        context["paths"]["transcription"] = output_path
        log.info(f"[{processing_id}] Module 1: Complete. Saved to {output_path}")
        return context
    except Exception as e:
        log.error(f"[{processing_id}] Module 1: FAILED. Error: {e}")
        raise e


@celery.task(name="tasks.extract_static_data")
def extract_static_data(context: dict, frame_interval_ms=2000):
    video_path = context["paths"]["original"]
    processing_id = context["processing_id"]
    log.info(f"[{processing_id}] Module 2: Extracting static data (TESSERACT v23)...")
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video file {video_path}")

        ocr_results = []
        current_pos_ms = 0
        
        while cap.isOpened():
            cap.set(cv2.CAP_PROP_POS_MSEC, current_pos_ms)
            ret, frame = cap.read()
            
            if not ret:
                break 
                
            timestamp_sec = current_pos_ms / 1000.0
            
            log.info(f"[{processing_id}] Running Tesseract OCR on frame at {timestamp_sec}s...")
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            pil_image = Image.fromarray(thresh)
            
            try:
                data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
                
                num_items = len(data['text'])
                for i in range(num_items):
                    confidence = float(data['conf'][i])
                    text = data['text'][i].strip()
                    
                    if confidence > 50 and text:
                        ocr_results.append({
                            "timestamp": timestamp_sec,
                            "text": text,
                            "confidence": confidence
                        })

            except pytesseract.TesseractNotFoundError:
                log.error(f"[{processing_id}] TESSERACT FAILED. The 'tesseract' executable was not found.")
                raise
            except Exception as ocr_err:
                log.warning(f"[{processing_id}] Pytesseract failed on frame at {timestamp_sec}s: {ocr_err}")

            current_pos_ms += frame_interval_ms

        cap.release()
        
        output_path = os.path.join(PROCESSING_DIR, f"{processing_id}_ocr_data.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ocr_results, f, indent=2, ensure_ascii=False)
            
        context["paths"]["ocr"] = output_path
        log.info(f"[{processing_id}] Module 2: Complete. Found {len(ocr_results)} text lines. Saved to {output_path}")
        return context

    except Exception as e:
        log.error(f"[{processing_id}] Module 2: FAILED. Error: {e}")
        raise e


@celery.task(name="tasks.describe_motion")
def describe_motion(context: dict, frame_interval_ms=10000):
    processing_id = context["processing_id"]
    video_path = context["paths"]["original"]
    log.info(f"[{processing_id}] Module 3: Describing motion (REAL v28 - Native Google Lib)...")
    
    output_path = os.path.join(PROCESSING_DIR, f"{processing_id}_motion_data.json")

    api_key = context.get("api_keys", {}).get("gemini")
        
    if not api_key:
        log.error(f"[{processing_id}] Module 3: FAILED. Gemini API key not found in context.")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([], f) 
        context["paths"]["motion"] = output_path
        return context

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        log.error(f"[{processing_id}] Failed to initialize Google Gemini model: {e}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([], f)
        context["paths"]["motion"] = output_path
        return context

    motion_results = []
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video file {video_path}")

        current_pos_ms = 0
        while cap.isOpened():
            cap.set(cv2.CAP_PROP_POS_MSEC, current_pos_ms)
            ret, frame = cap.read()
            
            if not ret:
                break 
                
            timestamp_sec = current_pos_ms / 1000.0
            log.info(f"[{processing_id}] Describing frame at {timestamp_sec}s...")

            _, buffer = cv2.imencode('.jpg', frame)
            
            img_blob = io.BytesIO(buffer)
            img = Image.open(img_blob)
            
            try:
                response = model.generate_content(
                    ["Describe this image in one brief sentence.", img],
                )
                description = response.text
                
                motion_results.append({
                    "timestamp": timestamp_sec,
                    "description": description
                })
                log.info(f"[{processing_id}]   Description: {description}")

            except Exception as gemini_err:
                log.error(f"[{processing_id}] Gemini Vision call failed at t={timestamp_sec}s: {gemini_err}")
            
            current_pos_ms += frame_interval_ms

        cap.release()

    except Exception as e:
        log.error(f"[{processing_id}] Module 3: FAILED during CV processing. Error: {e}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(motion_results, f, indent=2, ensure_ascii=False)
        
    context["paths"]["motion"] = output_path
    log.info(f"[{processing_id}] Module 3: Complete. Described {len(motion_results)} frames. Saved to {output_path}")
    return context


@celery.task(name="tasks.fuse_data")
def fuse_data(context: dict, time_step_seconds=5):
    processing_id = context["processing_id"]
    video_path = context["paths"]["original"]
    log.info(f"[{processing_id}] Module 4: Fusing data streams (REAL v13)...")
    
    try:
        with open(context["paths"]["transcription"], 'r', encoding='utf-8') as f:
            transcription = json.load(f)
        with open(context["paths"]["ocr"], 'r', encoding='utf-8') as f:
            ocr_data = json.load(f) 
        with open(context["paths"]["motion"], 'r', encoding='utf-8') as f:
            motion_data = json.load(f) 

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration_seconds = frame_count / fps
        cap.release()

        fused_timeline = []
        current_time = 0.0
        
        whisper_segments = transcription.get('segments', [])

        while current_time < video_duration_seconds:
            chunk_start = current_time
            chunk_end = current_time + time_step_seconds
            
            spoken_text = " ".join([
                seg['text'] for seg in whisper_segments 
                if seg['start'] < chunk_end and seg['end'] > chunk_start
            ]).strip()
            
            ocr_text_set = set()
            for item in ocr_data:
                if chunk_start <= item['timestamp'] < chunk_end:
                    ocr_text_set.add(item['text'])
            
            motion_descriptions = " ".join([
                item['description'] for item in motion_data
                if chunk_start <= item['timestamp'] < chunk_end
            ])
            
            if spoken_text or ocr_text_set or motion_descriptions:
                fused_timeline.append({
                    "time_chunk": f"{chunk_start:.1f}s - {chunk_end:.1f}s",
                    "spoken": spoken_text,
                    "on_screen_text": list(ocr_text_set), 
                    "visuals": motion_descriptions 
                })
            
            current_time += time_step_seconds

        output_path = os.path.join(PROCESSING_DIR, f"{processing_id}_fused_knowledge.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(fused_timeline, f, indent=2, ensure_ascii=False)
            
        context["paths"]["fused"] = output_path
        log.info(f"[{processing_id}] Module 4: Complete. Fused {len(fused_timeline)} time chunks. Saved to {output_path}")
        return context
        
    except Exception as e:
        log.error(f"[{processing_id}] Module 4: FAILED. Error: {e}")
        raise e


@celery.task(name="tasks.synthesize_knowledge")
def synthesize_knowledge(context: dict):
    """
    Module 5: Synthesis Agent (LLM) - REAL IMPLEMENTATION (v32 - Robust Failure)
    - Re-raises an exception on API failure so the frontend can report it.
    """
    processing_id = context["processing_id"]
    log.info(f"[{processing_id}] Module 5: Synthesizing final document (REAL v32 - LangChain/Groq)...")
    
    try:
        with open(context["paths"]["fused"], 'r', encoding='utf-8') as f:
            fused_data = json.load(f) 
    except Exception as e:
        log.error(f"[{processing_id}] Module 5: FAILED to read fused data. Error: {e}")
        raise e

    api_key = context.get("api_keys", {}).get("groq")
    if not api_key:
        log.error(f"[{processing_id}] Module 5: FAILED. GROQ_API_KEY not found in context.")
        raise ValueError("GROQ_API_KEY not found in context.")
        
    try:
        model = ChatGroq(
            model_name="llama-3.1-8b-instant",
            groq_api_key=api_key
        ) 

        master_prompt = f"""
        You are a technical analyst. You will receive a JSON object representing a video,
        broken down into time chunks. Each chunk contains:
        1. "spoken": The raw transcription (may contain errors).
        2. "on_screen_text": A list of de-duplicated text *words* found by Tesseract.
           (e.g., ["HOW", "NVIDIA", "AND", "OPEN", "AI"])
        3. "visuals": A description of the on-screen action.

        Your task is to synthesize this raw data into a clean, comprehensive markdown report.
        Perform the following actions:
        - Re-assemble the "on_screen_text" words into coherent sentences or labels.
        - SUMMARIZE what is happening in each time chunk by combining the spoken
          text, the (now re-assembled) on-screen text, AND the visual descriptions.
        - Be structured and precise.

        RAW DATA:
        {json.dumps(fused_data, indent=2)}

        ---
        
        FINAL SYNTHESIZED REPORT (Markdown Format):
        """
        
        log.info(f"[{processing_id}] Sending data to Groq API (llama-3.1-8b-instant)...")
        response = model.invoke(master_prompt)
        
        final_report = response.content
        log.info(f"[{processing_id}] Received synthesis from Groq API.")

    except Exception as e:
        log.error(f"[{processing_id}] Module 5: FAILED during Groq API call. Error: {e}")
        final_report = f"""
# Video Analysis: {processing_id}
LLM SYNTHESIS FAILED: {e}

Dumping raw (but fused) JSON data instead:
```json
{json.dumps(fused_data, indent=2, ensure_ascii=False)}
"""  # Re-raise the exception to notify the frontend raise e
    output_path = os.path.join(PROCESSING_DIR, f"{processing_id}_final_report.md")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_report)
        
    context["paths"]["final_report"] = output_path
    log.info(f"[{processing_id}] Module 5: COMPLETE. Final report saved to {output_path}")
    return context
# --- KEY CHANGE ---
# Return the final context for the API to read
