import streamlit as st
import requests
import time

# --- Page Configuration ---
# This sets the title of the browser tab, the icon, and uses the full screen width.
st.set_page_config(
    page_title="Cortex Video Analyzer",
    page_icon="🧠",
    layout="wide"
)

# --- Backend API URL ---
# This is the address of the FastAPI app you are running in Terminal 3
API_URL = "http://127.0.0.1:8000"

# --- Main Page UI ---
st.title("🧠 Project Cortex: Multi-Modal Video Analyzer")
st.write("This application transcribes audio, reads on-screen text, and analyzes visual motion to create a comprehensive, time-aligned report of any video.")

st.divider()

# --- API Key Input (in the sidebar) ---
with st.sidebar:
    st.header("🔑 API Keys")
    st.write("Your keys are required to run the analysis and are not stored.")
    
    # Use st.text_input for password-style masked input
    gemini_key = st.text_input("Gemini API Key (for Vision)", type="password")
    groq_key = st.text_input("Groq API Key (for Text)", type="password")
    
    st.info(
        "**Why two keys?**\n"
        "* **Gemini** is used for its powerful vision model to describe what's *happening* in the video.\n"
        "* **Groq** is used for its high-speed text model (`Llama 3.1`) to synthesize the final report."
    )

# --- File Uploader ---
uploaded_file = st.file_uploader("Upload your video file (mp4, mov, avi)", type=["mp4", "mov", "avi"])

# This dictionary will hold the final report content
if "report" not in st.session_state:
    st.session_state.report = ""

if uploaded_file is not None:
    
    st.video(uploaded_file)
    
    # Check if keys are provided before showing the button
    if not gemini_key or not groq_key:
        st.error("Please enter both your Gemini and Groq API keys in the sidebar to proceed.")
    else:
        # The main analysis button
        if st.button("Analyze Video", type="primary"):
            st.session_state.report = "" # Clear old report
            
            with st.spinner("Processing... This may take several minutes. Please wait."):
                
                # 1. --- Send video and keys to the FastAPI backend ---
                files = {'video_file': (uploaded_file.name, uploaded_file, uploaded_file.type)}
                data = {
                    'gemini_api_key': gemini_key,
                    'groq_api_key': groq_key
                }
                
                task_id = None
                try:
                    # Call your FastAPI server
                    response = requests.post(f"{API_URL}/process-video/", files=files, data=data)
                    
                    if response.status_code == 200:
                        task_id = response.json().get("task_id")
                        st.success(f"Processing started! Task ID: {task_id}")
                    else:
                        st.error(f"Error starting analysis: {response.status_code} - {response.text}")
                        st.stop() # Stop the script
                        
                except requests.exceptions.ConnectionError:
                    st.error(f"Connection Error: Could not connect to the FastAPI backend at {API_URL}.")
                    st.info("Please ensure your backend services (Redis, Celery, and FastAPI) are all running.")
                    st.stop() # Stop the script
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
                    st.stop()

                # 2. --- Poll the /get-result/ endpoint ---
                if task_id:
                    report_content = ""
                    status = "PENDING"
                    
                    with st.spinner(f"Task {task_id} is running. This is the slow part. Polling for result..."):
                        start_time = time.time()
                        
                        while status == "PENDING":
                            elapsed = int(time.time() - start_time)
                            st.text(f"Waiting for result... (Elapsed: {elapsed}s)")
                            
                            time.sleep(5) # Wait 5 seconds between checks
                            try:
                                poll_response = requests.get(f"{API_URL}/get-result/{task_id}")
                                
                                if poll_response.status_code == 200:
                                    result = poll_response.json()
                                    status = result.get("status")
                                    
                                    if status == "SUCCESS":
                                        report_content = result.get("report_markdown")
                                        st.session_state.report = report_content # Save to session state
                                        st.balloons()
                                    elif status == "FAILURE":
                                        st.error(f"Task Failed: {result.get('message')}")
                                        break
                                else:
                                    st.error("Failed to poll task status.")
                                    break
                            except Exception as poll_err:
                                st.error(f"Error while polling: {poll_err}")
                                break

# --- Display the final report ---
if st.session_state.report:
    st.divider()
    st.header("📄 Final Synthesized Report")
    
    # This is the key command that renders your beautiful markdown
    st.markdown(st.session_state.report)