"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

import type { FeatureId, GenerateResponse } from "@/lib/api";

const features: { id: FeatureId | "consultation"; label: string; href: string }[] = [
  { id: "consultation", label: "Consultation", href: "/consultation" },
  { id: "hairstyle", label: "Hairstyle", href: "/" },
  { id: "makeup", label: "Makeup", href: "/makeup" },
  { id: "nails", label: "Nails", href: "/nails" },
];

export function StudioShell({ feature, eyebrow, title, emphasis, description, badge, children }: {
  feature: FeatureId | "consultation"; eyebrow: string; title: string; emphasis: string;
  description: string; badge?: string; children: ReactNode;
}) {
  return <div className="studio-page">
    <header className="studio-header">
      <div className="studio-header-inner">
        <Link href="/" className="studio-brand" aria-label="Andrea's AI studio home">
          <span className="studio-brand-mark" aria-hidden="true">✦</span>
          <span><strong>ANDREA&apos;S</strong><small>AESTHETIC &amp; WELLNESS CLINIC</small></span>
        </Link>
        <nav aria-label="Features" className="studio-nav">
          {features.map((item) => item.id === feature
            ? <span key={item.id} aria-current="page" className="studio-nav-active">{item.label}</span>
            : <Link key={item.id} href={item.href}>{item.label}</Link>)}
        </nav>
        <span className="studio-header-note">Your look, reimagined</span>
      </div>
    </header>
    <main className="studio-main">
      <div className="studio-hero">
        <div className="studio-hero-copy">
          <p className="studio-eyebrow"><span className="studio-eyebrow-line" /> {eyebrow}</p>
          <h1>{title}<br /><em>{emphasis}</em></h1>
          <p className="studio-hero-description">{description}</p>
          {badge && <span className="studio-mode-badge"><span className="studio-mode-dot" />{badge}</span>}
        </div>
        <div className="studio-hero-art" aria-hidden="true"><span className="studio-orbit studio-orbit-one" /><span className="studio-orbit studio-orbit-two" /><span className="studio-hero-spark">✦</span><span className="studio-hero-monogram">B</span></div>
      </div>
      {children}
      <footer className="studio-footer"><span>ANDREA&apos;S <span aria-hidden="true">✦</span> AI STUDIO</span><span>Explore a look that feels like you.</span></footer>
    </main>
  </div>;
}

export function StudioPanel({ number, title, detail, children, id }: {
  number: string; title: string; detail?: string; children: ReactNode; id: string;
}) {
  return <section className="studio-panel" aria-labelledby={id}>
    <div className="studio-panel-heading"><span className="studio-step">{number}</span><div><h2 id={id}>{title}</h2>{detail && <p>{detail}</p>}</div></div>
    {children}
  </section>;
}

export function StudioPhoto({ src, alt }: { src: string; alt: string }) {
  return <div className="studio-photo"><Image src={src} alt={alt} fill unoptimized sizes="(max-width: 900px) 100vw, 50vw" className="object-contain" /></div>;
}

export function GenerationProgress({ feature, mock = false }: { feature: FeatureId; mock?: boolean }) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const label = feature === "nails" ? "Applying your nail look" : feature === "makeup" ? "Creating your makeup look" : "Creating your hairstyle";
  return <div className="studio-processing-backdrop">
    <div className="studio-processing" role="status" aria-live="polite" aria-label={`${label}. Please keep this page open.`}>
      <div className="studio-processing-emblem" aria-hidden="true"><span className="studio-processing-ring" /><span>✦</span></div>
      <p className="studio-eyebrow">A LITTLE BEAUTY IN PROGRESS</p>
      <h2>{mock ? "Preparing your preview" : label}<span className="studio-ellipsis" aria-hidden="true">…</span></h2>
      <p>{mock ? "Your preview is on its way." : feature === "nails" ? "We’re working across your nails. This can take a few minutes." : "Your image is being processed. This can take a little while."}</p>
      <div className="studio-progress-track" aria-hidden="true"><span /></div>
      <small aria-hidden="true">Time elapsed {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")} · Keep this page open</small>
    </div>
  </div>;
}

export function ResultDialog({ result, open, original, originalAlt, generatedAlt, title, note, onClose, onRegenerate }: {
  result: GenerateResponse | null; original: string; originalAlt: string; generatedAlt: string;
  open: boolean; title: string; note?: string; onClose: () => void; onRegenerate: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (result && open && !dialog.open) dialog.showModal();
    else if ((!result || !open) && dialog.open) dialog.close();
  }, [result, open]);
  if (!result) return null;
  const extension = result.image.content_type === "image/jpeg" ? "jpg" : "png";
  const filename = `andreas-${result.style.id}.${extension}`;
  return <dialog ref={ref} className="studio-result-dialog" aria-labelledby="studio-result-title" onClose={onClose} onClick={(event) => { if (event.target === ref.current) ref.current?.close(); }}>
    <div className="studio-result-content">
      <div className="studio-result-header"><div><p className="studio-eyebrow">YOUR NEW LOOK IS READY</p><h2 id="studio-result-title">{title}</h2><p>{result.style.name} · {result.status === "completed" ? "AI preview" : "Development preview"}</p></div><button type="button" className="studio-icon-button" aria-label="Close result" onClick={() => ref.current?.close()}>×</button></div>
      <div className="studio-result-grid"><div className="studio-result-image"><span>01 / ORIGINAL IMAGE</span><StudioPhoto src={original} alt={originalAlt} /></div><div className="studio-result-image studio-result-generated"><span>02 / GENERATED IMAGE</span><StudioPhoto src={result.image.data_url} alt={generatedAlt} /></div></div>
      {note && <p className="studio-result-note">{note}</p>}
      <div className="studio-result-actions"><button type="button" className="studio-secondary-button" onClick={() => ref.current?.close()}>Close</button><button type="button" className="studio-secondary-button" onClick={() => { ref.current?.close(); onRegenerate(); }}>Regenerate</button><a className="studio-primary-button" href={result.image.data_url} download={filename}>Download image <span aria-hidden="true">↗</span></a></div>
    </div>
  </dialog>;
}
