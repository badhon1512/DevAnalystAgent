"use client";

import { useEffect, useRef, useState } from "react";

function MicIcon({ active }: { active: boolean }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M6 11a6 6 0 0 0 12 0" />
      <path d="M12 17v4" />
      <path d="M8.5 21h7" />
      {active ? <circle cx="18.5" cy="5.5" r="2.2" fill="currentColor" stroke="none" /> : null}
    </svg>
  );
}

export default function ChatComposer({
  onSend,
  disabled,
  onTranscribeAudio,
  onVoiceError,
  suggestions = [],
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
  onTranscribeAudio?: (audio: Blob) => Promise<string>;
  onVoiceError?: (message: string) => void;
  suggestions?: Array<{ label: string; query: string }>;
}) {
  const [text, setText] = useState("");
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  function send() {
    const t = text.trim();
    if (!t) return;
    onSend(t);
    setText("");
  }

  function fillSuggestion(query: string) {
    setText(query);
    requestAnimationFrame(() => textareaRef.current?.focus());
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter to send, Shift+Enter new line
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function stopRecording() {
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
    }
  }

  async function startRecording() {
    if (!onTranscribeAudio || disabled || transcribing) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onVoiceError?.("Voice recording is not supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      streamRef.current = stream;
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        recorderRef.current = null;
        setRecording(false);

        const audio = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        chunksRef.current = [];
        if (!audio.size) return;

        setTranscribing(true);
        try {
          const transcript = await onTranscribeAudio(audio);
          if (transcript) {
            setText((current) => (current ? `${current} ${transcript}` : transcript));
            textareaRef.current?.focus();
          }
        } catch (error) {
          onVoiceError?.(error instanceof Error ? error.message : "Voice transcription failed.");
        } finally {
          setTranscribing(false);
        }
      };

      recorder.start();
      setRecording(true);
    } catch (error) {
      onVoiceError?.(
        error instanceof Error ? error.message : "Microphone permission was not granted."
      );
    }
  }

  function toggleRecording() {
    if (recording) {
      stopRecording();
    } else {
      void startRecording();
    }
  }

  useEffect(() => {
    textareaRef.current?.focus();

    return () => {
      if (recorderRef.current && recorderRef.current.state !== "inactive") {
        recorderRef.current.stop();
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  return (
    <div className="composerShell">
      {suggestions.length > 0 ? (
        <div className="composerSuggestions" aria-label="Demo queries">
          <span>Try:</span>
          {suggestions.map((suggestion) => (
            <button
              key={suggestion.label}
              type="button"
              onClick={() => fillSuggestion(suggestion.query)}
              disabled={disabled || transcribing}
            >
              {suggestion.label}
            </button>
          ))}
        </div>
      ) : null}
      <div className="composer">
        {onTranscribeAudio && (
          <button
            className={`composerBtn composerIconBtn${recording ? " composerIconBtnRecording" : ""}`}
            onClick={toggleRecording}
            disabled={transcribing || (!recording && disabled)}
            title={recording ? "Stop recording" : "Record voice question"}
            aria-label={recording ? "Stop recording" : "Record voice question"}
            type="button"
          >
            {transcribing ? <span className="composerIconLabel">...</span> : <MicIcon active={recording} />}
          </button>
        )}
        <textarea
          ref={textareaRef}
          className="composerInput"
          placeholder='Ask ProductAI: "Show top-selling products last 7 days"'
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          disabled={disabled || transcribing}
        />
        <button
          className="composerBtn"
          onClick={send}
          disabled={disabled || transcribing || recording || !text.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}
