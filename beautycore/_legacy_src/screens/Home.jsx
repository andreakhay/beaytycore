import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

export default function Home() {
  return (
    <div>
      {/* Animated border keyframe */}
      <style>{`
        @keyframes spin-border {
          0%   { transform: translate(-50%, -50%) rotate(0deg); }
          100% { transform: translate(-50%, -50%) rotate(360deg); }
        }
        .service-card-border {
          position: relative;
          border-radius: 2px;
          overflow: hidden;
          padding: 3px;
        }
        .service-card-border::before {
          content: '';
          position: absolute;
          top: 50%;
          left: 50%;
          width: 200%;
          height: 200%;
          background: conic-gradient(
            from 0deg,
            transparent 0deg,
            transparent 60deg,
            #b040d8 90deg,
            #d060f0 130deg,
            #7b2fa0 160deg,
            transparent 200deg,
            transparent 360deg
          );
          animation: spin-border 3s linear infinite;
          z-index: 0;
        }
        .service-card-inner {
          position: relative;
          z-index: 1;
          width: 100%;
          height: 100%;
          overflow: hidden;
        }

        /* Hero orb drift */
        @keyframes orb-drift {
          0%   { transform: translate(0px, 0px) scale(1); opacity: 0.22; }
          33%  { transform: translate(40px, -30px) scale(1.08); opacity: 0.28; }
          66%  { transform: translate(-25px, 20px) scale(0.95); opacity: 0.18; }
          100% { transform: translate(0px, 0px) scale(1); opacity: 0.22; }
        }
        @keyframes orb-drift2 {
          0%   { transform: translate(0px, 0px) scale(1); opacity: 0.15; }
          50%  { transform: translate(-50px, 35px) scale(1.12); opacity: 0.22; }
          100% { transform: translate(0px, 0px) scale(1); opacity: 0.15; }
        }

        /* Hero text fade-up */
        @keyframes fade-up {
          from { opacity: 0; transform: translateY(28px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .hero-tag   { animation: fade-up 0.9s cubic-bezier(.22,1,.36,1) 0.1s both; }
        .hero-title { animation: fade-up 1s  cubic-bezier(.22,1,.36,1) 0.3s both; }
        .hero-sub   { animation: fade-up 1s  cubic-bezier(.22,1,.36,1) 0.55s both; }
        .hero-cta   { animation: fade-up 1s  cubic-bezier(.22,1,.36,1) 0.75s both; }

        /* Floating particles */
        @keyframes float-up {
          0%   { transform: translateY(0) translateX(0); opacity: 0; }
          10%  { opacity: 0.6; }
          90%  { opacity: 0.2; }
          100% { transform: translateY(-100vh) translateX(20px); opacity: 0; }
        }
        .particle {
          position: absolute;
          border-radius: 50%;
          background: rgba(176,64,216,0.5);
          animation: float-up linear infinite;
          pointer-events: none;
        }
      `}</style>
      <Navbar />

      {/* HERO */}
      <section className="relative min-h-[88vh] flex items-center justify-center text-center px-6 py-20 overflow-hidden"
        style={{ background: 'linear-gradient(160deg,#1a0a2e 0%,#2d1054 50%,#1a0a2e 100%)' }}>

        {/* Drifting orbs */}
        <div className="absolute pointer-events-none" style={{
          top: '30%', left: '55%', width: '520px', height: '520px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(176,64,216,0.35) 0%, transparent 70%)',
          animation: 'orb-drift 12s ease-in-out infinite',
        }} />
        <div className="absolute pointer-events-none" style={{
          top: '50%', left: '20%', width: '380px', height: '380px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(123,47,160,0.25) 0%, transparent 70%)',
          animation: 'orb-drift2 16s ease-in-out infinite',
        }} />

        {/* Floating particles */}
        {[
          { left:'10%',  size:3, dur:'9s',  delay:'0s'   },
          { left:'22%',  size:2, dur:'13s', delay:'2s'   },
          { left:'38%',  size:4, dur:'11s', delay:'4s'   },
          { left:'55%',  size:2, dur:'15s', delay:'1s'   },
          { left:'68%',  size:3, dur:'10s', delay:'6s'   },
          { left:'80%',  size:2, dur:'14s', delay:'3s'   },
          { left:'90%',  size:3, dur:'12s', delay:'5s'   },
        ].map((p, i) => (
          <span key={i} className="particle" style={{
            left: p.left, bottom: '-10px',
            width: p.size, height: p.size,
            animationDuration: p.dur,
            animationDelay: p.delay,
          }} />
        ))}

        {/* Content */}
        <div className="relative z-10 max-w-[700px]">
          <p className="hero-tag font-sans text-[10px] tracking-[4px] text-[#f0a800] uppercase mb-5">AESTHETIC &amp; WELLNESS CLINIC</p>
          <h1 className="hero-title font-serif font-light tracking-[14px] text-white leading-none mb-7" style={{ fontSize: 'clamp(56px,10vw,100px)' }}>ANDREA'S</h1>
          <p className="hero-sub font-sans text-[13px] font-light text-[#e0c8f0] leading-[1.9] max-w-[480px] mx-auto mb-9">
            Experience the ultimate in beauty, wellness, and self-care. A luxury retreat designed to restore, refresh, and rejuvenate your mind and body.
          </p>
          <div className="hero-cta">
            <Link to="/services" className="inline-block font-sans text-[10px] font-semibold tracking-[2.5px] uppercase text-[#f0a800] border border-[#f0a800] px-[30px] py-3 transition-all duration-200 hover:bg-[#f0a800] hover:text-[#1a0a2e]">
              DISCOVER OUR SERVICES
            </Link>
          </div>
        </div>
      </section>

      {/* SERVICES */}
      <section className="bg-[#f9f4ff] py-20" id="services">
        <div className="max-w-[1100px] mx-auto px-6">
          <h2 className="font-serif font-normal tracking-[6px] uppercase text-center text-[#1a0a2e] mb-3" style={{ fontSize: 'clamp(24px,4vw,36px)' }}>SERVICES WE OFFER</h2>
          <div className="w-10 h-px bg-[#c88800] mx-auto mb-12" />
          <div className="grid grid-cols-3 gap-5 mb-12 max-[900px]:grid-cols-1 max-[900px]:max-w-[360px] max-[900px]:mx-auto">
            {[
              { label: 'HAIR',    btn: 'Book', img: '/hairextension.jpg' },
              { label: 'MAKE UP', btn: 'Book', img: '/makeup.png'        },
              { label: 'NAILS',   btn: 'Book', img: '/nails.jpg'         },
            ].map(({ label, btn, img }) => (
              <div key={label} className="aspect-[3/4] max-[900px]:aspect-[4/3] service-card-border">
                <div className="service-card-inner w-full h-full relative flex flex-col items-center justify-center gap-4">
                  {/* Photo background */}
                  <img src={img} alt={label}
                    className="absolute inset-0 w-full h-full object-cover object-center" />
                  {/* Dark overlay so text stays readable */}
                  <div className="absolute inset-0 bg-black/45" />
                  <h3 className="relative z-10 font-serif text-[22px] font-normal tracking-[5px] text-white">{label}</h3>
                  <Link to="#" className="relative z-10 font-sans text-[9px] font-medium tracking-[1.5px] uppercase text-[#1a0a2e] bg-white px-[18px] py-1.5 transition-all duration-200 hover:bg-[#f0a800] hover:text-white">
                    {btn}
                  </Link>
                </div>
              </div>
            ))}
          </div>
          <p className="font-serif text-[18px] italic text-[#1a0a2e] text-center mb-7">Self-care is not an indulgence. It's a necessity.</p>
          <Link to="/contact" className="block w-fit mx-auto font-sans text-[10px] font-semibold tracking-[2px] uppercase text-white bg-[#2d1054] px-8 py-3.5 transition-all duration-200 hover:bg-[#7b2fa0]">
            BOOK YOUR APPOINTMENT
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  )
}
