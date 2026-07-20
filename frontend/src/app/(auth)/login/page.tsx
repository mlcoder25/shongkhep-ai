"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Eye, EyeOff, ArrowRight, Loader2 } from "lucide-react";
import toast from "react-hot-toast";

export default function LoginPage() {
  const router   = useRouter();
  const login    = useAuthStore((s) => s.login);
  const loading  = useAuthStore((s) => s.loading);

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [showPw,   setShowPw]   = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(email, password);
      toast.success("Welcome back!");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Login failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{
      background: "radial-gradient(ellipse 70% 60% at 30% 20%, hsla(145,55%,10%,0.7) 0%, transparent 55%), #131419",
    }}>
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 mb-6">
            <span className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center text-white font-display font-bold text-xl">স</span>
            <span className="font-display text-2xl font-bold text-ink-50">Shongkhep <span className="text-brand-400">AI</span></span>
          </Link>
          <h1 className="font-display text-3xl font-bold text-ink-50 mb-2">Welcome back</h1>
          <p className="text-ink-500 text-sm">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} className="card p-8 space-y-5 shadow-2xl shadow-black/50">
          {/* Email */}
          <div>
            <label className="label">Email address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="input"
            />
          </div>

          {/* Password */}
          <div>
            <label className="label">Password</label>
            <div className="relative">
              <input
                type={showPw ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="input pr-11"
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-500 hover:text-ink-300 transition-colors"
              >
                {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 py-3">
            {loading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="text-center text-sm text-ink-500 mt-6">
          Don't have an account?{" "}
          <Link href="/signup" className="text-brand-400 hover:text-brand-300 transition-colors font-medium">
            Sign up free
          </Link>
        </p>
      </div>
    </div>
  );
}
