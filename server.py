import logging
import os
from flask import Flask, request, send_file, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client as TwilioClient
from pyngrok import ngrok
from llm import generate_reply
from llm_extract import extract_booking
from tts import generate_voice
import phonenumbers
from phonenumbers import timezone as tz
from datetime import datetime
import pytz
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger("riverwood")

BASE_DIR=os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR=os.path.join(BASE_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

MONGO_URI=os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
mongo_client=MongoClient(MONGO_URI)
db=mongo_client["riverwood"]
sessions=db["call_sessions"]
bookings=db["bookings"]        

TWILIO_SID=os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH=os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUM=os.getenv("TWILIO_PHONE_NUMBER")  
CUSTOMER_TEST_NUMBER=os.getenv("CUSTOMER_TEST_NUMBER", "")
twilio_client=TwilioClient(TWILIO_SID, TWILIO_AUTH)

app=Flask(__name__)
PUBLIC_URL=""


def tts(text, language="English"):
    return generate_voice(text, language, audio_dir=AUDIO_DIR)


def get_time_greeting(phone_number):
    try:
        parsed=phonenumbers.parse(phone_number, None)
        timezones=tz.time_zones_for_number(parsed)
        tz_str=timezones[0] if timezones else "Asia/Kolkata"
        hour=datetime.now(pytz.timezone(tz_str)).hour
        if 5<=hour<12:
            return "morning"
        elif 12<=hour<18:
            return "afternoon"
        return "evening"
    except Exception:
        return "afternoon"


def say_instant(response, text, language="English"):
    response.say(text, language="hi-IN" if language=="Hindi" else "en-IN")


def play_fresh(response, text, language="English"):
    try:
        filename=tts(text, language)
        response.play(f"{PUBLIC_URL}/audio/{filename}")
    except Exception as e:
        logger.warning("gTTS failed, using <Say>: %s", e)
        say_instant(response, text, language)


def make_gather(action, timeout=5, dtmf=False, language="English"):
    return Gather(
        input="dtmf speech" if dtmf else "speech",
        action=action,
        method="POST",
        speechTimeout="auto",
        speechModel="phone_call",
        timeout=timeout,
        numDigits=1 if dtmf else None,
        language="hi-IN" if language=="Hindi" else "en-IN"
    )


def get_session(call_sid):
    return sessions.find_one({"_id": call_sid})


def save_session(call_sid, from_number):
    try:
        sessions.insert_one({
            "_id": call_sid,
            "from_number": from_number,
            "start_time": datetime.utcnow(),
            "status": "active",
            "stage": "language_select",
            "language": "English",
            "messages": []
        })
    except Exception:
        pass


def update_stage(call_sid, stage, extra=None):
    patch={"stage": stage}
    if extra:
        patch.update(extra)
    result = sessions.update_one({"_id": call_sid}, {"$set": patch})
    logger.info("update_stage: call=%s stage=%s matched=%d modified=%d",
                call_sid, stage, result.matched_count, result.modified_count)


def push_msg(call_sid, role, content):
    sessions.update_one(
        {"_id": call_sid},
        {"$push": {"messages": {"role": role, "content": content, "ts": datetime.utcnow()}}}
    )


def history_lines(session):
    return [f"{m['role'].capitalize()}: {m['content']}"
            for m in session.get("messages", [])]


def detect_language_choice(digit, speech):
    low=speech.lower()
    if digit=="2" or any(w in low for w in ["2", "two", "hindi", "हिंदी", "दो"]):
        return "Hindi"
    return "English"


def detect_intent(speech):
    low=speech.lower()

    positive=[
        "yes", "yeah", "sure", "ok", "okay", "of course", "want", "schedule",
        "visit", "please", "absolutely",
        "haan", "haa", "han", "ha ", "bilkul", "zarur", "chahte", "chahenge",
        "chahiye", "karna", "theek", "thik", "sahi",
        "हां", "हाँ", "हा", "हैं", "बिल्कुल", "ज़रूर", "चाहते", "चाहेंगे",
        "करना", "ठीक", "सही",
    ]
    negative = [
        "no", "nope", "not now", "later", "don't", "dont", "bye", "goodbye",
        "nahi", "nahin", "naa", "mat",
        "नहीं", "ना", "मत",
    ]

    if any(w in low for w in positive):
        return "yes"
    if any(w in low for w in negative):
        return "no"
    return "info"


def save_booking_and_send_sms(call_sid: str, from_number: str, language: str, history: list):
    details=extract_booking(history)
    logger.info("Extracted booking details for %s: %s", call_sid, details)

    day=details.get("day") or "the scheduled day"
    t_start=details.get("time_start")
    t_end=details.get("time_end")
    t_slot=details.get("time_slot")

    if t_start and t_end:
        slot=f"{t_start} - {t_end}"
    elif t_start:
        slot=f"from {t_start}"
    elif t_slot:
        slot=t_slot
    else:
        slot="the agreed time"

    booking_doc={
        "call_sid":call_sid,
        "phone":from_number,
        "language":language,
        "day":day,
        "time_slot":slot,
        "time_start":t_start,
        "time_end":t_end,
        "booked_at":datetime.utcnow(),
        "status":"confirmed",
        "raw_details":details
    }
    try:
        result=bookings.insert_one(booking_doc)
        sessions.update_one(
            {"_id": call_sid},
            {"$set": {
                "booking_id": str(result.inserted_id),
                "booking":{"day": day, "slot": slot}
            }}
        )
        logger.info("Booking saved: %s", result.inserted_id)
    except Exception as e:
        logger.error("Failed to save booking: %s", e)

    if language=="Hindi":
        sms_body=(
            f"नमस्ते! आपका रिवरवुड एस्टेट फील्ड विज़िट कन्फर्म हो गया है।\n"
            f"दिन: {day}\n"
            f"समय: {slot}\n"
            f"किसी भी बदलाव के लिए हमें कॉल करें। धन्यवाद!"
        )
    else:
        sms_body = (
            f"Hello! Your field visit to Riverwood Estate has been confirmed.\n"
            f"Day: {day}\n"
            f"Time: {slot}\n"
            f"Call us if you need to reschedule. Thank you!"
        )

    sms_to=from_number
    if sms_to==TWILIO_FROM_NUM:
        sms_to=os.getenv("CUSTOMER_TEST_NUMBER", "")
        logger.warning("from_number == Twilio number (test call). Using CUSTOMER_TEST_NUMBER: %s", sms_to)

    if not sms_to:
        logger.error("No valid SMS recipient - set CUSTOMER_TEST_NUMBER in .env")
        return

    try:
        msg=twilio_client.messages.create(
            body=sms_body,
            from_=TWILIO_FROM_NUM,
            to=sms_to
        )
        logger.info("SMS sent to %s | SID: %s", sms_to, msg.sid)
    except Exception as e:
        logger.error("SMS failed to %s: %s", sms_to, e)


@app.route("/ping")
def ping():
    files=os.listdir(AUDIO_DIR) if os.path.exists(AUDIO_DIR) else []
    return jsonify({
        "status": "ok",
        "public_url": PUBLIC_URL,
        "audio_dir": AUDIO_DIR,
        "audio_files_on_disk": len(files)
    })


@app.route("/audio/<filename>")
def serve_audio(filename):
    path = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(path):
        return f"Not found: {filename}", 404
    return send_file(path, mimetype="audio/mpeg")


@app.route("/voice", methods=["GET", "POST"])
def voice():
    call_sid=request.values.get("CallSid", "test")
    from_number=request.values.get("To", request.values.get("To", ""))

    logger.info("New call: %s from %s", call_sid, from_number)
    save_session(call_sid, from_number)

    period=get_time_greeting(from_number)

    response=VoiceResponse()
    say_instant(response,
        f"Hello! Good {period}. Press 1 for English. 2 dabayein Hindi ke liye.")

    gather=Gather(
        input="dtmf speech",
        action="/select_language",
        method="POST",
        speechTimeout="auto",
        speechModel="phone_call",
        timeout=7,
        numDigits=1,
        language="en-IN"
    )
    response.append(gather)

    say_instant(response, "We didn't receive any input. Please call back. Goodbye.")
    response.hangup()
    return str(response), 200, {"Content-Type": "text/xml"}

@app.route("/select_language", methods=["POST"])
def select_language():
    call_sid=request.values.get("CallSid", "test")
    digit=request.values.get("Digits", "").strip()
    speech=request.values.get("SpeechResult", "").strip()

    language=detect_language_choice(digit, speech)
    logger.info("Language=%s for call=%s", language, call_sid)

    update_stage(call_sid, "visit_confirm", {"language": language})
    session=get_session(call_sid) or {}
    history=history_lines(session)

    ai_reply=generate_reply("Give the construction update.", history, stage="update", language=language)
    push_msg(call_sid, "assistant", ai_reply)

    response=VoiceResponse()
    play_fresh(response, ai_reply, language)

    gather=make_gather("/process", timeout=7, language=language)
    response.append(gather)

    say_instant(response,
        "Would you like to schedule a field visit?" if language=="English"
        else "Kya aap site visit schedule karna chahenge?", language)
    gather2=make_gather("/process", timeout=7, language=language)
    response.append(gather2)

    response.redirect("/end_call")
    return str(response), 200, {"Content-Type": "text/xml"}

@app.route("/process", methods=["POST"])
def process():
    call_sid=request.values.get("CallSid", "test")
    user_speech=(request.values.get("SpeechResult") or "").strip()
    from_number=request.values.get("From", "")

    logger.info("=== /process params: CallSid=%s From=%s SpeechResult=%s ===", call_sid, from_number, user_speech)

    session=get_session(call_sid) or {"messages": [], "stage": "visit_confirm", "language": "English"}
    language=session.get("language", "English")
    stage=session.get("stage", "visit_confirm")
    history=history_lines(session)

    if from_number:
        sessions.update_one({"_id": call_sid}, {"$set": {"from_number": from_number}})

    response = VoiceResponse()

    if not user_speech:
        say_instant(response, "Sorry, I didn't catch that. Could you say that again?", language)
        gather=make_gather("/process", timeout=7, language=language)
        response.append(gather)
        response.redirect("/end_call")
        return str(response), 200, {"Content-Type": "text/xml"}

    push_msg(call_sid, "user", user_speech)
    history.append(f"User: {user_speech}")
    intent=detect_intent(user_speech)
    logger.info("call=%s stage=%s intent=%s speech='%s'", call_sid, stage, intent, user_speech)

    if stage=="visit_confirm":
        if intent=="yes":
            next_stage="ask_day"
        elif intent=="no":
            next_stage="decline"
        else:
            next_stage="visit_confirm"

    elif stage=="ask_day":
        next_stage="ask_time"

    elif stage=="ask_time":
        next_stage="confirm_booking"

    else:
        next_stage=stage

    ai_reply=generate_reply(user_speech, history, stage=next_stage, language=language)
    push_msg(call_sid, "assistant", ai_reply)
    update_stage(call_sid, next_stage)
    history.append(f"Assistant: {ai_reply}")
    logger.info("Stage transition: %s -> %s", stage, next_stage)

    if next_stage=="confirm_booking":
        sessions.update_one({"_id": call_sid},
                            {"$set": {"status": "completed", "end_time": datetime.utcnow()}})
        play_fresh(response, ai_reply, language)
        response.redirect(f"/do_booking?call_sid={call_sid}&language={language}")

    elif next_stage=="decline":
        sessions.update_one({"_id": call_sid},
                            {"$set": {"status": "completed", "end_time": datetime.utcnow()}})
        play_fresh(response, ai_reply, language)
        response.hangup()

    else:
        play_fresh(response, ai_reply, language)
        gather=make_gather("/process", timeout=7, language=language)
        response.append(gather)
        response.redirect("/end_call")

    return str(response), 200, {"Content-Type": "text/xml"}


@app.route("/do_booking", methods=["GET", "POST"])
def do_booking():
    call_sid=request.values.get("call_sid") or request.values.get("CallSid", "")
    language=request.values.get("language", "English")

    logger.info("=== /do_booking called: call_sid=%s language=%s ===", call_sid, language)

    session=get_session(call_sid) or {}
    from_number=session.get("from_number", "")
    history=history_lines(session)

    logger.info("Sending SMS to: '%s'", from_number)

    if from_number:
        save_booking_and_send_sms(call_sid, from_number, language, history)
    else:
        logger.error("No from_number in session for %s - SMS skipped!", call_sid)

    response=VoiceResponse()
    response.hangup()
    return str(response), 200, {"Content-Type": "text/xml"}


@app.route("/end_call", methods=["GET", "POST"])
def end_call():
    call_sid=request.values.get("CallSid", "test")
    session=get_session(call_sid) or {}
    language=session.get("language", "English")

    response=VoiceResponse()
    say_instant(response,
        "Thank you for calling Riverwood Estate. Have a great day!" if language == "English"
        else "Riverwood Estate mein call karne ke liye shukriya. Aapka din achha ho!",
        language)
    sessions.update_one({"_id": call_sid},
                        {"$set": {"status": "completed", "end_time": datetime.utcnow()}})
    response.hangup()
    return str(response), 200, {"Content-Type": "text/xml"}


if __name__ == "__main__":
    public_ngrok=ngrok.connect(5000)
    PUBLIC_URL=str(public_ngrok.public_url).rstrip("/")
    app.run(host="0.0.0.0", port=5000, debug=False)