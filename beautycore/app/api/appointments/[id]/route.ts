import { NextResponse } from 'next/server';
import { eq, and } from 'drizzle-orm';
import { db } from '@/db';
import { appointments, appointmentStatusEnum, type AppointmentStatus } from '@/db/schema';
import { getSession } from '@/lib/auth';

/** PATCH /api/appointments/:id — update status or details. */
export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: 'Not signed in.' }, { status: 401 });
    }

    const { id } = await params;
    const body = await req.json();

    const existing = await db.query.appointments.findFirst({
      where: eq(appointments.id, id),
    });
    if (!existing) {
      return NextResponse.json({ error: 'Appointment not found.' }, { status: 404 });
    }

    // Clients may only touch their own booking, and only to cancel it.
    if (session.role === 'client') {
      if (existing.clientId !== session.userId) {
        return NextResponse.json({ error: 'Not allowed.' }, { status: 403 });
      }
      if (body.status && body.status !== 'cancelled') {
        return NextResponse.json(
          { error: 'You can only cancel your own appointment.' },
          { status: 403 }
        );
      }
    }

    // Stylists may only update appointments assigned to them.
    if (session.role === 'stylist' && existing.stylistId !== session.userId) {
      return NextResponse.json({ error: 'Not allowed.' }, { status: 403 });
    }

    const updates: Partial<typeof appointments.$inferInsert> = {};

    if (body.status) {
      if (!appointmentStatusEnum.enumValues.includes(body.status as AppointmentStatus)) {
        return NextResponse.json({ error: 'Invalid status.' }, { status: 400 });
      }
      updates.status = body.status;
    }
    if (typeof body.notes === 'string') updates.notes = body.notes.slice(0, 1000);
    if (body.appointmentDate && session.role !== 'client') {
      const d = new Date(body.appointmentDate);
      if (Number.isNaN(d.getTime())) {
        return NextResponse.json({ error: 'Invalid date.' }, { status: 400 });
      }
      updates.appointmentDate = d;
    }

    if (Object.keys(updates).length === 0) {
      return NextResponse.json({ error: 'Nothing to update.' }, { status: 400 });
    }

    const [updated] = await db
      .update(appointments)
      .set(updates)
      .where(eq(appointments.id, id))
      .returning();

    return NextResponse.json({ appointment: updated });
  } catch (error) {
    console.error('[api/appointments PATCH]', error);
    return NextResponse.json({ error: 'Could not update.' }, { status: 500 });
  }
}

/** DELETE /api/appointments/:id — admin only. */
export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSession();
    if (!session || session.role !== 'admin') {
      return NextResponse.json({ error: 'Not allowed.' }, { status: 403 });
    }

    const { id } = await params;
    const removed = await db
      .delete(appointments)
      .where(eq(appointments.id, id))
      .returning({ id: appointments.id });

    if (removed.length === 0) {
      return NextResponse.json({ error: 'Appointment not found.' }, { status: 404 });
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('[api/appointments DELETE]', error);
    return NextResponse.json({ error: 'Could not delete.' }, { status: 500 });
  }
}
