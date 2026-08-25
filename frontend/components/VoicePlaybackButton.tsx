"use client";

import { useEffect, useRef, useState } from "react";

import { synthesizeVoice } from "../lib/api";

type PlaybackState = "idle" | "loading" | "playing" | "error";

function SpeakerIcon({ playing }: { playing: boolean }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M11 5 6 9H3v6h3l5 4V5Z" />
      {playing ? (
        <path d="M15.5 8.5a5 5 0 0 1 0 7" />
      ) : (
        <path d="M16 9.5a3.5 3.5 0 0 1 0 5" />
      )}
      <path d="M18.5 6a8.5 8.5 0 0 1 0 12" />
    </svg>
  );
}

export default function VoicePlaybackButton({ text }: { text: string }) {
  const [state, setState] = useState<PlaybackState>("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    };
  }, []);

  async function togglePlayback() {
    if (state === "loading") return;

    if (state === "playing") {
      audioRef.current?.pause();
      setState("idle");
      return;
    }

    setState("loading");
    try {
      if (!audioRef.current) {
        const audioBlob = await synthesizeVoice(text);
        objectUrlRef.current = URL.createObjectURL(audioBlob);
        const audio = new Audio(objectUrlRef.current);
        audio.onended = () => setState("idle");
        audio.onerror = () => setState("error");
        audioRef.current = audio;
      }

      if (audioRef.current.ended) audioRef.current.currentTime = 0;
      await audioRef.current.play();
      setState("playing");
    } catch {
      setState("error");
    }
  }

  const label =
    state === "loading"
      ? "Generating speech"
      : state === "playing"
        ? "Pause spoken response"
        : state === "error"
          ? "Retry spoken response"
          : "Listen to response";

  return (
    <button
      className={`voicePlaybackButton voicePlaybackButton-${state}`}
      type="button"
      onClick={togglePlayback}
      disabled={state === "loading"}
      aria-label={label}
      title={label}
    >
      {state === "loading" ? (
        <span className="voicePlaybackLoading" aria-hidden="true" />
      ) : (
        <SpeakerIcon playing={state === "playing"} />
      )}
      <span>{state === "playing" ? "Pause" : state === "loading" ? "Preparing" : "Listen"}</span>
    </button>
  );
}
