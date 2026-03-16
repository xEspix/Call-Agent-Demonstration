import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Optional
from langchain_openai import ChatOpenAI

load_dotenv()

llm=ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"), temperature=0)


class BookingDetails(BaseModel):
    day: Optional[str]=Field(description="The day of the visit e.g. Monday, Tuesday, this Sunday etc. Null if not found.")
    time_start: Optional[str]=Field(description="Start time of visit e.g. 9 AM, 10:30 AM. Null if not found.")
    time_end: Optional[str]=Field(description="End time of visit e.g. 11 AM, 1 PM. Null if not found.")
    time_slot: Optional[str]=Field(description="General slot if exact times not given: morning, afternoon, evening. Null if not found.")


parser=PydanticOutputParser(pydantic_object=BookingDetails)

prompt=PromptTemplate(
    template="""
    Extract the field visit booking details from this conversation.

    Conversation:
    {conversation}

    Extract:
    - day: what day the customer wants to visit
    - time_start: start time if mentioned
    - time_end: end time if mentioned  
    - time_slot: morning/afternoon/evening if no exact time given

    {format_instructions}
""",
    input_variables=["conversation"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

chain=prompt|llm|parser


def extract_booking(conversation_history: list) -> dict:
    conversation_text="\n".join(conversation_history[-20:])
    try:
        result=chain.invoke({"conversation": conversation_text})
        return {
            "day": result.day,
            "time_start": result.time_start,
            "time_end": result.time_end,
            "time_slot": result.time_slot,
        }
    except Exception as e:
        print(f"[extract_booking] Failed: {e}")
        return {"day": None, "time_start": None, "time_end": None, "time_slot": None}