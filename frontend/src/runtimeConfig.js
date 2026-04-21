function readRuntimeConfig() {
  if (typeof window === 'undefined') {
    return {};
  }
  return window.__APP_CONFIG__ ?? {};
}

export function getRuntimeConfig(key) {
  const runtimeValue = readRuntimeConfig()[key];
  if (typeof runtimeValue === 'string' && runtimeValue.trim()) {
    return runtimeValue.trim();
  }

  const envValue = import.meta.env[key];
  if (typeof envValue === 'string' && envValue.trim()) {
    return envValue.trim();
  }

  return '';
}