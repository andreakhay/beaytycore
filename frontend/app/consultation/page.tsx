"use client";

import Link from "next/link";
import { type ChangeEvent, useEffect, useRef, useState } from "react";

import { StudioPanel, StudioPhoto, StudioShell } from "@/components/ai-studio";
import type { FeatureId, GenerateResponse } from "@/lib/api";
import { createConsultation, generateRecommendation, getGenerationDetail, recommendConsultation,
  selectRecommendation, updateConsultation, uploadConsultationPhoto,
  type GenerationDetail, type Preferences, type Recommendation } from "@/lib/consultation-api";
import { rememberCustomPhoto } from "@/lib/photo-handoff";

type CardStatus = "pending" | "generating" | "completed" | "failed" | "unknown";
type Card = { recommendation: Recommendation; status: CardStatus; result: GenerateResponse | null;
  error: string; canRetry: boolean };
type Phase = "setup" | "preparing" | "generating" | "ready" | "attention";

const SERVICES: { id: FeatureId; label: string; detail: string; href: string }[] = [
  { id: "hairstyle", label: "Hairstyle", detail: "A cut or shape for your next look", href: "/" },
  { id: "makeup", label: "Makeup", detail: "A finish for your portrait", href: "/makeup" },
  { id: "nails", label: "Nails", detail: "A polished hand look", href: "/nails" },
];
const MAX_BYTES = 8 * 1024 * 1024;
const wait = (milliseconds: number) => new Promise((resolve) => setTimeout(resolve, milliseconds));

