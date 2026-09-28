"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { GenerationProgress, ResultDialog, StudioPanel, StudioPhoto, StudioShell } from "@/components/ai-studio";
import { API_BASE_URL, generate as generateFeature, getStyles, type GenerateResponse, type Style } from "@/lib/api";

const MAX_BYTES = 8 * 1024 * 1024;
const COLORS: Record<string, string> = {
  classic_red: "#aa2138", nude_pink: "#d696a3", glossy_black: "#24232a",
  french_tip: "#e9d7d6", pink_ombre: "#c6719e",
};

export default function NailsPage() {
  const [styles, setStyles] = useState<Style[]>([]);
  const [loading, setLoading] = useState(true);
  const [stylesError, setStylesError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [styleId, setStyleId] = useState("");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [resultOpen, setResultOpen] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const previewRef = useRef("");
  const submitting = useRef(false);

  useEffect(() => {
    let active = true;
    getStyles("nails").then((items) => { if (active) setStyles(items); })
      .catch(() => { if (active) setStylesError(`The local API is unavailable at ${API_BASE_URL}.`); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; if (previewRef.current) URL.revokeObjectURL(previewRef.current); };
  }, []);

  function resetResult() { setResultOpen(false); setResult(null); }

  function choose(event: ChangeEvent<HTMLInputElement>) {
    const next = event.target.files?.[0];
    event.target.value = "";
    if (!next) return;
    if (!["image/jpeg", "image/png"].includes(next.type) || next.size < 1 || next.size > MAX_BYTES) {
      setError("Choose a JPG or PNG image up to 8 MB."); return;
    }
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = URL.createObjectURL(next);
    setPreview(previewRef.current);
    setFile(next);
    setError("");
    resetResult();
  }

  function clear() {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = "";
    setPreview("");
    setFile(null);
    resetResult();
    setError("");
  }

  async function generate() {
    if (!file || !styleId || submitting.current) return;
    submitting.current = true;
    setWorking(true);
    setError("");
    resetResult();
    try {
      const generated = await generateFeature("nails", file, styleId);
      setResult(generated);
      setResultOpen(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Preview failed. Please try again.");
    } finally {
      submitting.current = false;
      setWorking(false);
    }
  }

  const selectedStyle = styles.find((style) => style.id === styleId);
  return <StudioShell feature="nails" eyebrow="THE AI BEAUTY STUDIO" title="A polished look." emphasis="Made for your hands."
    description="Try a nail finish on your own photo. For the clearest preview, show the back of your hand with three to five visible nails."
    badge="Virtual nail try-on">
    <div className="studio-workspace">
      <StudioPanel id="nails-photo-heading" number="01" title="Your hand photo" detail="Show the back of your hand in clear light.">
        <input ref={input} className="sr-only" type="file" accept="image/jpeg,image/png" onChange={choose} disabled={working} aria-label="Choose a hand photo" />
        {preview ? <StudioPhoto src={preview} alt="Uploaded hand photo" /> : <button type="button" className="studio-upload" onClick={() => input.current?.click()}><span className="studio-upload-icon" aria-hidden="true">↑</span><strong>Choose your hand photo</strong><small>JPG or PNG image, up to 8 MB. Your original stays available for comparison.</small></button>}
        {file && <div className="studio-file-row"><div><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(2)} MB</small></div><div><button type="button" className="studio-text-button" disabled={working} onClick={() => input.current?.click()}>Replace</button><button type="button" className="studio-text-button" disabled={working} onClick={clear}>Remove</button></div></div>}
      </StudioPanel>
      <StudioPanel id="nails-styles-heading" number="02" title="Choose a nail look" detail="Pick the finish you want to see.">
        {loading && <p role="status" className="studio-loading-styles">Loading styles…</p>}
        {stylesError && <p role="alert" className="studio-alert">{stylesError}</p>}
        <div className="studio-nail-grid">{styles.map((style) => <button key={style.id} type="button" className="studio-nail-card" disabled={working} aria-pressed={styleId === style.id} onClick={() => { setStyleId(style.id); resetResult(); setError(""); }}><span className="studio-nail-swatch" style={{ background: COLORS[style.id] || "#9a7ab8" }} aria-hidden="true" /><span><strong>{style.name}</strong><small>{style.description}</small></span></button>)}</div>
        <p className="studio-tip"><strong>Photo tip</strong><br />Keep nails visible and in focus. Model-backed looks are applied across each nail and may take several minutes.</p>
      </StudioPanel>
    </div>
    <section aria-label="Generate nails preview" className="studio-action-bar"><div><small>03 / CREATE YOUR LOOK</small><h2>Ready for your nail preview?</h2><p>{selectedStyle ? `Selected: ${selectedStyle.name}` : "Upload a hand photo and select a style."}</p></div><button type="button" className="studio-primary-button" disabled={!file || !styleId || working} onClick={() => void generate()}>{working ? "Applying nail style…" : "Try this style"} <span aria-hidden="true">✦</span></button></section>
    {error && <p role="alert" className="studio-alert">{error}</p>}
    {result && !resultOpen && <button type="button" className="studio-view-result" onClick={() => setResultOpen(true)}>View your result again</button>}
    {working && <GenerationProgress feature="nails" />}
    <ResultDialog result={result} open={resultOpen} original={preview} originalAlt="Original hand photo" generatedAlt={result?.status === "placeholder" ? "Original photo preview" : `Hand with ${result?.style.name} nails`}
      title={result?.status === "placeholder" ? "A preview of the workflow" : "Your nail look is ready"} note={result?.status === "placeholder" ? "Nail styling is unavailable in this development preview." : "AI previews may differ from real polish. Check the comparison before downloading."}
      onClose={() => setResultOpen(false)} onRegenerate={() => void generate()} />
  </StudioShell>;
}
