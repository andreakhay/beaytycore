'use client';

import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowLeft, ArrowRight, Camera, Check, CircleAlert, Clock3, Download, Hand, LoaderCircle, MessageCircle, RotateCcw, Scissors, Sparkles, UploadCloud, WandSparkles } from 'lucide-react';
import { AiClientError, createConsultation, generateCustom, generateRecommendation, getGenerationStatus, getMode, getRecommendations, getStyles, selectRecommendation, sendTurn, updatePreferences, uploadPhoto, type AiStyle, type ConsultationView, type FeatureId, type GeneratedResult, type Preferences } from '@/lib/ai/browser-client';
import { applyGenerationDetail, generateOne, generateSequential, initialCards, type LookCard } from '@/lib/ai/consultation-flow';

type Step = 1 | 2 | 3;
const SERVICES = [
  { id: 'hairstyle' as const, name: 'Hairstyle', description: 'Find the shape and style that feels like you.', icon: Scissors },
  { id: 'makeup' as const, name: 'Makeup', description: 'Explore a finish for the moments ahead.', icon: WandSparkles },
  { id: 'nails' as const, name: 'Nails', description: 'Discover color and detail for your hands.', icon: Hand },
];
const AVAILABLE = new Set(['prototype', 'experimental', 'verified', 'available', 'trained_preset']);
const MAX_BYTES = 8 * 1024 * 1024;
const pause = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
const button = 'inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-gold px-7 py-3 text-sm font-semibold text-deep transition hover:bg-gold-hover focus-visible:outline-offset-4 disabled:cursor-not-allowed disabled:opacity-50';
const secondary = 'inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-purple-light/35 px-5 py-2 text-sm text-secondary transition hover:border-gold/60 hover:text-white disabled:opacity-50';
const input = 'min-h-11 w-full rounded-2xl border border-purple-light/25 bg-deep/65 px-4 py-3 text-sm text-white placeholder:text-muted/80 focus:border-gold focus:outline-none';

function Progress({ step }: { step: Step }) {
  return <ol aria-label="Consultation progress" className="grid grid-cols-3 gap-2 rounded-2xl border border-purple-light/15 bg-card/80 p-2 sm:gap-3">
    {(['Service', 'Direction', 'Your Looks'] as const).map((name, index) => {
      const number = index + 1;
      return <li key={name} aria-current={step === number ? 'step' : undefined}
        className={'rounded-xl px-2 py-2 text-center text-[11px] transition-colors sm:px-4 sm:text-sm ' +
          (step === number ? 'bg-surface text-white ring-1 ring-gold/65' : step > number ? 'text-gold' : 'text-muted')}>
        <span className="mr-1 font-semibold">0{number}</span><span className="hidden min-[350px]:inline">{name}</span>
        {step > number && <Check size={12} className="ml-1 inline" aria-label="Completed" />}
      </li>;
    })}
  </ol>;
}

