import React, { useState, useEffect, useCallback } from "react";
import { Mail, Plus, Search, X, Send, ChevronRight, FileText, Trash2 } from "lucide-react";

export default function EmailPanel({ apiUrl, onEmailCountChange, onAttachToChat }) {
  const [emails, setEmails] = useState([]);
  const [total, setTotal] = useState(0);
  const [searchQ, setSearchQ] = useState("");
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const loadEmails = useCallback(async (q = "") => {
    setIsLoading(true);
    try {
      const url = q
        ? `${apiUrl}/api/emails?q=${encodeURIComponent(q)}&limit=50`
        : `${apiUrl}/api/emails?limit=50`;
      const res = await fetch(url);
      const data = await res.json();
      setEmails(data.emails || []);
      setTotal(data.total || 0);
      onEmailCountChange(data.total || 0);
    } catch (e) {
      console.error("Failed to load emails", e);
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, onEmailCountChange]);

  useEffect(() => {
    loadEmails();
  }, [loadEmails]);

  const handleSearch = (e) => {
    e.preventDefault();
    loadEmails(searchQ);
  };

  const deleteEmail = async (id) => {
    await fetch(`${apiUrl}/api/emails/${id}`, { method: "DELETE" });
    loadEmails(searchQ);
  };

  return (
    <aside
      data-testid="email-references-panel"
      className="flex flex-col shrink-0"
      style={{
        width: "320px",
        borderLeft: "1px solid rgba(255,255,255,0.08)",
        background: "#030305",
      }}
    >
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center justify-between"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        <div className="flex items-center gap-2">
          <Mail size={14} style={{ color: "#A855F7" }} />
          <span
            className="text-xs tracking-widest uppercase"
            style={{ fontFamily: "'JetBrains Mono', monospace", color: "#A855F7" }}
          >
            Email References
          </span>
          <span
            className="text-xs px-1.5 py-0.5 rounded"
            style={{
              background: "rgba(168,85,247,0.1)",
              color: "rgba(168,85,247,0.7)",
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            {total}
          </span>
        </div>
        <button
          data-testid="add-email-button"
          onClick={() => setShowAddForm(v => !v)}
          className="p-1.5 rounded transition-colors"
          style={{
            background: showAddForm ? "rgba(168,85,247,0.15)" : "transparent",
            border: "1px solid rgba(168,85,247,0.3)",
            color: "#A855F7",
            cursor: "pointer",
          }}
        >
          <Plus size={13} />
        </button>
      </div>

      {/* Add Email Form */}
      {showAddForm && (
        <AddEmailForm
          apiUrl={apiUrl}
          onSuccess={() => { loadEmails(searchQ); setShowAddForm(false); }}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      {/* Search Bar */}
      <form
        onSubmit={handleSearch}
        className="flex items-center gap-2 px-3 py-2"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        <Search size={12} style={{ color: "#A1A1AA", flexShrink: 0 }} />
        <input
          data-testid="email-search-input"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          placeholder="Search emails..."
          className="flex-1 bg-transparent text-xs outline-none"
          style={{
            color: "#F8F8F8",
            fontFamily: "'IBM Plex Sans', sans-serif",
          }}
        />
        {searchQ && (
          <button
            type="button"
            onClick={() => { setSearchQ(""); loadEmails(""); }}
            style={{ background: "none", border: "none", color: "#A1A1AA", cursor: "pointer" }}
          >
            <X size={11} />
          </button>
        )}
      </form>

      {/* Email List or Detail */}
      {selectedEmail ? (
        <EmailDetail
          email={selectedEmail}
          onBack={() => setSelectedEmail(null)}
          onAttach={() => {
            const content = `From: ${selectedEmail.sender}\nTo: ${selectedEmail.recipients}\nSubject: ${selectedEmail.subject}\nDate: ${selectedEmail.email_date}\n\n${selectedEmail.body}`;
            onAttachToChat(content);
            setSelectedEmail(null);
          }}
          onDelete={() => { deleteEmail(selectedEmail.id); setSelectedEmail(null); }}
        />
      ) : (
        <div
          data-testid="email-list"
          className="flex-1 overflow-y-auto"
        >
          {isLoading ? (
            <div className="p-6 text-center" style={{ color: "#A1A1AA", fontSize: "12px", fontFamily: "'JetBrains Mono', monospace" }}>
              Loading...
            </div>
          ) : emails.length === 0 ? (
            <div className="p-6 text-center">
              <FileText size={24} style={{ color: "rgba(255,255,255,0.15)", margin: "0 auto 8px" }} />
              <p style={{ color: "#A1A1AA", fontSize: "12px", fontFamily: "'JetBrains Mono', monospace" }}>
                No email references yet.
              </p>
              <p style={{ color: "rgba(161,161,170,0.4)", fontSize: "11px", marginTop: "4px" }}>
                Add emails to reference in cases.
              </p>
            </div>
          ) : (
            emails.map(email => (
              <EmailCard
                key={email.id}
                email={email}
                onClick={() => setSelectedEmail(email)}
              />
            ))
          )}
        </div>
      )}
    </aside>
  );
}

function EmailCard({ email, onClick }) {
  return (
    <div
      data-testid={`email-card-${email.id}`}
      className="p-4 cursor-pointer transition-colors"
      style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}
      onClick={onClick}
      onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.03)"}
      onMouseLeave={e => e.currentTarget.style.background = "transparent"}
    >
      <div className="flex items-start gap-2">
        <Mail size={11} style={{ color: "rgba(168,85,247,0.5)", marginTop: "3px", flexShrink: 0 }} />
        <div className="flex-1 min-w-0">
          <p
            className="truncate text-sm"
            style={{ color: "#F8F8F8", fontFamily: "'IBM Plex Sans', sans-serif" }}
          >
            {email.subject || "(No Subject)"}
          </p>
          <p
            className="truncate"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "10px",
              color: "rgba(161,161,170,0.6)",
              marginTop: "2px",
            }}
          >
            {email.sender}
          </p>
          <p
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "10px",
              color: "rgba(161,161,170,0.4)",
              marginTop: "1px",
            }}
          >
            {email.email_date ? new Date(email.email_date).toLocaleDateString("en-CA") : "No date"}
          </p>
        </div>
        <ChevronRight size={12} style={{ color: "rgba(255,255,255,0.2)", flexShrink: 0 }} />
      </div>
    </div>
  );
}

