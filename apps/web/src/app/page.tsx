import { Hero } from "@/components/landing/hero";
import {
  CallToAction,
  Capabilities,
  HowItWorks,
  SiteFooter,
  UseCases,
} from "@/components/landing/sections";
import { SiteHeader } from "@/components/landing/site-header";
import { hasSessionCookie } from "@/lib/session";

export default async function Home() {
  // Visitors see sign-up/log-in; the console link only appears once signed in.
  const signedIn = await hasSessionCookie();

  return (
    <>
      <SiteHeader signedIn={signedIn} />
      <main className="flex-1">
        <Hero signedIn={signedIn} />
        <HowItWorks />
        <Capabilities />
        <UseCases />
        <CallToAction signedIn={signedIn} />
      </main>
      <SiteFooter />
    </>
  );
}
