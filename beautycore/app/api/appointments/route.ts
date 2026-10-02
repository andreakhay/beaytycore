import { NextResponse } from 'next/server';
import { eq, and, desc, gte } from 'drizzle-orm';
import { db } from '@/db';
import { appointments, users } from '@/db/schema';
import { getSession } from '@/lib/auth';

/**
 * GET /api/appointments
 *
 * Scoped by role:
 *   client  -> their own bookings
 *   stylist -> bookings assigned to them
 *   admin   -> everything
 *
 * Query: ?upcoming=true to exclude past dates.
 */
export async function GET(req: Request) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: 'Not signed in.' }, { status: 401 });
    }

    const { searchParams } = new URL(req.url);
    const upcomingOnly = searchParams.get('upcoming') === 'true';

    const filters = [];
    if (session.role === 'client') {
      filters.push(eq(appointments.clientId, session.userId));
    } else if (session.role === 'stylist') {
      filters.push(eq(appointments.stylistId, session.userId));
    }
    if (upcomingOnly) {
      filters.push(gte(appointments.appointmentDate, new Date()));
    }

    const rows = await db.query.appointments.findMany({
      where: filters.length ? and(...filters) : undefined,
      with: {
        client: { columns: { id: true, name: true, email: true } },
        stylist: { columns: { id: true, name: true } },
      },
      orderBy: [desc(appointments.appointmentDate)],
    });

    return NextResponse.json({ appointments: rows });
  } catch (error) {
    console.error('[api/appointments GET]', error);
    return NextResponse.json(
      { error: 'Could not load appointments.' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/appointments — create a booking.
 *
 * Body: { serviceName, serviceType, appointmentDate, stylistId?, totalPrice?, notes? }
 */
export async function POST(req: Request) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json(
        { error: 'Please sign in to book an appointment.' },
        { status: 401 }
      );
    }

    const body = await req.json();
    const { serviceName, serviceType, appointmentDate, stylistId, totalPrice, notes } =
      body ?? {};

    if (!serviceName || !serviceType || !appointmentDate) {
      return NextResponse.json(
        { error: 'Service and date are required.' },
        { status: 400 }
      );
    }

    const when = new Date(appointmentDate);
    if (Number.isNaN(when.getTime())) {
      return NextResponse.json({ error: 'Invalid date.' }, { status: 400 });
    }
    if (when.getTime() < Date.now()) {
      return NextResponse.json(
        { error: 'Please choose a future date and time.' },
        { status: 400 }
      );
    }

    // Only accept a stylistId that really belongs to a stylist.
    let assignedStylist: string | null = null;
    if (stylistId) {
      const stylist = await db.query.users.findFirst({
        where: and(eq(users.id, stylistId), eq(users.role, 'stylist')),
        columns: { id: true },
      });
      assignedStylist = stylist?.id ?? null;
    }

    // Clients always book for themselves; staff may book on a client's behalf.
    const clientId =
      session.role === 'client' ? session.userId : (body.clientId ?? session.userId);

    const [created] = await db
      .insert(appointments)
      .values({
        clientId,
        stylistId: assignedStylist,
        serviceName: String(serviceName).slice(0, 255),
        serviceType: String(serviceType).slice(0, 100),
        appointmentDate: when,
        status: 'pending',
        totalPrice: typeof totalPrice === 'number' ? totalPrice : null,
        notes: notes ? String(notes).slice(0, 1000) : null,
      })
      .returning();

    return NextResponse.json({ appointment: created }, { status: 201 });
  } catch (error) {
    console.error('[api/appointments POST]', error);
    return NextResponse.json(
      { error: 'Could not create the appointment.' },
      { status: 500 }
    );
  }
}
