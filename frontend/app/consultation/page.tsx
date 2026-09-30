"use client";

import Link from "next/link";
import { type ChangeEvent, useEffect, useRef, useState } from "react";

import { StudioPhoto, StudioShell } from "@/components/ai-studio";
import type { FeatureId, GenerateResponse } from "@/lib/api";
import { createConsultation, generateRecommendation, getConsultationMode, getGenerationDetail, recommendConsultation,
  sendConsultationTurn,
  selectRecommendation, updateConsultation, uploadConsultationPhoto,
  type GenerationDetail, type Preferences, type Recommendation } from "@/lib/consultation-api";
import { rememberCustomPhoto } from "@/lib/photo-handoff";

type CardStatus = "pending" | "generating" | "completed" | "failed" | "unknown";
type Card = { recommendation: Recommendation; status: CardStatus; result: GenerateResponse | null;
  error: string; canRetry: boolean };
type Phase = "setup" | "preparing" | "generating" | "ready" | "attention";
type Step = 1 | 2 | 3;

const SERVICES: { id: FeatureId; label: string; detail: string; href: string }[] = [
  { id: "hairstyle", label: "Hairstyle", detail: "A cut or shape for your next look", href: "/" },
  { id: "makeup", label: "Makeup", detail: "A finish for your portrait", href: "/makeup" },
  { id: "nails", label: "Nails", detail: "A polished hand look", href: "/nails" },
];
const MAX_BYTES = 8 * 1024 * 1024;
const wait = (milliseconds: number) => new Promise((resolve) => setTimeout(resolve, milliseconds));