function EmailDetail({ email, onBack, onAttach, onDelete }) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Detail Header */}
      <div
        className="px-4 py-3 flex items-center gap-2"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        <button
          onClick={onBack}
          className="p-1 rounded"
          style={{ background: "none", border: "none", color: "#A1A1AA", cursor: "pointer" }}
        >
          <ChevronRight size={14} style={{ transform: "rotate(180deg)" }} />
        </button>
        <span
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "11px",
            color: "#A1A1AA",
            flex: 1,
            truncate: true,
          }}
          className="truncate"
        >
          {email.subject}
        </span>
      </div>

      {/* Meta */}
      <div className="px-4 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
        <MetaRow label="From" value={email.sender} />
        <MetaRow label="To" value={email.recipients} />
        <MetaRow label="Date" value={email.email_date ? new Date(email.email_date).toLocaleDateString("en-CA") : "N/A"} />
        {email.case_id && <MetaRow label="Case" value={email.case_id} />}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        <pre
          style={{
            fontFamily: "'IBM Plex Sans', sans-serif",
            fontSize: "12px",
            color: "#A1A1AA",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            lineHeight: "1.6",
          }}
        >
          {email.body || "(No body)"}
        </pre>
      </div>

      {/* Actions */}
      <div
        className="p-3 flex gap-2"
        style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
      >
        <button
          data-testid="attach-email-to-chat"
          onClick={onAttach}
          className="flex-1 flex items-center justify-center gap-2 py-2 rounded text-xs"
          style={{
            background: "rgba(0,255,212,0.1)",
            border: "1px solid rgba(0,255,212,0.3)",
            color: "#00FFD4",
            cursor: "pointer",
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          <Send size={11} />
          Attach to Chat
        </button>
        <button
          data-testid="delete-email-btn"
          onClick={onDelete}
          className="p-2 rounded"
          style={{
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.2)",
            color: "rgba(239,68,68,0.7)",
            cursor: "pointer",
          }}
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
}

