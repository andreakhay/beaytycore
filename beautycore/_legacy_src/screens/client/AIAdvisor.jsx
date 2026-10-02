import { useState, useRef } from 'react'
import ClientSidebar from '../../components/ClientSidebar'
import { useAuth } from '../../context/AuthContext'

// ── Simulated AI suggestion engine ──────────────────────────────────────────
const SERVICE_DB = {
  haircut: [
    { name:'Soft Curtain Bangs + Layers', price:350, duration:'60 min', gradient:'linear-gradient(135deg,#3d2314,#8b5e3c)', desc:'Face-framing layers with soft curtain bangs. Ideal for oval and heart-shaped faces.' },
    { name:'Textured Bob Cut', price:350, duration:'45 min', gradient:'linear-gradient(135deg,#1a1a1a,#555)', desc:'A modern chin-length bob with texture. Low maintenance and very versatile.' },
    { name:'Long Layers with Balayage', price:1850, duration:'120 min', gradient:'linear-gradient(135deg,#c8a87a,#e8d5b0)', desc:'Effortless long layers paired with sun-kissed balayage highlights.' },
  ],
  wedding: [
    { name:'Bridal Updo', price:1500, duration:'90 min', gradient:'linear-gradient(135deg,#f0a800,#fff3c0)', desc:'Elegant pinned updo with soft tendrils. Perfect for formal ceremonies.' },
    { name:'Bridal Makeup (Full Glam)', price:2500, duration:'90 min', gradient:'linear-gradient(135deg,#e8607a,#f0a800)', desc:'Full coverage foundation, dramatic eyes, and long-lasting lip color.' },
    { name:'Gel Manicure + Nail Art', price:550, duration:'60 min', gradient:'linear-gradient(135deg,#f4a7b9,#f5f5f5)', desc:'Classic French tips or custom bridal nail art with gel finish.' },
  ],
  prom: [
    { name:'Glamour Waves + Volume', price:500, duration:'60 min', gradient:'linear-gradient(135deg,#7b2fa0,#d060f0)', desc:'Hollywood-style voluminous waves for a show-stopping prom look.' },
    { name:'Prom Makeup (Glitter & Glow)', price:1800, duration:'75 min', gradient:'linear-gradient(135deg,#b040d8,#f0a800)', desc:'Glitter eye shadow, defined brows, and dewy skin for the big night.' },
    { name:'Acrylic Nails + Ombre', price:750, duration:'75 min', gradient:'linear-gradient(135deg,#8e44ad,#e8607a)', desc:'Long acrylic nails with a stunning purple-to-pink ombre effect.' },
  ],
  casual: [
    { name:'Blowdry & Style', price:250, duration:'30 min', gradient:'linear-gradient(135deg,#5c3d2e,#a07850)', desc:'A quick blowdry and style for a polished everyday look.' },
    { name:'Classic Manicure', price:180, duration:'30 min', gradient:'linear-gradient(135deg,#e8c9a0,#d4b080)', desc:'Clean, shaped nails with your choice of polish color.' },
    { name:'Express Facial (30 min)', price:400, duration:'30 min', gradient:'linear-gradient(135deg,#2d1054,#7b2fa0)', desc:'Quick deep-cleanse facial to refresh and brighten your skin.' },
  ],
  spa: [
    { name:'Japanese Head Spa (60 min)', price:850, duration:'60 min', gradient:'linear-gradient(135deg,#1a0a2e,#7b2fa0)', desc:'Deep scalp cleanse and relaxing massage for ultimate stress relief.' },
    { name:'Swedish Massage (60 min)', price:600, duration:'60 min', gradient:'linear-gradient(135deg,#2d1054,#b040d8)', desc:'Full-body relaxation massage with long, flowing strokes.' },
    { name:'HydraFacial', price:1800, duration:'60 min', gradient:'linear-gradient(135deg,#7b2fa0,#f0a800)', desc:'Medical-grade facial that cleanses, extracts, and hydrates.' },
  ],
  graduation: [
    { name:'Sleek Straight + Shine', price:350, duration:'45 min', gradient:'linear-gradient(135deg,#1a1a1a,#7b2fa0)', desc:'Perfectly straight, glossy hair for a polished graduation look.' },
    { name:'Natural Glam Makeup', price:1500, duration:'60 min', gradient:'linear-gradient(135deg,#e8c9a0,#e8607a)', desc:'Soft, natural makeup with a glowing finish. Camera-ready.' },
    { name:'Gel Pedicure', price:400, duration:'45 min', gradient:'linear-gradient(135deg,#7ecba1,#b8e8d0)', desc:'Long-lasting gel pedicure so your feet look great in open-toe shoes.' },
  ],
}