export default function ClientAiConsultationPage() {
  const reducedMotion = useReducedMotion();
  const [step, setStep] = useState<Step>(1);
  const [service, setService] = useState<FeatureId | null>(null);
  const [provider, setProvider] = useState<'loading' | 'gemini' | 'deterministic'>('loading');
  const [handle, setHandle] = useState<string | null>(null);
  const handleRef = useRef<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const previewRef = useRef('');
  const fileInput = useRef<HTMLInputElement>(null);
  const running = useRef(false);
  const sentPreferences = useRef('');
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');
  const [occasion, setOccasion] = useState('');
  const [vibe, setVibe] = useState('');
  const [avoid, setAvoid] = useState('');
  const [notes, setNotes] = useState('');
  const [featureChoice, setFeatureChoice] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [view, setView] = useState<ConsultationView | null>(null);
  const [ready, setReady] = useState(false);
  const [cards, setCards] = useState<LookCard[]>([]);
  const [activeId, setActiveId] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const [custom, setCustom] = useState(false);
  const [styles, setStyles] = useState<AiStyle[]>([]);
  const [customStyle, setCustomStyle] = useState('');
  const [customResult, setCustomResult] = useState<GeneratedResult | null>(null);

  useEffect(() => {
    let mounted = true;
    getMode().then((mode) => { if (mounted) setProvider(mode); })
      .catch(() => { if (mounted) setError('The AI consultation is unavailable. Please try again later.'); });
    return () => { mounted = false; };
  }, []);
  useEffect(() => () => { if (previewRef.current) URL.revokeObjectURL(previewRef.current); }, []);

  function resetConsultation() {
    handleRef.current = null; setHandle(null); setView(null); setReady(false); setCards([]); setActiveId(''); setSelectedId('');
    setCustomResult(null); setCustom(false); sentPreferences.current = '';
  }
  function restart(message = '') {
    resetConsultation(); setStep(1); setService(null); setFile(null); setPreview('');
    setOccasion(''); setVibe(''); setAvoid(''); setNotes(''); setFeatureChoice(''); setChatInput('');
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = ''; setError(message);
  }
  function report(errorValue: unknown) {
    if (errorValue instanceof AiClientError && errorValue.status === 403 && handleRef.current) {
      restart('Your consultation expired or access changed. Please start again.');
      return;
    }
    setError(errorValue instanceof Error ? errorValue.message : 'Something went wrong. Please try again.');
  }
  function acceptFile(chosen?: File) {
    if (!chosen) return;
    if (!['image/jpeg', 'image/png'].includes(chosen.type) || chosen.size < 1 || chosen.size > MAX_BYTES) {
      setError('Choose a JPG or PNG image up to 8 MB.'); return;
    }
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    const url = URL.createObjectURL(chosen);
    previewRef.current = url; setPreview(url); setFile(chosen);
    resetConsultation(); setError('');
  }
  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault(); setDragging(false); acceptFile(event.dataTransfer.files[0]);
  }
  function preferences(): Preferences {
    const value: Preferences = {
      occasion: occasion || undefined, vibe: vibe || undefined,
      avoids: avoid.split(',').map((part) => part.trim()).filter(Boolean).slice(0, 5),
      notes: notes.trim() || undefined,
    };
    if (service === 'hairstyle' && featureChoice) value.hair_maintenance = featureChoice as Preferences['hair_maintenance'];
    if (service === 'makeup' && featureChoice) value.makeup_intensity = featureChoice as Preferences['makeup_intensity'];
    if (service === 'nails' && featureChoice) value.nail_finish = featureChoice as Preferences['nail_finish'];
    return value;
  }
  function preferenceMessage(): string {
    const parts: string[] = [];
    if (occasion) parts.push('Occasion: ' + occasion + '.');
    if (vibe) parts.push('Desired look: ' + vibe + '.');
    if (featureChoice && service === 'hairstyle') parts.push('Maintenance: ' + featureChoice + '.');
    if (featureChoice && service === 'makeup') parts.push('Makeup intensity: ' + featureChoice + '.');
    if (featureChoice && service === 'nails') parts.push('Nail finish: ' + featureChoice + '.');
    if (avoid.trim()) parts.push('Please avoid: ' + avoid.trim() + '.');
    if (notes.trim()) parts.push('Other preferences: ' + notes.trim() + '.');
    return parts.join(' ');
  }
  function setRecommendations(rows: LookCard['recommendation'][]) {
    if (rows.length !== 3) throw new Error('The consultant did not return three looks.');
    setCards(initialCards(rows)); setActiveId(rows[0].id); setReady(true);
  }
  async function locked(work: () => Promise<void>) {
    if (running.current) return;
    running.current = true; setBusy(true); setError('');
    try { await work(); } catch (cause) { report(cause); }
    finally { running.current = false; setBusy(false); }
  }
  async function startConsultation() {
    if (!service || !file || provider === 'loading') return;
    await locked(async () => {
      const created = handle ? { handle } : await createConsultation(service);
      handleRef.current = created.handle;
      if (!handle) setHandle(created.handle);
      const uploaded = await uploadPhoto(created.handle, file);
      setView(uploaded);
      if (provider === 'gemini') {
        const first = await sendTurn(created.handle);
        setView(first.state);
        if (first.status === 'ready_for_recommendation' && first.recommendations)
          setRecommendations(first.recommendations);
      } else {
        const updated = await updatePreferences(created.handle, preferences());
        setView(updated);
        setRecommendations(await getRecommendations(created.handle));
      }
    });
  }
  async function reply() {
    if (!handle || provider !== 'gemini') return;
    const preferenceText = preferenceMessage();
    const extra = preferenceText && preferenceText !== sentPreferences.current ? preferenceText : '';
    const message = [chatInput.trim(), extra].filter(Boolean).join(' ');
    if (!message) { setError('Tell the consultant a little about what you want.'); return; }
    await locked(async () => {
      const turn = await sendTurn(handle, message);
      sentPreferences.current = preferenceText; setChatInput(''); setView(turn.state);
      if (turn.status === 'ready_for_recommendation' && turn.recommendations)
        setRecommendations(turn.recommendations);
    });
  }
  function patch(card: LookCard) {
    setCards((old) => old.map((item) => item.recommendation.id === card.recommendation.id ? card : item));
  }
  function boundary(currentHandle: string) {
    return {
      generate: (id: string) => generateRecommendation(currentHandle, id),
      status: (id: string) => getGenerationStatus(currentHandle, id),
      wait: pause,
    };
  }
  async function generateLooks(rows: LookCard[]) {
    if (!handle || rows.length === 0) return;
    await locked(async () => { await generateSequential(rows, boundary(handle), patch); });
  }
  async function retry(card: LookCard) {
    if (!handle || !card.canRetry) return;
    await locked(async () => { await generateOne(card, boundary(handle), patch); });
  }
  async function checkStatus(card: LookCard) {
    if (!handle) return;
    await locked(async () => {
      const detail = await getGenerationStatus(handle, card.recommendation.id);
      if (detail.generation.status === 'pending')
        patch({ ...card, status: 'failed', error: 'Generation did not start. You can retry this look.', canRetry: true });
      else patch(applyGenerationDetail(card, detail));
    });
  }
  async function chooseLook(card: LookCard) {
    if (!handle || card.status !== 'completed') return;
    await locked(async () => {
      const saved = await selectRecommendation(handle, card.recommendation.id);
      setView(saved); setSelectedId(saved.selected_recommendation_id || '');
    });
  }
  async function openCustom() {
    if (!service || !file) { setError('Add a photo before choosing a custom look.'); return; }
    await locked(async () => {
      const available = (await getStyles(service)).filter((style) => AVAILABLE.has(style.status));
      setStyles(available); setCustomStyle(available[0]?.id || ''); setCustom(true); setCustomResult(null);
    });
  }
  async function makeCustom() {
    if (!service || !file || !customStyle) return;
    await locked(async () => { setCustomResult(await generateCustom(service, file, customStyle)); });
  }

  const selectedService = SERVICES.find((item) => item.id === service);
  const active = cards.find((card) => card.recommendation.id === activeId) || cards[0];
  const pending = cards.filter((card) => card.status === 'pending');
  const uncertain = cards.some((card) => card.status === 'unknown');
  const firstGeneration = cards.length === 3 && cards.every((card) => card.status === 'pending');
  const selected = cards.find((card) => card.recommendation.id === selectedId);
  const messages = view?.messages || [];
  const choiceOptions = service === 'hairstyle' ? ['low', 'medium', 'high']
    : service === 'makeup' ? ['natural', 'soft', 'bold'] : ['glossy', 'matte', 'ombre', 'french'];
  const choiceLabel = service === 'hairstyle' ? 'Maintenance' : service === 'makeup' ? 'Intensity' : 'Finish';
  const entrance = reducedMotion ? {} : {
    initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.24 },
  };

  return <div className="mx-auto max-w-7xl pb-16">
    <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
      <div><p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.26em] text-gold">ANDREA&apos;S • PERSONAL STUDIO</p>
        <h1 className="font-serif text-3xl text-white sm:text-4xl">AI Consultation</h1>
        <p className="mt-2 max-w-xl text-sm text-muted">A few details from you. Three visual directions to explore.</p></div>
      {step > 1 && <button className={secondary} type="button" disabled={busy} onClick={() => {
        if (custom) setCustom(false);
        else if (step === 3) setStep(2);
        else restart();
      }}><ArrowLeft size={16} /> {custom ? 'Back to consultation' : step === 3 ? 'Back to direction' : 'Start over'}</button>}
    </div>
    <Progress step={step} />
    {error && <div role="alert" className="mt-5 flex items-start gap-3 rounded-2xl border border-error/35 bg-error/10 p-4 text-sm text-white">
      <CircleAlert size={18} className="mt-0.5 shrink-0 text-error" /><span>{error}</span></div>}

    {step === 1 && <motion.section {...entrance} className="mt-8" aria-label="Choose a service">
      <div className="mb-7"><p className="text-xs font-semibold uppercase tracking-[0.22em] text-gold">01 — CHOOSE A SERVICE</p>
        <h2 className="mt-3 max-w-2xl font-serif text-3xl text-white sm:text-4xl">Find a look made for you.</h2>
        <p className="mt-3 max-w-xl text-sm text-muted">Start with the beauty service you want to explore. You can choose your own style later, too.</p></div>
      <div className="grid gap-4 md:grid-cols-3">{SERVICES.map(({ id, name, description, icon: Icon }) =>
        <button key={id} type="button" aria-pressed={service === id} onClick={() => {
          if (service !== id) { setService(id); setFeatureChoice(''); resetConsultation(); }
        }} className={'group min-h-56 rounded-3xl border p-7 text-left transition duration-200 hover:-translate-y-1 hover:border-gold/70 focus-visible:outline-offset-4 ' +
          (service === id ? 'border-gold bg-surface shadow-lg shadow-purple/20' : 'border-purple-light/20 bg-card hover:bg-surface/60')}>
          <span className="mb-8 flex h-12 w-12 items-center justify-center rounded-2xl border border-purple-light/25 bg-deep text-gold"><Icon size={24} /></span>
          <span className="block font-serif text-2xl text-white">{name}</span>
          <span className="mt-2 block max-w-xs text-sm leading-relaxed text-muted">{description}</span>
          <span className="mt-5 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-gold">{service === id ? 'Selected' : 'Explore'} <ArrowRight size={14} /></span>
        </button>)}</div>
      <div className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-purple-light/15 bg-card/70 px-6 py-5">
        <p className="text-sm text-muted">{selectedService ? selectedService.name + ' selected' : 'Select one service to continue.'}</p>
        <button className={button} type="button" disabled={!service} onClick={() => setStep(2)}>Continue <ArrowRight size={17} /></button></div>
    </motion.section>}

    {step === 2 && !custom && <motion.section {...entrance} className="mt-8" aria-label="Tell us your direction">
      <div className="mb-6"><p className="text-xs font-semibold uppercase tracking-[0.22em] text-gold">02 — TELL US YOUR DIRECTION</p>
        <h2 className="mt-2 font-serif text-3xl text-white">Your look begins with you.</h2>
        <p className="mt-2 text-sm text-muted">Add one photo, then tell our consultant what matters to you.</p></div>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
        <div className="order-2 space-y-5 lg:order-1">
          <div className="rounded-3xl border border-purple-light/20 bg-card p-5 sm:p-7">
            <div className="mb-5 flex items-center gap-3"><MessageCircle size={19} className="text-gold" />
              <h3 className="font-serif text-xl text-white">A little about your direction</h3></div>
            <p className="mb-5 text-sm text-muted">Pick what feels right. You can also explain it in your own words.</p>
            <div className="space-y-5">
              <fieldset><legend className="mb-2 text-xs font-semibold uppercase tracking-wider text-secondary">Occasion</legend>
                <div className="flex flex-wrap gap-2">{['Everyday', 'Graduation', 'Special event'].map((value) =>
                  <button key={value} type="button" aria-pressed={occasion === value} onClick={() => setOccasion(value)}
                    className={secondary + (occasion === value ? ' border-gold bg-gold/10 text-white' : '')}>{value}</button>)}</div></fieldset>
              <fieldset><legend className="mb-2 text-xs font-semibold uppercase tracking-wider text-secondary">Desired vibe</legend>
                <div className="flex flex-wrap gap-2">{['Natural', 'Classic', 'Bold'].map((value) =>
                  <button key={value} type="button" aria-pressed={vibe === value} onClick={() => setVibe(value)}
                    className={secondary + (vibe === value ? ' border-gold bg-gold/10 text-white' : '')}>{value}</button>)}</div></fieldset>
              <fieldset><legend className="mb-2 text-xs font-semibold uppercase tracking-wider text-secondary">{choiceLabel}</legend>
                <div className="flex flex-wrap gap-2">{choiceOptions.map((value) =>
                  <button key={value} type="button" aria-pressed={featureChoice === value} onClick={() => setFeatureChoice(value)}
                    className={secondary + (featureChoice === value ? ' border-gold bg-gold/10 text-white' : '')}>{value}</button>)}</div></fieldset>
              <div className="grid gap-4 sm:grid-cols-2"><label className="text-xs text-secondary">Things to avoid
                <input className={input + ' mt-2'} value={avoid} onChange={(event) => setAvoid(event.target.value)}
                  placeholder="e.g. dramatic colors" maxLength={160} /></label>
                <label className="text-xs text-secondary">Anything else?
                  <input className={input + ' mt-2'} value={notes} onChange={(event) => setNotes(event.target.value)}
                    placeholder="What should we know?" maxLength={500} /></label></div>
            </div>
            {!handle && <div className="mt-7 flex flex-wrap items-center gap-3">
              <button className={button} type="button" disabled={!file || provider === 'loading' || busy}
                onClick={() => void startConsultation()}>{busy ? <LoaderCircle size={17} className="animate-spin" /> : <Sparkles size={17} />}
                {provider === 'gemini' ? 'Start my consultation' : 'Find my directions'}</button>
              <span className="text-xs text-muted">Your photo stays temporary.</span></div>}
          </div>
          {provider === 'gemini' && handle && <div className="rounded-3xl border border-purple-light/20 bg-card p-5 sm:p-7" aria-label="AI conversation">
            <h3 className="mb-5 font-serif text-xl text-white">Your conversation</h3>
            <div aria-live="polite" className="max-h-80 space-y-3 overflow-y-auto pr-1">
              {messages.length === 0 && <p className="text-sm text-muted">The consultant is preparing your first question.</p>}
              {messages.map((message, index) => <div key={index}
                className={'max-w-[95%] rounded-2xl p-3 text-sm leading-relaxed transition ' +
                  (message.role === 'assistant' ? 'mr-auto border border-purple-light/20 bg-surface/60 text-white' : 'ml-auto bg-gold/15 text-secondary')}>
                <span className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-gold">{message.role === 'assistant' ? 'Consultant' : 'You'}</span>
                {message.content}</div>)}
              {busy && <p role="status" className="flex items-center gap-2 text-sm text-muted"><LoaderCircle size={15} className="animate-spin" /> Waiting for your consultant…</p>}
            </div>
            {!ready && <form className="mt-5 flex flex-col gap-3 sm:flex-row" onSubmit={(event) => { event.preventDefault(); void reply(); }}>
              <label className="sr-only" htmlFor="consultation-answer">Your answer</label>
              <input id="consultation-answer" className={input} value={chatInput} onChange={(event) => setChatInput(event.target.value)}
                placeholder="Tell us in your own words…" maxLength={500} disabled={busy} />
              <button type="submit" className={button} disabled={busy}>Send <ArrowRight size={16} /></button>
            </form>}
          </div>}
          {ready && cards.length === 3 && <div role="status" className="rounded-3xl border border-gold/35 bg-gold/10 p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">YOUR DIRECTION IS READY</p>
            <h3 className="mt-3 font-serif text-2xl text-white">Ready to explore your looks?</h3>
            <p className="mt-2 text-sm text-secondary">Three supported styles have been selected for you. You decide when to generate them.</p>
            <button className={button + ' mt-5'} type="button" onClick={() => setStep(3)}>Explore My Looks <ArrowRight size={17} /></button>
          </div>}
          {file && <button type="button" className={secondary} onClick={() => void openCustom()} disabled={busy}>Prefer to choose yourself? Custom {selectedService?.name}</button>}
        </div>
        <div className="order-1 lg:order-2 lg:sticky lg:top-6">
          <div className="overflow-hidden rounded-3xl border border-purple-light/20 bg-card">
            <div className="flex items-center justify-between border-b border-purple-light/15 px-5 py-4">
              <span className="text-xs font-semibold uppercase tracking-widest text-secondary">Your photo</span>
              {file && <button className="text-xs font-medium text-gold hover:underline" type="button" onClick={() => fileInput.current?.click()}>Change photo</button>}
            </div>
            <input ref={fileInput} type="file" accept="image/jpeg,image/png" className="sr-only"
              onChange={(event: ChangeEvent<HTMLInputElement>) => { acceptFile(event.target.files?.[0]); event.target.value = ''; }} />
            {preview ? <div className="relative aspect-[4/5] bg-deep"><motion.img src={preview} alt="Your uploaded photo" className="h-full w-full object-contain"
              initial={reducedMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }} /></div>
              : <div role="button" tabIndex={0} onClick={() => fileInput.current?.click()}
                  onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') fileInput.current?.click(); }}
                  onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)} onDrop={onDrop}
                  className={'flex aspect-[4/5] cursor-pointer flex-col items-center justify-center gap-3 border-2 border-dashed p-8 text-center transition ' +
                    (dragging ? 'border-gold bg-gold/10' : 'border-transparent hover:bg-surface/40')}>
                  <UploadCloud size={34} className="text-gold" /><span className="font-serif text-lg text-white">Upload a photo</span>
                  <span className="max-w-xs text-sm text-muted">Drag a JPG or PNG here, or choose a file. Maximum 8 MB.</span>
                  <span className={secondary}>Choose photo</span></div>}
            {file && <p className="truncate px-5 py-3 text-xs text-muted">{file.name} · {Math.ceil(file.size / 1024)} KB</p>}
          </div>
        </div>
      </div>
    </motion.section>}
    {step === 3 && !custom && <motion.section {...entrance} className="mt-8" aria-label="Explore your looks">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4"><div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-gold">03 — EXPLORE YOUR LOOKS</p>
        <h2 className="mt-2 font-serif text-3xl text-white">Three directions. Your choice.</h2>
        <p className="mt-2 text-sm text-muted">Looks generate one at a time. Nails may take longer; keep this page open.</p></div>
        {firstGeneration && <button className={button} type="button" disabled={busy} onClick={() => void generateLooks(cards)}>
          <Sparkles size={17} /> Generate My Looks</button>}</div>
      {active && <div className="grid overflow-hidden rounded-3xl border border-purple-light/25 bg-card lg:grid-cols-[minmax(0,1.1fr)_minmax(300px,0.9fr)]">
        <div className="relative flex min-h-[320px] items-center justify-center bg-deep sm:min-h-[480px]">
          {active.result ? <motion.img key={active.recommendation.id} src={active.result.image.data_url} alt={'Generated ' + active.recommendation.primary.style_name}
            className="max-h-[560px] w-full object-contain" initial={reducedMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }} />
            : <div className="flex flex-col items-center gap-4 p-8 text-center">
              {active.status === 'generating' ? <LoaderCircle size={36} className="animate-spin text-gold" /> : <Camera size={36} className="text-muted" />}
              <p className="font-serif text-xl text-white">{active.status === 'generating' ? 'Creating this look…' :
                active.status === 'pending' ? 'Your preview is up next' : active.status === 'unknown' ? 'Checking its status' : 'Preview unavailable'}</p>
              <p className="text-sm text-muted">Look 0{cards.indexOf(active) + 1} of 03</p></div>}
        </div>
        <div className="flex flex-col justify-between gap-8 p-6 sm:p-8">
          <div><div className="flex items-center justify-between gap-3 text-xs uppercase tracking-widest text-gold">
            <span>PERSONALIZED DIRECTION</span><span>{active.status}</span></div>
            <h3 className="mt-5 font-serif text-3xl text-white">{active.recommendation.primary.style_name}</h3>
            <p className="mt-4 text-sm leading-relaxed text-secondary">{active.recommendation.reason}</p>
            <div className="mt-7 flex flex-wrap items-center gap-4 border-t border-purple-light/15 pt-5 text-sm text-muted">
              <span>Demo estimate: ₱{active.recommendation.primary.service.estimated_price.toLocaleString('en-PH')}</span>
              <span className="inline-flex items-center gap-1"><Clock3 size={15} /> {active.recommendation.primary.service.estimated_duration_minutes} min</span></div>
            {active.recommendation.complements.length > 0 && <p className="mt-5 text-xs text-muted">
              Pairs with {active.recommendation.complements.map((item) => item.style_name).join(', ')}. Complementary visuals are not generated.</p>}
            {active.error && <p role="alert" className="mt-5 rounded-xl bg-error/10 p-3 text-sm text-secondary">{active.error}</p>}</div>
          <div className="flex flex-wrap gap-3">
            {active.status === 'completed' && <><button className={button} type="button" disabled={busy} onClick={() => void chooseLook(active)}>
              {selectedId === active.recommendation.id ? 'Selected' : 'Select This Look'} <Check size={17} /></button>
              <a className={secondary} href={active.result!.image.data_url}
                download={'andreas-' + active.recommendation.primary.style_id +
                  (active.result!.image.content_type === 'image/jpeg' ? '.jpg' : '.png')}>
                <Download size={16} /> Download</a></>}
            {active.canRetry && <button className={secondary} type="button" disabled={busy} onClick={() => void retry(active)}><RotateCcw size={15} /> Retry this look</button>}
            {active.status === 'unknown' && <button className={secondary} type="button" disabled={busy} onClick={() => void checkStatus(active)}>Check status</button>}
          </div>
        </div>
      </div>}
      <div className="mt-5 grid gap-3 sm:grid-cols-3" aria-live="polite" aria-label="Recommendation cards">{cards.map((card, index) =>
        <button key={card.recommendation.id} type="button" aria-pressed={active?.recommendation.id === card.recommendation.id}
          onClick={() => setActiveId(card.recommendation.id)}
          className={'flex min-h-28 items-center gap-4 rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 ' +
            (active?.recommendation.id === card.recommendation.id ? 'border-gold bg-surface' : 'border-purple-light/20 bg-card')}>
          <span className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-deep">
            {card.result ? <img src={card.result.image.data_url} alt="" className="h-full w-full object-cover" />
              : card.status === 'generating' ? <LoaderCircle size={19} className="animate-spin text-gold" /> : <span className="text-lg text-gold">0{index + 1}</span>}</span>
          <span className="min-w-0"><span className="block truncate text-sm font-semibold text-white">{card.recommendation.primary.style_name}</span>
            <span className="mt-1 block text-xs capitalize text-muted">{card.status === 'pending' ? 'Up next' : card.status}</span></span>
        </button>)}</div>
      {pending.length > 0 && !firstGeneration && <button className={secondary + ' mt-6'} type="button" disabled={busy || uncertain}
        onClick={() => void generateLooks(pending)}>Continue with remaining looks <ArrowRight size={16} /></button>}
      {selected && <div role="status" className="mt-6 rounded-2xl border border-gold/35 bg-gold/10 p-5 text-sm text-secondary">
        <strong className="block font-serif text-lg text-white">{selected.recommendation.primary.style_name} selected</strong>
        Saved for this temporary consultation. No appointment has been made; BeautyCore booking prices remain separate.</div>}
      <button type="button" className={secondary + ' mt-7'} disabled={busy} onClick={() => void openCustom()}>
        Prefer to choose yourself? Custom {selectedService?.name} <ArrowRight size={16} /></button>
    </motion.section>}
    {custom && <motion.section {...entrance} className="mt-8" aria-label={'Custom ' + selectedService?.name}>
      <div className="mb-6"><p className="text-xs font-semibold uppercase tracking-[0.22em] text-gold">CUSTOM STUDIO</p>
        <h2 className="mt-2 font-serif text-3xl text-white">Choose your own {selectedService?.name.toLowerCase()} style.</h2>
        <p className="mt-2 text-sm text-muted">Use your uploaded photo. This stays inside your Client portal.</p></div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-3xl border border-purple-light/20 bg-card p-5 sm:p-7">
          <h3 className="mb-4 font-serif text-xl text-white">Available styles</h3>
          <div className="grid gap-2 sm:grid-cols-2">{styles.map((style) =>
            <button key={style.id} type="button" aria-pressed={customStyle === style.id}
              onClick={() => { setCustomStyle(style.id); setCustomResult(null); }}
              className={'rounded-2xl border p-4 text-left transition ' +
                (customStyle === style.id ? 'border-gold bg-gold/10' : 'border-purple-light/20 bg-deep/40 hover:border-gold/50')}>
              <span className="block font-semibold text-white">{style.name}</span><span className="mt-1 block text-xs text-muted">{style.description}</span></button>)}</div>
          {styles.length === 0 && <p className="text-sm text-muted">No available styles for this service.</p>}
          <button className={button + ' mt-6'} type="button" disabled={!customStyle || busy} onClick={() => void makeCustom()}>
            {busy ? <LoaderCircle size={16} className="animate-spin" /> : <Sparkles size={16} />} Try this style</button>
          <p className="mt-3 text-xs text-muted">Manual generation may take several minutes. No automatic retry is sent.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="overflow-hidden rounded-3xl border border-purple-light/20 bg-card"><div className="p-3 text-xs uppercase tracking-widest text-muted">Original</div>
            {preview && <img src={preview} alt="Original photo" className="aspect-[4/5] w-full object-contain" />}</div>
          <div className="overflow-hidden rounded-3xl border border-purple-light/20 bg-card"><div className="p-3 text-xs uppercase tracking-widest text-gold">Generated</div>
            {customResult ? <img src={customResult.image.data_url} alt="Custom generated look" className="aspect-[4/5] w-full object-contain" />
              : <div className="flex aspect-[4/5] items-center justify-center p-6 text-center text-sm text-muted">{busy ? 'Generating your style…' : 'Your result will appear here.'}</div>}</div>
        </div>
      </div>
    </motion.section>}
  </div>;
}
