export function detectCurrency() {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz === 'Asia/Calcutta' || tz === 'Asia/Kolkata') return 'INR';
    return 'USD';
  } catch { return 'INR'; }
}

export const PRICES = {
  INR: { pro: '₹799', elite: '₹1,599', period: '/mo', lifetimePro: '₹7,999', lifetimeElite: '₹14,999' },
  USD: { pro: '$9',   elite: '$18',     period: '/mo', lifetimePro: '$89',    lifetimeElite: '$169'     },
};
