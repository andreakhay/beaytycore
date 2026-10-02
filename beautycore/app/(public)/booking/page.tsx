import { Suspense } from 'react';
import type { Metadata } from 'next';
import { Loader2 } from 'lucide-react';
import BookingForm from './booking-form';

export const metadata: Metadata = {
  title: 'Book an Appointment',
  description:
    "Book a hair, nail, facial, or massage appointment at Andrea's Aesthetic & Wellness Clinic in Daet.",
};

export default function BookingPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 size={24} className="animate-spin text-gold" />
        </div>
      }
    >
      <BookingForm />
    </Suspense>
  );
}
