import type { Metadata } from "next";
import { PaymentPage } from "@/components/payment/PaymentPage";

interface Props {
  params: Promise<{ token: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { token } = await params;
  return {
    title: `ParkSmart — Complete Payment`,
    description: `Complete your parking reservation payment — token: ${token.slice(0, 8)}…`,
  };
}

export default async function PaymentRoute({ params }: Props) {
  const { token } = await params;
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0f1e] via-[#0d1526] to-[#0a1520]">
      <PaymentPage token={token} />
    </div>
  );
}
