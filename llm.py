import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

load_dotenv()
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

context_text="""
    Riverwood Estate Sector 7, Kharkhauda - Phase 1 construction update:
    - Overall completion: approximately 60 percent
    - Land grading: fully completed
    - Internal roads: currently being installed
    - Drainage infrastructure: currently being installed
    - Projected completion of Phase 1 infrastructure: 80 to 85 percent very soon
"""

class ReplyModel(BaseModel):
    reply: str=Field(description="Short natural spoken response for a phone call.")

parser=PydanticOutputParser(pydantic_object=ReplyModel)

llm=ChatOpenAI(
    model="gpt-4o",
    api_key=OPENAI_API_KEY,
    temperature=0.6
)

prompt=PromptTemplate(
    template="""
    You are a warm, friendly, human-sounding call agent for Riverwood Estate Construction Company.
    You are currently on a live phone call with a customer.

    Project Context:
    {context}

    Full Conversation So Far:
    {history}

    Current Stage: {stage}
    Language: {language}

    Customer just said: "{user_query}"

    Stage Instructions:
    - "greeting": You have just connected. Do NOT greet again (greeting already happened). Jump straight to the update.
    - "update": Introduce yourself briefly as calling from Riverwood Constructions. Share the Phase 1 progress naturally in 2 sentences. End by asking if they want to schedule a field visit.
    - "visit_confirm": Customer said yes to a visit. Ask them which day works for them.
    - "ask_time": Customer gave a day. Acknowledge it warmly and ask what time slot works - morning or afternoon, and their preferred hours.
    - "confirm_booking": Customer gave their time. Confirm the exact day and time slot warmly. Tell them to call if they change their mind. Thank them for their time and wish them well. End the call naturally.
    - "decline": Customer does not want a visit. Acknowledge gracefully, thank them for their time, wish them well.
    - "unclear": Customer said something unclear. Politely ask again in context of current stage.

    Rules:
    - Respond ONLY in {language}. If Hindi, use natural Hinglish or Devanagari as appropriate.
    - Keep it to 2-3 short sentences max. Sound warm, not robotic.
    - Do NOT repeat anything already said in the conversation history.
    - Do NOT use filler phrases like "Of course!", "Certainly!", "Absolutely!".
    - Sound like a real human agent — casual but professional.
    - If language is Hindi, mix Hindi and English naturally (Hinglish style is fine).

    {format_instructions}
""",
    input_variables=["user_query", "history", "context", "stage", "language"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

chain=prompt|llm|parser


def generate_reply(user_query: str, history: list, stage: str="update", language: str="English") -> str:
    history_text="\n".join(history[-16:])
    result=chain.invoke({
        "user_query": user_query,
        "history": history_text,
        "context": context_text,
        "stage": stage,
        "language": language
    })
    return result.reply