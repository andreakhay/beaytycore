import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

/* ── Scroll-reveal hook ── */
function useReveal(options = {}) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        el.classList.add('revealed')
        obs.disconnect()
      }
    }, { threshold: 0.15, ...options })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])
  return ref
}

export default function About() {
  const photoRef   = useReveal()
  const textRef    = useReveal()
  const pillar0    = useReveal()
  const pillar1    = useReveal()
  const pillar2    = useReveal()
  const ctaRef     = useReveal()

  return (
    <div>
      <style>{`
        /* ── Orb drift (hero banner) ── */
        @keyframes about-orb {
          0%   { transform: translate(0,0) scale(1);    opacity:.20; }
          40%  { transform: translate(30px,-25px) scale(1.1); opacity:.28; }
          70%  { transform: translate(-20px,18px) scale(.93); opacity:.16; }
          100% { transform: translate(0,0) scale(1);    opacity:.20; }
        }
        @keyframes about-orb2 {
          0%   { transform: translate(0,0) scale(1);    opacity:.14; }
          50%  { transform: translate(-40px,30px) scale(1.12); opacity:.22; }
          100% { transform: translate(0,0) scale(1);    opacity:.14; }
        }

        /* ── Hero title shimmer ── */
        @keyframes shimmer-text {
          0%,100% { background-position: -200% center; }
          50%     { background-position:  200% center; }
        }
        .hero-shimmer {
          background: linear-gradient(90deg,
            #fff 0%, #fff 40%,
            #d060f0 50%,
            #fff 60%, #fff 100%
          );
          background-size: 200% auto;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          animation: shimmer-text 5s linear infinite;
        }

        /* ── Scroll-reveal base states ── */
        .reveal-left {
          opacity: 0;
          transform: translateX(-40px);
          transition: opacity .9s cubic-bezier(.22,1,.36,1),
                      transform .9s cubic-bezier(.22,1,.36,1);
        }
        .reveal-up {
          opacity: 0;
          transform: translateY(32px);
          transition: opacity .9s cubic-bezier(.22,1,.36,1),
                      transform .9s cubic-bezier(.22,1,.36,1);
        }
        .reveal-up.delay-1 { transition-delay:.15s; }
        .reveal-up.delay-2 { transition-delay:.30s; }
        .reveal-up.delay-3 { transition-delay:.45s; }
        .reveal-left.revealed,
        .reveal-up.revealed {
          opacity: 1;
          transform: translate(0,0);
        }

        /* ── Pillar card hover glow ── */
        .pillar-card {
          transition: transform .3s ease, box-shadow .3s ease;
        }
        .pillar-card:hover {
          transform: translateY(-6px);
          box-shadow: 0 12px 40px rgba(176,64,216,.25);
        }

        /* ── Glowing violet border on photo ── */
        @keyframes glow-pulse {
          0%, 100% { box-shadow: 0 0 18px 4px rgba(176,64,216,.6), 0 0 40px 10px rgba(123,47,160,.35), 0 0 70px 20px rgba(176,64,216,.15); }
          50%       { box-shadow: 0 0 28px 8px rgba(208,96,240,.8), 0 0 60px 18px rgba(176,64,216,.5),  0 0 100px 30px rgba(123,47,160,.2); }
        }
        .about-photo-wrap {
          border-radius: 4px;
          overflow: hidden;
          animation: glow-pulse 3s ease-in-out infinite;
          border: 2px solid rgba(176,64,216,.5);
        }

        /* ── CTA pulse ring ── */
        @keyframes pulse-ring {
          0%   { box-shadow: 0 0 0 0 rgba(123,47,160,.5); }
          70%  { box-shadow: 0 0 0 12px rgba(123,47,160,0); }
          100% { box-shadow: 0 0 0 0 rgba(123,47,160,0); }
        }
        .cta-btn { animation: pulse-ring 2.8s ease-out infinite; }
      `}</style>

      <Navbar />

      {/* ── MEET ANDREA ── */}
      <section className="bg-[#f9f4ff] py-24">
        <div className="max-w-[1100px] mx-auto px-6 grid grid-cols-[1fr_1.6fr] gap-[60px] items-start max-[900px]:grid-cols-1">

          {/* Photo — slides in from left */}
          <div ref={photoRef}
            className="reveal-left about-photo-wrap aspect-[3/4] w-full max-[900px]:aspect-[4/3] max-[900px]:max-w-[400px] max-[900px]:mx-auto">
            <img src="/aboutpic.jpg" alt="Andrea, Founder & Principal Specialist"
              className="w-full h-full object-cover object-center" />
          </div>

          {/* Text — fades up */}
          <div ref={textRef} className="reveal-up pt-2.5">
            <p className="font-sans text-[10px] tracking-[3px] text-[#c88800] uppercase mb-3">THE FOUNDER</p>
            <h2 className="font-serif font-normal tracking-[4px] text-[#1a0a2e] uppercase mb-6"
              style={{ fontSize:'clamp(28px,4vw,42px)' }}>MEET ANDREA</h2>
            {[
              'Andrea founded this clinic with a singular vision: to create a sanctuary where beauty and wellness converge. With over 15 years of experience in aesthetic medicine and holistic wellness, she has built a team of dedicated professionals who share her passion for excellence.',
              'Her approach is rooted in the belief that true beauty comes from within. Every treatment, every service, and every interaction at Andrea\'s is designed to nurture not just your appearance, but your overall sense of wellbeing and confidence.',
              'From the carefully curated product lines to the bespoke treatment protocols, every detail reflects Andrea\'s commitment to providing an experience that is as transformative as it is luxurious. She believes that self-care is not a luxury — it is a fundamental act of self-respect.',
            ].map((p, i) => (
              <p key={i} className="font-sans text-[13px] text-[#444] leading-[1.9] mb-4">{p}</p>
            ))}
            <p className="font-serif text-[15px] text-[#666] mt-6 italic">— Andrea, Founder &amp; Principal Specialist</p>
          </div>
        </div>
      </section>

      {/* ── CORE PILLARS ── */}
      <section className="py-24 overflow-hidden"
        style={{ background:'linear-gradient(160deg,#1a0a2e 0%,#2d1054 100%)' }}>
        <div className="max-w-[1100px] mx-auto px-6">
          <h2 className="font-serif font-normal tracking-[6px] uppercase text-center text-white mb-3"
            style={{ fontSize:'clamp(24px,4vw,36px)' }}>OUR CORE PILLARS</h2>
          <div className="w-10 h-px bg-[#f0a800] mx-auto mb-12" />

          <div className="grid grid-cols-3 gap-8 max-[900px]:grid-cols-1 max-[900px]:gap-6">
            {[
              { ref: pillar0, delay: '',        title:'PRECISION',   text:'Every treatment is performed with meticulous attention to detail. We use only the most advanced techniques and highest-quality products to ensure exceptional results.' },
              { ref: pillar1, delay:'delay-1',  title:'PURITY',      text:'We are committed to clean, ethical beauty. Our products are carefully selected for their purity, efficacy, and sustainability — because what goes on your skin matters.' },
              { ref: pillar2, delay:'delay-2',  title:'TRANQUILITY', text:'From the moment you walk through our doors, you enter a space designed for calm. Every element of our environment is crafted to help you unwind and restore.' },
            ].map(({ ref, delay, title, text }) => (
              <div key={title} ref={ref}
                className={`reveal-up ${delay} pillar-card border border-[#b040d8]/20 p-8`}
                style={{ background:'rgba(176,64,216,.06)' }}>
                {/* Accent line */}
                <div className="w-8 h-[2px] bg-[#f0a800] mb-5" />
                <h4 className="font-sans text-[11px] font-semibold tracking-[2.5px] text-[#f0a800] uppercase mb-4">{title}</h4>
                <p className="font-sans text-xs text-[#e0c8f0] leading-[1.9]">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="bg-[#f9f4ff] py-24 px-6 text-center">
        <div ref={ctaRef} className="reveal-up">
          <p className="font-sans text-[9px] tracking-[3px] text-[#c88800] uppercase mb-4">BEGIN YOUR JOURNEY</p>
          <h2 className="font-serif font-normal italic text-[#1a0a2e] mb-8"
            style={{ fontSize:'clamp(26px,4vw,40px)' }}>Ready to begin your journey?</h2>
          <Link to="/contact"
            className="cta-btn inline-block font-sans text-[10px] font-semibold tracking-[2px] uppercase text-white bg-[#2d1054] px-10 py-4 transition-all duration-200 hover:bg-[#7b2fa0]">
            Book your session
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  )
}
