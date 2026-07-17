import Chat from "../../components/Chat";
import MerchantShell from "../../modules/merchant/MerchantShell";

export default function Page() {
  return (
    <MerchantShell title="AI Analysis" showChatWidget={false}>
      <Chat embedded />
    </MerchantShell>
  );
}
