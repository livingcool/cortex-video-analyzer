🧠 Project Cortex - Architecture & Design Log

Hello! This document is the "blueprint" for our Cortex Video Analyzer. We'll explain how it's built, why it's built that way, and how all the pieces work together.

We'll use our "High-Tech Restaurant" analogy to keep things simple and clear.

1. Project Structure (The "Restaurant Layout")

First, let's look at the "floor plan" of our restaurant. This is the list of all the files and what they do.

app.py

The "Waiter" (Frontend): This is the Streamlit website you see. It takes the "order" from the user (the video file and their two API keys).

main.py

The "Kitchen" (Backend API): This is the FastAPI server. The Waiter (app.py) sends the order here. The Kitchen's only job is to create the 5-step "recipe" (the Celery chain) and hand it to the Order Wheel.

celery_app.py

The "Recipe Book": This is a small file that just configures our Chef (tasks.py) so he knows how to talk to the Order Wheel (redis).

tasks.py

The "Chef" (The Worker): This is the most important file! It's our Celery worker. This is the "robot" that does all the work. It contains the 5 "recipes," which we call Modules.

video_uploads/ (Folder)

The "Pantry": A simple folder where we store the raw videos that users upload.

video_processing_storage/ (Folder)

The "Finished Plates": This is where the Chef puts all the data he generates (the JSON files and the final Markdown report).

requirements.txt

The "Shopping List": This file tells Python all the "ingredients" (libraries) we need to pip install.

README.md

The "Instruction Manual": This is what you give to a new person to tell them how to set up and run the restaurant.

2. Code Structure (The "Restaurant Workflow")

Now, let's look at how an "order" (a video) moves through the system from start to finish.

A user opens the Waiter (app.py) in their browser. They upload a video and paste in their 2 API keys.

The Waiter sends this entire package (the video + keys) to the Kitchen (main.py).

The Kitchen receives the package. It builds a chain of all 5 recipes (modules) from tasks.py. It tells the chain, "When you're done, the user wants the final report."

The Kitchen puts this "chain-recipe" on the Order Wheel (redis) and gets a "ticket number" (the task_id) for the final step.

The Kitchen immediately gives this "ticket number" back to the Waiter.

The Chef (tasks.py), who is always watching the Order Wheel, sees the new recipe. He grabs it and starts cooking.

The Chef works through the chain, one step at a time:

Module 1 (Listen) -> Module 2 (Read) -> Module 3 (Watch) -> Module 4 (Organize) -> Module 5 (Think & Write)

Meanwhile, the Waiter is "stuck" (on purpose!). He is in a loop, pinging the kitchen every 5 seconds, "Is the food for this ticket number ready yet?"

This takes 1-2 minutes. When the Chef finally finishes Module 5, he puts the final report down. The kitchen marks the ticket "COMPLETE."

The Waiter's next "ping" gets a "SUCCESS!" message. He grabs the final report and displays it on the website.

This is called an asynchronous system. It's perfect because the user can wait at the "table" (the website) while the "Chef" (Celery) is doing the long, hard work in the "back room."

3. The 5 Modules (The "Chef's Recipes")

This is the "magic." The Chef (tasks.py) is a "robot" with 5 different tools. Here is what each tool is, and why we chose it.

Module 1: The "Ears" (Audio Transcription)

Tool: openai-whisper (the tiny model)

What it does: It listens to the audio of the video and writes down every word that is spoken.

Why we chose it: Whisper is the "industry standard" for accuracy. It's really good at understanding speech. We use the tiny model as a strategic choice: it's not as "smart" as the "large" model, but it runs very fast on your local computer (your CPU) and doesn't use much RAM.

Module 2: The "Eyes" (Reading Text)

Tool: pytesseract

What it does: It looks at video frames (like "brute-forcing" every 2 seconds) and reads any text it sees.

Why we chose it (The Pivot): This was our biggest challenge.

We first tried PaddleOCR: This is a very powerful "fancy" tool. But it failed for two reasons: 1) It was huge and took 10 minutes to load on your 8GB RAM. 2) It had a dependency conflict (langchain.docstore error) with our "Brain" modules. It was fundamentally incompatible.

Tesseract is the fix: We rebuilt the venv and chose Tesseract. It's simple, fast, and has no conflicts with our other tools. We "helped" it by adding image pre-processing (turning the frame black and white), which makes it much better at reading text off a messy video.

Module 3: The "Context" (Watching Action)

Tool: Gemini 2.5 Flash (via Google's native Python library)

What it does: This is our first cloud "brain." We send it a picture (a video frame) and ask, "What is happening in this image?" It sends back a sentence like, "A hand is drawing a diagram."

Why we chose it (The 8GB RAM problem):

We first tried ollama (a local model): This was too much for your 8GB of RAM. Trying to run Whisper, Tesseract, and a local vision model at the same time caused a crash.

The Gemini API is the fix: We offload this heavy "watching" task to the cloud. It doesn't use any of your computer's RAM. This is the project's main strategic compromise: we trade a bit of speed (network lag) for the ability to run at all.

Module 4: The "Organizer" (Fusing Data)

Tool: Simple Python (dict and set)

What it does: After the first 3 modules, we have three messy piles of data: a long audio script, a giant list of 104 text words, and 3-4 visual descriptions. This module is the "clean-up crew."

Why we chose it: It creates 5-second "time buckets." It goes through all our data and puts the right data in the right bucket. Most importantly, it uses a Python set() to de-duplicate the text, which is why your final report has a clean list of words, not 104 jumbled ones.

Module 5: The "Brain" (Writing the Report)

Tool: Groq + Llama 3.1 (via langchain-groq)

What it does: This is our second cloud "brain." It takes the clean, organized JSON from Module 4 and follows our "master prompt" to write the final, beautiful Markdown report.

Why we chose it: You requested this, and it was the perfect choice.

Speed: Groq is insanely fast at text generation. This makes the final "thinking" step feel instantaneous.

Intelligence: Llama 3.1 is smart enough to follow our complex prompt: "Read the noisy words ['WOW', 'NVIDIA', 'MOREY'], understand it means 'HOW NVIDIA MONEY', and then combine it with the audio and visuals to write a summary."

4. How to Improve Efficiency (The Future)

The app works perfectly, but as you noted, Module 3 (the "Watching" part) is slow. This is because we are making API calls to Gemini Vision.

There are two ways to fix this:

1. The Software Fix (Free, but a Trade-off)

In tasks.py, inside the describe_motion function, we have this line:
def describe_motion(context: dict, frame_interval_ms=10000):

We are sampling one frame every 10 seconds (10000ms).

To make it faster: Change this to 20000 (20 seconds). The whole pipeline will run much faster, but the "visuals" part of your report will have less detail.

To make it more detailed (and slower): Change this to 5000 (5 seconds). The app will take longer, but the "visuals" descriptions will be more granular.

2. The Hardware Fix (The "Real" Solution)

The only way to get "fast" and "local" vision analysis is to solve the 8GB RAM problem.

The Bottleneck: Your 8GB of system RAM.

The Solution: A dedicated Graphics Card (GPU) with at least 16GB of VRAM.

Why? A powerful GPU (like an NVIDIA RTX 3080 or 40-series card) would act as a "private kitchen" just for the vision AI. We could go back to using Ollama and a local model (like llava). This model would live entirely on the GPU's own memory, and it could analyze a frame in less than a second. This would remove the network lag entirely and make your 3-second goal possible.