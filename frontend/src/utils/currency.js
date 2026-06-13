export function detectCurrency() {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz === 'Asia/Calcutta' || tz === 'Asia/Kolkata') return 'INR';
    return 'USD';
  } catch { return 'INR'; }
}

// Billing rail for a currency. INR settles through Razorpay (India, UPI/cards/
// netbanking); every other currency checks out through Paddle, which acts as
// Merchant of Record for the rest of the world (collects + remits global tax).
export function railForCurrency(currency) {
  return currency === 'INR' ? 'razorpay' : 'paddle';
}

export const PRICES = {
  INR: { pro: '₹999', elite: '₹1,999', period: '/mo', lifetimePro: '₹11,999', lifetimeElite: '₹19,999' },
  USD: { pro: '$15',  elite: '$25',     period: '/mo', lifetimePro: '$149',     lifetimeElite: '$249'    },
};
