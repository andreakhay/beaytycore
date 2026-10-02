import { NextResponse } from 'next/server';
import { sql, eq, gte, and, desc } from 'drizzle-orm';
import { db } from '@/db';
import { appointments, inventory, users } from '@/db/schema';
import { requireRole } from '@/lib/auth';

/**
 * GET /api/admin/stats — dashboard aggregates.
 *
 * Revenue counts completed appointments only, so pending/cancelled bookings
 * don't inflate the figure.
 */
export async function GET() {
  try {
    const session = await requireRole(['admin']);
    if (!session) {
      return NextResponse.json({ error: 'Admins only.' }, { status: 403 });
    }

    const startOfMonth = new Date();
    startOfMonth.setDate(1);
    startOfMonth.setHours(0, 0, 0, 0);

    const [
      revenueRow,
      monthRevenueRow,
      bookingsRow,
      stylistsRow,
      lowStockItems,
      statusBreakdown,
      topServices,
    ] = await Promise.all([
      db
        .select({ total: sql<number>`coalesce(sum(total_price), 0)::int` })
        .from(appointments)
        .where(eq(appointments.status, 'completed')),

      db
        .select({ total: sql<number>`coalesce(sum(total_price), 0)::int` })
        .from(appointments)
        .where(
          and(
            eq(appointments.status, 'completed'),
            gte(appointments.appointmentDate, startOfMonth)
          )
        ),

      db.select({ n: sql<number>`count(*)::int` }).from(appointments),

      db
        .select({ n: sql<number>`count(*)::int` })
        .from(users)
        .where(eq(users.role, 'stylist')),

      db
        .select({
          id: inventory.id,
          productName: inventory.productName,
          category: inventory.category,
          currentStock: inventory.currentStock,
          minimumThreshold: inventory.minimumThreshold,
          status: inventory.status,
        })
        .from(inventory)
        .where(sql`current_stock <= minimum_threshold`)
        .orderBy(inventory.currentStock),

      db
        .select({
          status: appointments.status,
          n: sql<number>`count(*)::int`,
        })
        .from(appointments)
        .groupBy(appointments.status),

      db
        .select({
          serviceName: appointments.serviceName,
          serviceType: appointments.serviceType,
          bookings: sql<number>`count(*)::int`,
          revenue: sql<number>`coalesce(sum(total_price), 0)::int`,
        })
        .from(appointments)
        .groupBy(appointments.serviceName, appointments.serviceType)
        .orderBy(desc(sql`count(*)`))
        .limit(8),
    ]);

    const clientsRow = await db
      .select({ n: sql<number>`count(*)::int` })
      .from(users)
      .where(eq(users.role, 'client'));

    return NextResponse.json({
      stats: {
        totalRevenue: revenueRow[0]?.total ?? 0,
        monthRevenue: monthRevenueRow[0]?.total ?? 0,
        totalBookings: bookingsRow[0]?.n ?? 0,
        activeStylists: stylistsRow[0]?.n ?? 0,
        totalClients: clientsRow[0]?.n ?? 0,
        lowStockCount: lowStockItems.length,
      },
      lowStockItems,
      statusBreakdown,
      topServices,
    });
  } catch (error) {
    console.error('[api/admin/stats]', error);
    return NextResponse.json({ error: 'Could not load stats.' }, { status: 500 });
  }
}
