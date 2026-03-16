# 🏗️ Riverwood Estate - AI Call Agent

An intelligent inbound call agent for Riverwood Estate that greets customers, shares real-time construction updates, schedules field visits, saves bookings to MongoDB, and sends SMS confirmations - all powered by GPT-4o, gTTS, and Twilio.

---

## 🎥 Demonstration

👉 [Watch the demo on Loom](https://www.loom.com/share/77af52b91a1044ec9bafaa88f28cbed5)

---

## 📞 How It Works

```
Call connects
     │
     ▼
Greeting (time-based: Good morning/afternoon/evening)
     │
     ▼
Language Selection  ──► Press 1 → English
                    ──► Press 2 → Hindi
     │
     ▼
AI shares Phase 1 construction update
"I'm calling from Riverwood Constructions. Your Phase 1 is about 60% complete..."
     │
     ▼
Asks if customer wants a field visit
     │
     ├── No  ──► Graceful goodbye → Call ends
     │
     └── Yes ──► Ask for day
                    │
                    ▼
                Ask for time slot
                    │
                    ▼
                Confirm booking
                    │
                    ▼
          ┌─────────────────────┐
          │  Save to MongoDB    │
          │  Send SMS to user   │
          │  Auto hang up       │
          └─────────────────────┘
```

---

## 🗂️ Project Structure

```
Riverwood/
│
├── server.py          # Flask app — Twilio webhook handler, call flow logic
├── llm.py             # GPT-4o conversation generator (stage-aware, bilingual)
├── llm_extract.py     # GPT-4o booking extractor (pulls day/time from conversation)
├── tts.py             # gTTS text-to-speech with optional pydub speed-up
├── requirements.txt   # Python dependencies
├── .env               # API keys and config (never commit this)
└── audio/             # Auto-created — stores generated mp3 files
```

---

## ⚙️ Setup

### 1. Clone / copy the project files

```bash
cd C:\Users\yourname\Desktop\Riverwood
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install ffmpeg (for faster TTS audio — optional but recommended)

**Windows:**
```bash
winget install ffmpeg
```
Then restart your terminal.

### 4. Create your `.env` file

Create a file named `.env` in the project root with the following:

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX

# For testing — your real mobile number to receive SMS during test calls
# (Only needed when calling from your Twilio number itself)
CUSTOMER_TEST_NUMBER=+91XXXXXXXXXX

# MongoDB (local or Atlas)
MONGODB_URI=mongodb://localhost:27017/
```

> **Where to find Twilio credentials:**
> - Account SID + Auth Token → https://console.twilio.com (Dashboard homepage)
> - Phone Number → Phone Numbers → Manage → Active Numbers

### 5. Set up ngrok (for exposing local server to Twilio)

**Free static domain (recommended — URL never changes):**
1. Sign up at https://ngrok.com
2. Go to https://dashboard.ngrok.com/domains → claim your free static domain
3. Add your authtoken:
```bash
ngrok config add-authtoken YOUR_TOKEN
```
4. Update the bottom of `server.py`:
```python
public_ngrok = ngrok.connect(5000, domain="your-domain.ngrok-free.app")
PUBLIC_URL = "https://your-domain.ngrok-free.app"
```

### 6. Configure Twilio webhook

In Twilio Console → Phone Numbers → Manage → your number → Voice Configuration:

```
A call comes in:  Webhook
URL:              https://your-domain.ngrok-free.app/voice
HTTP Method:      POST
```

---

## 🚀 Running the Agent

```bash
python server.py
```

You should see:
```
✅ Ngrok Public URL: https://your-domain.ngrok-free.app
📁 Audio directory:  C:\...\Riverwood\audio
📞 Twilio webhook  → POST /voice
```

Now call your Twilio number. The agent will pick up immediately.

---

## 🗄️ MongoDB Collections

### `call_sessions`
Stores the full call history for every call.

| Field | Description |
|---|---|
| `_id` | Twilio CallSid |
| `from_number` | Caller's phone number |
| `language` | English or Hindi |
| `stage` | Current conversation stage |
| `messages` | Full conversation history |
| `status` | active / completed |
| `start_time` | Call start UTC |
| `end_time` | Call end UTC |
| `booking_id` | Reference to booking doc (if scheduled) |

### `bookings`
Stores confirmed field visit bookings.

| Field | Description |
|---|---|
| `call_sid` | Reference to call session |
| `phone` | Customer phone number |
| `language` | English or Hindi |
| `day` | Visit day (e.g. Monday) |
| `time_slot` | e.g. 9:00 AM - 11:00 AM |
| `time_start` | Start time |
| `time_end` | End time |
| `booked_at` | Booking timestamp UTC |
| `status` | confirmed |

---

## 🧠 Conversation Stages

| Stage | What happens |
|---|---|
| `language_select` | User picks English or Hindi |
| `visit_confirm` | AI gives update, asks if user wants a visit |
| `ask_day` | AI asks which day works |
| `ask_time` | AI asks what time slot |
| `confirm_booking` | AI confirms, saves to DB, sends SMS, hangs up |
| `decline` | User said no, graceful goodbye, hangs up |

---

## 📱 SMS Confirmation

After a successful booking, the customer automatically receives an SMS:

**English:**
```
Hello! Your field visit to Riverwood Estate has been confirmed.
Day: Monday
Time: 9:00 AM - 11:00 AM
Call us if you need to reschedule. Thank you!
```

**Hindi:**
```
नमस्ते! आपका Riverwood Estate का फील्ड विज़िट कन्फर्म हो गया है।
दिन: Monday
समय: 9:00 AM - 11:00 AM
कोई भी बदलाव के लिए हमें कॉल करें। शुक्रिया!
```

---

## 🔧 Configuration & Tuning

### Adjust TTS speed (`tts.py`)
```python
SPEED = 1.3  # 1.0 = normal, 1.3 = 30% faster, 1.5 = fast
```

### Update construction context (`llm.py`)
Edit `context_text` to reflect current project status:
```python
context_text = """
Riverwood Estate Sector 7, Kharkhauda - Phase 1 construction update:
- Overall completion: approximately 60 percent
...
"""
```

### Health check
Visit in browser to verify server is running:
```
https://your-domain.ngrok-free.app/ping
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Call handling | Twilio Programmable Voice |
| AI conversation | OpenAI GPT-4o via LangChain |
| Text-to-speech | gTTS (Google TTS) + pydub |
| Web server | Flask |
| Tunnel | pyngrok (ngrok) |
| Database | MongoDB (pymongo) |
| SMS | Twilio Messaging API |
| Language support | English + Hindi (Devanagari) |

---
