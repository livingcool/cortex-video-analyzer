# 🧠 Welcome to the Cortex Video Analyzer!

## Hello there! This is a very special project that acts like a robot with super-senses. You give it a video, and it watches, listens, and reads everything in it, all at the same time.

Then, it uses a super-smart "brain" (AI) to write a beautiful report telling you what the video was about, what was said, and what was on the screen.

### How It Works (It's Like a Restaurant!)

To make this work, we have to run 4 different programs at the same time. Think of it like a magical restaurant:

The Waiter (Streamlit - app.py): This is the friendly website you see. You give your "order" (your video and API keys) to the waiter.

The Kitchen (FastAPI - main.py): The waiter takes your order to the kitchen. The kitchen (our backend API) takes the order and puts it on the order wheel.

The Order Wheel (Redis): This is a little message board where the kitchen posts new orders for the chef.

The Chef (Celery - tasks.py): The chef is our "worker." He's the one who does all the hard work: watching the video, listening, and writing the report. He keeps checking the order wheel for new jobs.

Your computer is going to run all four of these parts at once!

Step 1: Get Your "Ingredients" Ready

Before we can cook, we need to get our kitchen set up.

1. Install Docker Desktop (The Fridge for our Order Wheel)

This is a program that runs "virtual" programs in little boxes. We will use it to run our Redis Order Wheel.

Go to: https://www.docker.com/products/docker-desktop/

Download and install it.

Important: After it's installed, you must open the Docker Desktop app and let it run in the background. You have to see the little whale icon in your system tray.

2. Install Tesseract OCR (The "Reading Glasses")

This is the program our Chef (Celery) uses to read text from the video frames.

Go to: https://github.com/UB-Mannheim/tesseract/wiki

Download the tesseract-ocr-w64-setup-...exe installer.

Run the installer.

VERY IMPORTANT: During installation, you will see a screen for "Select Additional Tasks." You MUST check the box that says "Add Tesseract to system PATH." If you miss this, the app won't be able to find its glasses!

(Just in case, we've added a "secret note" in the tasks.py file (pytesseract.pytesseract.tesseract_cmd = ...) to tell the Chef exactly where to look for this. If you installed it in the default location, you're all set!)

Step 2: Set Up Your Project

Now we set up the code itself.

1. Create a "Magic Bubble" (Virtual Environment)

This keeps all our Python ingredients tidy and separate from your computer's other projects.

Open your PowerShell terminal and navigate to your project folder:

# Create the magic bubble (a folder named 'venv')
python -m venv venv

# Activate the bubble
.\venv\Scripts\activate


(You'll see (venv) next to your prompt. This means you're "inside" the bubble!)

2. Install All the Python Ingredients

While inside your (venv) bubble, run this one command. It will read the requirements.txt file and install everything we need.

pip install -r requirements.txt


Step 3: Get Your "Secret Keys" (The AI Brains)

Our Chef needs to talk to two different AI "brains" in the cloud. You need to give him the secret keys to do this.

Gemini Key (The "Eyes"): Used by Module 3 to look at the video frames and describe what's happening.

Go to https://aistudio.google.com/

Sign in and click "Get API key".

Groq Key (The "Text Brain"): Used by Module 5 to write the final report very fast.

Go to https://console.groq.com/

Sign in, go to the "API Keys" section, and create a new key.

Don't share these keys! They are just for you.

Step 4: Let's Run the App! (The 4 Terminals)

This is the big moment! You need to open 4 separate PowerShell terminals. Running them as Administrator is a good idea to prevent any file permission errors.

➡️ Terminal 1: Start the Order Wheel (Redis)

This terminal runs our "fridge."

docker run -d -p 6379:6379 --name cortex-redis redis


(If you get an error that says "Conflict. The container name is already in use," it's good news! It just means it's already running from last time. You can skip this terminal.)

➡️ Terminal 2: Start the Chef (Celery)

This is our worker. It will wait for jobs.
(Make sure your (venv) is active!)

# Activate the magic bubble
.\venv\Scripts\activate

# Start the Chef
celery -A celery_app.celery worker --loglevel=info -P solo


(You might see a bunch of gRPC errors here. They are just warnings and can be ignored. Wait until you see celery@... ready.)

➡️ Terminal 3: Start the Kitchen (FastAPI)

This is our backend API.
(Make sure your (venv) is active!)

# Activate the magic bubble
.\venv\Scripts\activate

# Start the Kitchen
uvicorn main:app --reload


➡️ Terminal 4: Start the Waiter (Streamlit)

This is your website!
(Make sure your (venv) is active!)

# Activate the magic bubble
.\venv\Scripts\activate

# Start the Website
streamlit run app.py


This command will automatically open your web browser. You're ready to go!

🆘 Help! Something Went Wrong!

Error: TesseractNotFoundError

Problem: The Chef can't find his "reading glasses."

Fix: You missed checking the "Add Tesseract to system PATH" box in Step 1. Just re-run the Tesseract installer and make sure you check that box.

Error: [WinError 5] Access is denied

Problem: A "ghost" Python process is locking your files.

Fix: Close all your terminals. Open your computer's Task Manager (Ctrl+Shift+Esc), go to the "Details" tab, and "End task" on every python.exe process. Then, re-run your terminals as Administrator.

Error: INTERNAL:Illegal header value (gRPC Error)

Problem: A "ghost" Google credential on your computer is confusing the app.

Fix: This is already fixed! The line os.environ["GOOGLE_AUTH_SUPPRESS_DEFAULT_CREDS"] = "true" at the very top of tasks.py tells Python to ignore these "ghosts."

Error: 401 - Invalid API Key

Problem: The Groq or Gemini key you pasted into the website is wrong.

Fix: You might have copied a space by accident, or swapped the keys. Go back to your Groq/Gemini dashboard, generate a brand new key, and very carefully paste it into the website. This fixes it 99% of the time.

You've built an amazing, complex system. Congratulations, Developer !