export default function ConsultationPage() {
  const [service, setService] = useState<FeatureId | null>(null);
  const [step, setStep] = useState<Step>(1);
  const [activeLookId, setActiveLookId] = useState("");
  const [showMorePreferences, setShowMorePreferences] = useState(false);
  const [dragging, setDragging] = useState(false);
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
  const [providerMode, setProviderMode] = useState<"loading" | "deterministic" | "gemini">("loading");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<{ role: "user" | "assistant"; content: string }[]>([]);
  const [conversationReady, setConversationReady] = useState(false);
  const [phase, setPhase] = useState<Phase>("setup");
  const [consultationId, setConsultationId] = useState("");
  const [cards, setCards] = useState<Card[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => () => { if (previewRef.current) URL.revokeObjectURL(previewRef.current); }, []);

  useEffect(() => {
    let active = true;
    getConsultationMode().then((mode) => { if (active) setProviderMode(mode.provider); })
      .catch(() => { if (active) setError("Consultation mode is unavailable. Check the backend and reload."); });
    return () => { active = false; };
  }, []);

  function acceptFile(chosen?: File) {
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
    setActiveLookId("");
    setPhase("setup");
    setConsultationId(""); setChatMessages([]); setChatInput(""); setConversationReady(false);
    setError("");
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    acceptFile(event.target.files?.[0]);
    event.target.value = "";
  }

  function changeService(next: FeatureId) {
    setService(next);
    setServicePreference("");
    setCards([]);
    setSelectedId("");
    setActiveLookId("");
    setPhase("setup");
    setConsultationId(""); setChatMessages([]); setChatInput(""); setConversationReady(false);
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
      setActiveLookId((current) => current || id);
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
    if (!file || !service || running.current) return;
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
      setActiveLookId(set.recommendations[0].id);
      setConversationReady(true);
      setPhase("setup");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Consultation could not start. Please try again.");
      setPhase("setup");
    } finally { running.current = false; }
  }

  async function beginConversation() {
    if (!file || !service || running.current || providerMode !== "gemini") return;
    running.current = true;
    setError(""); setPhase("preparing"); setCards([]); setSelectedId("");
    try {
      const created = await createConsultation(service);
      setConsultationId(created.id);
      await uploadConsultationPhoto(created.id, file);
      const first = await sendConsultationTurn(created.id);
      setChatMessages((first.state.messages || []).map(({ role, content }) => ({ role, content })));
      setPhase("setup");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The AI consultant could not start.");
      setPhase("setup");
    } finally { running.current = false; }
  }

  async function retryOpeningQuestion() {
    if (!consultationId || running.current || chatMessages.length) return;
    running.current = true;
    setError(""); setPhase("preparing");
    try {
      const first = await sendConsultationTurn(consultationId);
      setChatMessages((first.state.messages || []).map(({ role, content }) => ({ role, content })));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The AI consultant could not respond.");
    } finally { setPhase("setup"); running.current = false; }
  }

  async function replyToConsultant() {
    const message = chatInput.trim();
    if (!message || !consultationId || running.current || providerMode !== "gemini") return;
    running.current = true;
    setError(""); setPhase("preparing");
    try {
      const turn = await sendConsultationTurn(consultationId, message);
      setChatInput("");
      setChatMessages((turn.state.messages || []).map(({ role, content }) => ({ role, content })));
      if (turn.status === "ready_for_recommendation" && turn.recommendations) {
        setConversationReady(true);
        setCards(turn.recommendations.recommendations.map((recommendation) => ({ recommendation,
          status: "pending", result: null, error: "", canRetry: false })));
        setActiveLookId(turn.recommendations.recommendations[0].id);
        setPhase("setup");
      } else setPhase("setup");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The AI consultant could not respond.");
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

  async function generateLooks() {
    if (!consultationId || running.current || cards.length !== 3 || cards.some((card) => card.status !== "pending")) return;
    running.current = true;
    try { await generatePending(consultationId, cards.map((card) => card.recommendation)); }
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

  const serviceInfo = SERVICES.find((item) => item.id === service);
  const busy = phase === "preparing" || phase === "generating";
  const selected = cards.find((card) => card.recommendation.id === selectedId);
  const activeCard = cards.find((card) => card.recommendation.id === activeLookId) || cards[0];
  const activeIndex = cards.findIndex((card) => card.recommendation.id === activeCard?.recommendation.id);
  const lastQuestion = [...chatMessages].reverse().find((item) => item.role === "assistant")?.content || "";
  const quickReplies = /maintenance|easy to maintain/i.test(lastQuestion) ? ["Easy to maintain", "Some styling is fine", "No preference"]
    : /intensity|natural|soft|bold/i.test(lastQuestion) ? ["Natural and subtle", "Soft and polished", "Bold and expressive"]
    : /color|finish/i.test(lastQuestion) ? ["Dark and glossy", "Soft and natural", "No preference"]
    : /occasion|getting ready|event/i.test(lastQuestion) ? ["Everyday", "Special event", "Graduation"] : [];
  const customLink = serviceInfo && <Link className="consult-custom-link" href={serviceInfo.href}
    onClick={() => { if (file) rememberCustomPhoto(serviceInfo.id, file); }}>Prefer to choose yourself? <strong>Custom {serviceInfo.label} <span aria-hidden="true">↗</span></strong></Link>;

  return <StudioShell feature="consultation" eyebrow="A PERSONAL BEAUTY EXPERIENCE" title="Find a look" emphasis="made for you."
    description="One service. One photo. Three directions chosen around what you love."
    badge={providerMode === "gemini" ? "AI beauty consultation" : "Guided consultation preview"}>
    <nav className="consult-steps" aria-label="Consultation progress">
      {([1, 2, 3] as const).map((number) => <div key={number} className={`consult-step ${number === step ? "is-current" : number < step ? "is-complete" : ""}`}
        aria-current={number === step ? "step" : undefined}>
        <span className="consult-step-number">{number < step ? "✓" : `0${number}`}</span>
        <span>{number === 1 ? "Service" : number === 2 ? "Direction" : "Your Looks"}</span>
      </div>)}
    </nav>
    {error && <p role="alert" className="studio-alert">{error}</p>}

    {step === 1 && <section key="service" className="consult-stage consult-service-stage" aria-labelledby="consult-service-title">
      <div className="consult-stage-heading"><span className="studio-eyebrow">01 / CHOOSE A SERVICE</span>
        <h2 id="consult-service-title">Where shall we begin?</h2>
        <p>Choose the experience you want to explore today.</p></div>
      <div className="consult-service-grid" role="group" aria-label="Choose service">
        {SERVICES.map((item, index) => <button key={item.id} type="button" className={`consult-service-card consult-service-${item.id}`}
          aria-label={`${item.label} — ${item.detail}`} aria-pressed={service === item.id} onClick={() => changeService(item.id)}>
          <span className="consult-service-art" aria-hidden="true"><span>{index === 0 ? "✦" : index === 1 ? "◐" : "◇"}</span></span>
          <span className="consult-service-copy"><small>0{index + 1} / BEAUTY SERVICE</small><strong>{item.label}</strong><span>{item.detail}</span></span>
          <span className="consult-service-arrow" aria-hidden="true">↗</span>
        </button>)}
      </div>
      <div className="consult-stage-footer"><p>{service ? `${serviceInfo?.label} selected` : "Select one service to continue."}</p>
        <button type="button" className="studio-primary-button" disabled={!service}
          onClick={() => setStep(2)}>Continue <span aria-hidden="true">→</span></button></div>
      {service && <div className="consult-custom-row">{customLink}</div>}
    </section>}

    {step === 2 && <section key="direction" className="consult-stage" aria-labelledby="consult-direction-title">
      <div className="consult-stage-heading"><span className="studio-eyebrow">02 / TELL US YOUR DIRECTION</span>
        <h2 id="consult-direction-title">Tell us what feels like you.</h2>
        <p>{providerMode === "gemini" ? "A short conversation helps us find styles that fit your plans." : "A few thoughtful choices are enough to get started."}</p></div>
      <div className="consult-direction-layout">
        <div className="consult-direction-panel">
          {providerMode === "loading" ? <p role="status" className="consult-waiting"><span className="consult-spinner" />Connecting to your consultation…</p>
          : providerMode === "gemini" ? <div className="consult-conversation">
            {chatMessages.length === 0 ? <div className="consult-chat-intro"><span aria-hidden="true">✦</span>
              <h3>A conversation about your look</h3><p>Start when your photo is ready. The consultant will ask a few useful questions.</p></div>
              : <div className="consult-chat-log" role="log" aria-label="Consultation conversation" aria-live="polite">
                {chatMessages.map((item, index) => <p key={index} className={`consult-chat-message consult-chat-${item.role}`}>
                  <strong>{item.role === "assistant" ? "AI consultant" : "You"}</strong><span>{item.content}</span></p>)}
              </div>}
            {phase === "preparing" && <p role="status" className="consult-waiting"><span className="consult-spinner" />Waiting for the consultant…</p>}
            {consultationId && chatMessages.length === 0 && !busy && <button type="button" className="studio-secondary-button"
              onClick={() => void retryOpeningQuestion()}>Retry opening question</button>}
            {!consultationId && <button type="button" className="studio-primary-button" disabled={!file || busy}
              onClick={() => void beginConversation()}>{busy ? "Starting…" : "Start AI consultation"} <span aria-hidden="true">✦</span></button>}
            {consultationId && !conversationReady && chatMessages.length > 0 && <div className="consult-chat-compose">
              {quickReplies.length > 0 && <div className="consult-quick-replies" aria-label="Suggested replies"><small>Quick replies</small><div>
                {quickReplies.map((reply) => <button key={reply} type="button" className="consult-chip" aria-pressed={chatInput === reply}
                  disabled={busy} onClick={() => setChatInput(reply)}>{reply}</button>)}</div></div>}
              <label htmlFor="consult-reply">Your reply</label>
              <textarea id="consult-reply" value={chatInput} maxLength={500} rows={3} disabled={busy}
                onChange={(event) => setChatInput(event.target.value)}
                onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void replyToConsultant(); } }}
                placeholder="Add your own details or edit a quick reply…" />
              <button type="button" className="studio-primary-button" disabled={!chatInput.trim() || busy}
                onClick={() => void replyToConsultant()}>Send reply <span aria-hidden="true">→</span></button>
            </div>}
          </div> : <div className="consult-fields">
            <fieldset><legend>What are you getting ready for?</legend><div className="consult-chip-row">
              {["Everyday", "Celebration", "Formal"].map((option) => <button key={option} type="button" className="consult-chip" aria-pressed={occasion === option}
                disabled={busy} onClick={() => setOccasion(occasion === option ? "" : option)}>{option}</button>)}</div>
              <label className="consult-field-subtle" htmlFor="consult-occasion">Or describe it</label><input id="consult-occasion" value={occasion} maxLength={80}
                disabled={busy} onChange={(event) => setOccasion(event.target.value)} placeholder="Occasion or event" aria-label="Occasion or event" /></fieldset>
            <fieldset><legend>What mood are you drawn to?</legend><div className="consult-chip-row">
              {["Natural", "Classic", "Bold"].map((option) => <button key={option} type="button" className="consult-chip" aria-pressed={vibe === option}
                disabled={busy} onClick={() => setVibe(vibe === option ? "" : option)}>{option}</button>)}</div>
              <label className="consult-field-subtle" htmlFor="consult-vibe">Or describe it</label><input id="consult-vibe" value={vibe} maxLength={80}
                disabled={busy} onChange={(event) => setVibe(event.target.value)} placeholder="Desired vibe" aria-label="Desired vibe" /></fieldset>
            <fieldset><legend>{service === "hairstyle" ? "Maintenance preference" : service === "makeup" ? "Makeup intensity" : "Nail finish"}</legend>
              <div className="consult-chip-row">{(service === "hairstyle" ? ["low", "medium", "high"] : service === "makeup" ? ["natural", "soft", "bold"] : ["glossy", "matte", "ombre", "french"])
                .map((option) => <button key={option} type="button" className="consult-chip" aria-pressed={servicePreference === option}
                  disabled={busy} onClick={() => setServicePreference(servicePreference === option ? "" : option)}>{option.charAt(0).toUpperCase() + option.slice(1)}</button>)}</div></fieldset>
            <button type="button" className="consult-more-toggle" aria-expanded={showMorePreferences}
              onClick={() => setShowMorePreferences((value) => !value)}>{showMorePreferences ? "Hide optional details" : "Add optional details"} <span aria-hidden="true">{showMorePreferences ? "−" : "+"}</span></button>
            {showMorePreferences && <div className="consult-extra-fields">
              <label>Anything to avoid? <small>(comma separated)</small><input value={avoids} maxLength={160} disabled={busy}
                onChange={(event) => setAvoids(event.target.value)} placeholder="For example, high maintenance" /></label>
              <label>Optional notes<textarea value={notes} maxLength={500} disabled={busy} rows={3}
                onChange={(event) => setNotes(event.target.value)} placeholder="What else should we consider?" /></label>
            </div>}
            {!conversationReady && <button type="button" className="studio-primary-button" disabled={!file || busy}
              onClick={() => void start()}>{busy ? "Preparing…" : "Find my looks"} <span aria-hidden="true">✦</span></button>}
          </div>}
          {conversationReady && cards.length === 3 && <div className="consult-ready" role="status">
            <span className="consult-ready-mark" aria-hidden="true">✦</span><div><h3>We&apos;ve got your direction.</h3>
              <p>Three supported looks are ready for you to explore.</p></div>
            <button type="button" className="studio-primary-button" onClick={() => setStep(3)}>Explore My Looks <span aria-hidden="true">→</span></button>
          </div>}
        </div>
        <aside className="consult-photo-panel" aria-label="Your consultation photo">
          <div className="consult-photo-label"><span>YOUR {service === "nails" ? "HAND PHOTO" : "PORTRAIT"}</span><span>01 PHOTO · 03 LOOKS</span></div>
          <input ref={inputRef} className="sr-only" type="file" accept="image/jpeg,image/png"
            aria-label="Upload consultation photo" onChange={onFileChange} disabled={busy} />
          {preview ? <div className="consult-photo-preview"><StudioPhoto src={preview} alt="Consultation photo preview" /></div>
            : <button type="button" className={`studio-upload consult-upload ${dragging ? "is-dragging" : ""}`}
              onClick={() => inputRef.current?.click()}
              onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => { event.preventDefault(); setDragging(false); acceptFile(event.dataTransfer.files[0]); }}>
              <span className="studio-upload-icon" aria-hidden="true">↑</span><strong>Bring your photo in</strong>
              <small>Choose or drop a JPG or PNG, up to 8 MB.</small></button>}
          {file && <div className="studio-file-row"><strong>{file.name}</strong><button type="button" className="studio-text-button"
            disabled={busy} onClick={() => inputRef.current?.click()}>Change photo</button></div>}
          <p className="consult-photo-note">One photo is reused for all three results. Your photo is not sent to the conversational AI.</p>
        </aside>
      </div>
      <div className="consult-stage-footer"><button type="button" className="studio-secondary-button" disabled={busy || !!consultationId}
        onClick={() => setStep(1)}>Back to services</button>{customLink}</div>
    </section>}

    {step === 3 && <section key="looks" className="consult-stage" aria-labelledby="consult-looks-title">
      <div className="consult-stage-heading"><span className="studio-eyebrow">03 / EXPLORE YOUR LOOKS</span>
        <h2 id="consult-looks-title">Three looks, your direction.</h2>
        <p>They&apos;ll be generated one at a time. Nails can take longer; keep this page open.</p></div>
      {cards.length === 3 && cards.every((card) => card.status === "pending") && <div className="consult-generate-intro">
        <div><strong>Your recommendations are ready.</strong><p>Generate three visual previews using your uploaded photo. Each look begins after the previous one finishes.</p></div>
        <button type="button" className="studio-primary-button" disabled={busy} onClick={() => void generateLooks()}>Generate My Looks <span aria-hidden="true">✦</span></button>
      </div>}
      {cards.length > 0 && <div className="consult-look-layout">
        {activeCard && <div className={`consult-featured-look ${activeCard.status === "completed" ? "has-result" : ""}`} aria-label="Featured look">
          <div className="consult-featured-visual">{activeCard.result ? <StudioPhoto src={activeCard.result.image.data_url}
            alt={`Generated ${activeCard.recommendation.primary.style_name} preview`} />
            : <div className="consult-card-placeholder">{activeCard.status === "generating" && <span className="consult-spinner" />}
              <span>{activeCard.status === "pending" ? "Your preview is up next" : activeCard.status === "generating" ? "Creating this look…" : activeCard.status === "unknown" ? "Checking request status" : "Preview unavailable"}</span></div>}
            <span className="consult-featured-index">LOOK 0{activeIndex + 1} / 03</span></div>
          <div className="consult-featured-copy"><div className="consult-card-top"><span>YOUR PERSONALIZED EDIT</span><span className={`consult-status consult-status-${activeCard.status}`}>{activeCard.status === "pending" ? "Up next" : activeCard.status}</span></div>
            <h3>{activeCard.recommendation.primary.style_name}</h3><p className="consult-reason">{activeCard.recommendation.reason}</p>
            <p className="consult-estimate">Estimated ₱{activeCard.recommendation.primary.service.estimated_price.toLocaleString()} · {activeCard.recommendation.primary.service.estimated_duration_minutes} min <small>(demo estimate)</small></p>
            {activeCard.recommendation.complements.length > 0 && <p className="consult-complements">Pairs with {activeCard.recommendation.complements.map((item) => item.style_name).join(", ")}. Complementary visuals are not generated.</p>}
            {activeCard.error && <p role="alert" className="consult-card-error">{activeCard.error}</p>}
            <div className="consult-card-actions">{activeCard.status === "completed" && <><button type="button" className="studio-primary-button"
              onClick={() => void select(activeCard)}>{selectedId === activeCard.recommendation.id ? "Selected" : "Select This Look"}</button>
              <a className="studio-secondary-button" href={activeCard.result!.image.data_url}
                download={`andreas-${activeCard.recommendation.primary.style_id}.${activeCard.result!.image.content_type === "image/jpeg" ? "jpg" : "png"}`}>Download</a></>}
              {activeCard.canRetry && <button type="button" className="studio-secondary-button" disabled={busy}
                onClick={() => void retry(activeCard)}>Retry this look</button>}
              {activeCard.status === "unknown" && <button type="button" className="studio-secondary-button"
                onClick={() => void checkStatus(activeCard)}>Check status</button>}</div>
          </div>
        </div>}
        <div className="consult-look-list" aria-label="Your three recommendations">{cards.map((card, index) => <article key={card.recommendation.id}
          className={`consult-look-tile ${activeCard?.recommendation.id === card.recommendation.id ? "is-active" : ""}`}
          aria-label={`Recommendation ${index + 1}: ${card.recommendation.primary.style_name}`}>
          <button type="button" className="consult-look-switch" aria-pressed={activeCard?.recommendation.id === card.recommendation.id}
            onClick={() => setActiveLookId(card.recommendation.id)} aria-label={`View look ${index + 1}: ${card.recommendation.primary.style_name}`}>
            <span className="consult-look-thumb">{card.result ? <StudioPhoto src={card.result.image.data_url} alt="" /> : <span aria-hidden="true">0{index + 1}</span>}</span>
            <span className="consult-look-summary"><small>LOOK 0{index + 1} · <span className={`consult-status consult-status-${card.status}`}>{card.status === "pending" ? "Up next" : card.status}</span></small>
              <strong>{card.recommendation.primary.style_name}</strong><span>{card.recommendation.reason}</span></span>
            <span className="consult-look-chevron" aria-hidden="true">↗</span>
          </button>
        </article>)}</div>
      </div>}
      {phase === "attention" && cards.some((card) => card.status === "pending") && !cards.some((card) => card.status === "unknown")
        && <button type="button" className="studio-secondary-button consult-continue" onClick={() => void continuePending()}>Continue remaining looks</button>}
      {selected && <section className="consult-selection" aria-label="Selected recommendation"><p className="studio-eyebrow">YOUR SELECTED LOOK</p>
        <h2>{selected.recommendation.primary.style_name}</h2><p>Saved to this consultation for the current session. No booking has been made.</p>
        <p>{selected.recommendation.primary.service.name} · ₱{selected.recommendation.primary.service.estimated_price.toLocaleString()} · {selected.recommendation.primary.service.estimated_duration_minutes} min (demo estimate)</p>
        {selected.recommendation.complements.length > 0 && <p>Suggested complements: {selected.recommendation.complements.map((item) => item.style_name).join(", ")}</p>}
      </section>}
      <div className="consult-stage-footer">{customLink}</div>
    </section>}
  </StudioShell>;
}
