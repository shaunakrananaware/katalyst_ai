import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import Markdown from "react-markdown";

function App() {
  const [session, setSession] = useState(() => {
    let id = sessionStorage.getItem("katalyst-session");
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem("katalyst-session", id);
    }
    return id;
  });
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);
  const end = useRef(null);
  const sending = useRef(false);
  useEffect(() => {
    fetch("/api/health")
      .then((r) => {
        if (!r.ok) throw Error();
        return r.json();
      })
      .then(setHealth)
      .catch(() => setHealth({ offline: true }));
  }, []);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);
  async function send() {
    const text = input;
    if (!text.trim() || sending.current) return;
    sending.current = true;
    setBusy(true);
    setError("");
    setInput("");
    setMessages((items) => [...items, { role: "user", text }]);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: session, message: text }),
      });
      const result = await response.json();
      if (!response.ok)
        throw Error(
          typeof result.detail === "string"
            ? result.detail
            : "The request could not be processed.",
        );
      setMessages((items) => [
        ...items,
        { role: "assistant", text: result.reply, tools: result.tool_calls },
      ]);
    } catch (err) {
      setError(
        err.message === "Failed to fetch"
          ? "Cannot reach the backend. Start FastAPI and try again."
          : err.message,
      );
      setInput(text);
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  function reset() {
    const id = crypto.randomUUID();
    sessionStorage.setItem("katalyst-session", id);
    setSession(id);
    setMessages([]);
    setError("");
    setInput("");
  }
  return (
    <div className="app">
      <aside>
        <div className="brand">
          <span className="logo">k</span> katalyst
          <span className="badge">LAB</span>
        </div>
        <div className="sidebar-label">WORKSPACE</div>
        <div className="selected">◌ &nbsp; Sales memory</div>
        <div className="sidebar-label sources-title">MOCK SOURCES</div>
        {[
          "Salesforce · deals & people",
          "Gmail · conversations",
          "Calendar · meetings",
          "Notion · meeting notes",
        ].map((s) => (
          <div className="source" key={s}>
            <span /> {s}
          </div>
        ))}
        <div className="sidebar-footer">
          8 deals · 6 prospect organizations
          <br />
          Fictional data · September 2026
        </div>
      </aside>
      <main>
        <header>
          <div>
            <strong>Sales memory</strong>
            <small>Your CRM, in context.</small>
          </div>
          <button className="secondary" onClick={reset} disabled={busy}>
            New conversation
          </button>
        </header>
        <section className="conversation" aria-label="Conversation">
          {!messages.length && (
            <div className="welcome">
              <div className="eyebrow">YOUR SALES WORKSPACE</div>
              <h1>
                Every deal has a story.
                <br />
                <span>Get the full picture.</span>
              </h1>
              <p>
                Ask about your pipeline, revisit a meeting, or learn what helped
                a deal close.
              </p>
            </div>
          )}
          <div role="log" aria-live="polite">
            {messages.map((m, i) => (
              <article className={`message ${m.role}`} key={i}>
                <div className="author">
                  {m.role === "user" ? "YOU" : "KATALYST"}
                </div>
                <div className="bubble">
                  {m.role === "assistant" ? (
                    <Markdown>{m.text}</Markdown>
                  ) : (
                    m.text
                  )}
                </div>
                {m.tools?.length > 0 && (
                  <details>
                    <summary>
                      {m.tools.length} tool calls · view evidence
                    </summary>
                    {m.tools.map((tool, j) => (
                      <div className="trace" key={j}>
                        <strong>{tool.name}</strong>
                        <pre>
                          {JSON.stringify(
                            { arguments: tool.args, result: tool.result },
                            null,
                            2,
                          )}
                        </pre>
                      </div>
                    ))}
                  </details>
                )}
              </article>
            ))}
          </div>
          {busy && (
            <div className="loading" role="status">
              Checking your sales memory<span>…</span>
            </div>
          )}
          <div ref={end} />
        </section>
        <footer>
          {health?.offline && (
            <div className="notice">
              Backend is offline. Start the API on port 8000.
            </div>
          )}
          {health && !health.offline && !health.gemini_configured && (
            <div className="notice">
              Add GOOGLE_API_KEY to the backend .env and restart it to enable
              chat.
            </div>
          )}
          {error && (
            <div role="alert" className="error">
              {error}
            </div>
          )}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              send();
            }}
          >
            <label className="sr-only" htmlFor="message">
              Message
            </label>
            <input
              id="message"
              value={input}
              maxLength={8000}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a deal, meeting, or your pipeline…"
              disabled={busy}
            />
            <button type="submit" disabled={busy || !input.trim()}>
              {busy ? "Working…" : "Send ↑"}
            </button>
          </form>
          <div className="footnote">
            Read-only mock CRM · Answers grounded in retrieved records
          </div>
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
