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

# ─── ENVIRONMENT ────────────────────────────────────────────────────
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "scss_advocate")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
XAI_API_KEY = os.environ.get("XAI_API_KEY")

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
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

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


@app.get("/api/models")
async def get_models():
    return {
        "models": [
            {
                "id": "claude",
                "name": "Claude Sonnet 4.5",
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

    # Build extra context via web search
    extra_context = ""
    search_results = []
    if req.search_enabled and is_policy_query(req.message):
        search_query = f"Alberta {req.message} ETW ALSS income support policy"
        search_results = web_search(search_query, max_results=4)
        extra_context = build_search_context(search_results)

    # Check for relevant emails in DB
    email_context = ""
    session_title = session.get("title", "")
    if session.get("case_id"):
        emails = list(emails_col.find({"case_id": session["case_id"]}).limit(3))
        if emails:
            email_context = "\n\n[EMAIL REFERENCES FOR THIS CASE]\n"
            for e in emails:
                email_context += f"\nFrom: {e.get('sender','')}\nTo: {e.get('recipients','')}\nSubject: {e.get('subject','')}\nDate: {e.get('email_date','')}\n---\n{e.get('body','')[:800]}\n"

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
