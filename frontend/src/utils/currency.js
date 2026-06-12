export function detectCurrency() {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz === 'Asia/Calcutta' || tz === 'Asia/Kolkata') return 'INR';
    return 'USD';
  } catch { return 'INR'; }
}

// Currencies the checkout supports. Each maps to a billing rail (see railForCurrency).
export const SUPPORTED_CURRENCIES = ['INR', 'USD'];

const CURRENCY_STORAGE_KEY = 'datathink.currency';

// The user's explicit currency choice (from the pricing-page selector) wins over
// geo-detection and persists across surfaces, so the chosen billing rail is
// consistent everywhere — the landing pricing table AND every in-app upgrade
// button. Falls back to timezone detection on first visit / privacy mode.
export function getStoredCurrency() {
  try {
    const stored = window.localStorage.getItem(CURRENCY_STORAGE_KEY);
    if (stored && SUPPORTED_CURRENCIES.includes(stored)) return stored;
  } catch { /* ignore — SSR or storage disabled */ }
  return detectCurrency();
}

export function setStoredCurrency(currency) {
  if (!SUPPORTED_CURRENCIES.includes(currency)) return;
  try { window.localStorage.setItem(CURRENCY_STORAGE_KEY, currency); } catch { /* ignore */ }
}

// Billing rail for a currency. INR settles through Razorpay (India, UPI/cards/
// netbanking); every other currency checks out through Paddle, which acts as
// Merchant of Record for the rest of the world (collects + remits global tax).
export function railForCurrency(currency) {
  return currency === 'INR' ? 'razorpay' : 'paddle';
}

export const PRICES = {
  INR: { pro: '₹999', elite: '₹1,999', period: '/mo', lifetimePro: '₹11,999', lifetimeElite: '₹19,999' },
  USD: { pro: '$12',  elite: '$22',     period: '/mo', lifetimePro: '$129',     lifetimeElite: '$229'    },
};
