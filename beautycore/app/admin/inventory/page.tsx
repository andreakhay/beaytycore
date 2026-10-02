'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  Search,
  Plus,
  Minus,
  Trash2,
  Loader2,
  Package,
  X,
  AlertTriangle,
} from 'lucide-react';
import {
  PageHeader,
  Card,
  EmptyState,
  Skeleton,
  formatDate,
  formatPeso,
} from '@/components/ui';
import type { ProductStatus } from '@/db/schema';

interface Item {
  id: string;
  productName: string;
  category: string;
  currentStock: number;
  minimumThreshold: number;
  unitPrice: number | null;
  status: ProductStatus;
  lastRestocked: string | null;
}

const statusStyle: Record<ProductStatus, string> = {
  in_stock: 'border-success/30 bg-success/10 text-success',
  low_stock: 'border-warning/30 bg-warning/10 text-warning',
  out_of_stock: 'border-error/30 bg-error/10 text-error',
};

const statusLabel: Record<ProductStatus, string> = {
  in_stock: 'In stock',
  low_stock: 'Low',
  out_of_stock: 'Out',
};

export default function AdminInventoryPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [busy, setBusy] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  const [form, setForm] = useState({
    productName: '',
    category: '',
    currentStock: '0',
    minimumThreshold: '10',
    unitPrice: '',
  });

  const load = () => {
    fetch('/api/inventory')
      .then((r) => r.json())
      .then((d) => setItems(d.inventory ?? []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const adjustStock = async (item: Item, delta: number) => {
    const next = Math.max(0, item.currentStock + delta);
    setBusy(item.id);
    try {
      const res = await fetch('/api/inventory', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: item.id, currentStock: next }),
      });
      const d = await res.json();
      if (res.ok) setItems((xs) => xs.map((x) => (x.id === item.id ? d.item : x)));
    } finally {
      setBusy(null);
    }
  };

  const remove = async (id: string) => {
    if (!confirm('Remove this product?')) return;
    setBusy(id);
    try {
      const res = await fetch(`/api/inventory?id=${id}`, { method: 'DELETE' });
      if (res.ok) setItems((xs) => xs.filter((x) => x.id !== id));
    } finally {
      setBusy(null);
    }
  };

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy('new');
    try {
      const res = await fetch('/api/inventory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          productName: form.productName,
          category: form.category,
          currentStock: Number(form.currentStock),
          minimumThreshold: Number(form.minimumThreshold),
          unitPrice: form.unitPrice ? Number(form.unitPrice) : null,
        }),
      });
      if (res.ok) {
        setShowAdd(false);
        setForm({ productName: '', category: '', currentStock: '0', minimumThreshold: '10', unitPrice: '' });
        load();
      }
    } finally {
      setBusy(null);
    }
  };

  const categories = useMemo(
    () => ['all', ...Array.from(new Set(items.map((i) => i.category))).sort()],
    [items]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((i) => {
      if (category !== 'all' && i.category !== category) return false;
      return !q || i.productName.toLowerCase().includes(q);
    });
  }, [items, query, category]);

  const alertCount = items.filter((i) => i.currentStock <= i.minimumThreshold).length;

  return (
    <>
      <PageHeader
        title="Inventory"
        subtitle={`${items.length} products · ${alertCount} need restocking`}
        action={
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 bg-gold px-5 py-2.5 text-[10px] font-semibold uppercase tracking-[1.5px] text-card transition-colors hover:bg-gold-hover"
          >
            <Plus size={13} />
            Add Product
          </button>
        }
      />

      {/* Add form */}
      {showAdd && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}>
          <Card className="mb-6">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-serif text-lg text-white">New Product</h3>
              <button onClick={() => setShowAdd(false)} aria-label="Close" className="text-muted hover:text-white">
                <X size={16} />
              </button>
            </div>
            <form onSubmit={add} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {[
                { key: 'productName', label: 'Product name', type: 'text', required: true },
                { key: 'category', label: 'Category', type: 'text', required: true },
                { key: 'currentStock', label: 'Stock', type: 'number', required: true },
                { key: 'minimumThreshold', label: 'Min threshold', type: 'number', required: true },
                { key: 'unitPrice', label: 'Unit price (₱)', type: 'number', required: false },
              ].map((f) => (
                <div key={f.key}>
                  <label className="mb-1.5 block text-[10px] uppercase tracking-wide text-muted">
                    {f.label}
                  </label>
                  <input
                    type={f.type}
                    required={f.required}
                    min={f.type === 'number' ? 0 : undefined}
                    value={form[f.key as keyof typeof form]}
                    onChange={(e) => setForm((s) => ({ ...s, [f.key]: e.target.value }))}
                    className="w-full rounded-sm border border-purple-light/20 bg-surface/40 px-3 py-2 text-[13px] text-white focus:border-purple-light focus:outline-none"
                  />
                </div>
              ))}
              <div className="sm:col-span-2 lg:col-span-5">
                <button
                  type="submit"
                  disabled={busy === 'new'}
                  className="flex items-center gap-2 bg-gold px-5 py-2.5 text-[10px] font-semibold uppercase tracking-[1.5px] text-card transition-colors hover:bg-gold-hover disabled:opacity-50"
                >
                  {busy === 'new' ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />}
                  Add
                </button>
              </div>
            </form>
          </Card>
        </motion.div>
      )}

      {/* Controls */}
      <div className="mb-6 flex flex-wrap gap-3">
        <div className="relative min-w-[240px] flex-1">
          <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search products…"
            className="w-full rounded-sm border border-purple-light/20 bg-surface/40 py-2.5 pl-9 pr-4 text-[13px] text-white placeholder-muted focus:border-purple-light focus:outline-none"
          />
        </div>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-sm border border-purple-light/20 bg-surface/40 px-4 py-2.5 text-[13px] text-white focus:border-purple-light focus:outline-none"
        >
          {categories.map((c) => (
            <option key={c} value={c}>
              {c === 'all' ? 'All categories' : c}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-44 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState icon={Package} title="No products match" />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((item, i) => {
            const alert = item.currentStock <= item.minimumThreshold;
            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: Math.min(i * 0.03, 0.25) }}
              >
                <Card className={`h-full ${alert ? 'border-warning/25' : ''}`}>
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="mb-1 text-[13px] font-medium leading-snug text-white">
                        {item.productName}
                      </h3>
                      <p className="text-[10px] uppercase tracking-wide text-muted">
                        {item.category}
                      </p>
                    </div>
                    <span
                      className={`shrink-0 rounded-full border px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide ${statusStyle[item.status]}`}
                    >
                      {statusLabel[item.status]}
                    </span>
                  </div>

                  <div className="mb-4 flex items-baseline gap-2">
                    <span className={`font-serif text-3xl ${alert ? 'text-warning' : 'text-white'}`}>
                      {item.currentStock}
                    </span>
                    <span className="text-[11px] text-muted">
                      / min {item.minimumThreshold}
                    </span>
                    {alert && <AlertTriangle size={13} className="text-warning" />}
                  </div>

                  <div className="mb-4 flex items-center justify-between text-[11px] text-muted">
                    <span>{formatPeso(item.unitPrice)} each</span>
                    {item.lastRestocked && <span>{formatDate(item.lastRestocked)}</span>}
                  </div>

                  <div className="flex items-center gap-2 border-t border-purple-light/10 pt-3">
                    <button
                      onClick={() => adjustStock(item, -1)}
                      disabled={busy === item.id || item.currentStock === 0}
                      aria-label="Decrease stock"
                      className="rounded-sm border border-purple-light/25 p-1.5 text-muted transition-colors hover:text-white disabled:opacity-40"
                    >
                      <Minus size={12} />
                    </button>
                    <button
                      onClick={() => adjustStock(item, 1)}
                      disabled={busy === item.id}
                      aria-label="Increase stock"
                      className="rounded-sm border border-purple-light/25 p-1.5 text-muted transition-colors hover:text-white disabled:opacity-40"
                    >
                      <Plus size={12} />
                    </button>
                    <button
                      onClick={() => adjustStock(item, 10)}
                      disabled={busy === item.id}
                      className="rounded-sm border border-purple-light/25 px-2.5 py-1.5 text-[10px] font-medium uppercase tracking-wide text-muted transition-colors hover:text-white disabled:opacity-40"
                    >
                      +10
                    </button>
                    <button
                      onClick={() => remove(item.id)}
                      disabled={busy === item.id}
                      aria-label="Delete product"
                      className="ml-auto rounded-sm border border-error/30 p-1.5 text-error transition-colors hover:bg-error/10 disabled:opacity-40"
                    >
                      {busy === item.id ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <Trash2 size={12} />
                      )}
                    </button>
                  </div>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}
    </>
  );
}
