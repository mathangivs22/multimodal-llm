import { useEffect, useRef } from "react";

/** Call `fn` every `ms` while `active` is true. Always calls the latest `fn`. */
export function usePolling(fn, active, ms) {
  const latest = useRef(fn);
  latest.current = fn;
  useEffect(() => {
    if (!active) return undefined;
    const id = setInterval(() => latest.current(), ms);
    return () => clearInterval(id);
  }, [active, ms]);
}