export default function ConsultationPage() {
  const [service, setService] = useState<FeatureId>("hairstyle");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const previewRef = useRef("");
  const inputRef = useRef<HTMLInputElement>(null);
  const running = useRef(false);
  const [occasion, setOccasion] = useState("");
  const [vibe, setVibe] = useState("");
  const [avoids, setAvoids] = useState("");
  const [notes, setNotes] = useState("");
  const [servicePreference, setServicePreference] = useState("");
  const [phase, setPhase] = useState<Phase>("setup");
  const [consultationId, setConsultationId] = useState("");
  const [cards, setCards] = useState<Card[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => () => { if (previewRef.current) URL.revokeObjectURL(previewRef.current); }, []);

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0];
    event.target.value = "";
    if (!chosen) return;
    if (!["image/jpeg", "image/png"].includes(chosen.type) || chosen.size < 1 || chosen.size > MAX_BYTES) {
      setError("Choose a JPG or PNG image up to 8 MB."); return;
    }
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = URL.createObjectURL(chosen);
    setPreview(previewRef.current);
    setFile(chosen);
    setCards([]);
    setSelectedId("");
    setPhase("setup");
    setError("");
  }

  function changeService(next: FeatureId) {
    setService(next);
    setServicePreference("");
    setCards([]);
    setSelectedId("");
    setPhase("setup");
    setError("");
  }

  function preferences(): Preferences {
    const shared: Preferences = { occasion: occasion.trim() || undefined, vibe: vibe.trim() || undefined,
      avoids: avoids.split(",").map((value) => value.trim()).filter(Boolean).slice(0, 5),
      notes: notes.trim() || undefined };
    if (service === "hairstyle" && servicePreference) shared.hair_maintenance = servicePreference as "low" | "medium" | "high";
    if (service === "makeup" && servicePreference) shared.makeup_intensity = servicePreference as "natural" | "soft" | "bold";
    if (service === "nails" && servicePreference) shared.nail_finish = servicePreference as "glossy" | "matte" | "ombre" | "french";
    return shared;
  }

  function patchCard(id: string, change: Partial<Card>) {
    setCards((old) => old.map((card) => card.recommendation.id === id ? { ...card, ...change } : card));
  }

  function applyDetail(id: string, detail: GenerationDetail): boolean {
    if (detail.generation.status === "completed" && detail.result) {
      patchCard(id, { status: "completed", result: detail.result, error: "", canRetry: false });
      return true;
    }
    if (detail.generation.status === "failed") {
      patchCard(id, { status: "failed", error: detail.generation.error || "This look could not be generated.",
        canRetry: true });
      return true;
    }
    return false;
  }

  async function generateOne(id: string, recommendationId: string): Promise<boolean> {
    patchCard(recommendationId, { status: "generating", error: "", canRetry: false });
    try {
      const detail = await generateRecommendation(id, recommendationId);
      if (applyDetail(recommendationId, detail)) return true;
      throw new Error("The generation response did not contain a completed result.");
    } catch (cause) {
      // This is a status read, never a second generation request. A lost HTTP
      // response can leave the original GPU request active.
      try {
        let detail = await getGenerationDetail(id, recommendationId);
        for (let checks = 0; detail.generation.status === "generating" && checks < 120; checks++) {
          await wait(5000);
          detail = await getGenerationDetail(id, recommendationId);
        }
        if (applyDetail(recommendationId, detail)) return true;
        if (detail.generation.status === "pending") {
          patchCard(recommendationId, { status: "failed", error: cause instanceof Error ? cause.message : "This look is unavailable.", canRetry: false });
          return true;
        }
      } catch {
        // Keep the state uncertain; do not send another generation POST.
      }
      patchCard(recommendationId, { status: "unknown", error: "Generation status is uncertain. Check status before continuing.", canRetry: false });
      return false;
    }
  }

  async function generatePending(id: string, rows: Recommendation[]) {
    setPhase("generating");
    for (const row of rows) {
      if (!await generateOne(id, row.id)) { setPhase("attention"); return; }
    }
    setPhase("ready");
  }

  async function start() {
    if (!file || running.current) return;
    running.current = true;
    setError("");
    setCards([]);
    setSelectedId("");
    setPhase("preparing");
    try {
      const created = await createConsultation(service);
      setConsultationId(created.id);
      await uploadConsultationPhoto(created.id, file);
      await updateConsultation(created.id, preferences());
      const set = await recommendConsultation(created.id);
      setCards(set.recommendations.map((recommendation) => ({ recommendation, status: "pending",
        result: null, error: "", canRetry: false })));
      await generatePending(created.id, set.recommendations);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Consultation could not start. Please try again.");
      setPhase("setup");
    } finally { running.current = false; }
  }

  async function retry(card: Card) {
    if (!consultationId || !card.canRetry || running.current) return;
    running.current = true;
    setPhase("generating");
    try {
      const settled = await generateOne(consultationId, card.recommendation.id);
      setPhase(settled && !cards.some((item) => item.status === "pending" || item.status === "unknown")
        ? "ready" : "attention");
    }
    finally { running.current = false; }
  }

  async function checkStatus(card: Card) {
    if (!consultationId || running.current) return;
    try {
      const detail = await getGenerationDetail(consultationId, card.recommendation.id);
      if (applyDetail(card.recommendation.id, detail)) setPhase("attention");
      else patchCard(card.recommendation.id, { status: "unknown", error: "Still processing or status unavailable. Check again shortly." });
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not check generation status."); }
  }

  async function continuePending() {
    if (!consultationId || running.current || cards.some((card) => card.status === "unknown")) return;
    running.current = true;
    try { await generatePending(consultationId, cards.filter((card) => card.status === "pending").map((card) => card.recommendation)); }
    finally { running.current = false; }
  }

  async function select(card: Card) {
    if (!consultationId || card.status !== "completed") return;
    try {
      const state = await selectRecommendation(consultationId, card.recommendation.id);
      setSelectedId(state.selected_recommendation_id || "");
      setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Selection could not be saved."); }
  }

  const serviceInfo = SERVICES.find((item) => item.id === service)!;
  const busy = phase === "preparing" || phase === "generating";
  const selected = cards.find((card) => card.recommendation.id === selectedId);

  return <StudioShell feature="consultation" eyebrow="THE AI BEAUTY STUDIO" title="Find a look" emphasis="made for your plans."
    description="Choose a service, share one photo and a few preferences, then explore three supported looks. This guided preview uses a deterministic recommender."
    badge="Guided consultation preview">
    <div className="studio-workspace">
      <StudioPanel id="consult-service" number="01" title="Choose a service" detail="Each consultation focuses on one primary service.">
        <div className="consult-service-grid" role="group" aria-label="Choose service">
          {SERVICES.map((item) => <button key={item.id} type="button" className="consult-service-card"
            aria-pressed={service === item.id} disabled={busy} onClick={() => changeService(item.id)}>
            <strong>{item.label}</strong><span>{item.detail}</span></button>)}
        </div>
        <div className="consult-photo-block">
          <h3>Your {service === "nails" ? "hand photo" : "portrait"}</h3>
          <input ref={inputRef} className="sr-only" type="file" accept="image/jpeg,image/png"
            aria-label="Upload consultation photo" onChange={onFileChange} disabled={busy} />
          {preview ? <div className="consult-photo-preview"><StudioPhoto src={preview} alt="Consultation photo preview" /></div>
            : <button type="button" className="studio-upload consult-upload" onClick={() => inputRef.current?.click()}>
              <span className="studio-upload-icon" aria-hidden="true">↑</span><strong>Choose one photo</strong>
              <small>JPG or PNG, up to 8 MB. Reused for all three looks.</small></button>}
          {file && <div className="studio-file-row"><strong>{file.name}</strong><button type="button" className="studio-text-button"
            disabled={busy} onClick={() => inputRef.current?.click()}>Replace</button></div>}
        </div>
      </StudioPanel>
      <StudioPanel id="consult-preferences" number="02" title="Tell us your direction" detail="A few answers help narrow the supported styles.">
        <div className="consult-fields">
          <label>Occasion or event<input value={occasion} maxLength={80} disabled={busy} onChange={(event) => setOccasion(event.target.value)} placeholder="Everyday, celebration, formal…" /></label>
          <label>Desired vibe<input value={vibe} maxLength={80} disabled={busy} onChange={(event) => setVibe(event.target.value)} placeholder="Soft, bold, classic…" /></label>
          <label>{service === "hairstyle" ? "Maintenance preference" : service === "makeup" ? "Makeup intensity" : "Nail finish"}
            <select value={servicePreference} disabled={busy} onChange={(event) => setServicePreference(event.target.value)}>
              <option value="">No preference</option>
              {(service === "hairstyle" ? ["low", "medium", "high"] : service === "makeup" ? ["natural", "soft", "bold"] : ["glossy", "matte", "ombre", "french"])
                .map((option) => <option key={option} value={option}>{option.charAt(0).toUpperCase() + option.slice(1)}</option>)}
            </select></label>
          <label>Anything to avoid? <small>(comma separated)</small><input value={avoids} maxLength={160} disabled={busy}
            onChange={(event) => setAvoids(event.target.value)} placeholder="For example, high maintenance" /></label>
          <label>Optional notes<textarea value={notes} maxLength={500} disabled={busy} rows={3}
            onChange={(event) => setNotes(event.target.value)} placeholder="What else should we consider?" /></label>
        </div>
        <p className="studio-tip"><strong>For this preview</strong><br />Recommendations come from supported styles and configured demo estimates. No appointment or real salon price is being offered.</p>
      </StudioPanel>
    </div>
    <section className="studio-action-bar" aria-label="Start consultation"><div><small>03 / EXPLORE THREE LOOKS</small>
      <h2>Ready for your recommendations?</h2><p>Looks generate one at a time. Nails may take longer.</p></div>
      <div className="consult-actions"><Link className="studio-secondary-button" href={serviceInfo.href}
        onClick={() => { if (file) rememberCustomPhoto(service, file); }}>Custom {serviceInfo.label}</Link>
        <button type="button" className="studio-primary-button" disabled={!file || busy} onClick={() => void start()}>
          {phase === "preparing" ? "Preparing…" : busy ? "Generating looks…" : cards.length ? "Start a new consultation" : "Find my looks"} ✦</button></div>
    </section>
    {error && <p role="alert" className="studio-alert">{error}</p>}
    {phase === "preparing" && <p role="status" className="consult-progress"><span className="consult-spinner" />Preparing your recommendations…</p>}
    {cards.length > 0 && <section className="consult-results" aria-label="Your three recommendations">
      <div className="consult-results-heading"><div><p className="studio-eyebrow">YOUR PERSONALIZED EDIT</p><h2>Three looks to explore</h2></div>
        <p>One result completes before the next begins. Select the look you like best.</p></div>
      <div className="consult-card-grid">{cards.map((card, index) => <article key={card.recommendation.id} className="consult-card"
        aria-label={`Recommendation ${index + 1}: ${card.recommendation.primary.style_name}`}>
        <div className="consult-card-visual">{card.result ? <StudioPhoto src={card.result.image.data_url}
          alt={`Generated ${card.recommendation.primary.style_name} preview`} />
          : <div className="consult-card-placeholder">{card.status === "generating" && <span className="consult-spinner" />}
            <span>{card.status === "pending" ? "Waiting for this look" : card.status === "generating" ? "Generating this look…" : card.status === "unknown" ? "Checking request status" : "Preview unavailable"}</span></div>}</div>
        <div className="consult-card-body"><div className="consult-card-top"><span>LOOK {index + 1}</span><span className={`consult-status consult-status-${card.status}`}>{card.status}</span></div>
          <h3>{card.recommendation.primary.style_name}</h3><p>{card.recommendation.reason}</p>
          <p className="consult-estimate">Estimated ₱{card.recommendation.primary.service.estimated_price.toLocaleString()} · {card.recommendation.primary.service.estimated_duration_minutes} min <small>(demo estimate)</small></p>
          {card.recommendation.complements.length > 0 && <p className="consult-complements">Pairs with {card.recommendation.complements.map((item) => item.style_name).join(", ")}. Visuals are not generated for complementary services.</p>}
          {card.error && <p role="alert" className="consult-card-error">{card.error}</p>}
          <div className="consult-card-actions">{card.status === "completed" && <><button type="button" className="studio-primary-button"
            onClick={() => void select(card)}>{selectedId === card.recommendation.id ? "Selected" : "Select this look"}</button>
            <a className="studio-secondary-button" href={card.result!.image.data_url} download={`andreas-${card.recommendation.primary.style_id}.${card.result!.image.content_type === "image/jpeg" ? "jpg" : "png"}`}>Download</a></>}
            {card.canRetry && <button type="button" className="studio-secondary-button" disabled={busy}
              onClick={() => void retry(card)}>Retry this look</button>}
            {card.status === "unknown" && <button type="button" className="studio-secondary-button"
              onClick={() => void checkStatus(card)}>Check status</button>}</div>
        </div>
      </article>)}</div>
      {phase === "attention" && cards.some((card) => card.status === "pending") && !cards.some((card) => card.status === "unknown")
        && <button type="button" className="studio-secondary-button consult-continue" onClick={() => void continuePending()}>Continue remaining looks</button>}
    </section>}
    {selected && <section className="consult-selection" aria-label="Selected recommendation"><p className="studio-eyebrow">YOUR SELECTED LOOK</p>
      <h2>{selected.recommendation.primary.style_name}</h2><p>Saved to this consultation for the current session. The estimate is for demonstration only; no booking has been made.</p>
      <p>{selected.recommendation.primary.service.name} · ₱{selected.recommendation.primary.service.estimated_price.toLocaleString()} · {selected.recommendation.primary.service.estimated_duration_minutes} min</p>
      {selected.recommendation.complements.length > 0 && <p>Suggested complements: {selected.recommendation.complements.map((item) => item.style_name).join(", ")}</p>}
    </section>}
  </StudioShell>;
}
