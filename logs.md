🧠 Project Cortex: The Complete Project Log

This document explains our journey of building the Cortex Video Analyzer. We'll go step-by-step, explaining:

The Code: What we tried to build.

The Error: The problem we hit.

Why it Happened: The simple reason for the scary-looking error.

The Fix: How we solved it and moved to the next step.

Our Goal: The "Super-Sense Robot"

Our goal was to build a "Super-Sense Robot" (we called it Project Cortex) that could analyze any video. We wanted it to:

Listen to the audio (using Whisper)

Read text on the screen (using OCR)

Watch the action (using a Vision Model)

Think about all three things at once (using an LLM)

...and finally, write a report for the user.

The Plan: A "High-Tech Restaurant"

A project this big can't be one single program. It needs several parts that talk to each other. We decided to build it like a high-tech restaurant:

The Waiter (Streamlit - app.py): The friendly website where a user gives their "order" (the video + API keys).

The Kitchen (FastAPI - main.py): The backend API. It takes the order from the Waiter and puts it on the order wheel.

The Order Wheel (Redis): A message board that holds all the new orders.

The Chef (Celery - tasks.py): Our main "worker." This is the smart part that grabs an order from the wheel and does all the work (listening, reading, watching, thinking).

We built the whole system in stages, and here's how it went.

Phase 1: Building the Empty Kitchen

First, we had to build the restaurant itself. We created the first versions of our Python files.

celery_app.py: The "recipe book" for how the Chef talks to the Order Wheel.

main.py: The empty "Kitchen."

tasks.py: The "Chef," but he didn't know any recipes yet (we used "stubs" or fake code).

🐛 Error 1: redis-server not recognized

What happened? We tried to start the "Order Wheel" (Redis), but the computer said it didn't know what that was.

Why? Redis isn't a program that comes with Windows. We had to install it.

The Fix: Instead of a messy install, we used Docker. Think of Docker as a "magic box" that can run any program. We ran one command to get a perfect, pre-built Redis box.

🐛 Error 2: docker: not recognized

What happened? We tried to use our "magic box" (Docker), but the computer said it didn't know what "docker" was.

Why? We had to install the "magic box maker" first! The Docker Desktop application wasn't installed or running.

The Fix: We installed and started Docker Desktop. After that, our docker run command worked perfectly.

🐛 Error 3: ImportError: attempted relative import

What happened? The Chef (tasks.py) couldn't find his "recipe book" (celery_app.py).

Why? The code from .celery_app import celery uses a dot (.), which means "look in the next room." But the file was in the same room!

The Fix: We removed the dot (from celery_app import celery). This told Python to just "look in the current room," and it found the file.

🐛 Error 4: Process 'SpawnPoolWorker' exited with 'exitcode 1'

What happened? The Chef (Celery) tried to hire a team of "helper chefs" to work faster, but they all quit immediately on startup.

