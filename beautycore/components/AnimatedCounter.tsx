'use client';

import { useEffect, useRef, useState } from 'react';
import { animate } from 'framer-motion';

/**
 * Counts up to `value` once the component mounts (or the value changes).
 * Falls back to rendering the final number when the user prefers reduced motion.
 */
export default function AnimatedCounter({
  value,
  prefix = '',
  duration = 1.1,
}: {
  value: number;
  prefix?: string;
  duration?: number;
}) {
  const [display, setDisplay] = useState(0);
  const previous = useRef(0);

  useEffect(() => {
    const reduce =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reduce) {
      setDisplay(value);
      previous.current = value;
      return;
    }

    const controls = animate(previous.current, value, {
      duration,
      ease: 'easeOut',
      onUpdate: (v) => setDisplay(Math.round(v)),
    });

    previous.current = value;
    return () => controls.stop();
  }, [value, duration]);

  return (
    <span>
      {prefix}
      {display.toLocaleString('en-PH')}
    </span>
  );
}
