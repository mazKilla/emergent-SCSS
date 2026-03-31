import React, { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import ChatArea from "./components/ChatArea";
import EmailPanel from "./components/EmailPanel";
import EmailConverter from "./components/EmailConverter";
import DebugPanel from "./components/DebugPanel";

const API = process.env.REACT_APP_BACKEND_URL;

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [selectedModel, setSelectedModel] = useState("claude");
  const [isLoading, setIsLoading] = useState(false);
  const [showEmailPanel, setShowEmailPanel] = useState(false);
  const [emailCount, setEmailCount] = useState(0);
  const [activeTab, setActiveTab] = useState("chat"); // "chat" | "converter"
  const [showDebug, setShowDebug] = useState(false);

  // Load sessions on mount
  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/sessions`);
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (e) {
      console.error("Failed to load sessions", e);
    }
  }, []);

  useEffect(() => {
    loadSessions();
    // Load email count
    fetch(`${API}/api/emails`)
      .then(r => r.json())
      .then(d => setEmailCount(d.total || 0))
      .catch(() => {});
  }, [loadSessions]);

  // Load messages for active session
  const loadMessages = useCallback(async (sessionId) => {
    try {
      const res = await fetch(`${API}/api/sessions/${sessionId}/messages`);
      const data = await res.json();
      setMessages(data.messages || []);
    } catch (e) {
      console.error("Failed to load messages", e);
    }
  }, []);

  useEffect(() => {
    if (activeSession) {
      loadMessages(activeSession.id);
    } else {
      setMessages([]);
    }
  }, [activeSession, loadMessages]);

  const createSession = async (title) => {
    try {
      const res = await fetch(`${API}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title || null, model: selectedModel }),
      });
      const session = await res.json();
      setSessions(prev => [session, ...prev]);
      setActiveSession(session);
      setMessages([]);
    } catch (e) {
      console.error("Failed to create session", e);
    }
  };

  const deleteSession = async (sessionId) => {
    try {
      await fetch(`${API}/api/sessions/${sessionId}`, { method: "DELETE" });
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSession?.id === sessionId) {
        setActiveSession(null);
        setMessages([]);
      }
    } catch (e) {
      console.error("Failed to delete session", e);
    }
  };

  const sendMessage = async (content) => {
    if (!content.trim() || isLoading) return;

    let sessionId = activeSession?.id;

    // Auto-create session if none active
    if (!sessionId) {
      try {
        const res = await fetch(`${API}/api/sessions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: content.slice(0, 60),
            model: selectedModel,
          }),
        });
        const session = await res.json();
        setSessions(prev => [session, ...prev]);
        setActiveSession(session);
        sessionId = session.id;
      } catch (e) {
        console.error("Failed to auto-create session", e);
        return;
      }
    }

    // Optimistic UI — add user message
    const userMsg = {
      id: `temp-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
      model: selectedModel,
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: content,
          model: selectedModel,
          search_enabled: true,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "API error");
      }

      const data = await res.json();

      // Add AI response
      const aiMsg = {
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: data.response,
        timestamp: new Date().toISOString(),
        model: data.model,
        citations: data.citations || [],
      };
      setMessages(prev => [...prev, aiMsg]);

      // Refresh session list to update message count
      loadSessions();
    } catch (e) {
      const errMsg = {
        id: `err-${Date.now()}`,
        role: "assistant",
        content: `**Error:** ${e.message}. Please try again.`,
        timestamp: new Date().toISOString(),
        model: selectedModel,
        isError: true,
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="flex flex-col h-screen w-screen overflow-hidden"
      style={{ background: "#030305", color: "#F8F8F8" }}
    >
      <Header
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        showEmailPanel={showEmailPanel}
        onToggleEmailPanel={() => setShowEmailPanel(v => !v)}
        emailCount={emailCount}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onOpenDebug={() => setShowDebug(true)}
      />

      <div className="flex flex-1 overflow-hidden">
        {activeTab === "chat" ? (
          <>
            {/* Left Sidebar */}
            <Sidebar
              sessions={sessions}
              activeSession={activeSession}
              onSelectSession={(s) => setActiveSession(s)}
              onNewSession={createSession}
              onDeleteSession={deleteSession}
            />

            {/* Main Chat Area */}
            <ChatArea
              messages={messages}
              isLoading={isLoading}
              onSendMessage={sendMessage}
              activeSession={activeSession}
              selectedModel={selectedModel}
            />

            {/* Right Email Panel */}
            {showEmailPanel && (
              <EmailPanel
                apiUrl={API}
                onEmailCountChange={setEmailCount}
                onAttachToChat={(emailContent) => {
                  sendMessage(`[EMAIL REFERENCE]\n\n${emailContent}`);
                }}
              />
            )}
          </>
        ) : (
          <EmailConverter onSendToAdvocate={(content, subject) => {
            setActiveTab("chat");
            setTimeout(() => {
              sendMessage(
                `[SEND TO ADVOCATE — Email Analysis Request]\n\nSubject: ${subject}\n\n` +
                `Please analyze this email correspondence for ETW/ALSS appeal relevance. ` +
                `Identify any policy violations, missed obligations, rights implications, ` +
                `and the strongest advocacy position for the recipient:\n\n---\n${content}`
              );
            }, 150);
          }} />
        )}
      </div>

      {showDebug && <DebugPanel onClose={() => setShowDebug(false)} />}
    </div>
  );
}
