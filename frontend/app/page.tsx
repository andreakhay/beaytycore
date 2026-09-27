"use client";

import Image from "next/image";
import Link from "next/link";
import { ChangeEvent, useEffect, useRef, useState } from "react";

import { API_BASE_URL, generate, getHealth, getStyles, type GenerateResponse, type Style } from "@/lib/api";

const MAX_FILE_BYTES = 8 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png"]);
const TONES = [
  "from-[#d8c5ad] to-[#aa8d6f]", "from-[#b5c2b4] to-[#78907d]",
  "from-[#d9b2a8] to-[#b58178]", "from-[#aeb6c2] to-[#78899d]",
  "from-[#c9b9d2] to-[#9884a6]", "from-[#d9c7a9] to-[#ad9d7f]",
];

function Photo({ src, alt }: { src: string; alt: string }) {
  return <div className="relative aspect-[4/5] overflow-hidden rounded-2xl bg-[#e8e9e2]"><Image src={src} alt={alt} fill unoptimized sizes="(max-width: 1024px) 100vw, 50vw" className="object-contain" /></div>;
}

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

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0];
    event.target.value = "";
    if (!chosen) return;
    if (!ACCEPTED_TYPES.has(chosen.type)) {
      setUploadError("Choose a JPG or PNG portrait.");
      return;
    }
    if (chosen.size === 0 || chosen.size > MAX_FILE_BYTES) {
      setUploadError("Choose an image between 1 byte and 8 MB.");
      return;
    }
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = URL.createObjectURL(chosen);
    setPreviewUrl(previewRef.current);
    setFile(chosen);
    setUploadError("");
    setGenerateError("");
    setResult(null);
  }

  function clearImage() {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = "";
    setFile(null);
    setPreviewUrl("");
    setResult(null);
    setUploadError("");
    setGenerateError("");
  }

  async function onGenerate() {
    if (!file || !selectedId || submittingRef.current) return;
    submittingRef.current = true;
    setGenerating(true);
    setGenerateError("");
    setResult(null);
    try {
      setResult(await generate("hairstyle", file, selectedId));
    } catch (error) {
      setGenerateError(error instanceof Error ? error.message : "Generation failed. Please try again.");
    } finally {
      submittingRef.current = false;
      setGenerating(false);
    }
  }

  const selectedStyle = styles.find((style) => style.id === selectedId);
  const isMock = generatorMode === "mock";

  return <div className="min-h-screen bg-[#f6f4ef] text-[#202522]">
    <header className="border-b border-[#dce1d8] bg-[#faf9f5]">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-10">
        <div className="flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#2f5141] text-sm font-bold text-white">HC</span><div><p className="text-sm font-bold tracking-[0.14em]">HAIR CAPSTONE</p><p className="text-xs text-[#738075]">AI virtual hairstyle</p></div></div>
        <div className="flex items-center gap-3"><nav aria-label="Features" className="flex gap-1 rounded-full border border-[#d1ddd0] bg-white p-1 text-xs font-semibold"><span aria-current="page" className="rounded-full bg-[#2f5141] px-3 py-2 text-white">Hairstyle</span><Link href="/makeup" className="rounded-full px-3 py-2 text-[#42654b] hover:bg-[#eaf1e8] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2f5141]">Makeup</Link><Link href="/nails" className="rounded-full px-3 py-2 text-[#42654b] hover:bg-[#eaf1e8] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2f5141]">Nails</Link></nav><span className="hidden rounded-full border border-[#d1ddd0] bg-[#eaf1e8] px-3 py-1 text-xs font-semibold text-[#42654b] sm:inline">{isMock ? "Development preview" : "Experimental model demo"}</span></div>
      </div>
    </header>

    <main className="mx-auto max-w-7xl px-5 pb-20 pt-12 sm:px-8 lg:px-10">
      <div className="mb-10 max-w-3xl"><p className="mb-3 text-xs font-bold uppercase tracking-[0.22em] text-[#aa7058]">Your next look starts here</p><h1 className="text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">See the flow.<br /><span className="font-serif font-normal italic text-[#6d8a74]">Shape what comes next.</span></h1><p className="mt-5 max-w-2xl text-base leading-7 text-[#617066]">{isMock ? "Upload a portrait and pick a hairstyle to try the application flow. The AI model is not connected yet, so this development preview returns your original portrait." : "Upload a portrait and choose an available experimental hairstyle. Results can still alter facial details."}</p></div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <section aria-labelledby="portrait-heading" className="rounded-3xl border border-[#e0e4dc] bg-white p-5 shadow-[0_12px_35px_rgba(36,54,42,0.05)] sm:p-7">
          <div className="mb-6 flex items-start justify-between gap-3"><div><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-[#aa7058]">01 / Your portrait</p><h2 id="portrait-heading" className="text-2xl font-semibold tracking-tight">Start with a photo</h2></div><span className="rounded-full bg-[#f2f4ef] px-3 py-1 text-xs text-[#677569]">JPG or PNG</span></div>
          <input ref={inputRef} id="portrait-upload" className="sr-only" type="file" accept="image/jpeg,image/png" onChange={onFileChange} aria-describedby="upload-help upload-error" />
          {previewUrl ? <Photo src={previewUrl} alt="Preview of your uploaded portrait" /> : <button type="button" onClick={() => inputRef.current?.click()} className="flex aspect-[4/5] w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-[#b9c9bc] bg-[#f3f7f1] px-7 text-center transition hover:border-[#64856d] hover:bg-[#edf4ea]"><span aria-hidden="true" className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-white text-3xl text-[#54775d] shadow-sm">↑</span><span className="text-lg font-semibold">Choose your portrait</span><span id="upload-help" className="mt-2 text-sm leading-6 text-[#718075]">Select a JPG or PNG image up to 8 MB.</span></button>}
          {file && <div className="mt-4 flex flex-wrap items-center justify-between gap-3"><div className="min-w-0"><p className="truncate text-sm font-medium">{file.name}</p><p className="text-xs text-[#78847b]">{(file.size / 1024 / 1024).toFixed(2)} MB</p></div><div className="flex gap-2"><button type="button" onClick={() => inputRef.current?.click()} className="rounded-full border border-[#cbd6cc] px-4 py-2 text-sm font-medium hover:bg-[#f2f6f0]">Replace</button><button type="button" onClick={clearImage} className="rounded-full px-4 py-2 text-sm font-medium text-[#a04e3c] hover:bg-[#fdf0eb]">Remove</button></div></div>}
          {uploadError && <p id="upload-error" role="alert" className="mt-4 rounded-xl bg-[#fff0e9] px-4 py-3 text-sm text-[#9b4834]">{uploadError}</p>}
        </section>

        <section aria-labelledby="styles-heading" className="rounded-3xl border border-[#e0e4dc] bg-white p-5 shadow-[0_12px_35px_rgba(36,54,42,0.05)] sm:p-7">
          <div className="mb-6"><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-[#aa7058]">02 / Explore styles</p><h2 id="styles-heading" className="text-2xl font-semibold tracking-tight">Choose a direction</h2><p className="mt-2 text-sm text-[#6d7970]">{isMock ? "Prototype choices only. No hairstyle model has been trained for them yet." : "Each listed style belongs to a project-trained experimental adapter."}</p></div>
          {stylesError && <div role="alert" className="mb-5 rounded-xl border border-[#f0c7b7] bg-[#fff3ee] p-4 text-sm text-[#8d4434]"><p>{stylesError}</p><button type="button" onClick={() => void loadStyles()} className="mt-3 font-semibold underline underline-offset-4">Retry connection</button></div>}
          {stylesLoading ? <p role="status" className="rounded-xl bg-[#f5f6f2] p-6 text-sm text-[#66756b]">Loading hairstyle choices…</p> : <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{styles.map((style, index) => <button key={style.id} type="button" onClick={() => { setSelectedId(style.id); setResult(null); setGenerateError(""); }} aria-pressed={selectedId === style.id} className={`overflow-hidden rounded-2xl border text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2f5141] ${selectedId === style.id ? "border-[#37634b] bg-[#f1f7f0] ring-2 ring-[#37634b]" : "border-[#dfe5dc] bg-white hover:border-[#95aa97] hover:shadow-md"}`}><span aria-hidden="true" className={`relative flex h-24 items-end overflow-hidden bg-gradient-to-br ${TONES[index % TONES.length]} p-3`}><span className="absolute -right-4 -top-6 h-24 w-24 rounded-full border-[14px] border-white/20" /><span className="relative font-serif text-4xl italic text-white/90">{style.name.charAt(0)}</span></span><span className="block px-3 pb-3 pt-3"><span className="block text-sm font-semibold leading-5">{style.name}</span><span className="mt-1 block text-xs leading-4 text-[#6a766d]">{style.description}</span><span className="mt-3 inline-block rounded-full bg-[#eef1eb] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#64756a]">{style.status}</span></span></button>)}</div>}
          <div className="mt-7 rounded-2xl bg-[#f2f4ed] p-5"><div className="flex items-start gap-3"><span aria-hidden="true" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#dce9db] text-sm font-bold text-[#42694e]">i</span><div><p className="text-sm font-semibold">{isMock ? "Development preview" : "Experimental model"}</p><p className="mt-1 text-sm leading-6 text-[#66766a]">{isMock ? "Generate proves the upload and API flow. The result currently mirrors your original image." : "The result comes from our FLUX.2 Klein hairstyle LoRA running in the active Kaggle session. Generation can take about a minute."}</p></div></div></div>
        </section>
      </div>

      <section aria-label="Generate preview" className="mt-6 rounded-3xl bg-[#2f493e] p-5 text-white shadow-[0_15px_35px_rgba(35,57,44,0.18)] sm:flex sm:items-center sm:justify-between sm:gap-6 sm:p-7"><div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#c9dccb]">03 / Generate</p><h2 className="mt-1 text-xl font-semibold">Ready to see the preview?</h2><p className="mt-1 text-sm text-[#d5e0d5]">{selectedStyle ? `Selected: ${selectedStyle.name}` : "Upload a portrait and choose a style to continue."}</p></div><button type="button" onClick={() => void onGenerate()} disabled={!file || !selectedId || generating} className="mt-5 w-full rounded-full bg-[#f0dcc9] px-8 py-3.5 text-sm font-bold text-[#2b4035] transition hover:bg-white disabled:cursor-not-allowed disabled:bg-[#698074] disabled:text-[#d1ded3] sm:mt-0 sm:w-auto">{generating ? "Generating preview…" : "Generate preview"}</button></section>
      {generating && <p role="status" aria-live="polite" className="mt-5 rounded-xl bg-[#eaf0e9] px-5 py-4 text-sm text-[#405d47]">{isMock ? "Processing your portrait with the mock generator…" : "Generating with the trained model on Kaggle. Please keep this page open…"}</p>}
      {generateError && <p role="alert" className="mt-5 rounded-xl bg-[#fff0e9] px-5 py-4 text-sm text-[#9b4834]">{generateError}</p>}

      {result && previewUrl && <section aria-labelledby="result-heading" className="mt-14"><div className="mb-6 flex flex-wrap items-end justify-between gap-3"><div><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-[#aa7058]">Your result</p><h2 id="result-heading" className="text-3xl font-semibold tracking-tight">{isMock ? "A first look at the flow" : "Your experimental result"}</h2></div><span className="rounded-full bg-[#e7eee5] px-3 py-1 text-xs font-semibold uppercase tracking-wider text-[#3d6649]">{result.status}</span></div><div className="grid gap-5 md:grid-cols-2"><div className="rounded-3xl border border-[#e0e3dc] bg-white p-4"><Photo src={previewUrl} alt="Original uploaded portrait" /><p className="px-2 pt-4 text-lg font-semibold">Original</p></div><div className="rounded-3xl border border-[#c7d9c7] bg-white p-4"><Photo src={result.image.data_url} alt={isMock ? "Development preview from the mock generator" : "Hairstyle generated by the project trained model"} /><div className="flex flex-wrap items-center justify-between gap-2 px-2 pt-4"><p className="text-lg font-semibold">Generated result</p><span className="rounded-full bg-[#eaf0e9] px-3 py-1 text-xs font-semibold text-[#466d51]">{result.style.name}</span></div></div></div><div className="mt-5 rounded-2xl border border-[#e4d5bc] bg-[#fbf4e7] p-5 text-sm leading-6 text-[#756348]"><strong>{isMock ? "Development Preview" : "Experimental FLUX result"} · generator: {result.generator}</strong><br />{isMock ? "AI model not connected yet. This is your normalized original image, not a hairstyle transformation." : "Generated with a project-trained hairstyle LoRA. Facial details may change; review the result before using it."}</div></section>}
    </main>
  </div>;
}
