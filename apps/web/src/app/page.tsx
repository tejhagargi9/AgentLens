import { Hero } from "@/components/landing/hero";
import {
  CallToAction,
  Capabilities,
  HowItWorks,
  SiteFooter,
  UseCases,
} from "@/components/landing/sections";
import { SiteHeader } from "@/components/landing/site-header";

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main className="flex-1">
        <Hero />
        <HowItWorks />
        <Capabilities />
        <UseCases />
        <CallToAction />
      </main>
      <SiteFooter />
    </>
  );
}
