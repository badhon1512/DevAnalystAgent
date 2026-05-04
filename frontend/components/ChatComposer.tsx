"use client";

import { useEffect, useRef, useState } from "react";

export default function ChatComposer({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
}) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  function send() {
    const t = text.trim();
    if (!t) return;
    onSend(t);
    setText("");
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter to send, Shift+Enter new line
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  return (
    <div className="composer">
      <textarea
        ref={textareaRef}
        className="composerInput"
        placeholder='Ask ProductAI: "Show top-selling products last 7 days"'
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        rows={1}
        disabled={disabled}
      />
      <button
        className="composerBtn"
        onClick={send}
        disabled={disabled || !text.trim()}
      >
        Send
      </button>
    </div>
  );
}
