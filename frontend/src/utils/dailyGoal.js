/**
 * Daily goal tracking — global, day-scoped, event-driven.
 *
 * Persists in localStorage under 'dt-daily-solves' as { date: "YYYY-MM-DD", count: N }.
 * Resets at local midnight (date is compared against today's local calendar day).
 * Fires a 'dt-daily-solves-changed' CustomEvent on every increment so live listeners update.
 */

const STORAGE_KEY = 'dt-daily-solves';
const EVENT_NAME = 'dt-daily-solves-changed';

/** Returns today's date as "YYYY-MM-DD" in local time (not UTC). */
function localToday() {
  return new Date().toLocaleDateString('en-CA'); // 'en-CA' gives YYYY-MM-DD
}

/**
 * Returns the number of distinct practice questions the user has newly solved today.
 * Returns 0 if nothing is stored or if the stored date is not today (stale → treat as 0).
 */
export function getDailySolves() {
  if (typeof window === 'undefined') return 0;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return 0;
    const parsed = JSON.parse(raw);
    if (!parsed || parsed.date !== localToday()) return 0;
    return typeof parsed.count === 'number' ? parsed.count : 0;
  } catch {
    return 0;
  }
}

/**
 * Increments today's solve count by 1.
 * If the stored date is not today (or nothing stored), resets count to 1 first.
 * Dispatches a 'dt-daily-solves-changed' CustomEvent so listeners can update live.
 * Returns the new count.
 */
export function incrementDailySolves() {
  if (typeof window === 'undefined') return 0;
  try {
    const today = localToday();
    let current = { date: today, count: 0 };
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && parsed.date === today && typeof parsed.count === 'number') {
          current = parsed;
        }
      }
    } catch {
      // If parse fails, start fresh for today
    }
    const next = { date: today, count: current.count + 1 };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    window.dispatchEvent(new CustomEvent(EVENT_NAME));
    return next.count;
  } catch {
    return 0;
  }
}

export { EVENT_NAME };
