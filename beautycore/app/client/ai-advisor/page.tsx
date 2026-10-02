'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  Sparkles,
  Loader2,
  AlertCircle,
  X,
  Hand,
  Scissors,
  Wand2,
  Info,
  CalendarPlus,
  History,
} from 'lucide-react';
import { Card, EmptyState, formatDate } from '@/components/ui';
import type { StyleAnalysis, StyleRecommendation } from '@/lib/ai/types';
import type { StyleType } from '@/db/schema';

const MAX_MB = 8;

interface HistoryRow {
  id: string;
  promptText: string;
  generatedImageUrl: string | null;
  styleType: StyleType;
  analysisResult: StyleAnalysis | null;
  createdAt: string;
}

/** Per-recommendation preview state, keyed by index. */
interface PreviewState {
  loading: boolean;
  imageUrl?: string;
  message?: string;
}

export default function AIAdvisorPage() {
  const [image, setImage] = useState<string | null>(null);
  const [fileName, setFileName] = useState('');
  const [analysis, setAnalysis] = useState<StyleAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [previews, setPreviews] = useState<Record<number, PreviewState>>({});
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [dragging, setDragging] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);

  const loadHistory = useCallback(() => {
    fetch('/api/generations')
      .then((r) => r.json())
      .then((d) => setHistory(d.generations ?? []))
      .catch(() => setHistory([]));
  }, []);

  useEffect(loadHistory, [loadHistory]);

  // ─── Upload ───────────────────────────────────────────────────────────────

  const handleFile = useCallback((file: File) => {
    setError('');

    if (!file.type.startsWith('image/')) {
      setError('Please choose an image file.');
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`That image is ${(file.size / 1024 / 1024).toFixed(1)} MB. Please use one under ${MAX_MB} MB.`);
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setImage(reader.result as string);
      setFileName(file.name);
      setAnalysis(null);
      setPreviews({});
    };
    reader.onerror = () => setError('Could not read that file. Please try another.');
    reader.readAsDataURL(file);
  }, []);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const reset = () => {
    setImage(null);
    setFileName('');
    setAnalysis(null);
    setPreviews({});
    setError('');
    if (inputRef.current) inputRef.current.value = '';
  };

  // ─── Analyse ──────────────────────────────────────────────────────────────

  const analyze = async () => {
    if (!image) return;
    setAnalyzing(true);
    setError('');
    setAnalysis(null);
    setPreviews({});

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imageBase64: image }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? 'Analysis failed.');
      setAnalysis(data.analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not analyse that photo.');
    } finally {
      setAnalyzing(false);
    }
  };

  // ─── Preview ──────────────────────────────────────────────────────────────

  const generatePreview = async (rec: StyleRecommendation, index: number) => {
    if (!image || !analysis) return;

    setPreviews((p) => ({ ...p, [index]: { loading: true } }));

    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sourceImage: image,
          prompt: rec.generationPrompt,
          styleType: analysis.category,
          analysis,
        }),
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.error ?? 'Preview failed.');

      setPreviews((p) => ({
        ...p,
        [index]: data.success
          ? { loading: false, imageUrl: data.imageUrl }
          : { loading: false, message: data.message },
      }));

      loadHistory();
    } catch (err) {
      setPreviews((p) => ({
        ...p,
        [index]: {
          loading: false,
          message: err instanceof Error ? err.message : 'Preview failed.',
        },
      }));
    }
  };

  const CategoryIcon = analysis?.category === 'nails' ? Hand : Scissors;

  return (
    <>
      <div className="mb-8">
        <h1 className="flex items-center gap-2.5 font-serif text-3xl text-white">
          <Sparkles size={24} className="text-gold" />
          AI Style Advisor
        </h1>
        <p className="mt-1.5 text-[13px] text-muted">
          Upload a photo of your hair or nails. The AI reads what&apos;s actually
          there and suggests three styles with the reasoning behind each.
        </p>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 flex items-start gap-2 rounded-sm border border-error/30 bg-error/10 p-4 text-[13px] text-error"
        >
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </motion.div>
      )}

      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        {/* ─── Upload ─────────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4">
          <Card>
            <h2 className="mb-4 text-[10px] font-semibold uppercase tracking-[2px] text-gold">
              Your Photo
            </h2>

            {!image ? (
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                onClick={() => inputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-sm border-2 border-dashed px-6 py-14 text-center transition-colors ${
                  dragging
                    ? 'border-gold bg-gold/5'
                    : 'border-purple-light/25 hover:border-purple-light/50'
                }`}
              >
                <Upload size={26} className="mb-3 text-muted" />
                <p className="mb-1 text-[13px] font-medium text-white">
                  Drop a photo here
                </p>
                <p className="text-[11px] text-muted">
                  or click to browse · JPEG, PNG, WebP · max {MAX_MB} MB
                </p>
              </div>
            ) : (
              <div>
                <div className="relative mb-3 overflow-hidden rounded-sm border border-purple-light/20">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={image} alt="Your upload" className="w-full object-cover" />
                  <button
                    onClick={reset}
                    aria-label="Remove photo"
                    className="absolute right-2 top-2 rounded-full bg-black/70 p-1.5 text-white transition-colors hover:bg-error"
                  >
                    <X size={14} />
                  </button>
                </div>
                <p className="mb-4 truncate text-[11px] text-muted">{fileName}</p>

                <button
                  onClick={analyze}
                  disabled={analyzing}
                  className="flex w-full items-center justify-center gap-2 bg-gold px-5 py-3 text-[11px] font-semibold uppercase tracking-[2px] text-card transition-colors hover:bg-gold-hover disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {analyzing ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Analysing…
                    </>
                  ) : (
                    <>
                      <Wand2 size={14} />
                      {analysis ? 'Analyse Again' : 'Analyse Photo'}
                    </>
                  )}
                </button>
              </div>
            )}

            <input
              ref={inputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
              }}
              className="hidden"
            />
          </Card>

          {/* Detected attributes */}
          <AnimatePresence>
            {analysis && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <Card>
                  <div className="mb-4 flex items-center gap-2">
                    <CategoryIcon size={15} className="text-gold" />
                    <h2 className="text-[10px] font-semibold uppercase tracking-[2px] text-gold">
                      Detected: {analysis.category}
                    </h2>
                  </div>
                  <dl className="flex flex-col gap-3">
                    {[
                      { k: analysis.category === 'nails' ? 'Shape' : 'Cut', v: analysis.currentAttributes.shapeOrCut },
                      { k: 'Colour', v: analysis.currentAttributes.color },
                      { k: 'Condition', v: analysis.currentAttributes.condition },
                    ].map((row) => (
                      <div key={row.k} className="border-b border-white/[0.05] pb-3 last:border-0 last:pb-0">
                        <dt className="mb-1 text-[10px] uppercase tracking-wide text-muted">
                          {row.k}
                        </dt>
                        <dd className="text-[12px] leading-relaxed text-secondary">{row.v}</dd>
                      </div>
                    ))}
                  </dl>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ─── Recommendations ────────────────────────────────────────── */}
        <div>
          {analyzing && (
            <Card className="flex flex-col items-center justify-center py-24">
              <Loader2 size={28} className="mb-4 animate-spin text-gold" />
              <p className="mb-1 font-serif text-lg text-white">Reading your photo</p>
              <p className="text-[12px] text-muted">This usually takes 10–25 seconds.</p>
            </Card>
          )}

          {!analyzing && !analysis && (
            <Card className="py-24">
              <EmptyState
                icon={Sparkles}
                title="Your recommendations will appear here"
                body="Upload a photo and run the analysis to see three styles chosen for your hair or nails."
              />
            </Card>
          )}

          {!analyzing && analysis && (
            <div className="flex flex-col gap-4">
              {analysis.recommendations.map((rec, i) => {
                const preview = previews[i];
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: i * 0.1 }}
                  >
                    <Card>
                      <div className="mb-4 flex items-start justify-between gap-4">
                        <div>
                          <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[2px] text-gold">
                            Option {i + 1}
                          </span>
                          <h3 className="font-serif text-xl text-white">{rec.title}</h3>
                        </div>
                        <Link
                          href={`/booking?service=${analysis.category === 'nails' ? 'nail-studio' : 'hair-design'}`}
                          className="flex shrink-0 items-center gap-1.5 border border-purple-light/40 px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[1.5px] text-secondary transition-colors hover:border-gold/50 hover:text-gold"
                        >
                          <CalendarPlus size={12} />
                          Book
                        </Link>
                      </div>

                      <dl className="mb-4 grid gap-3 sm:grid-cols-2">
                        <div>
                          <dt className="mb-1 text-[10px] uppercase tracking-wide text-muted">
                            Palette
                          </dt>
                          <dd className="text-[12px] text-secondary">{rec.colorPalette}</dd>
                        </div>
                        <div>
                          <dt className="mb-1 text-[10px] uppercase tracking-wide text-muted">
                            Details
                          </dt>
                          <dd className="text-[12px] text-secondary">{rec.designDetails}</dd>
                        </div>
                      </dl>

                      <div className="mb-4 rounded-sm border border-purple-light/10 bg-surface/25 p-3.5">
                        <p className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted">
                          <Info size={11} />
                          Why this suits you
                        </p>
                        <p className="text-[12px] leading-relaxed text-secondary">
                          {rec.reasoning}
                        </p>
                      </div>

                      {/* Preview */}
                      {preview?.imageUrl ? (
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div>
                            <p className="mb-2 text-[10px] uppercase tracking-wide text-muted">
                              Before
                            </p>
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={image!}
                              alt="Original"
                              className="w-full rounded-sm border border-purple-light/15"
                            />
                          </div>
                          <div>
                            <p className="mb-2 text-[10px] uppercase tracking-wide text-gold">
                              Preview
                            </p>
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={preview.imageUrl}
                              alt={`Preview of ${rec.title}`}
                              className="w-full rounded-sm border border-gold/30"
                            />
                          </div>
                        </div>
                      ) : preview?.message ? (
                        <div className="flex items-start gap-2 rounded-sm border border-info/25 bg-info/10 p-3.5 text-[12px] leading-relaxed text-info">
                          <Info size={14} className="mt-0.5 shrink-0" />
                          <span>{preview.message}</span>
                        </div>
                      ) : (
                        <button
                          onClick={() => generatePreview(rec, i)}
                          disabled={preview?.loading}
                          className="flex w-full items-center justify-center gap-2 border border-purple-light/40 px-5 py-2.5 text-[10px] font-semibold uppercase tracking-[1.5px] text-secondary transition-colors hover:border-gold/50 hover:text-gold disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {preview?.loading ? (
                            <>
                              <Loader2 size={13} className="animate-spin" />
                              Generating preview…
                            </>
                          ) : (
                            <>
                              <Wand2 size={13} />
                              Generate Preview
                            </>
                          )}
                        </button>
                      )}
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ─── History ─────────────────────────────────────────────────── */}
      {history.length > 0 && (
        <div className="mt-10">
          <h2 className="mb-4 flex items-center gap-2 font-serif text-xl text-white">
            <History size={17} className="text-gold" />
            Your Past Analyses
          </h2>
          <div className="scrollbar-thin flex gap-4 overflow-x-auto pb-3">
            {history.map((h) => {
              const title = h.analysisResult?.recommendations?.[0]?.title ?? h.promptText.slice(0, 40);
              const Icon = h.styleType === 'nail' ? Hand : Scissors;
              return (
                <div
                  key={h.id}
                  className="w-56 shrink-0 rounded-sm border border-purple-light/15 bg-card p-4"
                >
                  <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-sm border border-purple-light/20 bg-purple/15">
                    <Icon size={15} className="text-purple-glow" />
                  </div>
                  <p className="mb-1 line-clamp-2 text-[12px] font-medium leading-snug text-white">
                    {title}
                  </p>
                  <p className="text-[10px] capitalize text-muted">
                    {h.styleType} · {formatDate(h.createdAt)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
