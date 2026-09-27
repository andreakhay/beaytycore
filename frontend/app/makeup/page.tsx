"use client";

import Image from "next/image";
import Link from "next/link";
import { ChangeEvent, useEffect, useRef, useState } from "react";

import { API_BASE_URL, generate, getStyles, type GenerateResponse, type Style } from "@/lib/api";

const MAX_FILE_BYTES = 8 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png"]);
const TONES = [
  "from-[#e4c3ba] to-[#ba847a]", "from-[#dfccc2] to-[#ac938c]",
  "from-[#d7b8af] to-[#a96d75]", "from-[#9b8b9c] to-[#514e67]",
  "from-[#efc7a7] to-[#d38d72]", "from-[#eac4cd] to-[#bd778e]",
  "from-[#dfb899] to-[#a8764e]", "from-[#d8bfb5] to-[#a78375]",
  "from-[#c97878] to-[#993e4c]", "from-[#a67788] to-[#57354f]",
];

function Photo({ src, alt }: { src: string; alt: string }) {
  return <div className="relative aspect-[4/5] overflow-hidden rounded-2xl bg-[#f1e9e5]"><Image src={src} alt={alt} fill unoptimized sizes="(max-width: 1024px) 100vw, 50vw" className="object-contain" /></div>;
}

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
  const inputRef = useRef<HTMLInputElement>(null);
  const previewRef = useRef("");
  const submittingRef = useRef(false);

  async function loadStyles() {
    setStylesLoading(true);
    setStylesError("");
    try {
      setStyles(await getStyles("makeup"));
    } catch {
      setStylesError(`The local API is unavailable at ${API_BASE_URL}. Start the backend and retry.`);
    } finally {
      setStylesLoading(false);
    }
  }

  useEffect(() => {
    let mounted = true;
    getStyles("makeup")
      .then((loaded) => { if (mounted) setStyles(loaded); })
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
    setUploadError("");
    setGenerateError("");
    setResult(null);
  }

  async function onGenerate() {
    if (!file || !selectedId || submittingRef.current) return;
    submittingRef.current = true;
    setGenerating(true);
    setGenerateError("");
    setResult(null);
    try {
      setResult(await generate("makeup", file, selectedId));
    } catch (error) {
      setGenerateError(error instanceof Error ? error.message : "Makeup generation failed. Please try again.");
    } finally {
      submittingRef.current = false;
      setGenerating(false);
    }
  }

  const selectedStyle = styles.find((style) => style.id === selectedId);
  const liveMode = styles.some((style) => style.status === "trained_preset");
  const realResult = result?.status === "completed" && result.generator === "flux2_klein_base_makeup001";

  return <div className="min-h-screen bg-[#f8f5f1] text-[#2b2528]">
    <header className="border-b border-[#e6dcd8] bg-[#fdfbf9]">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-5 py-5 sm:px-8 lg:px-10">
        <div className="flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#754c5b] text-sm font-bold text-white">HC</span><div><p className="text-sm font-bold tracking-[0.14em]">HAIR CAPSTONE</p><p className="text-xs text-[#89777d]">Virtual makeup preview</p></div></div>
        <nav aria-label="Features" className="flex gap-1 rounded-full border border-[#e6d8db] bg-white p-1 text-xs font-semibold"><Link href="/" className="rounded-full px-3 py-2 text-[#754c5b] hover:bg-[#f5e9ed] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#754c5b]">Hairstyle</Link><span aria-current="page" className="rounded-full bg-[#754c5b] px-3 py-2 text-white">Makeup</span><Link href="/nails" className="rounded-full px-3 py-2 text-[#754c5b] hover:bg-[#f5e9ed] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#754c5b]">Nails</Link></nav>
      </div>
    </header>

    <main className="mx-auto max-w-7xl px-5 pb-20 pt-12 sm:px-8 lg:px-10">
      <div className="mb-10 max-w-3xl"><p className="mb-3 text-xs font-bold uppercase tracking-[0.22em] text-[#a46766]">Virtual Makeup Try-On</p><h1 className="text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">Explore a new look.<br /><span className="font-serif font-normal italic text-[#a56d7e]">Keep the portrait yours.</span></h1><p className="mt-5 max-w-2xl text-base leading-7 text-[#776c70]">{liveMode ? "Choose a makeup look generated with our project-trained MAKEUP-001 model. Results are AI previews and may retouch facial details or skin tone." : "Choose a makeup direction and preview the application flow. Mock mode returns your normalized original photo; real Makeup inference is not enabled in this session."}</p></div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <section aria-labelledby="makeup-portrait-heading" className="rounded-3xl border border-[#e9dfdc] bg-white p-5 shadow-[0_12px_35px_rgba(84,53,64,0.05)] sm:p-7">
          <div className="mb-6 flex items-start justify-between gap-3"><div><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-[#a46766]">01 / Your portrait</p><h2 id="makeup-portrait-heading" className="text-2xl font-semibold tracking-tight">Start with a photo</h2></div><span className="rounded-full bg-[#f7f0ef] px-3 py-1 text-xs text-[#8d777d]">JPG or PNG</span></div>
          <input ref={inputRef} id="makeup-upload" className="sr-only" type="file" accept="image/jpeg,image/png" onChange={onFileChange} disabled={generating} aria-label="Upload your portrait" aria-describedby="makeup-upload-help makeup-upload-error" />
          {previewUrl ? <Photo src={previewUrl} alt="Preview of your uploaded portrait" /> : <button type="button" onClick={() => inputRef.current?.click()} className="flex aspect-[4/5] w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-[#d8bcc5] bg-[#fbf3f5] px-7 text-center transition hover:border-[#ad7888] hover:bg-[#f8edf0] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#754c5b]"><span aria-hidden="true" className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-white text-3xl text-[#9f6578] shadow-sm">↑</span><span className="text-lg font-semibold">Choose your portrait</span><span id="makeup-upload-help" className="mt-2 text-sm leading-6 text-[#89777d]">Select a JPG or PNG image up to 8 MB.</span></button>}
          {file && <div className="mt-4 flex flex-wrap items-center justify-between gap-3"><div className="min-w-0"><p className="truncate text-sm font-medium">{file.name}</p><p className="text-xs text-[#89777d]">{(file.size / 1024 / 1024).toFixed(2)} MB</p></div><div className="flex gap-2"><button type="button" onClick={() => inputRef.current?.click()} disabled={generating} className="rounded-full border border-[#ddcbd0] px-4 py-2 text-sm font-medium hover:bg-[#faf3f5]">Replace</button><button type="button" onClick={clearImage} disabled={generating} className="rounded-full px-4 py-2 text-sm font-medium text-[#a04e3c] hover:bg-[#fdf0eb]">Remove</button></div></div>}
          {uploadError && <p id="makeup-upload-error" role="alert" className="mt-4 rounded-xl bg-[#fff0e9] px-4 py-3 text-sm text-[#9b4834]">{uploadError}</p>}
        </section>

        <section aria-labelledby="makeup-styles-heading" className="rounded-3xl border border-[#e9dfdc] bg-white p-5 shadow-[0_12px_35px_rgba(84,53,64,0.05)] sm:p-7">
          <div className="mb-6"><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-[#a46766]">02 / Explore styles</p><h2 id="makeup-styles-heading" className="text-2xl font-semibold tracking-tight">Choose a makeup look</h2><p className="mt-2 text-sm text-[#776c70]">{liveMode ? "Ten fixed prompt presets guide one general Makeup edit LoRA. Subtle looks may appear more glamorous than intended." : "Ten makeup looks. Enable the separate MAKEUP-001 service for real generation."}</p></div>
          {stylesError && <div role="alert" className="mb-5 rounded-xl border border-[#f0c7b7] bg-[#fff3ee] p-4 text-sm text-[#8d4434]"><p>{stylesError}</p><button type="button" onClick={() => void loadStyles()} className="mt-3 font-semibold underline underline-offset-4">Retry connection</button></div>}
          {stylesLoading ? <p role="status" className="rounded-xl bg-[#faf5f4] p-6 text-sm text-[#89777d]">Loading makeup choices…</p> : <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{styles.map((style, index) => <button key={style.id} type="button" disabled={generating} onClick={() => { setSelectedId(style.id); setResult(null); setGenerateError(""); }} aria-pressed={selectedId === style.id} className={`overflow-hidden rounded-2xl border text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#754c5b] ${selectedId === style.id ? "border-[#885364] bg-[#fcf1f4] ring-2 ring-[#885364]" : "border-[#eadfe1] bg-white hover:border-[#bb8f9c] hover:shadow-md"}`}><span aria-hidden="true" className={`relative flex h-24 items-end overflow-hidden bg-gradient-to-br ${TONES[index % TONES.length]} p-3`}><span className="absolute -right-4 -top-6 h-24 w-24 rounded-full border-[14px] border-white/20" /><span className="relative font-serif text-4xl italic text-white/90">{style.name.charAt(0)}</span></span><span className="block px-3 pb-3 pt-3"><span className="block text-sm font-semibold leading-5">{style.name}</span><span className="mt-1 block text-xs leading-4 text-[#796c71]">{style.description}</span><span className="mt-3 inline-block rounded-full bg-[#f9eef1] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#8a6070]">{style.status === "trained_preset" ? "MAKEUP-001 preset" : style.status}</span></span></button>)}</div>}
          <div className="mt-7 rounded-2xl bg-[#faf1f2] p-5"><p className="text-sm font-semibold">{liveMode ? "MAKEUP-001 generation" : "Prototype preview"}</p><p className="mt-1 text-sm leading-6 text-[#786a70]">{liveMode ? "Your portrait is sent to the separate Makeup GPU service. The Kaggle inference session must remain running." : "The selected style is recorded, but mock results mirror the original portrait. No makeup is applied in mock mode."}</p></div>
        </section>
      </div>

      <section aria-label="Generate makeup preview" className="mt-6 rounded-3xl bg-[#674653] p-5 text-white shadow-[0_15px_35px_rgba(88,51,65,0.18)] sm:flex sm:items-center sm:justify-between sm:gap-6 sm:p-7"><div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#f1d8df]">03 / Preview</p><h2 className="mt-1 text-xl font-semibold">{liveMode ? "Ready for your makeup preview?" : "Ready to see the flow?"}</h2><p className="mt-1 text-sm text-[#f2e0e5]">{selectedStyle ? `Selected: ${selectedStyle.name}` : "Upload a portrait and choose a makeup style."}</p></div><button type="button" onClick={() => void onGenerate()} disabled={!file || !selectedId || generating} className="mt-5 w-full rounded-full bg-[#f5dfd7] px-8 py-3.5 text-sm font-bold text-[#503740] transition hover:bg-white disabled:cursor-not-allowed disabled:bg-[#9c7d88] disabled:text-[#ead8de] sm:mt-0 sm:w-auto">{generating ? (liveMode ? "Generating makeup…" : "Preparing preview…") : (liveMode ? "Generate makeup" : "Generate preview")}</button></section>
      {generating && <p role="status" aria-live="polite" className="mt-5 rounded-xl bg-[#f8eaf0] px-5 py-4 text-sm text-[#754c5b]">{liveMode ? "MAKEUP-001 is generating your look. This may take a minute; keep this page open." : "Preparing your prototype preview…"}</p>}
      {generateError && <p role="alert" className="mt-5 rounded-xl bg-[#fff0e9] px-5 py-4 text-sm text-[#9b4834]">{generateError}</p>}

      {result && previewUrl && <section aria-labelledby="makeup-result-heading" className="mt-14"><div className="mb-6"><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-[#a46766]">Your result</p><h2 id="makeup-result-heading" className="text-3xl font-semibold tracking-tight">{realResult ? "Your MAKEUP-001 result" : "A preview of the workflow"}</h2></div><div className="grid gap-5 md:grid-cols-2"><div className="rounded-3xl border border-[#e9dfdc] bg-white p-4"><Photo src={previewUrl} alt="Original uploaded portrait" /><p className="px-2 pt-4 text-lg font-semibold">Original</p></div><div className="rounded-3xl border border-[#dec8cf] bg-white p-4"><Photo src={result.image.data_url} alt={realResult ? `MAKEUP-001 generated ${result.style.name} result` : "Normalized original portrait returned by the makeup prototype"} /><div className="flex flex-wrap items-center justify-between gap-2 px-2 pt-4"><p className="text-lg font-semibold">{realResult ? "MAKEUP-001 result" : "Prototype result"}</p><span className="rounded-full bg-[#faf0f3] px-3 py-1 text-xs font-semibold text-[#875366]">{result.style.name}</span></div></div></div><p className="mt-5 rounded-2xl border border-[#ead4c5] bg-[#fff5ed] p-5 text-sm leading-6 text-[#805f50]">{realResult ? "Generated with FLUX.2 Klein Base + MAKEUP-001. This AI preview may change facial details, skin tone, lighting or texture; it is not an exact prediction of real cosmetics." : "No makeup was applied. This is your normalized original image, not an AI makeup transformation."}</p></section>}
    </main>
  </div>;
}