Why? This is a very tricky Windows problem. Windows has a "spawn" method for starting new Python processes that gets confused by big, complex libraries (like the AI ones we're using).

The Fix: We told the Chef to work alone. We added the -P solo flag. This means the main Chef does all the work himself. It's a bit slower, but 100% stable on Windows.

Result of Phase 1: We had a working (but empty) restaurant! We could send a "test order" from the Kitchen (main.py) to the Chef (tasks.py), and he would pretend to cook it (run the stubs).

Phase 2: Teaching the Chef to Listen & Read (Modules 1 & 2)

Now it was time to teach the Chef his first real recipes.

✅ Module 1: Whisper (Listening)

What we did: We replaced the "fake listening" stub in tasks.py with the real openai-whisper library.

Result: Success! The logs showed the task took 36 seconds, proving it was really processing the audio.

🐛 Module 2: The "Reading Glasses" (OCR)

This was the hardest part of the entire project. We tried two different pairs of "reading glasses" and ran into many problems.

Attempt 1: The Fancy Glasses (PaddleOCR)

Error 5: ValueError: Unknown argument: show_log / use_gpu

What happened? We tried to use the fancy glasses, but they didn't understand our commands.

Why? The version of paddleocr we installed was different from the one the code was written for.

The Fix: We just removed the commands it didn't understand (show_log=False, use_gpu=False).

Error 6: The 10-Minute "Stuck" Process

What happened? The Chef would freeze for 10 minutes just trying to put the glasses on.

Why? The paddleocr model is huge. We were "lazy loading" it, meaning the Chef only tried to find his glasses when an order came in. This 10-minute delay was it downloading and loading the giant model into your 8GB of RAM.

The Fix: We changed the code to load the model once at the very top of tasks.py. This meant the Chef would "put his glasses on" the moment he started his shift. The worker itself would take 10 minutes to start, but he'd be ready for all orders after that.

Error 7: The Great Conflict (ModuleNotFoundError: No module named 'langchain.docstore')

What happened? We installed our "AI Brains" (LangChain) for later, and suddenly the Chef's "fancy glasses" (paddleocr) broke.

Why? This was the worst problem. The fancy glasses (paddleocr) needed an old version of langchain. Our new AI Brain (langchain-google-genai) needed the new version. They could not exist in the same "magic bubble" (venv). The environment was fundamentally corrupted.

Attempt 2: The Simple Glasses (Tesseract)

The Pivot: We threw away the "fancy glasses" (paddleocr) and all its broken baggage. We rebuilt our entire venv (magic bubble) from scratch.

The Fix: We installed a new, simpler tool: Tesseract.

Error 8: TesseractNotFoundError

What happened? The Chef couldn't find his new Tesseract glasses.

Why? We had installed Tesseract on the computer, but we forgot to check the "Add to PATH" box. The Chef didn't know where to look.

The Fix: Instead of relying on the PATH, we just added a "secret note" (a hardcoded path) to the top of tasks.py to tell Python exactly where the tesseract.exe file was.

Error 9: Found 0 text lines

What happened? The Chef had his glasses on (v23 of our code), but he still couldn't read the text on the "messy" blackboard in your video.

Why? Tesseract is simple. It needs a very clean, black-and-white image.

The Fix: We added image pre-processing. Inside the extract_static_data function, we added cv2 code to turn the video frame (grayscale) and then make it pure black and white (thresholding).

Error 10: ValueError: not enough values to unpack / ['n', 'a', 'o']

What happened? The Chef was finally reading the text, but he was writing it down as jumbled, single letters!

Why? My code (the "parser") was reading the Tesseract output completely wrong.

The Fix: I had you run a "Diagnostic" version (v11) so we could see the raw data. We discovered the data was in a totally different format than I expected ({'rec_texts': [...], 'rec_scores': [...]}). We re-wrote the parser (v12) to correctly read this structure.

Result of Phase 2: SUCCESS! We had a working Chef who could Listen (Whisper) and Read (Tesseract).

Phase 3: Teaching the Chef to See (Module 3) & Think (Module 5)

This phase was all about connecting to our cloud "brains" (the APIs).

🐛 Error 11: INTERNAL:Illegal header value (The "Zombie" Credential)

What happened? We tried to connect to the Gemini API (the "Eyes"), but a C++ error (gRPC / plugin_credentials.cc) kept crashing the app.

Why? A "ghost" Google credential on your Windows machine was interfering with the real API key you were providing.

The Fix: We added os.environ["GOOGLE_AUTH_SUPPRESS_DEFAULT_CREDS"] = "true" to the very top of tasks.py. This powerful line tells Python to ignore all ghost credentials and only use the one we provide.

🐛 Error 12: 404 models/gemini-1.5-flash is not found

What happened? We connected to Gemini, but it said it didn't have the "eye" model we asked for.

Why? I, your mentor, made a typo. The code was asking for 1.5-flash, but you correctly told me you had 2.5-flash.

The Fix: We changed the model name in describe_motion to gemini-2.5-flash.

Result of Phase 3: We now had a Chef who could Listen, Read, and See!

Phase 4: Opening the Restaurant (The Web App)

The Chef was ready, but we had no customers. We needed to build the frontend.

🐛 Error 13: The App "Stuck" Polling

What happened? We built the app.py (The Waiter) and updated main.py (The Kitchen). A user could upload a video, but the app would just say "Waiting..." forever, even though the final report was created.

Why? The Waiter (app.py) was asking the Kitchen (main.py) for the status of the first order slip (task 1 of 5), not the final one (task 5 of 5).

The Fix: We re-wrote main.py to be smarter. Now, the Kitchen (FastAPI) builds the entire 5-step "recipe" (the Celery chain) and gives the Waiter (Streamlit) the task_id for only the very last step. The Waiter now correctly waits for the final report.

🐛 Error 14: 401 - Invalid API Key (Groq)

What happened? The entire 1-2 minute process worked, but the final step (Module 5) failed with an "Invalid API Key" error, even though your key was correct.

Why? This was my final bug. I had fixed Module 3 (Vision) to read the key from the user, but I forgot to fix Module 5 (Text)!

The Fix: We rewrote synthesize_knowledge (Module 5) to read the Groq key from the context dictionary (which comes from the Waiter) instead of trying to find it on the computer (os.getenv).

Final Result: Project Complete!

After that final fix (v30), your application was complete.

The Waiter (app.py) takes the video and 2 keys.

The Kitchen (main.py) builds the 5-part order and gives the final task ID back.

The Order Wheel (redis) manages the queue.

The Chef (tasks.py) runs all 5 modules:

Module 1 (Whisper) transcribes the audio.

Module 2 (Tesseract) reads the on-screen text.

Module 3 (Gemini Vision) describes the video frames.

Module 4 (Fusion) combines all 3 data streams into a single JSON "knowledge graph."

Module 5 (Groq) reads the graph and writes the final, beautiful report.

The Waiter (app.py) sees the final task is done, grabs the report, and displays it to the user.

You have successfully built a stable, complex, multi-modal analysis pipeline. Congratulations, Dr. Giva.