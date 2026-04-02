# Test Credentials

## SCSS AB ADVOCATE

No authentication required — app is open access.

### AI Models
- **Claude Sonnet 4.6**: Uses EMERGENT_LLM_KEY (sk-emergent-c2a8c8c88900a9fBc3) in backend/.env — model ID: claude-sonnet-4-6
- **Grok 3 (xAI)**: Uses XAI_API_KEY (xai-FPwPQ5BAfaIvMIC4ERLNOtHTn08L0En2PoPf8CJRD39mxgWQmZuo49Lg2pRhjgs7l6L78oGDm1wgi130) in backend/.env
  - **NOTE**: xAI account currently has no credits — add at https://console.x.ai/team/891136df-18e0-4aac-897f-9a9de5e90430

### Security Gate
- **Question (QUERY)**: PUG_BUD
- **Answer (Passphrase)**: BENJI
- Stored in sessionStorage key: `scss_gate_v1`
- MongoDB: mongodb://localhost:27017 | DB: scss_advocate
- Collections: chat_sessions, chat_messages, email_references

### App URLs
- Frontend: https://neon-advocate.preview.emergentagent.com
- Backend API: https://neon-advocate.preview.emergentagent.com/api

### Test Data
- A test email "ETW Denial Notice - Test" may exist in MongoDB email_references collection from testing
- Test sessions created during testing may exist in chat_sessions collection
