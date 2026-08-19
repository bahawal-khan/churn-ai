import { AmbientBackground } from "@/components/marketing/AmbientBackground";
import { Footer } from "@/components/layout/Footer";
import { MarketingNavbar } from "@/components/layout/MarketingNavbar";

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative isolate flex min-h-screen flex-col overflow-x-hidden bg-marketing-bg">
      <AmbientBackground />
      <MarketingNavbar />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}
