"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
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

export default function MerchantShell({
  title,
  children,
  showChatWidget = true,
}: {
  title: string;
  children: React.ReactNode;
  showChatWidget?: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [navOpen, setNavOpen] = useState(false);
  const username = useSyncExternalStore(
    subscribeStoredUsername,
    readStoredUsernameSnapshot,
    () => "",
  );

  // Close the drawer on navigation, including browser back and forward, so a
  // route change never leaves it open over the new page. Adjusting during
  // render rather than in an effect avoids the extra commit that setState in an
  // effect body causes.
  const [renderedPath, setRenderedPath] = useState(pathname);
  if (pathname !== renderedPath) {
    setRenderedPath(pathname);
    setNavOpen(false);
  }

  // Escape closes the drawer, matching the backdrop click.
  useEffect(() => {
    if (!navOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setNavOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [navOpen]);

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

  const isChatLayout = !showChatWidget;

  return (
    <div className={`merchantShell${isChatLayout ? " merchantShellChat" : ""}`}>
      {navOpen && (
        <button
          className="merchantNavBackdrop"
          aria-label="Close navigation"
          onClick={() => setNavOpen(false)}
          type="button"
        />
      )}
      <MerchantSidebar open={navOpen} onNavigate={() => setNavOpen(false)} />
      <main className={`merchantMain${isChatLayout ? " merchantMainChat" : ""}`}>
        <div className="appShellHeader">
          <div className="merchantTitleGroup">
            <button
              className="merchantNavToggle"
              type="button"
              onClick={() => setNavOpen((open) => !open)}
              aria-expanded={navOpen}
              aria-label={navOpen ? "Close navigation" : "Open navigation"}
            >
              <span aria-hidden="true" />
            </button>
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
            <Link href="/chat">AI Analysis</Link>
          </div>
        </div>
        <div className={`merchantContentPanel${isChatLayout ? " merchantContentPanelChat" : ""}`}>
          {children}
        </div>
        {showChatWidget && <ChatWidget pageContext={`Merchant Portal - ${title}`} />}
      </main>
    </div>
  );
}
