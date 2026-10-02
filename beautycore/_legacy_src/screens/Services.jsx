import { useState } from 'react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

const services = [
  {
    id: 'japanese-head-spa', label: 'Japanese Head Spa',
    sub: 'Scalp treatment & deep relaxation ritual',
    intro: 'Experience the ancient Japanese art of scalp care. Our head spa treatments combine deep cleansing, nourishing scalp massage, and premium hair treatments to restore balance and promote healthy hair growth.',
    categories: [
      { title: 'Signature Treatments', items: [
        ['Classic Head Spa (60 min)', '₱850'], ['Deep Cleanse Head Spa (75 min)', '₱1,100'], ['Scalp Detox Treatment', '₱750'],
        ['Premium Head Spa (90 min)', '₱1,350'], ['Scalp Analysis & Treatment', '₱950'], ['Hydrating Scalp Ritual', '₱900'],
      ]},
      { title: 'Add-Ons', items: [
        ['Aromatherapy Enhancement', '₱150'], ['Hot Oil Treatment', '₱200'],
        ['Neck & Shoulder Massage', '₱250'], ['Hair Mask Treatment', '₱300'],
      ]},
    ],
  },
  {
    id: 'hair-design', label: 'Hair Design',
    sub: 'Cuts, colour & styling by expert stylists',
    intro: 'Our talented stylists bring your vision to life with precision cuts, vibrant colour, and flawless styling. From everyday looks to special occasion transformations, we deliver results that exceed expectations.',
    categories: [
      { title: 'Cuts & Styling', items: [
        ["Women's Cut & Blowdry", '₱350'], ["Men's Cut", '₱180'], ["Children's Cut (under 12)", '₱150'], ['Blowdry & Style', '₱250'],
        ['Updo / Special Occasion', '₱500'], ['Bridal Hair', 'Mula ₱1,500'], ['Keratin Treatment', 'Mula ₱2,500'], ['Hair Extensions Consult', 'Libre'],
      ]},
      { title: 'Colour Services', items: [
        ['Full Colour', 'Mula ₱800'], ['Highlights (Full)', 'Mula ₱1,200'], ['Highlights (Partial)', 'Mula ₱700'],
        ['Balayage', 'Mula ₱1,500'], ['Toner / Gloss', '₱350'], ['Colour Correction', 'Konsultasyon'],
      ]},
    ],
  },
  {
    id: 'face-laser', label: 'Face & Laser',
    sub: 'Advanced aesthetic treatments for radiant skin',
    intro: 'Our medical-grade facial and laser treatments are performed by certified aesthetic specialists. We use the latest technology to address a wide range of skin concerns with safe, effective, and long-lasting results.',
    categories: [
      { title: 'Facial Treatments', items: [
        ['Classic Facial (60 min)', '₱600'], ['HydraFacial', '₱1,800'], ['Microdermabrasion', '₱1,200'], ['Chemical Peel (Light)', '₱1,000'],
        ['Chemical Peel (Medium)', '₱1,500'], ['LED Light Therapy', '₱700'], ['Microneedling', '₱2,500'], ['PRP Facial', '₱4,500'],
      ]},
      { title: 'Laser Treatments', items: [
        ['Laser Hair Removal – Face', 'Mula ₱800'], ['Laser Hair Removal – Body', 'Mula ₱1,500'], ['Laser Skin Resurfacing', 'Mula ₱3,500'],
        ['IPL Photofacial', '₱2,200'], ['Pigmentation Treatment', 'Mula ₱1,800'], ['Vascular Treatment', 'Mula ₱2,000'],
      ]},
    ],
  },
  {
    id: 'nail-studio', label: 'Nail Studio',
    sub: 'Manicures, pedicures & nail art',
    intro: 'Indulge in our full range of nail services, from classic manicures to intricate nail art. Our nail technicians use only premium, long-lasting products to keep your nails looking flawless.',
    categories: [
      { title: 'Manicure Services', items: [
        ['Classic Manicure', '₱180'], ['Gel Manicure', '₱350'], ['Acrylic Full Set', '₱650'], ['Acrylic Infill', '₱450'],
        ['Gel Extensions', '₱750'], ['Nail Art (per nail)', 'Mula ₱50'], ['Gel Removal', '₱150'], ['Nail Repair', '₱80'],
      ]},
      { title: 'Pedicure Services', items: [
        ['Classic Pedicure', '₱220'], ['Gel Pedicure', '₱400'], ['Spa Pedicure (60 min)', '₱550'],
        ['Luxury Pedicure (75 min)', '₱750'], ['Callus Treatment', '₱200'], ['Paraffin Wax Add-On', '₱150'],
      ]},
    ],
  },
  {
    id: 'massage-therapy', label: 'Massage Therapy',
    sub: 'Therapeutic & relaxation massage',
    intro: 'Our certified massage therapists offer a range of therapeutic and relaxation massages tailored to your individual needs. Whether you seek relief from tension or simply wish to unwind, we have the perfect treatment for you.',
    categories: [
      { title: 'Full Body Massage', items: [
        ['Swedish Massage (60 min)', '₱600'], ['Swedish Massage (90 min)', '₱850'], ['Deep Tissue (60 min)', '₱700'],
        ['Deep Tissue (90 min)', '₱950'], ['Hot Stone Massage (75 min)', '₱900'], ['Aromatherapy Massage', '₱750'],
      ]},
      { title: 'Targeted Treatments', items: [
        ['Back, Neck & Shoulder (30 min)', '₱350'], ['Foot Reflexology (45 min)', '₱450'],
        ['Prenatal Massage (60 min)', '₱650'], ['Sports Massage (60 min)', '₱700'],
      ]},
    ],
  },
]

