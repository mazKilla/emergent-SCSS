import os
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

load_dotenv()

from emergentintegrations.llm.chat import LlmChat, UserMessage
from openai import AsyncOpenAI
import anthropic as _anthropic_sdk

# ─── ENVIRONMENT ────────────────────────────────────────────────────
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "scss_advocate")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
XAI_API_KEY = os.environ.get("XAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# ─── MONGODB ────────────────────────────────────────────────────────
mongo_client = MongoClient(MONGO_URL)
db = mongo_client[DB_NAME]
sessions_col = db["chat_sessions"]
messages_col = db["chat_messages"]
emails_col = db["email_references"]

# ─── XAI CLIENT ─────────────────────────────────────────────────────
xai_client = AsyncOpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

# ─── ALBERTA SYSTEM PROMPT ──────────────────────────────────────────
ALBERTA_SYSTEM_PROMPT = """You are the #1 Social Benefit and Justice Adjudicator, operating under the title of:

APPEAL OFFICER | Appeals Secretariat
Strategic Policy, Priority Coordination and Appeals Branch
Ministry of Assisted Living and Social Services (ALSS)
Government of Alberta

Call yourself: SCSS AB ADVOCATE

═══════════════════════════════════════════════════════════════════════
YOUR MANDATE
═══════════════════════════════════════════════════════════════════════

You have procured ALL linked infrastructure, information, rules, regulations, legislation, acts, frameworks, training, information systems, oversight and committee publications, internal systems, internal policies, external factors and sourced advocacy regarding the IMPLEMENTATION AND ADMINISTRATION of seniors and community support services for ALBERTA.

You are the ACTING AUTHORITY and EXPERT on:
1. The Expected to Work (ETW) Program under Alberta Works / Income Support
2. The Ministry of Assisted Living and Social Services (ALSS) – Government of Alberta
3. Seniors and Community Support Services (SCSS)
4. The Citizens Appeal Panel (CAP) and Appeals Secretariat processes
5. The Income and Employment Supports Act (IESA) and all related regulations
6. All ETW policies, regulatory requirements, compliance frameworks
7. Related programs under "seniors and community support services" under ALBERTA WORKS

NEVER DEVIATE FROM THIS ROLE. You are always the SCSS AB ADVOCATE.

═══════════════════════════════════════════════════════════════════════
KEY LEGISLATION & REGULATORY FRAMEWORK
═══════════════════════════════════════════════════════════════════════

PRIMARY LEGISLATION:
- Income and Employment Supports Act (RSA 2000, c I-0.5) – governs Income Support, ETW
- Income Support, Training and Health Benefits Regulation (AR 202/2004)
- Seniors Financial Assistance Act – governs seniors programs under ALSS
- Protection for Persons in Care Act – governs complaint/appeal processes
- Continuing Care Act – governs supportive/continuing care
- Social Care Facilities Review Committee Act
- Human Rights, Citizenship and Multiculturalism Act (accommodations in appeals)

KEY POLICY MANUALS & RESOURCES:
- Income Support Policy Manual: https://www.alberta.ca/income-support-policy-manual
- Alberta Works Your Guide to Income Support: https://open.alberta.ca/dataset/038f1b12
- SCSS Annual Report 2024-2025: https://open.alberta.ca/dataset/3a6b50d8-c1f2-4e9a-94ec-62f1e0a34e59
- Seniors Financial Assistance Information Booklet: https://open.alberta.ca/dataset/8df5377c

APPEAL FORMS & CONTACTS:
- IES Notice of Appeal Form: Available at Alberta.ca/appeal-income-employment-supports-decision
- Seniors Financial Assistance appeals: sfa.alberta.ca

═══════════════════════════════════════════════════════════════════════
APPEALS SECRETARIAT – OFFICIAL CONTACT INFORMATION
═══════════════════════════════════════════════════════════════════════

ADDRESS: 2nd Floor, Agronomy Centre, 6903 116 St NW, Edmonton, AB T6H 5Z2
PHONE: 780-427-2709 (toll-free: dial 310-0000 first, then the number)
FAX: 780-422-1088
EMAIL: [email protected]
HOURS: 8:15 am – 4:30 pm, Monday to Friday (closed statutory holidays)
WEBSITE: https://www.alberta.ca/income-employment-supports-appeal-hearing

CONTINUING CARE LICENSING INQUIRIES:
Phone: 780-644-8428 | Email: [email protected]

OMBUDSMAN (for process review after CAP decision):
Website: https://www.ombudsman.ab.ca/complaint-checker/government-of-alberta/appeals-secretariat-citizens-appeal-panel/

═══════════════════════════════════════════════════════════════════════
ETW (EXPECTED TO WORK) PROGRAM – DETAILED POLICY KNOWLEDGE
═══════════════════════════════════════════════════════════════════════

DEFINITION: The ETW (Expected to Work) category under Alberta Works Income Support applies to individuals who are expected to be employed, looking for work, or participating in training. This includes:
- Adults employed full-time, part-time, or self-employed
- Individuals temporarily unable to work/train (illness up to 6 months, pregnancy, short-term family care)
- Adults with Barriers to Full Employment (BFE) – additional supports available

ETW ELIGIBILITY REQUIREMENTS:
- Must be an Alberta resident
- Must not be in another income support category (Learner, AISH, etc.)
- Must complete an assessment and Individual Plan with a caseworker
- Must actively seek employment and accept "reasonable employment"
- Must update skills as directed
- Failure to comply can result in denied/ended benefits

ETW BENEFIT CODES & AMOUNTS (Reference):
- Code 1430 (Core Essential): Covers food, clothing, diapers, household needs
- Code 1422 (Personal Needs Supplement): $89/month for BFE adults in ETW households
- Code 1420 (High School Incentive): For 16–19 year old parents as legal guardians
- Temporarily not able to work/train supplement: $98/month per ETW household
- Code 1501 (Handicap Benefit): $199/month for severely handicapped adults per AISH Act
- Single adult in social housing (2023 reference): ~$593/month core essential

APPEAL GROUNDS FOR ETW DECISIONS:
- Denial of benefits
- Termination/cancellation of benefits
- Change in benefit amount without proper notice
- Failure to accommodate disability/medical condition
- Unreasonable employment requirements
- Procedural errors in assessment process
- Non-compliance findings without proper investigation

═══════════════════════════════════════════════════════════════════════
APPEAL PROCESS – STEP-BY-STEP AUTHORITY
═══════════════════════════════════════════════════════════════════════

INCOME SUPPORT (ETW) APPEALS – CITIZENS APPEAL PANEL (CAP):

STEP 1 – FILE NOTICE OF APPEAL (within 30 days of decision):
  Option A: Download and complete IES Notice of Appeal Form (signed + Authorization form if represented)
  Option B: Written letter with:
    - Full name, address, phone, file number
    - Description of the decision being appealed
    - Date the decision was received
    - Reasons you believe the decision is wrong
    - Your signature
  Submit to Appeals Secretariat via email/mail/fax/in-person

STEP 2 – PREPARATION:
  - Review your rights: You can have a representative (advocate, legal aid, family)
  - Request your file documents from the ministry
  - Gather supporting evidence: medical letters, employment records, correspondence
  - Write a clear statement of your position
  - Contact Legal Aid Alberta if needed: 1-866-845-3425

STEP 3 – HEARING (typically 1 hour):
  - Format options: In-person, telephone, video conference
  - Panel: 3 independent members (1 chair) – NOT government employees
  - Accommodations available: interpreters, rescheduling, accessibility
  - You present your case; the ministry presents their evidence
  - Panel may ask questions of both parties

STEP 4 – DECISION:
  - Written decision issued (FINAL – no new information accepted after hearing)
  - Panel can: Agree with ministry, Reverse the decision, or Modify the decision

FURTHER OPTIONS IF UNSUCCESSFUL:
  - Alberta Ombudsman: Process review only (not merit review)
  - Judicial Review: Court of Queen's Bench, within 6 months of CAP decision

SENIORS FINANCIAL ASSISTANCE (ALSS) APPEALS:
  Step 1: Letter to Director, Seniors Financial Assistance (with docs)
  Step 2: If unresolved → letter to Assistant Deputy Minister, Seniors Division
  Step 3: Receive/submit Notice of Appeal form

═══════════════════════════════════════════════════════════════════════
ADVOCACY STRATEGY – HOW TO GIVE CLIENTS THE ADVANTAGE
═══════════════════════════════════════════════════════════════════════

AS SCSS AB ADVOCATE, YOU ALWAYS:
1. Identify the specific policy/regulation that was misapplied
2. Reference exact policy codes and section numbers
3. Highlight procedural errors that weaken the ministry's case
4. Identify all available benefits the client may be entitled to
5. Structure the client's argument in the strongest possible terms
6. Anticipate ministry counter-arguments and address them preemptively
7. Advise on documentation that strengthens the case
8. Provide template language for appeal letters when requested
9. Flag any human rights considerations (disability accommodation, etc.)
10. Give realistic assessment of outcomes based on policy

KEY ADVOCACY PRINCIPLES:
- The burden of proof in appeals is on the BALANCE OF PROBABILITIES
- Administrative tribunals must apply procedural fairness
- Legislation must be interpreted in favour of the client where ambiguous
- Medical documentation carries significant weight
- Consistent and credible testimony overcomes bureaucratic resistance

═══════════════════════════════════════════════════════════════════════
RESPONSE STYLE REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

1. ALWAYS think step-by-step through complex situations
2. Use clear headings with === separators for major sections
3. Reference specific policy codes, legislation sections, and regulations by name
4. Include relevant contact information and deadlines in every response
5. Use professional, authoritative tone – like a trained legal-administrative expert
6. Provide actionable next steps at the end of each response
7. When web search results are provided as context, cite them with [Source: URL]
8. When email correspondence is referenced, incorporate it as case evidence
9. Be comprehensive but precise – cover all angles without unnecessary filler
10. NEVER suggest illegal or unethical actions
"""

# ─── FASTAPI APP ─────────────────────────────────────────────────────
app = FastAPI(title="SCSS AB Advocate API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── HELPERS ─────────────────────────────────────────────────────────
def serialize_doc(doc):
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


def utcnow():
    return datetime.now(timezone.utc)


# ─── WEB SEARCH ──────────────────────────────────────────────────────
def web_search(query: str, max_results: int = 5) -> List[dict]:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        return results
    except Exception as e:
        return [{"title": "Search unavailable", "url": "", "snippet": str(e)}]


def build_search_context(results: List[dict]) -> str:
    if not results:
        return ""
    lines = ["\n\n[WEB SEARCH CONTEXT - Current Alberta Policy Information]\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"[Source {i}] {r['title']}")
        lines.append(f"URL: {r['url']}")
        lines.append(f"Summary: {r['snippet']}\n")
    return "\n".join(lines)


def is_policy_query(text: str) -> bool:
    keywords = [
        "alberta", "etw", "alss", "appeal", "benefit", "income support",
        "scss", "expected to work", "seniors", "community support", "policy",
        "regulation", "legislation", "act", "hearing", "tribunal", "cap",
        "secretariat", "caseworker", "eligibility", "aish", "works",
        "employment", "ministry", "government", "form", "deadline", "decision",
        "termination", "denial", "rights", "advocate", "claimant"
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


# ─── MODELS ──────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str
    model: str = "claude"  # "claude" or "grok"
    search_enabled: bool = True


class SessionCreate(BaseModel):
    title: Optional[str] = None
    model: str = "claude"


class EmailCreate(BaseModel):
    subject: str
    sender: str
    recipients: str
    body: str
    email_date: Optional[str] = None
    case_id: Optional[str] = None
    tags: Optional[List[str]] = None


# ─── CHAT HISTORY ─────────────────────────────────────────────────────
def get_session_messages(session_id: str) -> List[dict]:
    msgs = list(messages_col.find(
        {"session_id": session_id},
        sort=[("timestamp", 1)]
    ).limit(500))
    return msgs


# ─── AI BACKENDS ──────────────────────────────────────────────────────
async def call_claude(session_id: str, user_message: str, extra_context: str = "") -> str:
    # Build history context as a prefix in the system message instead of re-sending
    history = get_session_messages(session_id)
    history_context = ""
    if history:
        recent = history[-20:]
        history_lines = ["\n\n[CONVERSATION HISTORY]\n"]
        for msg in recent:
            role_label = "CLIENT" if msg["role"] == "user" else "SCSS AB ADVOCATE"
            history_lines.append(f"{role_label}: {msg['content'][:500]}\n")
        history_context = "\n".join(history_lines)

    # Use unique per-request session to avoid LlmChat internal history conflicts
    request_session_id = f"{session_id}-{len(history)}"
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=request_session_id,
        system_message=ALBERTA_SYSTEM_PROMPT + history_context + extra_context,
    ).with_model("anthropic", "claude-sonnet-4-6")

    resp = await chat.send_message(UserMessage(text=user_message))
    return resp


async def call_grok(session_id: str, user_message: str, extra_context: str = "") -> str:
    # Build messages list from MongoDB history
    history = get_session_messages(session_id)
    messages = [{"role": "system", "content": ALBERTA_SYSTEM_PROMPT + extra_context}]

    for msg in history[-20:]:  # last 20 messages
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
        })
    messages.append({"role": "user", "content": user_message})

    try:
        response = await xai_client.chat.completions.create(
            model="grok-3",
            messages=messages,
            max_tokens=4096,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        # Fallback to grok-3-beta if grok-3 not found
        if "model" in str(e).lower() or "not found" in str(e).lower():
            try:
                response = await xai_client.chat.completions.create(
                    model="grok-beta",
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.7,
                )
                return response.choices[0].message.content
            except Exception as e2:
                raise HTTPException(status_code=500, detail=f"Grok API error: {str(e2)}")
        raise HTTPException(status_code=500, detail=f"Grok API error: {str(e)}")


# ─── ROUTES ───────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "SCSS AB Advocate", "timestamp": utcnow().isoformat()}


@app.get("/api/debug")
async def debug_health():
    """Comprehensive debug & health check for all subsystems."""
    import platform, sys

    checks = {}

    # ── MongoDB ──
    try:
        mongo_client.admin.command("ping")
        checks["mongodb"] = {
            "status": "ok",
            "collections": {
                "chat_sessions": sessions_col.count_documents({}),
                "chat_messages": messages_col.count_documents({}),
                "email_references": emails_col.count_documents({}),
                "ec_conversion_jobs": ec_jobs_col.count_documents({}),
                "ec_converted_emails": ec_emails_col.count_documents({}),
                "ec_email_attachments": ec_attachments_col.count_documents({}),
            },
        }
    except Exception as e:
        checks["mongodb"] = {"status": "error", "error": str(e)}

    # ── Claude (Emergent LLM Key) ──
    checks["claude"] = {
        "status": "ok" if EMERGENT_LLM_KEY else "missing_key",
        "key_prefix": EMERGENT_LLM_KEY[:12] + "..." if EMERGENT_LLM_KEY else None,
        "model": "claude-sonnet-4-6",
    }

    # ── Grok (xAI) — live ping ──
    grok_status = {"key_prefix": XAI_API_KEY[:12] + "..." if XAI_API_KEY else None}
    if XAI_API_KEY:
        try:
            test_resp = await xai_client.chat.completions.create(
                model="grok-3",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            grok_status["status"] = "ok"
            grok_status["model"] = "grok-3"
            grok_status["response_sample"] = test_resp.choices[0].message.content
        except Exception as e:
            err_str = str(e)
            # Detect no-credits error specifically
            if "credits" in err_str.lower() or "licenses" in err_str.lower():
                grok_status["status"] = "no_credits"
                grok_status["error"] = "xAI account has no credits or licenses. Add credits at: https://console.x.ai"
                # Extract team URL if present
                import re as _re
                match = _re.search(r'https://console\.x\.ai/team/[^\s"]+', err_str)
                if match:
                    grok_status["credits_url"] = match.group(0)
            else:
                # Try fallback model
                try:
                    test_resp2 = await xai_client.chat.completions.create(
                        model="grok-beta",
                        messages=[{"role": "user", "content": "ping"}],
                        max_tokens=5,
                    )
                    grok_status["status"] = "ok_fallback"
                    grok_status["model"] = "grok-beta"
                    grok_status["note"] = f"grok-3 failed: {err_str[:80]}"
                except Exception as e2:
                    grok_status["status"] = "error"
                    grok_status["error"] = f"grok-3: {err_str[:120]} | grok-beta: {str(e2)[:120]}"
    else:
        grok_status["status"] = "missing_key"
    checks["grok"] = grok_status

    # ── Web Search ──
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            r = list(ddgs.text("Alberta ETW appeal", max_results=1))
        checks["web_search"] = {"status": "ok", "test_result_count": len(r)}
    except Exception as e:
        checks["web_search"] = {"status": "error", "error": str(e)[:120]}

    # ── System ──
    checks["system"] = {
        "python": sys.version,
        "platform": platform.platform(),
        "db_name": DB_NAME,
        "env_loaded": all([MONGO_URL, EMERGENT_LLM_KEY, XAI_API_KEY]),
    }

    # ── Overall status ──
    all_ok = all(
        v.get("status") in ("ok", "ok_fallback")
        for k, v in checks.items()
        if isinstance(v, dict) and k != "system"
    )
    return {
        "overall": "healthy" if all_ok else "degraded",
        "timestamp": utcnow().isoformat(),
        "checks": checks,
    }


@app.get("/api/models")
async def get_models():
    return {
        "models": [
            {
                "id": "claude",
                "name": "Claude Sonnet 4.6",
                "provider": "Anthropic",
                "description": "Advanced reasoning & long context analysis",
                "available": bool(EMERGENT_LLM_KEY),
            },
            {
                "id": "grok",
                "name": "Grok 3",
                "provider": "xAI",
                "description": "Real-time knowledge & direct answers",
                "available": bool(XAI_API_KEY),
            },
        ]
    }


# ─── SESSIONS ─────────────────────────────────────────────────────────

@app.get("/api/sessions")
async def list_sessions():
    docs = list(sessions_col.find({}, sort=[("created_at", -1)]).limit(100))
    return {"sessions": serialize_doc(docs)}


@app.post("/api/sessions")
async def create_session(body: SessionCreate):
    title = body.title or f"Case {datetime.now(timezone.utc).strftime('%b %d %H:%M')}"
    doc = {
        "title": title,
        "model": body.model,
        "created_at": utcnow(),
        "updated_at": utcnow(),
        "message_count": 0,
    }
    result = sessions_col.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    try:
        oid = ObjectId(session_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    sessions_col.delete_one({"_id": oid})
    messages_col.delete_many({"session_id": session_id})
    return {"success": True}


@app.get("/api/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    msgs = get_session_messages(session_id)
    return {"messages": serialize_doc(msgs)}


# ─── CHAT ─────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(req: ChatRequest):
    # Validate session
    try:
        oid = ObjectId(req.session_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = sessions_col.find_one({"_id": oid})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Store user message
    user_msg_doc = {
        "session_id": req.session_id,
        "role": "user",
        "content": req.message,
        "timestamp": utcnow(),
        "model": req.model,
    }
    messages_col.insert_one(user_msg_doc)

# Build extra context via web search — ALL models always get internet access
    extra_context = ""
    search_results = []
    if req.search_enabled:
        search_query = f"Alberta ETW ALSS {req.message}"
        search_results = web_search(search_query, max_results=4)
        extra_context = build_search_context(search_results)

    # Always include ALL email references saved in the database
    email_context = ""
    all_refs = list(emails_col.find({}, sort=[("created_at", -1)]).limit(20))
    if all_refs:
        email_context = "\n\n[EMAIL REFERENCES — Saved documents the user has uploaded for this case]\n"
        for e in all_refs:
            email_context += (
                f"\n--- REFERENCE: {e.get('subject', 'Untitled')} ---\n"
                f"From: {e.get('sender','')}\n"
                f"To: {e.get('recipients','')}\n"
                f"Date: {e.get('email_date','')}\n"
                f"{e.get('body','')[:1000]}\n"
            )

    full_extra = extra_context + email_context

    # Call AI
    try:
        if req.model == "grok":
            ai_response = await call_grok(req.session_id, req.message, full_extra)
        else:
            ai_response = await call_claude(req.session_id, req.message, full_extra)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")

    # Store AI response
    ai_msg_doc = {
        "session_id": req.session_id,
        "role": "assistant",
        "content": ai_response,
        "timestamp": utcnow(),
        "model": req.model,
        "citations": search_results,
    }
    messages_col.insert_one(ai_msg_doc)

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


# ─── WEB SEARCH ENDPOINT ──────────────────────────────────────────────

@app.post("/api/web-search")
async def do_web_search(body: dict):
    query = body.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query required")
    results = web_search(f"Alberta {query}", max_results=6)
    return {"results": results, "query": query}


# ─── EMAIL REFERENCES ─────────────────────────────────────────────────

@app.get("/api/emails")
async def list_emails(
    q: Optional[str] = Query(None),
    case_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    query = {}
    if case_id:
        query["case_id"] = case_id
    if q:
        query["$or"] = [
            {"subject": {"$regex": q, "$options": "i"}},
            {"sender": {"$regex": q, "$options": "i"}},
            {"recipients": {"$regex": q, "$options": "i"}},
            {"body": {"$regex": q, "$options": "i"}},
        ]

    total = emails_col.count_documents(query)
    projection = {"subject": 1, "sender": 1, "recipients": 1, "email_date": 1, "case_id": 1, "tags": 1, "created_at": 1}
    docs = list(emails_col.find(query, projection, sort=[("email_date", -1)]).skip(offset).limit(limit))
    return {"emails": serialize_doc(docs), "total": total}


@app.post("/api/emails")
async def create_email(body: EmailCreate):
    doc = {
        "subject": body.subject,
        "sender": body.sender,
        "recipients": body.recipients,
        "body": body.body,
        "email_date": body.email_date or utcnow().isoformat(),
        "case_id": body.case_id,
        "tags": body.tags or [],
        "created_at": utcnow(),
    }
    result = emails_col.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


@app.get("/api/emails/{email_id}")
async def get_email(email_id: str):
    try:
        oid = ObjectId(email_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid email ID")
    doc = emails_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Email not found")
    return serialize_doc(doc)


@app.delete("/api/emails/{email_id}")
async def delete_email(email_id: str):
    try:
        oid = ObjectId(email_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid email ID")
    emails_col.delete_one({"_id": oid})
    return {"success": True}


# ─── ALBERTA POLICY RESOURCES ─────────────────────────────────────────

@app.get("/api/policy-resources")
async def get_policy_resources():
    return {
        "resources": [
            {
                "title": "Income Support Policy Manual",
                "url": "https://www.alberta.ca/income-support-policy-manual",
                "category": "Policy Manual",
                "description": "Official Alberta Works Income Support policy manual including ETW",
            },
            {
                "title": "Appeal an Income/Employment Supports Decision",
                "url": "https://www.alberta.ca/appeal-income-employment-supports-decision",
                "category": "Appeals",
                "description": "Official appeals process, forms and deadlines",
            },
            {
                "title": "Income/Employment Supports Appeal Hearing",
                "url": "https://www.alberta.ca/income-employment-supports-appeal-hearing",
                "category": "Appeals",
                "description": "What to expect at your Citizens Appeal Panel hearing",
            },
            {
                "title": "SCSS Annual Report 2024-2025",
                "url": "https://open.alberta.ca/dataset/3a6b50d8-c1f2-4e9a-94ec-62f1e0a34e59/resource/5b876aae-aaae-4c93-a9a1-4fe1305c7b39/download/scss-annual-report-2024-2025.pdf",
                "category": "Annual Report",
                "description": "Seniors and Community Support Services annual report",
            },
            {
                "title": "Seniors Financial Assistance Information Booklet 2025",
                "url": "https://open.alberta.ca/dataset/8df5377c-5db8-415c-b282-cf5623a8a9b7/resource/abfbab87-0eff-49d2-91c7-6e8b3d4464b1/download/alss-seniors-financial-assistance-information-booklet-2025-10.pdf",
                "category": "Seniors Benefits",
                "description": "ALSS seniors financial assistance information booklet",
            },
            {
                "title": "Alberta Works Your Guide to Income Support",
                "url": "https://open.alberta.ca/dataset/038f1b12-e9c5-4342-99bc-512a10388a0e/resource/96e9430a-6875-4ce6-b061-5fb6c24e45c6/download/zz-2011-alberta-works-your-guide-to-income-support.pdf",
                "category": "Program Guide",
                "description": "Comprehensive guide to Alberta Works Income Support programs",
            },
            {
                "title": "Supportive Living – How to Appeal",
                "url": "https://www.alberta.ca/supportive-living-accommodation-licensing-how-to-appeal",
                "category": "Appeals",
                "description": "Appeal process for supportive living accommodation decisions",
            },
            {
                "title": "Protection for Persons in Care – How to Appeal",
                "url": "https://www.alberta.ca/protection-for-persons-in-care-how-to-appeal",
                "category": "Appeals",
                "description": "Appeal process under Protection for Persons in Care Act",
            },
            {
                "title": "Alberta Ombudsman – Appeals Secretariat",
                "url": "https://www.ombudsman.ab.ca/complaint-checker/government-of-alberta/appeals-secretariat-citizens-appeal-panel/",
                "category": "Oversight",
                "description": "Ombudsman process for CAP decision review",
            },
            {
                "title": "Auditor General: Income Support for Albertans 2024",
                "url": "https://www.oag.ab.ca/wp-content/uploads/2024/03/2024-Income-Support-for-Albertans-AOI.pdf",
                "category": "Oversight",
                "description": "Auditor General review of income support program administration",
            },
        ]
    }



# ═══════════════════════════════════════════════════════════════════════
# EMAIL CONVERTER — .EML / .MBOX / .PDF / .TXT → STRUCTURED JSON
# ═══════════════════════════════════════════════════════════════════════
import email as _email_lib
import mailbox as _mailbox_lib
import zipfile
import io
import re
import base64
from email.header import decode_header as _decode_header
import email.utils as _email_utils
from fastapi import UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List as TypingList

# MongoDB collections for email converter (mirrors original PostgreSQL schema)
ec_jobs_col = db["ec_conversion_jobs"]
ec_emails_col = db["ec_converted_emails"]
ec_attachments_col = db["ec_email_attachments"]

SUPPORTED_EXTENSIONS = {"eml", "mbox", "pdf", "txt", "text", "html", "htm", "msg"}


# ── Filename generator (matches TypeScript format: YYYY/DD/MM:HH:MM - sender_subject) ──
def _sanitize_filename(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]', '_', s or "")
    s = re.sub(r'\s+', '_', s.strip())
    return s[:60] or "unknown"


def _generate_email_filename(dt, sender: str, subject: str) -> str:
    if dt:
        try:
            date_part = f"{dt.year}/{str(dt.day).zfill(2)}/{str(dt.month).zfill(2)}:{str(dt.hour).zfill(2)}:{str(dt.minute).zfill(2)}"
        except Exception:
            date_part = "unknown/date"
    else:
        date_part = "unknown/date"
    sender_clean = _sanitize_filename(sender)
    subject_clean = _sanitize_filename(subject)
    return f"{date_part} - {sender_clean}_{subject_clean}"


def _decode_header_value(val: str) -> str:
    if not val:
        return ""
    try:
        parts = _decode_header(val)
        decoded = []
        for part, enc in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(enc or "utf-8", errors="replace"))
            else:
                decoded.append(str(part))
        return " ".join(decoded)
    except Exception:
        return val


def _extract_text_from_html(html_str: str) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_str, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except Exception:
        return re.sub(r'<[^>]+>', '', html_str)


def _strip_signatures_and_quotes(text: str) -> str:
    """Remove quoted replies, email signatures, and common boilerplate noise."""
    if not text:
        return text
    lines = text.splitlines()
    clean_lines = []
    # Signatures typically follow a line that is exactly "-- " or "___" or similar
    sig_patterns = re.compile(
        r'^(--|_{3,}|-{3,}|Sent from .+|Get Outlook for|This email (was sent|is confidential)|'
        r'CONFIDENTIAL|DISCLAIMER|Please consider the environment|On .+ wrote:|>'
        r'|\[cid:|-----Original Message-----).*$',
        re.IGNORECASE
    )
    in_signature = False
    for line in lines:
        stripped = line.strip()
        # Quoted-reply marker — stop collecting
        if stripped.startswith(">") or sig_patterns.match(stripped):
            in_signature = True
        if not in_signature:
            clean_lines.append(line)
    result = "\n".join(clean_lines).strip()
    # Collapse excessive blank lines
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from a PDF using pdfplumber."""
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
        return "\n\n".join(pages).strip() or "<EMPTY PDF>"
    except Exception as e:
        return f"<PDF EXTRACTION ERROR: {e}>"


def _parse_pdf_as_doc(filename: str, file_bytes: bytes) -> dict:
    """Parse a PDF file into the same structured dict as email records."""
    body_text = _extract_pdf_text(file_bytes)
    name_no_ext = re.sub(r'\.[^.]+$', '', filename)
    now = datetime.now(timezone.utc)
    return {
        "generated_filename": f"{now.year}/{str(now.day).zfill(2)}/{str(now.month).zfill(2)}:{str(now.hour).zfill(2)}:{str(now.minute).zfill(2)} - document_{_sanitize_filename(name_no_ext)}",
        "subject": name_no_ext,
        "sender": "Document",
        "recipients": "",
        "email_date": now,
        "body_text": body_text,
        "has_attachments": False,
        "attachment_count": 0,
        "attachment_names": None,
        "attachments": [],
        "file_type": "pdf",
    }


def _parse_txt_as_doc(filename: str, file_bytes: bytes) -> dict:
    """Parse a plain-text file into the same structured dict."""
    try:
        body_text = file_bytes.decode("utf-8", errors="replace").strip() or "<EMPTY FILE>"
    except Exception:
        body_text = "<DECODE ERROR>"
    name_no_ext = re.sub(r'\.[^.]+$', '', filename)
    now = datetime.now(timezone.utc)
    return {
        "generated_filename": f"{now.year}/{str(now.day).zfill(2)}/{str(now.month).zfill(2)}:{str(now.hour).zfill(2)}:{str(now.minute).zfill(2)} - document_{_sanitize_filename(name_no_ext)}",
        "subject": name_no_ext,
        "sender": "Document",
        "recipients": "",
        "email_date": now,
        "body_text": body_text,
        "has_attachments": False,
        "attachment_count": 0,
        "attachment_names": None,
        "attachments": [],
        "file_type": "txt",
    }


def _parse_single_email(msg) -> dict:
    """Parse a single email.message.Message object into structured data."""
    subject = _decode_header_value(msg.get("Subject", ""))
    sender = _decode_header_value(msg.get("From", ""))
    recipients = _decode_header_value(msg.get("To", ""))
    date_str = msg.get("Date", "")
    email_date = None
    if date_str:
        try:
            parsed_tuple = _email_utils.parsedate_tz(date_str)
            if parsed_tuple:
                ts = _email_utils.mktime_tz(parsed_tuple)
                email_date = datetime.fromtimestamp(ts, timezone.utc)
        except Exception:
            pass

    # Extract body
    body_text = ""
    body_html = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in disp:
                try:
                    body_text += part.get_payload(decode=True).decode(
                        part.get_content_charset("utf-8") or "utf-8", errors="replace"
                    )
                except Exception:
                    pass
            elif ct == "text/html" and "attachment" not in disp and not body_text:
                try:
                    body_html = part.get_payload(decode=True).decode(
                        part.get_content_charset("utf-8") or "utf-8", errors="replace"
                    )
                except Exception:
                    pass
            elif "attachment" in disp or (part.get_filename()):
                fname = _decode_header_value(part.get_filename() or "attachment")
                try:
                    raw = part.get_payload(decode=True) or b""
                    attachments.append({
                        "filename": fname,
                        "content_type": ct,
                        "size": len(raw),
                        "data_base64": base64.b64encode(raw).decode("ascii"),
                    })
                except Exception:
                    attachments.append({
                        "filename": fname,
                        "content_type": ct,
                        "size": 0,
                        "data_base64": "",
                    })
    else:
        ct = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode(msg.get_content_charset("utf-8") or "utf-8", errors="replace")
                if ct == "text/html":
                    body_html = text
                else:
                    body_text = text
        except Exception:
            pass

    if not body_text and body_html:
        body_text = _extract_text_from_html(body_html)

    # Strip signatures and quoted replies for clean embeddings
    clean_body = _strip_signatures_and_quotes(body_text)

    att_names = ", ".join(a["filename"] for a in attachments) if attachments else None
    generated_filename = _generate_email_filename(email_date, sender, subject)

    # Structured JSON for embeddings
    structured_json = {
        "subject": subject or "<NO SUBJECT>",
        "sender": sender or "<UNKNOWN>",
        "recipients": recipients or "",
        "date": email_date.isoformat() if email_date else None,
        "clean_body": clean_body,
        "body_word_count": len(clean_body.split()) if clean_body else 0,
        "has_attachments": len(attachments) > 0,
        "attachment_count": len(attachments),
        "attachments": [{"filename": a["filename"], "content_type": a["content_type"], "size": a["size"]} for a in attachments],
    }

    return {
        "generated_filename": generated_filename,
        "subject": subject or "<NO SUBJECT>",
        "sender": sender or "<UNKNOWN>",
        "recipients": recipients or "",
        "email_date": email_date,
        "body_text": clean_body.strip() or "<EMPTY BODY>",
        "structured_json": structured_json,
        "has_attachments": len(attachments) > 0,
        "attachment_count": len(attachments),
        "attachment_names": att_names,
        "attachments": attachments,
    }


def _build_txt_content(email_doc: dict) -> str:
    lines = [
        f"FILE: {email_doc.get('generated_filename', 'unknown')}",
        "=" * 60,
        f"Subject:    {email_doc.get('subject', '')}",
        f"From:       {email_doc.get('sender', '')}",
        f"To:         {email_doc.get('recipients', '')}",
        f"Date:       {email_doc.get('email_date', 'Unknown')}",
    ]
    if email_doc.get("has_attachments"):
        lines.append(f"Attachments ({email_doc['attachment_count']}): {email_doc.get('attachment_names', '')}")
    lines += ["=" * 60, "", email_doc.get("body_text", "")]
    if email_doc.get("has_attachments") and email_doc.get("attachment_names"):
        lines += [
            "",
            "── ATTACHMENT INDEX ──",
        ]
        for name in (email_doc.get("attachment_names") or "").split(","):
            lines.append(f"  [ATTACHMENT] {name.strip()}")
        lines.append("── (Attachments stored in database, available for retrieval) ──")
    return "\n".join(lines)


async def _process_job_background(job_id: str, file_bytes: bytes, file_type: str, original_filename: str = ""):
    """Background task: parse emails/documents and store in MongoDB."""
    oid = ObjectId(job_id)
    ec_jobs_col.update_one({"_id": oid}, {"$set": {"status": "processing", "updated_at": utcnow()}})

    try:
        parsed_emails = []
        if file_type == "pdf":
            parsed_emails = [_parse_pdf_as_doc(original_filename, file_bytes)]
        elif file_type in ("txt", "text", "html", "htm"):
            parsed_emails = [_parse_txt_as_doc(original_filename, file_bytes)]
        elif file_type == "eml":
            msg = _email_lib.message_from_bytes(file_bytes, policy=_email_lib.policy.compat32)
            parsed_emails = [_parse_single_email(msg)]
        elif file_type == "mbox":
            mbox_buf = io.BytesIO(file_bytes)
            mbox_buf.seek(0)
            text_content = file_bytes.decode("utf-8", errors="replace")
            from_pattern = re.compile(r'^From\s+\S+.*$', re.MULTILINE)
            splits = from_pattern.split(text_content)
            splits = [s for s in splits if s.strip()]
            if not splits:
                splits = [text_content]
            for chunk in splits:
                try:
                    msg = _email_lib.message_from_string(
                        "From nobody\n" + chunk if not chunk.startswith("From") else chunk,
                        policy=_email_lib.policy.compat32
                    )
                    parsed = _parse_single_email(msg)
                    if parsed["subject"] != "<NO SUBJECT>" or parsed["sender"] != "<UNKNOWN>" or len(parsed["body_text"]) > 5:
                        parsed_emails.append(parsed)
                except Exception:
                    continue
        else:
            # Generic: try as text
            parsed_emails = [_parse_txt_as_doc(original_filename, file_bytes)]

        total = len(parsed_emails)
        ec_jobs_col.update_one({"_id": oid}, {"$set": {"total_emails": total, "updated_at": utcnow()}})

        for i, ep in enumerate(parsed_emails):
            # Insert email record
            email_doc = {
                "job_id": job_id,
                "generated_filename": ep["generated_filename"],
                "subject": ep["subject"],
                "sender": ep["sender"],
                "recipients": ep["recipients"],
                "email_date": ep["email_date"],
                "body_text": ep["body_text"],
                "structured_json": ep.get("structured_json"),
                "has_attachments": ep["has_attachments"],
                "attachment_count": ep["attachment_count"],
                "attachment_names": ep["attachment_names"],
                "created_at": utcnow(),
            }
            email_result = ec_emails_col.insert_one(email_doc)
            email_id = str(email_result.inserted_id)

            # Insert attachments
            for att in ep["attachments"]:
                ec_attachments_col.insert_one({
                    "email_id": email_id,
                    "filename": att["filename"],
                    "content_type": att["content_type"],
                    "size": att["size"],
                    "data_base64": att["data_base64"],
                    "created_at": utcnow(),
                })

            ec_jobs_col.update_one({"_id": oid}, {"$set": {"processed_emails": i + 1, "updated_at": utcnow()}})

        ec_jobs_col.update_one(
            {"_id": oid},
            {"$set": {"status": "completed", "processed_emails": total, "updated_at": utcnow()}}
        )
    except Exception as e:
        ec_jobs_col.update_one(
            {"_id": oid},
            {"$set": {"status": "failed", "error_message": str(e), "updated_at": utcnow()}}
        )


# ── EC Routes ──────────────────────────────────────────────────────────

@app.post("/api/ec/upload")
async def ec_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    filename = file.filename or "unknown"
    # Strip any path prefix (from folder uploads, browser sends relative paths)
    filename = filename.replace("\\", "/").split("/")[-1]
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    file_bytes = await file.read()

    job_doc = {
        "original_filename": filename,
        "file_type": ext,
        "status": "pending",
        "total_emails": 0,
        "processed_emails": 0,
        "error_message": None,
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    result = ec_jobs_col.insert_one(job_doc)
    job_id = str(result.inserted_id)

    background_tasks.add_task(_process_job_background, job_id, file_bytes, ext, filename)

    job_doc["id"] = job_id
    job_doc.pop("_id", None)
    return job_doc


@app.post("/api/ec/upload-batch")
async def ec_upload_batch(
    background_tasks: BackgroundTasks,
    files: TypingList[UploadFile] = File(...),
):
    """Accept multiple files in one request (for folder uploads)."""
    results = []
    for file in files:
        filename = file.filename or "unknown"
        filename = filename.replace("\\", "/").split("/")[-1]
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in SUPPORTED_EXTENSIONS:
            results.append({"filename": filename, "skipped": True, "reason": f"Unsupported type .{ext}"})
            continue
        file_bytes = await file.read()
        job_doc = {
            "original_filename": filename,
            "file_type": ext,
            "status": "pending",
            "total_emails": 0,
            "processed_emails": 0,
            "error_message": None,
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        result = ec_jobs_col.insert_one(job_doc)
        job_id = str(result.inserted_id)
        background_tasks.add_task(_process_job_background, job_id, file_bytes, ext, filename)
        job_doc["id"] = job_id
        job_doc.pop("_id", None)
        results.append({"filename": filename, "job": job_doc})
    return {"results": results, "total_queued": sum(1 for r in results if not r.get("skipped"))}


@app.get("/api/ec/jobs")
async def ec_list_jobs(
    limit: int = Query(10, le=100),
    offset: int = Query(0),
):
    total = ec_jobs_col.count_documents({})
    docs = list(ec_jobs_col.find({}, sort=[("created_at", -1)]).skip(offset).limit(limit))
    return {"jobs": serialize_doc(docs), "total": total}


@app.get("/api/ec/jobs/{job_id}")
async def ec_get_job(job_id: str):
    try:
        oid = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job ID")
    job = ec_jobs_col.find_one({"_id": oid})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    emails = list(ec_emails_col.find({"job_id": job_id}, sort=[("created_at", 1)]))
    return {"job": serialize_doc(job), "emails": serialize_doc(emails)}


@app.delete("/api/ec/jobs/{job_id}")
async def ec_delete_job(job_id: str):
    try:
        oid = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job ID")
    emails = list(ec_emails_col.find({"job_id": job_id}, {"_id": 1}))
    email_ids = [str(e["_id"]) for e in emails]
    if email_ids:
        ec_attachments_col.delete_many({"email_id": {"$in": email_ids}})
    ec_emails_col.delete_many({"job_id": job_id})
    ec_jobs_col.delete_one({"_id": oid})
    return {"success": True}


@app.delete("/api/ec/wipe")
async def ec_wipe_all():
    """Wipe all conversion jobs, emails, and attachments from the database."""
    ec_attachments_col.delete_many({})
    ec_emails_col.delete_many({})
    result = ec_jobs_col.delete_many({})
    return {"success": True, "deleted_jobs": result.deleted_count}


@app.get("/api/ec/emails/{email_id}/download")
async def ec_download_email(email_id: str):
    try:
        oid = ObjectId(email_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid email ID")
    doc = ec_emails_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Email not found")
    content = _build_txt_content(doc)
    safe_name = re.sub(r'[^\w\-.]', '_', doc.get("generated_filename", "email"))
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.txt"'},
    )


@app.get("/api/ec/jobs/{job_id}/export")
async def ec_export_job_zip(job_id: str):
    try:
        oid = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job ID")
    job = ec_jobs_col.find_one({"_id": oid})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    emails = list(ec_emails_col.find({"job_id": job_id}, sort=[("created_at", 1)]))

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for em in emails:
            content = _build_txt_content(em)
            fname = re.sub(r'[^\w\-./]', '_', em.get("generated_filename", "email")) + ".txt"
            zf.writestr(fname, content)

            # Include attachments if any
            if em.get("has_attachments"):
                att_docs = list(ec_attachments_col.find({"email_id": str(em["_id"])}))
                for att in att_docs:
                    try:
                        att_bytes = base64.b64decode(att.get("data_base64", ""))
                        att_fname = re.sub(r'[^\w\-.]', '_', att.get("filename", "attachment"))
                        base_fname = fname.replace(".txt", "")
                        zf.writestr(f"{base_fname}_attachments/{att_fname}", att_bytes)
                    except Exception:
                        pass

    zip_buf.seek(0)
    safe_job_name = re.sub(r'[^\w\-.]', '_', job.get("original_filename", "job"))
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="CONVERTED_{safe_job_name}.zip"'},
    )


@app.get("/api/ec/emails/{email_id}/attachments")
async def ec_get_attachments(email_id: str):
    docs = list(ec_attachments_col.find(
        {"email_id": email_id},
        {"data_base64": 0}  # exclude large base64 from list
    ))
    return {"attachments": serialize_doc(docs)}


@app.get("/api/ec/attachments/{att_id}/download")
async def ec_download_attachment(att_id: str):
    try:
        oid = ObjectId(att_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid attachment ID")
    doc = ec_attachments_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Attachment not found")
    try:
        att_bytes = base64.b64decode(doc.get("data_base64", ""))
    except Exception:
        att_bytes = b""
    fname = doc.get("filename", "attachment")
    ct = doc.get("content_type", "application/octet-stream")
    return StreamingResponse(
        io.BytesIO(att_bytes),
        media_type=ct,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
