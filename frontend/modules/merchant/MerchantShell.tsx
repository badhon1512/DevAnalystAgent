"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSyncExternalStore } from "react";
import ChatWidget from "../../components/ChatWidget";
import UsernameGate from "../../components/UsernameGate";
import MerchantSidebar from "./MerchantSidebar";

function readStoredUsernameSnapshot() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("productai-username") || "";
}

function subscribeStoredUsername(onStoreChange: () => void) {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("storage", onStoreChange);
  window.addEventListener("productai-username-change", onStoreChange);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener("productai-username-change", onStoreChange);
  };
}

function notifyStoredUsernameChange() {
  window.dispatchEvent(new Event("productai-username-change"));
}

export default function MerchantShell({ title, children }: { title: string; children: React.ReactNode }) {
  const router = useRouter();
  const username = useSyncExternalStore(
    subscribeStoredUsername,
    readStoredUsernameSnapshot,
    () => "",
  );

  function handleUsernameResolved() {
    notifyStoredUsernameChange();
  }

  if (!username) {
    return <UsernameGate onResolved={handleUsernameResolved} />;
  }

  function handleSwitchUser() {
    localStorage.removeItem("productai-username");
    notifyStoredUsernameChange();
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