export default function Services() {
  const [active, setActive] = useState('japanese-head-spa')
  const current = services.find(s => s.id === active)

  return (
    <div>
      <Navbar />

      {/* HERO */}
      <section className="py-[70px] px-10 pb-[50px] text-center border-b border-[#b040d8]/20" style={{ background: 'linear-gradient(160deg,#1a0a2e 0%,#2d1054 100%)' }}>
        <h1 className="font-serif font-light tracking-[8px] text-white uppercase mb-2" style={{ fontSize: 'clamp(28px,5vw,48px)' }}>OUR SERVICES</h1>
        <p className="font-sans text-[11px] tracking-[2px] text-[#f0a800] uppercase">Andrea's Aesthetic &amp; Wellness Clinic</p>
      </section>

      {/* BODY */}
      <section className="bg-[#f9f4ff] pb-20">
        <div className="max-w-[1100px] mx-auto px-6 grid grid-cols-[200px_1fr] gap-0 max-[900px]:grid-cols-1">

          {/* Sidebar */}
          <aside className="py-10 border-r border-[#7b2fa0]/15 sticky top-[70px] h-fit max-[900px]:static max-[900px]:border-r-0 max-[900px]:border-b max-[900px]:border-[#7b2fa0]/15 max-[900px]:pb-5">
            <p className="font-sans text-[9px] font-bold tracking-[2.5px] text-[#7b2fa0] uppercase mb-5 pr-5">Menu</p>
            <nav className="flex flex-col gap-1 max-[900px]:flex-row max-[900px]:flex-wrap max-[900px]:gap-2">
              {services.map(s => (
                <a key={s.id} href={`#${s.id}`} onClick={() => setActive(s.id)}
                  className={`font-sans text-[11px] py-[7px] pr-5 border-b border-black/6 transition-colors duration-200 cursor-pointer max-[900px]:border-none max-[900px]:px-3 max-[900px]:py-[5px] max-[900px]:bg-[#7b2fa0]/10 max-[900px]:rounded-sm
                    ${active === s.id ? 'text-[#7b2fa0] font-semibold' : 'text-[#555] hover:text-[#7b2fa0]'}`}>
                  {s.label}
                </a>
              ))}
            </nav>
          </aside>

          {/* Main */}
          <main className="pt-10 pl-10 max-[900px]:pl-0 max-[900px]:pt-8">
            {services.map(svc => (
              <section key={svc.id} id={svc.id} className="mb-[60px] pb-[60px] border-b border-[#7b2fa0]/12 last:border-b-0 last:mb-0">
                {/* Banner */}
                <div className="w-full h-[180px] relative flex flex-col items-start justify-end p-6 mb-6 overflow-hidden"
                  style={{ background: 'linear-gradient(135deg,#2d1054 0%,#7b2fa0 60%,#b040d8 100%)' }}>
                  <div className="absolute inset-0" style={{ background: 'linear-gradient(to top,rgba(0,0,0,0.55) 0%,transparent 60%)' }} />
                  <div className="relative z-10">
                    <h2 className="font-serif text-[28px] font-normal tracking-[3px] text-white mb-1">{svc.label}</h2>
                    <p className="text-[11px] text-[#f5c040] tracking-[1px]">{svc.sub}</p>
                  </div>
                </div>
                <p className="text-xs text-[#555] mb-5 leading-[1.7]">{svc.intro}</p>
                {svc.categories.map(cat => (
                  <div key={cat.title} className="mb-6">
                    <p className="font-sans text-[10px] font-bold tracking-[2px] text-[#7b2fa0] uppercase mb-2.5 pb-1.5 border-b border-[#7b2fa0]/20">{cat.title}</p>
                    <div className="grid grid-cols-2 gap-x-10 max-[900px]:grid-cols-1">
                      {cat.items.map(([name, price]) => (
                        <div key={name} className="flex justify-between items-baseline py-[7px] border-b border-black/5 gap-3">
                          <span className="text-xs text-[#333] flex-1">{name}</span>
                          <span className="font-sans text-xs font-semibold text-[#7b2fa0] whitespace-nowrap">{price}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </section>
            ))}
          </main>
        </div>
      </section>

      <Footer />
    </div>
  )
}
