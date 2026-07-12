"use client";

import { FormEvent, useState } from "react";

import { resolveChatUser } from "../lib/api";

type UsernameGateProps = {
  onResolved: (username: string) => void;
  submitLabel?: string;
};

export default function UsernameGate({
  onResolved,
  submitLabel = "Continue to dashboard",
}: UsernameGateProps) {
  const [usernameInput, setUsernameInput] = useState("");
  const [initializing, setInitializing] = useState(false);
  const [error, setError] = useState("");

  async function handleUsernameSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextUsername = usernameInput.trim().toLowerCase();
    setError("");
    setInitializing(true);
    try {
      const user = await resolveChatUser(nextUsername);
      localStorage.setItem("productai-username", user.username);
      onResolved(user.username);
    } catch (e: unknown) {
      setInitializing(false);
      setError(e instanceof Error ? e.message : "Failed to set username");
    }
  }

  return (
    <div className="chatWorkspace userSetupWorkspace">
      <section className="userSetupPanel">
        <div className="userSetupIntro">
          <div className="userSetupBrand">
            <span>AI</span>
            <strong>ProductAI</strong>
          </div>
          <p className="userSetupEyebrow">Before you start</p>
          <h1>Set a demo username for your AI workspace</h1>
          <p>
            No login hassle for the demo. Pick one unique username and ProductAI will keep
            your conversations separate when you return.
          </p>
          <p className="userSetupNote">
            Admins can still review demo activity for moderation, support, and cleanup.
          </p>
          <div className="userSetupBenefits" aria-label="Workspace benefits">
            <span>Saved history</span>
            <span>User-scoped chats</span>
            <span>No account required</span>
          </div>
        </div>

        <form onSubmit={handleUsernameSubmit} className="userSetupForm">
          <div className="userSetupFormHeader">
            <span>01</span>
            <div>
              <strong>Create workspace identity</strong>
              <small>This is only for separating demo chat history.</small>
            </div>
          </div>
          <label>
            Username
            <input
              value={usernameInput}
              onChange={(event) => setUsernameInput(event.target.value)}
              placeholder="e.g. badhon"
              pattern="[a-zA-Z0-9_-]{3,40}"
              minLength={3}
              maxLength={40}
              required
            />
          </label>
          <small>Use 3-40 letters, numbers, underscores, or hyphens.</small>
          <button type="submit" disabled={initializing}>
            {initializing ? "Preparing workspace..." : submitLabel}
          </button>
        </form>
        {error ? <div className="errorBanner">{error}</div> : null}
      </section>
    </div>
  );
}
