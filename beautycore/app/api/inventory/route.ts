import { NextResponse } from 'next/server';
import { eq, asc } from 'drizzle-orm';
import { db } from '@/db';
import { inventory, productStatusEnum, type ProductStatus } from '@/db/schema';
import { requireRole } from '@/lib/auth';

/** Keeps `status` consistent with the stock numbers. */
function deriveStatus(stock: number, threshold: number): ProductStatus {
  if (stock <= 0) return 'out_of_stock';
  if (stock <= threshold) return 'low_stock';
  return 'in_stock';
}

/** GET /api/inventory — admin and stylists can read. */
export async function GET() {
  try {
    const session = await requireRole(['admin', 'stylist']);
    if (!session) {
      return NextResponse.json({ error: 'Not allowed.' }, { status: 403 });
    }

    const rows = await db
      .select()
      .from(inventory)
      .orderBy(asc(inventory.category), asc(inventory.productName));

    return NextResponse.json({ inventory: rows });
  } catch (error) {
    console.error('[api/inventory GET]', error);
    return NextResponse.json({ error: 'Could not load inventory.' }, { status: 500 });
  }
}

/** POST /api/inventory — admin only. */
export async function POST(req: Request) {
  try {
    const session = await requireRole(['admin']);
    if (!session) {
      return NextResponse.json({ error: 'Admins only.' }, { status: 403 });
    }

    const body = await req.json();
    const productName = String(body.productName ?? '').trim();
    const category = String(body.category ?? '').trim();

    if (!productName || !category) {
      return NextResponse.json(
        { error: 'Product name and category are required.' },
        { status: 400 }
      );
    }

    const currentStock = Number(body.currentStock ?? 0);
    const minimumThreshold = Number(body.minimumThreshold ?? 10);

    if (!Number.isFinite(currentStock) || currentStock < 0) {
      return NextResponse.json({ error: 'Invalid stock value.' }, { status: 400 });
    }

    const [created] = await db
      .insert(inventory)
      .values({
        productName: productName.slice(0, 255),
        category: category.slice(0, 100),
        currentStock,
        minimumThreshold,
        unitPrice: body.unitPrice != null ? Number(body.unitPrice) : null,
        status: deriveStatus(currentStock, minimumThreshold),
        lastRestocked: new Date(),
      })
      .returning();

    return NextResponse.json({ item: created }, { status: 201 });
  } catch (error) {
    console.error('[api/inventory POST]', error);
    return NextResponse.json({ error: 'Could not add product.' }, { status: 500 });
  }
}

/** PATCH /api/inventory — update stock or details. Admin only. */
export async function PATCH(req: Request) {
  try {
    const session = await requireRole(['admin']);
    if (!session) {
      return NextResponse.json({ error: 'Admins only.' }, { status: 403 });
    }

    const body = await req.json();
    const id = String(body.id ?? '');
    if (!id) {
      return NextResponse.json({ error: 'Product id is required.' }, { status: 400 });
    }

    const existing = await db.query.inventory.findFirst({
      where: eq(inventory.id, id),
    });
    if (!existing) {
      return NextResponse.json({ error: 'Product not found.' }, { status: 404 });
    }

    const updates: Partial<typeof inventory.$inferInsert> = {};

    if (body.productName != null) updates.productName = String(body.productName).slice(0, 255);
    if (body.category != null) updates.category = String(body.category).slice(0, 100);
    if (body.unitPrice != null) updates.unitPrice = Number(body.unitPrice);

    const stock =
      body.currentStock != null ? Number(body.currentStock) : existing.currentStock;
    const threshold =
      body.minimumThreshold != null
        ? Number(body.minimumThreshold)
        : existing.minimumThreshold;

    if (body.currentStock != null) {
      if (!Number.isFinite(stock) || stock < 0) {
        return NextResponse.json({ error: 'Invalid stock value.' }, { status: 400 });
      }
      updates.currentStock = stock;
      // Treat an increase as a restock.
      if (stock > existing.currentStock) updates.lastRestocked = new Date();
    }
    if (body.minimumThreshold != null) updates.minimumThreshold = threshold;

    // Explicit status wins; otherwise keep it in step with the numbers.
    if (body.status && productStatusEnum.enumValues.includes(body.status)) {
      updates.status = body.status;
    } else if (body.currentStock != null || body.minimumThreshold != null) {
      updates.status = deriveStatus(stock, threshold);
    }

    const [updated] = await db
      .update(inventory)
      .set(updates)
      .where(eq(inventory.id, id))
      .returning();

    return NextResponse.json({ item: updated });
  } catch (error) {
    console.error('[api/inventory PATCH]', error);
    return NextResponse.json({ error: 'Could not update product.' }, { status: 500 });
  }
}

/** DELETE /api/inventory?id=... — admin only. */
export async function DELETE(req: Request) {
  try {
    const session = await requireRole(['admin']);
    if (!session) {
      return NextResponse.json({ error: 'Admins only.' }, { status: 403 });
    }

    const id = new URL(req.url).searchParams.get('id');
    if (!id) {
      return NextResponse.json({ error: 'Product id is required.' }, { status: 400 });
    }

    const removed = await db
      .delete(inventory)
      .where(eq(inventory.id, id))
      .returning({ id: inventory.id });

    if (removed.length === 0) {
      return NextResponse.json({ error: 'Product not found.' }, { status: 404 });
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('[api/inventory DELETE]', error);
    return NextResponse.json({ error: 'Could not delete product.' }, { status: 500 });
  }
}
