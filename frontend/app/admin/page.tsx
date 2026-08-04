"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  adminDeleteConversation,
  adminGetConversation,
  adminListConversations,
  adminLogin,
  adminSetConversationActive,
} from "../../lib/api";
import type { AdminConversationDetail, AdminConversationSummary } from "../../lib/types";
import TrafficPanel from "../../components/TrafficPanel";

const ADMIN_TOKEN_KEY = "productai-admin-token";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function AdminPage() {
  const [secret, setSecret] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [conversations, setConversations] = useState<AdminConversationSummary[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [selected, setSelected] = useState<AdminConversationDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const savedToken = localStorage.getItem(ADMIN_TOKEN_KEY);
    if (savedToken) setToken(savedToken);
  }, []);

  useEffect(() => {
    if (!token) return;
    void refresh(token);
  }, [token]);

  useEffect(() => {
    if (!token || !selectedId) {
      setSelected(null);
      return;
    }
    void loadSelected(token, selectedId);
  }, [token, selectedId]);

  const activeCount = useMemo(
    () => conversations.filter((conversation) => conversation.is_active).length,
    [conversations],
  );

  async function refresh(activeToken = token) {
    if (!activeToken) return;
    setLoading(true);
    setError("");
    try {
      const data = await adminListConversations(activeToken);
      setConversations(data);
      if (!selectedId && data[0]) setSelectedId(data[0].conversation_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load admin conversations");
    } finally {
      setLoading(false);
    }
  }

  async function loadSelected(activeToken: string, conversationId: string) {
    try {
      setSelected(await adminGetConversation(activeToken, conversationId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load conversation");
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const nextToken = await adminLogin(secret, password);
      localStorage.setItem(ADMIN_TOKEN_KEY, nextToken);
      setToken(nextToken);
      setSecret("");
      setPassword("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    setToken("");
    setSelectedId("");
    setSelected(null);
    setConversations([]);
  }

  async function toggleConversation(conversation: AdminConversationSummary) {
    setError("");
    try {
      const updated = await adminSetConversationActive(
        token,
        conversation.conversation_id,
        !conversation.is_active,
      );
      setConversations((items) =>
        items.map((item) => (item.conversation_id === updated.conversation_id ? updated : item)),
      );
      if (selectedId === updated.conversation_id) await loadSelected(token, updated.conversation_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update conversation");
    }
  }

  async function deleteAdminConversation(conversation: AdminConversationSummary) {
    if (!window.confirm(`Delete "${conversation.title}" permanently?`)) return;
    setError("");
    try {
      await adminDeleteConversation(token, conversation.conversation_id);
      setConversations((items) =>
        items.filter((item) => item.conversation_id !== conversation.conversation_id),
      );
      if (selectedId === conversation.conversation_id) {
        setSelectedId("");
        setSelected(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete conversation");
    }
  }

  if (!token) {
    return (
      <main className="adminPage">
        <section className="adminLoginPanel">
          <div className="adminLoginCopy">
            <div className="adminLoginBrand">
              <span>AI</span>
              <strong>ProductAI</strong>
            </div>
            <p className="adminEyebrow">Protected admin access</p>
            <h1>Conversation governance for your agentic commerce demo</h1>
            <p>
              Review user-scoped chat activity, pause unsafe or noisy threads, and remove
              conversations that should not remain visible in the demo environment.
            </p>
            <div className="adminLoginHighlights" aria-label="Admin capabilities">
              <span>All users</span>
              <span>Deactivate chats</span>
              <span>Delete records</span>
            </div>
          </div>

          <form className="adminLoginForm" onSubmit={handleLogin}>
            <div>
              <p className="adminEyebrow">Sign in</p>
              <h2>Admin credentials</h2>
              <p className="adminLoginHint">Use the secret and password configured on the backend.</p>
            </div>
            <label>
              Admin secret
              <input
                type="password"
                value={secret}
                onChange={(event) => setSecret(event.target.value)}
                autoComplete="off"
                placeholder="Enter admin secret"
                required
              />
            </label>
            <label>
              Admin password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                placeholder="Enter admin password"
                required
              />
            </label>
            {error ? <div className="adminError">{error}</div> : null}
            <button type="submit" disabled={loading}>
              {loading ? "Verifying access..." : "Enter admin console"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="adminPage adminWorkspace">
      <header className="adminHeader">
        <div>
          <p className="adminEyebrow">ProductAI Admin</p>
          <h1>Conversation control</h1>
          <p>Review all user chats, deactivate conversations, or delete records permanently.</p>
        </div>
        <div className="adminHeaderActions">
          <button type="button" onClick={() => refresh()} disabled={loading}>
            Refresh
          </button>
          <button type="button" className="adminGhostButton" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>

      {error ? <div className="adminError">{error}</div> : null}

      <section className="adminStats">
        <div><span>{conversations.length}</span><p>Total</p></div>
        <div><span>{activeCount}</span><p>Active</p></div>
        <div><span>{conversations.length - activeCount}</span><p>Inactive</p></div>
      </section>

      <TrafficPanel token={token} />

      <section className="adminGrid">
        <div className="adminConversationList">
          <div className="adminPanelTitle">Detected conversations</div>
          {conversations.map((conversation) => (
            <article
              key={conversation.conversation_id}
              className={`adminConversationItem ${
                selectedId === conversation.conversation_id ? "isSelected" : ""
              }`}
            >
              <button type="button" onClick={() => setSelectedId(conversation.conversation_id)}>
                <span>{conversation.title}</span>
                <small>
                  @{conversation.username || "unknown"} · {conversation.message_count} messages ·{" "}
                  {formatDate(conversation.updated_at)}
                </small>
                <em>{conversation.last_message_preview || "No messages yet"}</em>
              </button>
              <div className="adminConversationActions">
                <span className={conversation.is_active ? "adminStatusActive" : "adminStatusInactive"}>
                  {conversation.is_active ? "Active" : "Inactive"}
                </span>
                <button type="button" onClick={() => toggleConversation(conversation)}>
                  {conversation.is_active ? "Deactivate" : "Activate"}
                </button>
                <button
                  type="button"
                  className="adminDangerButton"
                  onClick={() => deleteAdminConversation(conversation)}
                >
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>

        <div className="adminConversationDetail">
          <div className="adminPanelTitle">Conversation detail</div>
          {selected ? (
            <>
              <div className="adminDetailHeader">
                <div>
                  <h2>{selected.title}</h2>
                  <p>@{selected.username || "unknown"} · Updated {formatDate(selected.updated_at)}</p>
                </div>
                <span className={selected.is_active ? "adminStatusActive" : "adminStatusInactive"}>
                  {selected.is_active ? "Active" : "Inactive"}
                </span>
              </div>
              <div className="adminMessages">
                {selected.messages.map((message) => (
                  <article key={message.message_id} className={`adminMessage ${message.role}`}>
                    <div>
                      <strong>{message.role}</strong>
                      <span>{formatDate(message.created_at)}</span>
                    </div>
                    <p>{message.content}</p>
                  </article>
                ))}
              </div>
            </>
          ) : (
            <div className="adminEmpty">Select a conversation to inspect messages.</div>
          )}
        </div>
      </section>
    </main>
  );
}