function MetaRow({ label, value }) {
  return (
    <div className="flex gap-2 mb-1">
      <span
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "10px",
          color: "#A855F7",
          width: "36px",
          flexShrink: 0,
        }}
      >
        {label}:
      </span>
      <span
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "10px",
          color: "#A1A1AA",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function AddEmailForm({ apiUrl, onSuccess, onCancel }) {
  const [form, setForm] = useState({ subject: "", sender: "", recipients: "", body: "", email_date: "", case_id: "" });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await fetch(`${apiUrl}/api/emails`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject: form.subject,
          sender: form.sender,
          recipients: form.recipients,
          body: form.body,
          email_date: form.email_date || null,
          case_id: form.case_id || null,
        }),
      });
      onSuccess();
    } catch (e) {
      console.error("Failed to add email", e);
    } finally {
      setSaving(false);
    }
  };

  const fieldStyle = {
    background: "#08080C",
    border: "1px solid rgba(255,255,255,0.1)",
    color: "#F8F8F8",
    outline: "none",
    fontFamily: "'IBM Plex Sans', sans-serif",
    fontSize: "12px",
    padding: "6px 10px",
    borderRadius: "4px",
    width: "100%",
  };

  return (
    <form
      data-testid="add-email-form"
      onSubmit={handleSubmit}
      className="p-3"
      style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", background: "rgba(168,85,247,0.03)" }}
    >
      <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "10px", color: "#A855F7", marginBottom: "8px", textTransform: "uppercase" }}>
        Add Email Reference
      </p>
      <div className="space-y-2">
        <input placeholder="Subject *" required value={form.subject} onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} style={fieldStyle} data-testid="email-subject-input" />
        <input placeholder="From (sender) *" required value={form.sender} onChange={e => setForm(f => ({ ...f, sender: e.target.value }))} style={fieldStyle} data-testid="email-sender-input" />
        <input placeholder="To (recipients)" value={form.recipients} onChange={e => setForm(f => ({ ...f, recipients: e.target.value }))} style={fieldStyle} data-testid="email-recipients-input" />
        <input placeholder="Date (YYYY-MM-DD)" value={form.email_date} onChange={e => setForm(f => ({ ...f, email_date: e.target.value }))} style={fieldStyle} data-testid="email-date-input" />
        <input placeholder="Case ID (optional)" value={form.case_id} onChange={e => setForm(f => ({ ...f, case_id: e.target.value }))} style={fieldStyle} data-testid="email-caseid-input" />
        <textarea
          placeholder="Email body *"
          required
          rows={4}
          value={form.body}
          onChange={e => setForm(f => ({ ...f, body: e.target.value }))}
          style={{ ...fieldStyle, resize: "vertical" }}
          data-testid="email-body-input"
        />
      </div>
      <div className="flex gap-2 mt-2">
        <button
          type="submit"
          disabled={saving}
          className="flex-1 py-1.5 rounded text-xs"
          style={{
            background: "rgba(168,85,247,0.15)",
            color: "#A855F7",
            border: "1px solid rgba(168,85,247,0.3)",
            cursor: saving ? "wait" : "pointer",
            fontFamily: "'JetBrains Mono', monospace",
          }}
          data-testid="save-email-button"
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 py-1.5 rounded text-xs"
          style={{
            background: "transparent",
            color: "#A1A1AA",
            border: "1px solid rgba(255,255,255,0.1)",
            cursor: "pointer",
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
