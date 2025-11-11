import os
import shutil
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from celery import chain  # <-- Import chain
from celery.result import AsyncResult
from celery_app import celery
# --- KEY CHANGE: Import all tasks directly ---
from tasks import (
    transcribe_video, 
    extract_static_data, 
    describe_motion, 
    fuse_data, 
    synthesize_knowledge
)

app = FastAPI(
    title="Project Cortex API",
    description="The backend processor for the Cortex Video Analyzer."
)

log = logging.getLogger(__name__)

# --- Base upload directory ---
UPLOAD_DIR = "video_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def read_root():
    """Root endpoint for health check."""
    return {"message": "Project Cortex API is running."}


@app.post("/process-video/")
async def process_video_endpoint(
    gemini_api_key: str = Form(...),
    groq_api_key: str = Form(...),
    video_file: UploadFile = File(...)
):
    """
    Upload a video and API keys to trigger the asynchronous processing pipeline.
    """
    if not video_file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video.")
        
    try:
        # Save the uploaded video
        file_path = os.path.join(UPLOAD_DIR, video_file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        
        log.info(f"Video file saved to: {file_path}")

        # --- KEY CHANGE: Build the context dictionary here ---
        initial_context = {
            "original_video_path": file_path,
            "processing_id": os.path.basename(file_path).split('.')[0], 
            "paths": {"original": file_path},
            "api_keys": {
                "gemini": gemini_api_key,
                "groq": groq_api_key
            }
        }

        # --- KEY CHANGE: We build the chain here, in the API ---
        processing_chain = chain(
            transcribe_video.s(initial_context), # Pass context to the *first* task
            extract_static_data.s(),
            describe_motion.s(), 
            fuse_data.s(),
            synthesize_knowledge.s() # The *last* task
        )
        
        # Start the chain and get the AsyncResult of the *last* task
        task = processing_chain.delay()
        
        # Return the ID of the last task
        return {
            "status": "success",
            "message": "Video processing has started.",
            "task_id": task.id # This ID will have the final report
        }

    except Exception as e:
        log.error(f"Error during file upload or task queuing: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    finally:
        video_file.file.close()


@app.get("/get-result/{task_id}")
async def get_task_result(task_id: str):
    """
    Poll this endpoint with a task_id to check the status or get the result.
    """
    task_result = AsyncResult(task_id, app=celery)
    
    if task_result.ready():
        if task_result.successful():
            # The task completed successfully
            # The result *is* the final context dictionary
            final_context = task_result.get()
            
            # This logic is now correct
            report_path = final_context.get("paths", {}).get("final_report")
            
            if report_path and os.path.exists(report_path):
                # Read the markdown content and send it
                with open(report_path, 'r', encoding='utf-8') as f:
                    report_content = f.read()
                return {
                    "status": "SUCCESS",
                    "report_markdown": report_content
                }
            else:
                return {"status": "ERROR", "message": "Task finished but report file not found."}
        else:
            # The task failed
            return {"status": "FAILURE", "message": str(task_result.info)}
    else:
        # The task is still running
        return {"status": "PENDING", "message": "Processing is still in progress..."}