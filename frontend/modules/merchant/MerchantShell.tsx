"use client";

import Link from "next/link";
import ChatWidget from "../../components/ChatWidget";
import MerchantSidebar from "./MerchantSidebar";

export default function MerchantShell({ title, children }: { title: string; children: React.ReactNode }) {
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
