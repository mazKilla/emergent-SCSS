# SCSS AB ADVOCATE — PRD

## App Overview
AI-powered Alberta social benefits adjudicator and appeal guidance platform. The AI acts as "#1 Social Benefit and Justice Adjudicator" — Appeal Officer for the Appeals Secretariat, Ministry of Assisted Living and Social Services (ALSS), Government of Alberta.

## Architecture
- **Frontend**: React (Create React App) + Tailwind CSS — Port 3000
- **Backend**: FastAPI (Python) + MongoDB — Port 8001
- **AI Models**: Claude Sonnet 4.5 (Anthropic via Emergent LLM Key) + Grok 3 (xAI API)
- **Database**: MongoDB (sessions, messages, email references)
- **Web Search**: DuckDuckGo Search (auto-triggered on policy queries)
- **GitHub Ref**: https://github.com/mazzkilla1/Email-Transformer (PostgreSQL email schema reference)

## Core Requirements (Static)
1. AI orchestrator agent fully briefed on Alberta ETW, ALSS, SCSS policies
2. User-selectable AI model: Claude Sonnet 4.5 OR Grok 3
3. Long context memory (last 20 messages passed as context)
4. Automatic web search for Alberta policy queries
5. Email references panel (add/view/search/attach to chat)
6. Case/Session management (create, list, delete, per-session history)
7. High contrast shimmering dark theme — MazZKiLL@ logo in electric cyan
8. Alberta system prompt: ETW program, ALSS, appeal process, advocacy strategy

## What's Been Implemented (2026-03-31)
### Backend (`/app/backend/server.py`)
- FastAPI with CORS, MongoDB connection
- Alberta system prompt with comprehensive ETW/ALSS/SCSS policy knowledge
- `POST /api/chat` — AI chat with auto web search + email context
- `GET/POST /api/sessions`, `DELETE /api/sessions/{id}` — Session management
- `GET /api/sessions/{id}/messages` — Message history
- `GET/POST /api/emails`, `GET/DELETE /api/emails/{id}` — Email references (MongoDB)
- `POST /api/web-search` — DuckDuckGo web search
- `GET /api/policy-resources` — Alberta policy resource links
- `GET /api/models` — Available AI models
- Claude integration: emergentintegrations (claude-sonnet-4-5-20250929)
- Grok3 integration: openai SDK with xAI base URL (grok-3 + grok-beta fallback)

### Frontend (`/app/frontend/src/`)
- `App.js` — Main layout with full state management
- `Header.js` — MazZKiLL@ logo, model selector toggle (Claude/Grok3), Email panel toggle
- `Sidebar.js` — Session/case list, create new session, delete sessions
- `ChatArea.js` — Chat messages, textarea input, quick start prompts, thinking animation
- `MessageBubble.js` — Markdown rendering (react-markdown + remark-gfm), citations display
- `EmailPanel.js` — Email CRUD, search, detail view, attach to chat
- Design: #030305 deep black + #00FFD4 cyan + #A855F7 purple, Unbounded/IBM Plex Sans/JetBrains Mono fonts

## Prioritized Backlog
### P0 (Critical — must have)
- [x] AI chat (Claude + Grok3)
- [x] Session management  
- [x] Email references
- [x] Alberta policy system prompt

### P1 (High value)
- [ ] PostgreSQL email import from user's local DB (requires external access or import tool)
- [ ] Policy document PDF reader (crawl/parse Alberta.ca PDFs)
- [ ] Appeal letter template generator
- [ ] Export case to PDF

### P2 (Nice to have)
- [ ] Rate limiting on /api/chat
- [ ] Async MongoDB (motor driver) for better performance
- [ ] Authentication/multi-user support
- [ ] Case tagging and categorization
- [ ] Search across all sessions

## Environment Variables
- Backend: MONGO_URL, DB_NAME, EMERGENT_LLM_KEY, XAI_API_KEY, PG_* (for future PostgreSQL)
- Frontend: REACT_APP_BACKEND_URL

## Test Results (2026-03-31)
- Backend: 100% (15/15 tests passed)
- Frontend: 95% all core flows verified
