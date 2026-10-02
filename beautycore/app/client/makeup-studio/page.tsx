"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { GenerationProgress, ResultDialog, StudioPanel, StudioPhoto, StudioShell } from "@/components/ai-studio";
import { API_BASE_URL, generate, getStyles, type GenerateResponse, type Style } from "@/lib/ai/studio-api";
import { takeCustomPhoto } from "@/lib/ai/studio-photo-handoff";

const MAX_FILE_BYTES = 8 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png"]);

export default function MakeupPage() {
  const [styles, setStyles] = useState<Style[]>([]);
  const [stylesLoading, setStylesLoading] = useState(true);
  const [stylesError, setStylesError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [generateError, setGenerateError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [resultOpen, setResultOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const submittingRef = useRef(false);
  const previewRef = useRef("");

  async function loadStyles() {
    setStylesLoading(true);
    setStylesError("");
    try { setStyles(await getStyles("makeup")); }
    catch { setStylesError(`The local API is unavailable at ${API_BASE_URL}. Start the backend and retry.`); }
    finally { setStylesLoading(false); }
  }

  useEffect(() => {
    let mounted = true;
    const transferred = takeCustomPhoto("makeup");
    if (transferred && ACCEPTED_TYPES.has(transferred.type) && transferred.size > 0 && transferred.size <= MAX_FILE_BYTES) {
      previewRef.current = URL.createObjectURL(transferred);
      setPreviewUrl(previewRef.current);
      setFile(transferred);
    }
    getStyles("makeup").then((loaded) => { if (mounted) setStyles(loaded); })
      .catch(() => { if (mounted) setStylesError(`The local API is unavailable at ${API_BASE_URL}. Start the backend and retry.`); })
      .finally(() => { if (mounted) setStylesLoading(false); });
    return () => { mounted = false; if (previewRef.current) URL.revokeObjectURL(previewRef.current); };
  }, []);

  function resetResult() { setResultOpen(false); setResult(null); }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0];
    event.target.value = "";
    if (!chosen) return;
    if (!ACCEPTED_TYPES.has(chosen.type)) { setUploadError("Choose a JPG or PNG portrait."); return; }
    if (chosen.size === 0 || chosen.size > MAX_FILE_BYTES) { setUploadError("Choose an image between 1 byte and 8 MB."); return; }
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = URL.createObjectURL(chosen);
    setPreviewUrl(previewRef.current);
    setFile(chosen);
    setUploadError("");
    setGenerateError("");
    resetResult();
  }

  function clearImage() {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = "";
    setFile(null);
    setPreviewUrl("");
    resetResult();
    setUploadError("");
    setGenerateError("");
  }

  async function onGenerate() {
    if (!file || !selectedId || submittingRef.current) return;
    submittingRef.current = true;
    setGenerating(true);
    setGenerateError("");
    resetResult();
    try {
      const generated = await generate("makeup", file, selectedId);
      setResult(generated);
      setResultOpen(true);
    } catch (error) {
      setGenerateError(error instanceof Error ? error.message : "Makeup generation failed. Please try again.");
    } finally {
      submittingRef.current = false;
      setGenerating(false);
    }
  }

  const selectedStyle = styles.find((style) => style.id === selectedId);
  const liveMode = styles.some((style) => style.status === "trained_preset");
  const realResult = result?.status === "completed";

  return <StudioShell feature="makeup" eyebrow="THE AI BEAUTY STUDIO" title="Explore a new look." emphasis="Keep the portrait yours."
    description={liveMode ? "Choose a makeup look and see it on your portrait. Results are AI previews and may retouch facial details or skin tone." : "Choose a makeup direction and preview the application flow. In development mode, the result mirrors your original portrait."}
    badge={liveMode ? "AI makeup preview" : "Development preview"}>
    <div className="studio-workspace">
      <StudioPanel id="makeup-portrait-heading" number="01" title="Your portrait" detail="Use a clear, well-lit photo of your face.">
        <input ref={inputRef} id="makeup-upload" className="sr-only" type="file" accept="image/jpeg,image/png" onChange={onFileChange} disabled={generating} aria-label="Upload your portrait" aria-describedby="makeup-upload-help makeup-upload-error" />
        {previewUrl ? <StudioPhoto src={previewUrl} alt="Preview of your uploaded portrait" /> : <button type="button" className="studio-upload" onClick={() => inputRef.current?.click()}><span className="studio-upload-icon" aria-hidden="true">↑</span><strong>Choose your portrait</strong><small id="makeup-upload-help">JPG or PNG image, up to 8 MB. Your original stays available for comparison.</small></button>}
        {file && <div className="studio-file-row"><div><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(2)} MB</small></div><div><button type="button" className="studio-text-button" disabled={generating} onClick={() => inputRef.current?.click()}>Replace</button><button type="button" className="studio-text-button" disabled={generating} onClick={clearImage}>Remove</button></div></div>}
        {uploadError && <p id="makeup-upload-error" role="alert" className="studio-alert">{uploadError}</p>}
      </StudioPanel>
      <StudioPanel id="makeup-styles-heading" number="02" title="Choose a makeup look" detail="Find a finish that suits your mood.">
        {stylesError && <div role="alert" className="studio-alert">{stylesError}<button type="button" onClick={() => void loadStyles()}>Retry connection</button></div>}
        {stylesLoading ? <p role="status" className="studio-loading-styles">Loading makeup choices…</p> : <div className="studio-style-grid">{styles.map((style, index) => <button key={style.id} type="button" className="studio-style-card" disabled={generating} onClick={() => { setSelectedId(style.id); resetResult(); setGenerateError(""); }} aria-pressed={selectedId === style.id}><span className="studio-style-art" data-tone={index % 5} aria-hidden="true"><b>{style.name.charAt(0)}</b></span><span className="studio-style-body"><strong>{style.name}</strong><small>{style.description}</small><em>{style.status === "trained_preset" ? "MAKEUP-001 preset" : style.status}</em></span></button>)}</div>}
        <p className="studio-tip"><strong>{liveMode ? "MAKEUP-001 generation" : "Development preview"}</strong><br />{liveMode ? "Your portrait is processed by the active Makeup inference service. Subtle looks may appear more glamorous than intended." : "No makeup is applied while the model is unavailable. The preview mirrors the original portrait."}</p>
      </StudioPanel>
    </div>
    <section aria-label="Generate makeup preview" className="studio-action-bar"><div><small>03 / CREATE YOUR LOOK</small><h2>Ready for your makeup preview?</h2><p>{selectedStyle ? `Selected: ${selectedStyle.name}` : "Upload a portrait and choose a makeup style."}</p></div><button type="button" className="studio-primary-button" disabled={!file || !selectedId || generating} onClick={() => void onGenerate()}>{generating ? (liveMode ? "Generating makeup…" : "Preparing preview…") : (liveMode ? "Generate makeup" : "Generate preview")} <span aria-hidden="true">✦</span></button></section>
    {generateError && <p role="alert" className="studio-alert">{generateError}</p>}
    {result && !resultOpen && <button type="button" className="studio-view-result" onClick={() => setResultOpen(true)}>View your result again</button>}
    {generating && <GenerationProgress feature="makeup" mock={!liveMode} />}
    <ResultDialog result={result} open={resultOpen} original={previewUrl} originalAlt="Original uploaded portrait" generatedAlt={realResult ? `MAKEUP-001 generated ${result?.style.name} result` : "Normalized original portrait returned by the makeup prototype"}
      title={realResult ? "Your MAKEUP-001 result" : "A preview of the workflow"} note={realResult ? "Generated with FLUX.2 Klein Base + MAKEUP-001. This AI preview may change facial details, skin tone, lighting or texture; it is not an exact prediction of real cosmetics." : "No makeup was applied. This is your normalized original image, not an AI makeup transformation."}
      onClose={() => setResultOpen(false)} onRegenerate={() => void onGenerate()} />
  </StudioShell>;
}
