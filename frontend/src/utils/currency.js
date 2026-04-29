export function detectCurrency() {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz === 'Asia/Calcutta' || tz === 'Asia/Kolkata') return 'INR';
    return 'USD';
  } catch { return 'INR'; }
}

export const PRICES = {
  INR: { pro: '₹999', elite: '₹1,999', period: '/mo', lifetimePro: '₹11,999', lifetimeElite: '₹19,999' },
  USD: { pro: '$12',  elite: '$22',     period: '/mo', lifetimePro: '$129',     lifetimeElite: '$229'    },
};
