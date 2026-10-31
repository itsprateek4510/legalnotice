import { useEffect, useRef, useState } from "react";
import { getChatHistory, sendChatMessage } from "../api/api";
import { getErrorDetail } from "../api/api";

/**
 * Per-document AI assistant chat panel.
 */
export default function ChatPanel({ docId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(null);
      try {
        const history = await getChatHistory(docId);
        if (!cancelled) {
          setMessages(history);
          setLoaded(true);
        }
      } catch (err) {
        if (!cancelled) {
          setError(getErrorDetail(err));
          setLoaded(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [docId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: "user", content: text, local: true };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const { reply } = await sendChatMessage(docId, text);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: reply, local: true },
      ]);
    } catch (err) {
      setError(getErrorDetail(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-bot-icon" aria-hidden="true">🤖</span>
        <div>
          <h3>Ask your document assistant</h3>
          <p className="muted">
            Ask questions like: “What should I do first?” or “When is the hearing?”
          </p>
        </div>
      </div>

      <div className="chat-window" ref={scrollRef}>
        {!loaded ? (
          <p className="chat-placeholder">Loading conversation…</p>
        ) : messages.length === 0 ? (
          <p className="chat-placeholder">
            No questions yet. Start a conversation about this notice below.
          </p>
        ) : (
          messages.map((m, i) => (
            <div
              key={m.id || i}
              className={`chat-bubble chat-${m.role === "user" ? "user" : "assistant"}`}
            >
              <div className="chat-bubble-author">
                {m.role === "user" ? "You" : "Assistant"}
              </div>
              <div className="chat-bubble-text">{m.content}</div>
            </div>
          ))
        )}
        {loading && (
          <div className="chat-bubble chat-assistant chat-thinking">
            <span className="typing-dots" aria-label="Assistant is typing">
              <span>●</span><span>●</span><span>●</span>
            </span>
          </div>
        )}
        {error && <div className="alert alert-danger">{error}</div>}
      </div>

      <form className="chat-input-row" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about this notice…"
          disabled={loading}
          aria-label="Chat message"
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}