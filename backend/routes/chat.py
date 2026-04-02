"""Chat endpoint — /api/chat"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId

from config import (
    sessions_col, messages_col, emails_col, policy_docs_col,
    serialize_doc, utcnow,
    web_search, build_search_context,
    call_claude, call_grok,
)

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    model: str = "claude"
    search_enabled: bool = True


@router.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        oid = ObjectId(req.session_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = sessions_col.find_one({"_id": oid})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Store user message
    messages_col.insert_one({
        "session_id": req.session_id,
        "role": "user",
        "content": req.message,
        "timestamp": utcnow(),
        "model": req.model,
    })

    # Web search context
    extra_context = ""
    search_results = []
    if req.search_enabled:
        search_results = web_search(f"Alberta ETW ALSS {req.message}", max_results=4)
        extra_context = build_search_context(search_results)

    # Always include all saved email references — full structured content, capped per-ref
    all_refs = list(emails_col.find({}, sort=[("created_at", -1)]).limit(20))
    if all_refs:
        email_context = "\n\n[EMAIL REFERENCES — Saved documents the user has uploaded for this case]\n"
        for e in all_refs:
            body = (e.get("body") or "")[:8000]  # generous — Claude handles long context
            atts = e.get("attachments_summary", "")
            att_line = f"\nAttachments: {atts}" if atts else ""
            email_context += (
                f"\n--- REFERENCE: {e.get('subject', 'Untitled')} ---\n"
                f"From: {e.get('sender','')}\n"
                f"To: {e.get('recipients','')}\n"
                f"Date: {e.get('email_date','')}\n"
                f"{att_line}\n"
                f"Body:\n{body}\n"
            )
        extra_context += email_context

    # Always include crawled policy documents
    all_policy = list(policy_docs_col.find({}, sort=[("crawled_at", -1)]).limit(10))
    if all_policy:
        policy_context = "\n\n[POLICY DOCUMENTS — Alberta.ca sources crawled by user]\n"
        for pd in all_policy:
            policy_context += (
                f"\n--- POLICY DOC: {pd.get('title', pd.get('url', 'Unknown'))} ---\n"
                f"URL: {pd.get('url','')}\n"
                f"{pd.get('content','')[:5000]}\n"
            )
        extra_context += policy_context

    # Call AI
    try:
        if req.model == "grok":
            ai_response = await call_grok(req.session_id, req.message, extra_context)
        else:
            ai_response = await call_claude(req.session_id, req.message, extra_context)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")

    # Store AI response
    messages_col.insert_one({
        "session_id": req.session_id,
        "role": "assistant",
        "content": ai_response,
        "timestamp": utcnow(),
        "model": req.model,
        "citations": search_results,
    })

    # Update session
    sessions_col.update_one(
        {"_id": oid},
        {"$inc": {"message_count": 2}, "$set": {"updated_at": utcnow(), "model": req.model}},
    )

    return {
        "response": ai_response,
        "model": req.model,
        "citations": search_results,
        "session_id": req.session_id,
    }
