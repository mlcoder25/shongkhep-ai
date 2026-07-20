"use client";
import Link from "next/link";
import {
  ArrowRight,
  Zap,
  Globe,
  Shield,
  BarChart3,
  CheckCircle,
} from "lucide-react";

const FEATURES = [
  {
    icon: Globe,
    title: "বাংলা + English",
    desc: "Native support for both Bangla and English articles with automatic language detection.",
  },
  {
    icon: Zap,
    title: "Instant Results",
    desc: "Powered by Qwen3:8b on Apple Silicon — delivering high quality summaries in seconds.",
  },
  {
    icon: Shield,
    title: "API Key Access",
    desc: "Secure API key + JWT authentication. Integrate into any app with a single header.",
  },
  {
    icon: BarChart3,
    title: "Usage Analytics",
    desc: "Track every request. Monitor your monthly quota and stay in control.",
  },
];

const PLANS = [
  {
    name: "Free",
    price: "৳0",
    limit: "50",
    features: ["50 summaries/month", "API access", "Bangla + English"],
  },
  {
    name: "Student",
    price: "৳49",
    limit: "300",
    features: ["300 summaries/month", "API access", "PDF support"],
    highlight: false,
  },
  {
    name: "Basic",
    price: "৳149",
    limit: "1,000",
    features: ["1,000 summaries/month", "Priority access", "Analytics"],
    highlight: true,
  },
  {
    name: "Pro",
    price: "৳399",
    limit: "5,000",
    features: ["5,000 summaries/month", "All features", "Webhooks"],
  },
];
export default function LandingPage() {
  return (
    <div className="noise min-h-screen relative overflow-hidden">
      {/* Background mesh */}
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background: `
            radial-gradient(ellipse 80% 60% at 10% 10%, hsla(145,60%,12%,0.8) 0%, transparent 60%),
            radial-gradient(ellipse 60% 50% at 90% 80%, hsla(155,50%,10%,0.6) 0%, transparent 55%),
            #131419
          `,
        }}
      />

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-6 md:px-12 py-5 border-b border-ink-800/50">
        <div className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white font-display font-bold text-lg">
            স
          </span>
          <span className="font-display text-xl font-bold text-ink-50 tracking-tight">
            Shongkhep <span className="text-brand-400">AI</span>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login" className="btn-ghost text-sm">
            Sign in
          </Link>
          <Link href="/signup" className="btn-primary text-sm">
            Get started free
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 pt-24 pb-20 text-center">
        <h1 className="font-display text-5xl md:text-7xl font-bold text-ink-50 leading-[1.08] tracking-tight mb-6 animate-slide-up">
          Summarize any article
          <br />
          <span className="text-brand-400">বাংলায় বা ইংরেজিতে</span>
        </h1>

        <p className="text-ink-400 text-lg md:text-xl max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-in">
          Shongkhep AI distills long Bangla and English news articles into crisp
          summaries. Built for developers, journalists, and researchers in
          Bangladesh.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up">
          <Link
            href="/signup"
            className="btn-primary flex items-center gap-2 text-base px-7 py-3"
          >
            Start summarizing free <ArrowRight size={18} />
          </Link>
        </div>

        <p className="text-ink-600 text-sm mt-6">
          No credit card required · 100 free summaries/month
        </p>
      </section>


      {/* Features */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 pb-24">
        <h2 className="font-display text-3xl font-bold text-ink-100 text-center mb-12">
          Everything you need
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="card-hover p-5">
              <div className="w-10 h-10 rounded-xl bg-brand-950 border border-brand-900 flex items-center justify-center text-brand-400 mb-4">
                <Icon size={20} />
              </div>
              <h3 className="font-semibold text-ink-100 mb-2">{title}</h3>
              <p className="text-sm text-ink-500 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="relative z-10 max-w-4xl mx-auto px-6 pb-28">
        <h2 className="font-display text-3xl font-bold text-ink-100 text-center mb-3">
          Simple pricing
        </h2>
        <p className="text-ink-500 text-center mb-12">
          Priced for the Bangladesh market. Pay in BDT.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`card p-6 flex flex-col gap-5 ${plan.highlight ? "border-brand-600 shadow-lg shadow-brand-950/40 relative" : ""}`}
            >
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-brand-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                  Most popular
                </div>
              )}
              <div>
                <p className="text-sm text-ink-500 font-medium mb-1">
                  {plan.name}
                </p>
                <p className="font-display text-4xl font-bold text-ink-50">
                  {plan.price}
                  <span className="text-base text-ink-500 font-body font-normal">
                    /mo
                  </span>
                </p>
                <p className="text-xs text-ink-600 mt-1">
                  {plan.limit} summaries/month
                </p>
              </div>
              <ul className="space-y-2 flex-1">
                {plan.features.map((f) => (
                  <li
                    key={f}
                    className="flex items-center gap-2 text-sm text-ink-400"
                  >
                    <CheckCircle
                      size={14}
                      className="text-brand-500 shrink-0"
                    />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/signup"
                className={
                  plan.highlight
                    ? "btn-primary text-center text-sm"
                    : "btn-ghost text-center text-sm border border-ink-700"
                }
              >
                Get started
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-ink-800/50 py-8 text-center text-ink-600 text-sm">
        <p>© 2025 Shongkhep AI — Made for Bangladesh 🇧🇩</p>
      </footer>
    </div>
  );
}
