"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { GenerationProgress, ResultDialog, StudioPanel, StudioPhoto, StudioShell } from "@/components/ai-studio";
import { API_BASE_URL, generate, getHealth, getStyles, type GenerateResponse, type Style } from "@/lib/api";

const MAX_FILE_BYTES = 8 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png"]);

export default function Home() {
  const [styles, setStyles] = useState<Style[]>([]);
  const [generatorMode, setGeneratorMode] = useState("mock");
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
    try {
      const [loaded, health] = await Promise.all([getStyles("hairstyle"), getHealth()]);
      setStyles(loaded);
      setGeneratorMode(health.generator);
    } catch {
      setStylesError(`The local API is unavailable at ${API_BASE_URL}. Start the backend and retry.`);
    } finally {
      setStylesLoading(false);
    }
  }

  useEffect(() => {
    let mounted = true;
    Promise.all([getStyles("hairstyle"), getHealth()])
      .then(([loaded, health]) => { if (mounted) { setStyles(loaded); setGeneratorMode(health.generator); } })
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
      const generated = await generate("hairstyle", file, selectedId);
      setResult(generated);
      setResultOpen(true);
    } catch (error) {
      setGenerateError(error instanceof Error ? error.message : "Generation failed. Please try again.");
    } finally {
      submittingRef.current = false;
      setGenerating(false);
    }
  }

  const selectedStyle = styles.find((style) => style.id === selectedId);
  const isMock = generatorMode === "mock";

  return <StudioShell feature="hairstyle" eyebrow="THE AI BEAUTY STUDIO" title="Discover your" emphasis="next hairstyle."
    description={isMock ? "Upload a portrait and choose a hairstyle to explore the application flow. In development preview, the result mirrors your original image." : "Upload a portrait, choose a hairstyle, and see it reimagined for you. AI previews can alter facial details."}
    badge={isMock ? "Development preview" : "Experimental model demo"}>
    <div className="studio-workspace">
      <StudioPanel id="portrait-heading" number="01" title="Your portrait" detail="Start with a clear, front-facing photo.">
        <input ref={inputRef} id="portrait-upload" className="sr-only" type="file" accept="image/jpeg,image/png" onChange={onFileChange} disabled={generating} aria-label="Upload your portrait" aria-describedby="upload-help upload-error" />
        {previewUrl ? <StudioPhoto src={previewUrl} alt="Preview of your uploaded portrait" /> : <button type="button" className="studio-upload" onClick={() => inputRef.current?.click()}><span className="studio-upload-icon" aria-hidden="true">↑</span><strong>Choose your portrait</strong><small id="upload-help">JPG or PNG image, up to 8 MB. Your original stays available for comparison.</small></button>}
        {file && <div className="studio-file-row"><div><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(2)} MB</small></div><div><button type="button" className="studio-text-button" disabled={generating} onClick={() => inputRef.current?.click()}>Replace</button><button type="button" className="studio-text-button" disabled={generating} onClick={clearImage}>Remove</button></div></div>}
        {uploadError && <p id="upload-error" role="alert" className="studio-alert">{uploadError}</p>}
      </StudioPanel>
      <StudioPanel id="styles-heading" number="02" title="Find your style" detail="Select the look you would like to preview.">
        {stylesError && <div role="alert" className="studio-alert">{stylesError}<button type="button" onClick={() => void loadStyles()}>Retry connection</button></div>}
        {stylesLoading ? <p role="status" className="studio-loading-styles">Loading hairstyle choices…</p> : <div className="studio-style-grid">{styles.map((style, index) => <button key={style.id} type="button" className="studio-style-card" disabled={generating} onClick={() => { setSelectedId(style.id); resetResult(); setGenerateError(""); }} aria-pressed={selectedId === style.id}><span className="studio-style-art" data-tone={index % 5} aria-hidden="true"><b>{style.name.charAt(0)}</b></span><span className="studio-style-body"><strong>{style.name}</strong><small>{style.description}</small><em>{style.status}</em></span></button>)}</div>}
        <p className="studio-tip"><strong>{isMock ? "Development preview" : "Experimental model"}</strong><br />{isMock ? "The generated preview mirrors your original image while the model is unavailable." : "Your selected look uses the active hairstyle adapter. Generation can take about a minute."}</p>
      </StudioPanel>
    </div>
    <section aria-label="Generate preview" className="studio-action-bar"><div><small>03 / CREATE YOUR LOOK</small><h2>Ready to see your preview?</h2><p>{selectedStyle ? `Selected: ${selectedStyle.name}` : "Upload a portrait and choose a style to continue."}</p></div><button type="button" className="studio-primary-button" disabled={!file || !selectedId || generating} onClick={() => void onGenerate()}>{generating ? "Generating preview…" : "Generate preview"} <span aria-hidden="true">✦</span></button></section>
    {generateError && <p role="alert" className="studio-alert">{generateError}</p>}
    {result && !resultOpen && <button type="button" className="studio-view-result" onClick={() => setResultOpen(true)}>View your result again</button>}
    {generating && <GenerationProgress feature="hairstyle" mock={isMock} />}
    <ResultDialog result={result} open={resultOpen} original={previewUrl} originalAlt="Original uploaded portrait" generatedAlt={isMock ? "Development preview from the mock generator" : "Hairstyle generated by the project trained model"}
      title={isMock ? "A first look at the flow" : "Your experimental result"} note={isMock ? "AI model not connected yet. This is your normalized original image, not a hairstyle transformation." : "Generated with a project-trained hairstyle LoRA. Facial details may change; review the result before using it."}
      onClose={() => setResultOpen(false)} onRegenerate={() => void onGenerate()} />
  </StudioShell>;
}
