"use client";

import Image from "next/image";
import Link from "next/link";
import { ChangeEvent, useEffect, useRef, useState } from "react";
import { API_BASE_URL, generate as generateFeature, getStyles, type GenerateResponse, type Style } from "@/lib/api";

const MAX_BYTES = 8 * 1024 * 1024;
const COLORS: Record<string, string> = {
  classic_red: "#aa2138", nude_pink: "#d696a3", glossy_black: "#24232a",
  french_tip: "#e9d7d6", pink_ombre: "#c6719e",
};

function Photo({ src, alt }: { src: string; alt: string }) {
  return <div className="relative aspect-[4/5] overflow-hidden rounded-2xl bg-[#f2ece8]"><Image src={src} alt={alt} fill unoptimized sizes="(max-width: 768px) 100vw, 50vw" className="object-contain" /></div>;
}

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

  function choose(event: ChangeEvent<HTMLInputElement>) {
    const next = event.target.files?.[0];
    event.target.value = "";
    if (!next) return;
    if (!["image/jpeg", "image/png"].includes(next.type) || next.size < 1 || next.size > MAX_BYTES) {
      setError("Choose a JPG or PNG image up to 8 MB."); return;
    }
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = URL.createObjectURL(next);
    setPreview(previewRef.current); setFile(next); setError(""); setResult(null);
  }

  function clear() {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = ""; setPreview(""); setFile(null); setResult(null); setError("");
  }

  async function generate() {
    if (!file || !styleId || submitting.current) return;
    submitting.current = true; setWorking(true); setError(""); setResult(null);
    try { setResult(await generateFeature("nails", file, styleId)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Preview failed. Please try again."); }
    finally { submitting.current = false; setWorking(false); }
  }

  return <div className="min-h-screen bg-[#faf7f4] text-[#302629]">
    <header className="border-b border-[#e9dedd] bg-white"><div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-5">
      <div><p className="text-sm font-bold tracking-[0.14em]">HAIR CAPSTONE</p><p className="text-xs text-[#8d777d]">Nails try-on</p></div>
      <nav aria-label="Features" className="flex gap-3 text-sm font-semibold"><Link href="/" className="hover:underline">Hairstyle</Link><Link href="/makeup" className="hover:underline">Makeup</Link><span aria-current="page" className="text-[#a22b49]">Nails</span></nav>
    </div></header>
    <main className="mx-auto max-w-6xl px-5 pb-20 pt-10">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#a22b49]">Nails try-on</p>
      <h1 className="mt-3 text-4xl font-semibold">Explore five nail styles</h1>
      <p className="mt-4 max-w-2xl leading-7 text-[#755f65]">Use one clear photo of the back of your hand with 3 to 5 visible nails.</p>
      <div className="mt-9 grid gap-6 md:grid-cols-2">
        <section className="rounded-3xl border border-[#eadbdc] bg-white p-6"><h2 className="text-xl font-semibold">Your hand photo</h2>
          <input ref={input} className="sr-only" type="file" accept="image/jpeg,image/png" onChange={choose} aria-label="Choose a hand photo" />
          <div className="mt-5">{preview ? <Photo src={preview} alt="Uploaded hand photo" /> : <button type="button" onClick={() => input.current?.click()} className="flex aspect-[4/5] w-full items-center justify-center rounded-2xl border-2 border-dashed border-[#ddbfc7] bg-[#fcf6f7] p-6 text-center font-semibold">Choose a JPG or PNG hand photo</button>}</div>
          {file && <div className="mt-4 flex items-center justify-between gap-3"><span className="min-w-0 truncate text-sm">{file.name}</span><div className="flex gap-3 text-sm font-semibold"><button type="button" onClick={() => input.current?.click()}>Replace</button><button type="button" onClick={clear}>Remove</button></div></div>}
        </section>
        <section className="rounded-3xl border border-[#eadbdc] bg-white p-6"><h2 className="text-xl font-semibold">Choose a nail look</h2>
          {loading && <p role="status" className="mt-5">Loading styles…</p>}
          {stylesError && <p role="alert" className="mt-5 text-[#a22b49]">{stylesError}</p>}
          <div className="mt-5 grid gap-3 sm:grid-cols-2">{styles.map((style) => <button key={style.id} type="button" aria-pressed={styleId === style.id} onClick={() => { setStyleId(style.id); setResult(null); }} className={`flex items-center gap-4 rounded-2xl border p-4 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#a22b49] ${styleId === style.id ? "border-[#a22b49] bg-[#fff1f4]" : "border-[#eadbdc]"}`}><span className="h-12 w-12 shrink-0 rounded-xl border border-black/10" style={{ background: COLORS[style.id] }} /><span><strong className="block text-sm">{style.name}</strong><small className="text-[#7a6569]">{style.description}</small></span></button>)}</div>
        </section>
      </div>
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-[#703e4d] p-6 text-white"><p>{styleId ? `Selected: ${styles.find((style) => style.id === styleId)?.name}` : "Upload a hand photo and select a style."}</p><button type="button" disabled={!file || !styleId || working} onClick={() => void generate()} className="rounded-full bg-white px-6 py-3 font-semibold text-[#703e4d] disabled:opacity-50">{working ? "Applying nail style…" : "Try this style"}</button></div>
      {error && <p role="alert" className="mt-5 rounded-xl bg-[#fff0e9] p-4 text-[#914734]">{error}</p>}
      {result && preview && <section className="mt-10"><h2 className="mb-5 text-2xl font-semibold">Your result</h2><div className="grid gap-5 md:grid-cols-2"><div><Photo src={preview} alt="Original hand photo" /><p className="mt-3 font-semibold">Original</p></div><div><Photo src={result.image.data_url} alt={result.status === "placeholder" ? "Original photo preview" : `Hand with ${result.style.name} nails`} /><p className="mt-3 font-semibold">{result.status === "placeholder" ? "Preview" : result.style.name}</p></div></div>{result.status === "placeholder" && <p className="mt-5 rounded-xl bg-[#fff0e9] p-4 text-sm">Nail styling is unavailable in this development preview.</p>}</section>}
    </main>
  </div>;
}
