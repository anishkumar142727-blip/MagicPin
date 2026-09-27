from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Any
import time
from datetime import datetime
import os
import json
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
# Initialize LangChain Google GenAI client
llm = ChatGoogleGenerativeAI(
    model=os.environ.get("MODEL_NAME", "gemini-flash-latest"),
    api_key=os.environ.get("GEMINI_API_KEY"),
    temperature=0.2
)

# Define schemas for Structured Output
class ComposeOutput(BaseModel):
    body: str = Field(description="The message text")
    cta: str = Field(description="The button text or open_ended")
    rationale: str = Field(description="Why you wrote this")

class ReplyOutput(BaseModel):
    action: str = Field(description="send, wait, or end")
    body: str = Field(description="The reply message")
    wait_seconds: int | None = Field(default=None, description="Seconds to wait if action is wait")
    rationale: str = Field(description="Why you chose this action")

compose_llm = llm.with_structured_output(ComposeOutput)
reply_llm = llm.with_structured_output(ReplyOutput)

app = FastAPI()
START = time.time()

# In-memory stores
contexts: dict[tuple[str, str], dict] = {}
conversations: dict[str, list] = {}

@app.get("/v1/healthz")
async def healthz():
    counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
    for (scope, _), _ in contexts.items():
        counts[scope] = counts.get(scope, 0) + 1
    return {"status": "ok", "uptime_seconds": int(time.time() - START), "contexts_loaded": counts}

@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": "MagicPin Contender",
        "team_members": ["Anish Sharma"],
        "model": os.environ.get("MODEL_NAME", "gemini-flash-latest"),
        "approach": "single-prompt composer with context retrieval",
        "contact_email": "anishsharma_23ep015@dtu.ac.in",
        "version": "1.0.0",
        "submitted_at": "2026-09-27T07:05:28.703039Z"
    }


class CtxBody(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: dict[str, Any]
    delivered_at: str

@app.post("/v1/context")
async def push_context(body: CtxBody):
    key = (body.scope, body.context_id)
    cur = contexts.get(key)
    if cur and cur["version"] >= body.version:
        return {"accepted": False, "reason": "stale_version", "current_version": cur["version"]}
    contexts[key] = {"version": body.version, "payload": body.payload}
    return {
        "accepted": True,
        "ack_id": f"ack_{body.context_id}_v{body.version}",
        "stored_at": datetime.utcnow().isoformat() + "Z"
    }

class TickBody(BaseModel):
    now: str
    available_triggers: list[str] = []

@app.post("/v1/tick")
async def tick(body: TickBody):
    actions = []
    for trg_id in body.available_triggers:
        trg = contexts.get(("trigger", trg_id), {}).get("payload")
        if not trg: continue
        
        merchant_id = trg.get("merchant_id")
        merchant = contexts.get(("merchant", merchant_id), {}).get("payload")
        
        category_slug = merchant.get("category_slug") if merchant else None
        category = contexts.get(("category", category_slug), {}).get("payload") if category_slug else None
        
        if not (merchant and category): continue
        
        # LangChain Integration for Compose
        system_prompt = """You are Vera, magicpin's AI assistant for merchant growth.
You must compose a highly compelling message for a merchant.
RULES:
1. Specificity: Use numbers, real offers, specific dates.
2. Voice: Match the category ({category_slug}). 
3. Engagement: End with one clear low-friction question or action."""
        
        user_prompt = """Merchant: {merchant}
Category Data: {category}
Trigger: {trigger}
Compose the message."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])
        
        chain = prompt | compose_llm

        try:
            resp = await chain.ainvoke({
                "category_slug": category_slug,
                "merchant": json.dumps(merchant),
                "category": json.dumps(category),
                "trigger": json.dumps(trg)
            })
            
            body_text = resp.body
            cta = resp.cta
            rationale = resp.rationale
        except Exception as e:
            body_text = f"Hi {merchant.get('identity', {}).get('name', 'there')}, check out your latest digest!"
            cta = "open_ended"
            rationale = f"Error during generation: {str(e)}"

        actions.append({
            "conversation_id": f"conv_{merchant_id}_{trg_id}_{int(time.time())}",
            "merchant_id": merchant_id, 
            "customer_id": None,
            "send_as": "vera", 
            "trigger_id": trg_id,
            "template_name": "vera_generic_v1",
            "template_params": [merchant.get('identity', {}).get('name', 'Merchant')],
            "body": body_text, 
            "cta": cta,
            "suppression_key": trg.get("suppression_key", ""),
            "rationale": rationale
        })
    return {"actions": actions}

class ReplyBody(BaseModel):
    conversation_id: str
    merchant_id: str | None = None
    customer_id: str | None = None
    from_role: str
    message: str
    received_at: str
    turn_number: int

@app.post("/v1/reply")
async def reply(body: ReplyBody):
    conversations.setdefault(body.conversation_id, []).append({"from": body.from_role, "msg": body.message})
    
    # LangChain Integration for Reply
    history = conversations.get(body.conversation_id, [])
    history_text = "\n".join([f"{msg['from']}: {msg['msg']}" for msg in history])
    
    system_prompt = """You are Vera. Evaluate the merchant's reply.
If they are hostile, respond with action="end". 
If they want to proceed, respond with action="send" and the next message.
If they need time, respond with action="wait" and wait_seconds."""

    user_prompt = "Conversation History:\n{history}\nDetermine the next action."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_prompt)
    ])
    
    chain = prompt | reply_llm

    try:
        resp = await chain.ainvoke({
            "history": history_text
        })
        
        resp_json = { "action": resp.action, "body": resp.body, "cta": "open_ended", "rationale": resp.rationale }
        if resp.action == "wait" and resp.wait_seconds:
            resp_json["wait_seconds"] = resp.wait_seconds
        return resp_json
    except Exception as e:
        return {
            "action": "send", 
            "body": "Thanks for your response. Let me get back to you.", 
            "cta": "open_ended",
            "rationale": "Error fallback."
        }
