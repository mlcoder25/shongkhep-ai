"use client";
import { useState, useRef, useCallback } from "react";
import { summarizeApi, urlSummarizeApi, pdfSummarizeApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { authApi } from "@/lib/api";
import {
  Zap, Loader2, Copy, Check, ChevronDown, Clock,
  ToggleLeft, ToggleRight, Link2, FileText, ExternalLink,
  FileUp, X, File as FileIcon
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

type Lang      = "auto" | "en" | "bn";
type InputMode = "text" | "url" | "pdf";
type RunMode   = "sync" | "async";

interface SummarizeResult {
  summary: string;
  original_length: number;
  summary_length: number;
  language_detected: string;
  tokens_used: number;
  requests_remaining: number;
  model: string;
  cached?: boolean;
  title?: string;
  url?: string;
  source_domain?: string;
  page_count?: number;
  pages_read?: number;
}

const LANG_OPTIONS: { value: Lang; label: string }[] = [
  { value: "auto", label: "Auto-detect" },
  { value: "en",   label: "English" },
  { value: "bn",   label: "বাংলা" },
];

const TABS = [
  { mode: "text" as InputMode, icon: FileText, label: "Paste text"   },
  { mode: "url"  as InputMode, icon: Link2,    label: "Article URL"  },
  { mode: "pdf"  as InputMode, icon: FileUp,   label: "Upload PDF"   },
];

const EXAMPLE_URLS = [
  "https://www.prothomalo.com/",
  "https://www.thedailystar.net/",
  "https://www.kalerkantho.com/",
  "https://bdnews24.com/",
];

const POLL_INTERVAL_MS  = 1500;
const POLL_MAX_ATTEMPTS = 40;
const MAX_PDF_MB        = 20;

export default function SummarizePage() {
  const { user, setUser } = useAuthStore();

  const [inputMode, setInputMode] = useState<InputMode>("text");
  const [runMode,   setRunMode]   = useState<RunMode>("sync");
  const [text,      setText]      = useState("");
  const [url,       setUrl]       = useState("");
  const [pdfFile,   setPdfFile]   = useState<File | null>(null);
  const [language,  setLanguage]  = useState<Lang>("auto");
  const [loading,   setLoading]   = useState(false);
  const [result,    setResult]    = useState<SummarizeResult | null>(null);
  const [copied,    setCopied]    = useState(false);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [dragOver,  setDragOver]  = useState(false);

  const pollRef    = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Validation ──────────────────────────────────────────────────────────────
  const charCount = text.length;
  const tooShort  = inputMode === "text" && charCount > 0 && charCount < 50;
  const tooLong   = inputMode === "text" && charCount > 10000;
  const urlValid  = inputMode === "url" && url.startsWith("http");
  const pdfValid  = inputMode === "pdf" && pdfFile !== null;
  const canSubmit = !loading && (
    (inputMode === "text" && charCount >= 50 && !tooLong) ||
    (inputMode === "url"  && urlValid) ||
    (inputMode === "pdf"  && pdfValid)
  );

  const stopPolling = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  const refreshUser = () => authApi.me().then(setUser).catch(() => {});

  // ── PDF drag & drop ────────────────────────────────────────────────────────
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) validateAndSetPdf(file);
  }, []);

  const validateAndSetPdf = (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
      toast.error("Only PDF files are accepted");
      return;
    }
    if (file.size > MAX_PDF_MB * 1024 * 1024) {
      toast.error(`File too large — max ${MAX_PDF_MB} MB`);
      return;
    }
    setPdfFile(file);
    setResult(null);
  };

  // ── Submit ─────────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!canSubmit) return;
    setLoading(true); setResult(null); setJobStatus(null); stopPolling();

    try {
      // PDF mode
      if (inputMode === "pdf" && pdfFile) {
        const res = await pdfSummarizeApi.summarize(pdfFile, language);
        setResult(res);
        refreshUser();
        toast.success(`PDF summarized! (${res.pages_read} pages read)`);
        setLoading(false);
        return;
      }

      // URL mode
      if (inputMode === "url") {
        const res = await urlSummarizeApi.summarize({ url, language });
        setResult(res);
        refreshUser();
        toast.success(res.cached ? "⚡ From cache" : `Scraped from ${res.source_domain}!`);
        setLoading(false);
        return;
      }

      // Text sync
      if (runMode === "sync") {
        const res = await summarizeApi.summarize({ text, language });
        setResult(res);
        refreshUser();
        toast.success(res.cached ? "⚡ From cache" : "Summary ready!");
        setLoading(false);
        return;
      }

      // Text async (Celery)
      const { job_id } = await summarizeApi.submitAsync({ text, language });
      setJobStatus("PENDING");
      toast("Job queued…", { icon: "⏳" });
      let attempts = 0;
      pollRef.current = setInterval(async () => {
        if (++attempts > POLL_MAX_ATTEMPTS) {
          stopPolling(); setLoading(false);
          toast.error("Job timed out");
          return;
        }
        try {
          const poll = await summarizeApi.pollJob(job_id);
          setJobStatus(poll.status);
          if (poll.status === "SUCCESS" && poll.result) {
            stopPolling(); setResult(poll.result); setLoading(false);
            refreshUser(); toast.success("Async summary ready!");
          } else if (poll.status === "FAILURE") {
            stopPolling(); setLoading(false); toast.error(poll.error || "Job failed");
          }
        } catch { stopPolling(); setLoading(false); toast.error("Polling failed"); }
      }, POLL_INTERVAL_MS);

    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed");
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.summary);
    setCopied(true); setTimeout(() => setCopied(false), 2000);
    toast.success("Copied!");
  };

  const switchTab = (mode: InputMode) => {
    setInputMode(mode); setResult(null); setPdfFile(null);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink-50 mb-1">Summarize</h1>
          <p className="text-ink-500 text-sm">
            Text, URL, or PDF — we handle all three.
            {user && <span className="ml-2 text-brand-400">{user.remaining_requests} requests left</span>}
          </p>
        </div>
        {inputMode === "text" && (
          <button
            onClick={() => setRunMode(m => m === "sync" ? "async" : "sync")}
            className={clsx(
              "flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-medium transition-all",
              runMode === "async"
                ? "bg-brand-950 border-brand-700 text-brand-300"
                : "bg-ink-800 border-ink-700 text-ink-400 hover:text-ink-200"
            )}
          >
            {runMode === "async" ? <ToggleRight size={15} className="text-brand-400" /> : <ToggleLeft size={15} />}
            {runMode === "async" ? "Async (Celery)" : "Sync (direct)"}
          </button>
        )}
      </div>

      {/* Mode tabs */}
      <div className="flex gap-1 p-1 bg-ink-900 rounded-xl border border-ink-800 mb-6 w-fit">
        {TABS.map(({ mode, icon: Icon, label }) => (
          <button key={mode} onClick={() => switchTab(mode)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              inputMode === mode ? "bg-brand-600 text-white shadow" : "text-ink-400 hover:text-ink-200"
            )}
          >
            <Icon size={15} /> {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Left — Input ─────────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4">

          {/* Language */}
          <div>
            <label className="label">Language</label>
            <div className="relative">
              <select value={language} onChange={e => setLanguage(e.target.value as Lang)}
                      className="input appearance-none pr-8 cursor-pointer">
                {LANG_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-500 pointer-events-none" />
            </div>
          </div>

          {/* ── TEXT ── */}
          {inputMode === "text" && (
            <div className="flex-1 flex flex-col">
              <label className="label">Article text</label>
              <textarea value={text} onChange={e => setText(e.target.value)}
                placeholder="Paste your article here… বাংলা বা ইংরেজিতে"
                className={clsx(
                  "input flex-1 resize-none min-h-[260px] leading-relaxed text-sm",
                  tooLong && "border-red-500", tooShort && "border-saffron-400/60"
                )}
              />
              <div className="flex justify-between text-xs mt-1.5">
                <span className={clsx(tooShort ? "text-saffron-400" : tooLong ? "text-red-400" : "text-ink-600")}>
                  {tooShort && "Need at least 50 characters"}
                  {tooLong  && "Exceeds 10,000 character limit"}
                </span>
                <span className="text-ink-600">{charCount.toLocaleString()} / 10,000</span>
              </div>
            </div>
          )}

          {/* ── URL ── */}
          {inputMode === "url" && (
            <div className="flex flex-col gap-3">
              <div>
                <label className="label">Article URL</label>
                <div className="relative">
                  <input type="url" value={url} onChange={e => setUrl(e.target.value)}
                    placeholder="https://www.prothomalo.com/..."
                    className="input pl-10" />
                  <Link2 size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-500" />
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_URLS.map(u => (
                  <button key={u} onClick={() => setUrl(u)}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-ink-800 border border-ink-700 text-xs text-ink-400 hover:text-brand-300 hover:border-brand-800 transition-all">
                    <ExternalLink size={10} />
                    {new URL(u).hostname.replace("www.", "")}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── PDF ── */}
          {inputMode === "pdf" && (
            <div className="flex flex-col gap-3">
              {/* Drop zone */}
              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={clsx(
                  "border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all",
                  dragOver
                    ? "border-brand-500 bg-brand-950/30"
                    : pdfFile
                    ? "border-brand-700 bg-brand-950/20"
                    : "border-ink-700 hover:border-ink-600 hover:bg-ink-800/30"
                )}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) validateAndSetPdf(f); }}
                />

                {pdfFile ? (
                  <div className="flex items-center justify-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-brand-600/20 border border-brand-600/40 flex items-center justify-center text-brand-400 shrink-0">
                      <FileIcon size={20} />
                    </div>
                    <div className="text-left">
                      <p className="text-sm font-medium text-ink-200 truncate max-w-[180px]">{pdfFile.name}</p>
                      <p className="text-xs text-ink-500">{(pdfFile.size / 1024).toFixed(0)} KB</p>
                    </div>
                    <button
                      onClick={e => { e.stopPropagation(); setPdfFile(null); setResult(null); }}
                      className="ml-auto p-1.5 rounded-lg hover:bg-ink-700 text-ink-500 hover:text-red-400 transition-colors"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div>
                    <FileUp size={28} className="text-ink-600 mx-auto mb-3" />
                    <p className="text-sm font-medium text-ink-400">Drop PDF here or click to browse</p>
                    <p className="text-xs text-ink-600 mt-1">Max {MAX_PDF_MB} MB · Up to 50 pages · Bangla & English</p>
                  </div>
                )}
              </div>

              {/* Info strip */}
              <div className="p-3.5 rounded-xl bg-ink-900 border border-ink-800 text-xs text-ink-500 space-y-1">
                <p className="font-medium text-ink-400">How PDF mode works</p>
                <p>1. Upload any text-based PDF (news, reports, papers)</p>
                <p>2. We extract text from up to 50 pages</p>
                <p>3. mT5 generates a concise summary</p>
                <p className="text-ink-600">⚠ Scanned/image PDFs without text layer are not supported</p>
              </div>
            </div>
          )}

          {/* Submit button */}
          <button onClick={handleSubmit} disabled={!canSubmit}
                  className="btn-primary flex items-center justify-center gap-2 py-3">
            {loading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                {inputMode === "pdf"  ? "Extracting & summarizing…" :
                 inputMode === "url"  ? "Fetching & summarizing…" :
                 runMode === "async"  ? `Polling… (${jobStatus || "PENDING"})` : "Summarizing…"}
              </>
            ) : (
              <>
                <Zap size={18} />
                {inputMode === "pdf"  ? "Summarize PDF" :
                 inputMode === "url"  ? "Fetch & summarize URL" :
                 runMode === "async"  ? "Queue async job" : "Generate summary"}
              </>
            )}
          </button>

          {inputMode === "text" && runMode === "async" && (
            <p className="text-xs text-ink-600 flex items-center gap-1.5">
              <Clock size={11} /> Offloads to Celery worker. Polls every {POLL_INTERVAL_MS / 1000}s.
            </p>
          )}
        </div>

        {/* ── Right — Output ───────────────────────────────────────────────── */}
        <div className="flex flex-col">
          <div className="card flex-1 min-h-[420px] flex flex-col">
            {/* Output header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-ink-800 flex-wrap gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-ink-400">Summary</span>
                {result?.cached && (
                  <span className="badge bg-brand-950 text-brand-400 border border-brand-800 text-xs">⚡ cached</span>
                )}
                {result?.source_domain && (
                  <a href={result.url} target="_blank" rel="noopener noreferrer"
                     className="flex items-center gap-1 text-xs text-ink-500 hover:text-brand-300 transition-colors">
                    <ExternalLink size={11} /> {result.source_domain}
                  </a>
                )}
                {result?.page_count && (
                  <span className="text-xs text-ink-500">📄 {result.pages_read}/{result.page_count} pages</span>
                )}
              </div>
              {result && (
                <button onClick={handleCopy} className="btn-ghost p-1.5 flex items-center gap-1.5 text-xs shrink-0">
                  {copied ? <Check size={13} className="text-brand-400" /> : <Copy size={13} />}
                  {copied ? "Copied!" : "Copy"}
                </button>
              )}
            </div>

            <div className="flex-1 p-5">
              {/* Loading */}
              {loading && (
                <div className="h-full flex flex-col items-center justify-center gap-4">
                  <Loader2 size={28} className="text-brand-500 animate-spin" />
                  <div className="text-center space-y-1">
                    {inputMode === "pdf" && (
                      <>
                        <p className="text-sm text-ink-400">Extracting PDF text…</p>
                        <p className="text-xs text-ink-600">Parsing pages → running mT5</p>
                      </>
                    )}
                    {inputMode === "url" && (
                      <>
                        <p className="text-sm text-ink-400">Fetching article…</p>
                        <p className="text-xs text-ink-600">Scraping content → running mT5</p>
                      </>
                    )}
                    {inputMode === "text" && runMode === "sync" && (
                      <div className="space-y-2.5 w-full animate-pulse mt-2">
                        <div className="skeleton h-4 w-full rounded" />
                        <div className="skeleton h-4 w-5/6 rounded" />
                        <div className="skeleton h-4 w-4/5 rounded" />
                        <div className="skeleton h-4 w-full rounded" />
                      </div>
                    )}
                    {inputMode === "text" && runMode === "async" && jobStatus && (
                      <p className="text-xs font-mono text-ink-500">{jobStatus}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Empty state */}
              {!loading && !result && (
                <div className="h-full flex flex-col items-center justify-center text-center gap-3">
                  <div className="w-14 h-14 rounded-full bg-ink-800 flex items-center justify-center">
                    {inputMode === "pdf"  ? <FileUp size={24} className="text-ink-600" /> :
                     inputMode === "url"  ? <Link2  size={24} className="text-ink-600" /> :
                                           <Zap    size={24} className="text-ink-600" />}
                  </div>
                  <p className="text-ink-600 text-sm">
                    {inputMode === "pdf" ? "Upload a PDF to summarize" :
                     inputMode === "url" ? "Paste a news article URL" :
                                          "Your summary will appear here"}
                  </p>
                </div>
              )}

              {/* Result */}
              {!loading && result && (
                <div className="animate-fade-in">
                  {result.title && (
                    <>
                      <p className="text-xs font-semibold text-ink-500 uppercase tracking-wider mb-1.5">Title</p>
                      <p className="text-sm font-medium text-ink-200 mb-4 pb-4 border-b border-ink-800">{result.title}</p>
                    </>
                  )}
                  <p className="text-xs font-semibold text-ink-500 uppercase tracking-wider mb-2">Summary</p>
                  <p className={clsx("text-ink-200 text-sm leading-relaxed mb-5",
                                    result.language_detected === "bn" && "bangla")}>
                    {result.summary}
                  </p>
                  <div className="flex flex-wrap gap-2 pt-4 border-t border-ink-800">
                    <span className="badge badge-free">{result.language_detected === "bn" ? "বাংলা" : "English"}</span>
                    <span className="badge badge-free">{result.tokens_used} tokens</span>
                    <span className="badge badge-free">
                      {Math.round((1 - result.summary_length / result.original_length) * 100)}% shorter
                    </span>
                    <span className="badge badge-basic">{result.requests_remaining} left</span>
                    {result.page_count && (
                      <span className="badge badge-pro">📄 {result.pages_read} pages</span>
                    )}
                    {result.source_domain && (
                      <span className="badge badge-pro">🌐 {result.source_domain}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