const KEYWORDS = {
  wedding:    ['wedding','bride','bridal','ceremony','church','vow','marry','married'],
  prom:       ['prom','ball','formal','dance','night','party','gown','debut'],
  graduation: ['graduation','grad','ceremony','school','college','university','diploma'],
  spa:        ['relax','stress','tired','spa','massage','refresh','unwind','calm','rest'],
  casual:     ['casual','everyday','work','office','simple','quick','natural','minimal'],
  haircut:    ['haircut','hair','cut','trim','style','bangs','layers','color','colour'],
}

function detectTheme(text) {
  const lower = text.toLowerCase()
  for (const [theme, words] of Object.entries(KEYWORDS)) {
    if (words.some(w => lower.includes(w))) return theme
  }
  return 'casual'
}

function generateSuggestions(messages) {
  const fullText = messages.filter(m => m.role === 'user').map(m => m.text).join(' ')
  const theme = detectTheme(fullText)
  const suggestions = SERVICE_DB[theme] || SERVICE_DB.casual
  return { theme, suggestions }
}

// ── AI Look Generator (simulated) ───────────────────────────────────────────
const LOOKS = [
  { label:'Look 1 — Natural Glow',    gradient:'linear-gradient(135deg,#e8c9a0 0%,#f4a7b9 50%,#e8607a 100%)', tags:['Soft','Feminine','Everyday'] },
  { label:'Look 2 — Bold & Dramatic', gradient:'linear-gradient(135deg,#1a0a2e 0%,#7b2fa0 50%,#f0a800 100%)', tags:['Glamour','Evening','Statement'] },
  { label:'Look 3 — Fresh & Modern',  gradient:'linear-gradient(135deg,#7ecba1 0%,#2d1054 50%,#b040d8 100%)', tags:['Trendy','Youthful','Vibrant'] },
]

const QUICK_PROMPTS = [
  "I'm attending a wedding next week 💍",
  "I need a look for my prom night 🌟",
  "I want something relaxing and refreshing 🌿",
  "I'm graduating next month 🎓",
  "Just need a quick everyday style ✨",
  "I want a full glam transformation 💄",
]

