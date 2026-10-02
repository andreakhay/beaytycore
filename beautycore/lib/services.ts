/**
 * Service catalogue for Andrea's Aesthetic & Wellness Clinic.
 *
 * Single source of truth — used by the public services page, the booking
 * form, and the stylist services screen. Prices are Philippine pesos;
 * "Mula" = "from", "Libre" = "free", "Konsultasyon" = consultation.
 */

export interface ServiceItem {
  name: string;
  price: string;
}

export interface ServiceCategory {
  title: string;
  items: ServiceItem[];
}

export interface ServiceGroup {
  id: string;
  label: string;
  sub: string;
  intro: string;
  /** Maps to appointments.serviceType. */
  serviceType: 'hair' | 'nail' | 'treatment' | 'massage' | 'aesthetic';
  categories: ServiceCategory[];
}

const item = (name: string, price: string): ServiceItem => ({ name, price });

export const serviceGroups: ServiceGroup[] = [
  {
    id: 'japanese-head-spa',
    label: 'Japanese Head Spa',
    sub: 'Scalp treatment & deep relaxation ritual',
    serviceType: 'treatment',
    intro:
      'Experience the ancient Japanese art of scalp care. Our head spa treatments combine deep cleansing, nourishing scalp massage, and premium hair treatments to restore balance and promote healthy hair growth.',
    categories: [
      {
        title: 'Signature Treatments',
        items: [
          item('Classic Head Spa (60 min)', '₱850'),
          item('Deep Cleanse Head Spa (75 min)', '₱1,100'),
          item('Scalp Detox Treatment', '₱750'),
          item('Premium Head Spa (90 min)', '₱1,350'),
          item('Scalp Analysis & Treatment', '₱950'),
          item('Hydrating Scalp Ritual', '₱900'),
        ],
      },
      {
        title: 'Add-Ons',
        items: [
          item('Aromatherapy Enhancement', '₱150'),
          item('Hot Oil Treatment', '₱200'),
          item('Neck & Shoulder Massage', '₱250'),
          item('Hair Mask Treatment', '₱300'),
        ],
      },
    ],
  },
  {
    id: 'hair-design',
    label: 'Hair Design',
    sub: 'Cuts, colour & styling by expert stylists',
    serviceType: 'hair',
    intro:
      'Our talented stylists bring your vision to life with precision cuts, vibrant colour, and flawless styling. From everyday looks to special occasion transformations, we deliver results that exceed expectations.',
    categories: [
      {
        title: 'Cuts & Styling',
        items: [
          item("Women's Cut & Blowdry", '₱350'),
          item("Men's Cut", '₱180'),
          item("Children's Cut (under 12)", '₱150'),
          item('Blowdry & Style', '₱250'),
          item('Updo / Special Occasion', '₱500'),
          item('Bridal Hair', 'Mula ₱1,500'),
          item('Keratin Treatment', 'Mula ₱2,500'),
          item('Hair Extensions Consult', 'Libre'),
        ],
      },
      {
        title: 'Colour Services',
        items: [
          item('Full Colour', 'Mula ₱800'),
          item('Highlights (Full)', 'Mula ₱1,200'),
          item('Highlights (Partial)', 'Mula ₱700'),
          item('Balayage', 'Mula ₱1,500'),
          item('Toner / Gloss', '₱350'),
          item('Colour Correction', 'Konsultasyon'),
        ],
      },
    ],
  },
  {
    id: 'face-laser',
    label: 'Face & Laser',
    sub: 'Advanced aesthetic treatments for radiant skin',
    serviceType: 'aesthetic',
    intro:
      'Our medical-grade facial and laser treatments are performed by certified aesthetic specialists. We use the latest technology to address a wide range of skin concerns with safe, effective, and long-lasting results.',
    categories: [
      {
        title: 'Facial Treatments',
        items: [
          item('Classic Facial (60 min)', '₱600'),
          item('HydraFacial', '₱1,800'),
          item('Microdermabrasion', '₱1,200'),
          item('Chemical Peel (Light)', '₱1,000'),
          item('Chemical Peel (Medium)', '₱1,500'),
          item('LED Light Therapy', '₱700'),
          item('Microneedling', '₱2,500'),
          item('PRP Facial', '₱4,500'),
        ],
      },
      {
        title: 'Laser Treatments',
        items: [
          item('Laser Hair Removal – Face', 'Mula ₱800'),
          item('Laser Hair Removal – Body', 'Mula ₱1,500'),
          item('Laser Skin Resurfacing', 'Mula ₱3,500'),
          item('IPL Photofacial', '₱2,200'),
          item('Pigmentation Treatment', 'Mula ₱1,800'),
          item('Vascular Treatment', 'Mula ₱2,000'),
        ],
      },
    ],
  },
  {
    id: 'nail-studio',
    label: 'Nail Studio',
    sub: 'Manicures, pedicures & nail art',
    serviceType: 'nail',
    intro:
      'Indulge in our full range of nail services, from classic manicures to intricate nail art. Our nail technicians use only premium, long-lasting products to keep your nails looking flawless.',
    categories: [
      {
        title: 'Manicure Services',
        items: [
          item('Classic Manicure', '₱180'),
          item('Gel Manicure', '₱350'),
          item('Acrylic Full Set', '₱650'),
          item('Acrylic Infill', '₱450'),
          item('Gel Extensions', '₱750'),
          item('Nail Art (per nail)', 'Mula ₱50'),
          item('Gel Removal', '₱150'),
          item('Nail Repair', '₱80'),
        ],
      },
      {
        title: 'Pedicure Services',
        items: [
          item('Classic Pedicure', '₱220'),
          item('Gel Pedicure', '₱400'),
          item('Spa Pedicure (60 min)', '₱550'),
          item('Luxury Pedicure (75 min)', '₱750'),
          item('Callus Treatment', '₱200'),
          item('Paraffin Wax Add-On', '₱150'),
        ],
      },
    ],
  },
  {
    id: 'massage-therapy',
    label: 'Massage Therapy',
    sub: 'Therapeutic & relaxation massage',
    serviceType: 'massage',
    intro:
      'Our certified massage therapists offer a range of therapeutic and relaxation massages tailored to your individual needs. Whether you seek relief from tension or simply wish to unwind, we have the perfect treatment for you.',
    categories: [
      {
        title: 'Full Body Massage',
        items: [
          item('Swedish Massage (60 min)', '₱600'),
          item('Swedish Massage (90 min)', '₱850'),
          item('Deep Tissue (60 min)', '₱700'),
          item('Deep Tissue (90 min)', '₱950'),
          item('Hot Stone Massage (75 min)', '₱900'),
          item('Aromatherapy Massage', '₱750'),
        ],
      },
      {
        title: 'Targeted Treatments',
        items: [
          item('Back, Neck & Shoulder (30 min)', '₱350'),
          item('Foot Reflexology (45 min)', '₱450'),
          item('Prenatal Massage (60 min)', '₱650'),
          item('Sports Massage (60 min)', '₱700'),
        ],
      },
    ],
  },
];

/** Flat list for booking dropdowns. */
export const allServices = serviceGroups.flatMap((g) =>
  g.categories.flatMap((c) =>
    c.items.map((i) => ({
      ...i,
      groupId: g.id,
      groupLabel: g.label,
      serviceType: g.serviceType,
    }))
  )
);

/** "Mula ₱1,500" -> 1500. Returns null for "Libre" / "Konsultasyon". */
export function parsePrice(price: string): number | null {
  const m = price.match(/₱([\d,]+)/);
  return m ? Number(m[1].replace(/,/g, '')) : null;
}
