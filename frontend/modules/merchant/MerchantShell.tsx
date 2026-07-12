"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import ChatWidget from "../../components/ChatWidget";
import UsernameGate from "../../components/UsernameGate";
import MerchantSidebar from "./MerchantSidebar";

function readStoredUsername() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("productai-username") || "";
}

export default function MerchantShell({ title, children }: { title: string; children: React.ReactNode }) {
  const router = useRouter();
  const [username, setUsername] = useState<string | null>(() => readStoredUsername());

  useEffect(() => {
    if (username === null) setUsername(readStoredUsername() || "");
  }, [username]);

  if (username === null) {
    return (
      <div className="chatWorkspace userSetupWorkspace">
        <section className="userSetupPanel userSetupLoading">
          <div className="userSetupIntro">
            <div className="userSetupBrand">
              <span>AI</span>
              <strong>ProductAI</strong>
            </div>
            <p className="userSetupEyebrow">Preparing workspace</p>
            <h1>Loading your merchant dashboard</h1>
          </div>
        </section>
      </div>
    );
  }

  if (!username) {
    return <UsernameGate onResolved={setUsername} />;
  }

  function handleSwitchUser() {
    localStorage.removeItem("productai-username");
    setUsername("");
    router.push("/");
  }

  return (
    <div className="merchantShell">
      <MerchantSidebar />
      <main className="merchantMain">
        <div className="appShellHeader">
          <div className="merchantTitleGroup">
            <span>{title.slice(0, 2).toUpperCase()}</span>
            <div>
              <div className="merchantPageTitle">{title}</div>
              <div className="appShellSub">Merchant Portal</div>
            </div>
          </div>
          <div className="viewSwitch">
            <button className="merchantUserButton" type="button" onClick={handleSwitchUser}>
              @{username}
            </button>
            <Link href="/storefront">Storefront</Link>
            <Link href="/chat">AI Workspace</Link>
          </div>
        </div>
        <div className="merchantContentPanel">
          {children}
        </div>
        <ChatWidget pageContext={`Merchant Portal - ${title}`} />
      </main>
    </div>
  );
}