export default function AIAdvisor() {
  const { user } = useAuth()
  const [messages, setMessages] = useState([
    { role:'ai', text:`Hi ${user?.name?.split(' ')[0] || 'there'}! 👋 I'm your AI Style Advisor. Tell me about your upcoming event, theme, or what look you're going for — and I'll suggest the best services, estimated costs, and schedule for you!` }
  ])
  const [input, setInput] = useState('')
  const [photo, setPhoto] = useState(null)
  const [suggestions, setSuggestions] = useState(null)
  const [looks, setLooks] = useState(null)
  const [loading, setLoading] = useState(false)
  const [bookModal, setBookModal] = useState(null)
  const [booked, setBooked] = useState(false)
  const fileRef = useRef()
  const chatRef = useRef()

  function scrollToBottom() {
    setTimeout(() => chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior:'smooth' }), 100)
  }

  function sendMessage(text) {
    const msg = text || input.trim()
    if (!msg) return
    setInput('')

    const newMessages = [...messages, { role:'user', text: msg }]
    setMessages(newMessages)
    setLoading(true)
    scrollToBottom()

    setTimeout(() => {
      const { theme, suggestions: suggs } = generateSuggestions(newMessages)
      const themeLabel = theme.charAt(0).toUpperCase() + theme.slice(1)
      const aiReply = `Great! Based on your message, I've detected a **${themeLabel}** theme. Here are my top 3 personalized service recommendations for you — complete with pricing and estimated duration. I've also generated 3 AI look previews below! 🎨`

      setMessages(prev => [...prev, { role:'ai', text: aiReply }])
      setSuggestions({ theme, suggestions: suggs })
      setLooks(LOOKS)
      setLoading(false)
      scrollToBottom()
    }, 1200)
  }

  function handlePhoto(e) {
    const file = e.target.files[0]
    if (!file) return
    const url = URL.createObjectURL(file)
    setPhoto(url)
    const newMessages = [...messages, { role:'user', text:'📸 I uploaded my photo for analysis.', image: url }]
    setMessages(newMessages)
    setLoading(true)
    scrollToBottom()

    setTimeout(() => {
      setMessages(prev => [...prev, { role:'ai', text:"I've analyzed your photo! ✨ Based on your facial features, I can see you have beautiful bone structure. I'll factor this into my recommendations. Now tell me — what's the occasion or look you're going for?" }])
      setLoading(false)
      scrollToBottom()
    }, 1500)
  }

  function confirmBook(svc) {
    setBookModal(null)
    setBooked(true)
    setMessages(prev => [...prev, { role:'ai', text:`✅ Your **${svc.name}** appointment has been submitted! Estimated cost: **${svc.price.toLocaleString('en-PH', { style:'currency', currency:'PHP' })}**. Our team will confirm your schedule shortly.` }])
    scrollToBottom()
    setTimeout(() => setBooked(false), 3000)
  }

  const totalCost = suggestions?.suggestions.reduce((s, sv) => s + sv.price, 0) || 0

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <ClientSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        {/* Topbar */}
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">AI Style Advisor</h1>
            <p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1px]">Upload your photo · Chat about your event · Get personalized suggestions</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#6fcf97] animate-pulse" />
            <span className="font-sans text-[10px] text-[#6fcf97] tracking-[1px]">AI ONLINE</span>
          </div>
        </header>

        <div className="flex flex-1 overflow-hidden" style={{ height:'calc(100vh - 73px)' }}>

          {/* LEFT: Chat */}
          <div className="flex flex-col flex-1 min-w-0">
            {/* Messages */}
            <div ref={chatRef} className="flex-1 overflow-y-auto p-6 flex flex-col gap-4">

              {/* Photo upload prompt */}
              {!photo && (
                <div className="bg-[#b040d8]/8 border border-dashed border-[#b040d8]/30 p-5 text-center cursor-pointer hover:border-[#f0a800]/50 transition-colors"
                  onClick={() => fileRef.current?.click()}>
                  <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handlePhoto} />
                  <div className="w-12 h-12 rounded-full bg-[#b040d8]/15 flex items-center justify-center mx-auto mb-3">
                    <svg className="w-6 h-6 text-[#b040d8]" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                      <path d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
                      <circle cx="12" cy="13" r="3"/>
                    </svg>
                  </div>
                  <p className="font-sans text-[12px] font-semibold text-[#c8a8e0] mb-1">Upload Your Photo</p>
                  <p className="font-sans text-[10px] text-[#9a7ab8]">Our AI will analyze your features and suggest the most flattering styles</p>
                </div>
              )}

              {/* Chat messages */}
              {messages.map((m, i) => (
                <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 ${m.role === 'ai' ? 'bg-gradient-to-br from-[#7b2fa0] to-[#b040d8] text-white' : 'bg-gradient-to-br from-[#f0a800] to-[#f5c040] text-[#1a0a2e]'}`}>
                    {m.role === 'ai' ? 'AI' : user?.avatar || 'M'}
                  </div>
                  <div className={`max-w-[75%] ${m.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
                    {m.image && <img src={m.image} alt="uploaded" className="w-32 h-32 object-cover border border-[#b040d8]/30 mb-1" />}
                    <div className={`px-4 py-3 text-[12px] leading-[1.7] ${m.role === 'ai'
                      ? 'bg-[#1a0a2e] border border-[#b040d8]/20 text-[#e0c8f0]'
                      : 'bg-[#f0a800]/15 border border-[#f0a800]/25 text-white'}`}
                      dangerouslySetInnerHTML={{ __html: m.text.replace(/\*\*(.*?)\*\*/g, '<strong class="text-[#f0a800]">$1</strong>') }}
                    />
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#7b2fa0] to-[#b040d8] flex items-center justify-center text-[11px] font-bold text-white shrink-0">AI</div>
                  <div className="bg-[#1a0a2e] border border-[#b040d8]/20 px-4 py-3 flex gap-1.5 items-center">
                    {[0,1,2].map(i => <span key={i} className="w-1.5 h-1.5 rounded-full bg-[#b040d8] animate-bounce" style={{ animationDelay:`${i*0.15}s` }} />)}
                  </div>
                </div>
              )}
            </div>

            {/* Quick prompts */}
            <div className="px-6 pb-3 flex gap-2 flex-wrap">
              {QUICK_PROMPTS.map(p => (
                <button key={p} onClick={() => sendMessage(p)}
                  className="font-sans text-[10px] text-[#9a7ab8] border border-[#b040d8]/25 px-3 py-1.5 hover:border-[#f0a800]/50 hover:text-[#f0a800] transition-all cursor-pointer bg-transparent">
                  {p}
                </button>
              ))}
            </div>

            {/* Input */}
            <div className="px-6 pb-6 flex gap-3">
              <button onClick={() => fileRef.current?.click()}
                className="w-10 h-10 shrink-0 flex items-center justify-center bg-[#b040d8]/10 border border-[#b040d8]/25 text-[#9a7ab8] hover:text-[#f0a800] hover:border-[#f0a800]/50 transition-all cursor-pointer">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/><circle cx="12" cy="13" r="3"/></svg>
              </button>
              <input value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendMessage()}
                placeholder="Tell me about your event, theme, or desired look..."
                className="flex-1 bg-[#1a0a2e] border border-[#b040d8]/25 text-white font-sans text-xs px-4 py-3 outline-none focus:border-[#f0a800] placeholder:text-white/25" />
              <button onClick={() => sendMessage()}
                className="px-5 bg-[#f0a800] text-[#1a0a2e] font-sans text-[10px] font-bold tracking-[1.5px] uppercase border-none cursor-pointer hover:bg-[#f5c040] transition-colors">
                SEND
              </button>
            </div>
          </div>

          {/* RIGHT: Suggestions Panel */}
          {suggestions && (
            <div className="w-[380px] shrink-0 border-l border-[#b040d8]/15 overflow-y-auto bg-[#0f0520]">
              <div className="p-5">
                {/* Theme badge */}
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Your Recommendations</h2>
                  <span className="font-sans text-[9px] font-bold tracking-[1px] uppercase bg-[#f0a800]/15 text-[#f0a800] px-2.5 py-1">{suggestions.theme}</span>
                </div>

                {/* 3 Service suggestions */}
                <div className="flex flex-col gap-3 mb-5">
                  {suggestions.suggestions.map((svc, i) => (
                    <div key={i} className="bg-[#1a0a2e] border border-[#b040d8]/15 overflow-hidden hover:border-[#f0a800]/40 transition-all">
                      <div className="h-[60px] relative" style={{ background: svc.gradient }}>
                        <div className="absolute inset-0 bg-black/30 flex items-center px-4">
                          <span className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-white/80">Suggestion {i+1}</span>
                        </div>
                      </div>
                      <div className="p-3.5">
                        <p className="font-serif text-[15px] text-white mb-1">{svc.name}</p>
                        <p className="font-sans text-[10px] text-[#9a7ab8] mb-2.5 leading-[1.5]">{svc.desc}</p>
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <p className="font-sans text-[9px] text-[#9a7ab8] uppercase tracking-[1px]">Est. Cost</p>
                            <p className="font-serif text-[18px] text-[#f0a800]">₱{svc.price.toLocaleString()}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-sans text-[9px] text-[#9a7ab8] uppercase tracking-[1px]">Duration</p>
                            <p className="font-sans text-[11px] text-white font-semibold">{svc.duration}</p>
                          </div>
                        </div>
                        <button onClick={() => setBookModal(svc)}
                          className="w-full font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] py-2 border-none cursor-pointer hover:bg-[#f5c040] transition-colors">
                          BOOK THIS SERVICE
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Total estimate */}
                <div className="bg-[#f0a800]/7 border border-[#f0a800]/20 p-3.5 mb-5">
                  <div className="flex justify-between items-center">
                    <p className="font-sans text-[10px] text-[#9a7ab8] uppercase tracking-[1px]">Total Package Estimate</p>
                    <p className="font-serif text-[22px] text-[#f0a800]">₱{totalCost.toLocaleString()}</p>
                  </div>
                  <p className="font-sans text-[10px] text-[#9a7ab8] mt-1">All 3 services combined</p>
                </div>

                {/* AI Generated Looks */}
                <h3 className="font-serif text-[16px] text-white mb-3 tracking-[1px]">AI Generated Looks</h3>
                <div className="flex flex-col gap-3">
                  {looks.map((look, i) => (
                    <div key={i} className="border border-[#b040d8]/15 overflow-hidden hover:border-[#f0a800]/40 transition-all">
                      <div className="h-[100px]" style={{ background: look.gradient }} />
                      <div className="p-3 bg-[#1a0a2e]">
                        <p className="font-sans text-[11px] font-semibold text-white mb-1.5">{look.label}</p>
                        <div className="flex gap-1.5 flex-wrap">
                          {look.tags.map(t => (
                            <span key={t} className="font-sans text-[9px] font-semibold tracking-[1px] uppercase text-[#9a7ab8] bg-[#b040d8]/10 px-2 py-[3px]">{t}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Book Modal */}
      {bookModal && (
        <div className="fixed inset-0 bg-[#0a0214]/85 z-[200] flex items-center justify-center p-6"
          onClick={e => e.target === e.currentTarget && setBookModal(null)}>
          <div className="bg-[#1a0a2e] border border-[#b040d8]/30 w-full max-w-[440px]">
            <div className="px-6 py-5 border-b border-[#b040d8]/15 flex items-center justify-between">
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">Book Service</h3>
              <button onClick={() => setBookModal(null)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] leading-none">✕</button>
            </div>
            <div className="p-6">
              <div className="bg-[#f0a800]/7 border border-[#f0a800]/20 p-3.5 mb-5">
                <p className="font-sans text-[10px] text-[#9a7ab8] uppercase tracking-[1.5px] mb-1">Selected Service</p>
                <p className="text-[#f0a800] text-[14px] font-semibold">{bookModal.name}</p>
                <p className="font-sans text-[11px] text-[#9a7ab8] mt-1">Est. ₱{bookModal.price.toLocaleString()} · {bookModal.duration}</p>
              </div>
              <div className="grid grid-cols-2 gap-3.5 mb-4">
                <div>
                  <label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Date</label>
                  <input type="date" className="w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-3 outline-none focus:border-[#f0a800]" />
                </div>
                <div>
                  <label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Time</label>
                  <select className="w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-3 outline-none focus:border-[#f0a800] [&>option]:bg-[#2d1054]">
                    {['9:00 AM','10:00 AM','11:00 AM','1:00 PM','2:00 PM','3:00 PM'].map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Notes</label>
                <textarea rows={2} placeholder="Any special requests..." className="w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-3 outline-none focus:border-[#f0a800] resize-none placeholder:text-white/25" />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex gap-3 justify-end">
              <button onClick={() => setBookModal(null)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Cancel</button>
              <button onClick={() => confirmBook(bookModal)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Confirm Booking</button>
            </div>
          </div>
        </div>
      )}

      {booked && (
        <div className="fixed bottom-8 right-8 bg-[#6fcf97] text-[#0f0520] font-sans text-[11px] font-bold tracking-[1.5px] px-6 py-3 z-[9999]">
          ✓ Booking submitted successfully!
        </div>
      )}
    </div>
  )
}
