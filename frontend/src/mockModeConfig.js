export const BENCHMARK_BLUEPRINTS = {
  sql: {
    numQuestions: 3,
    timeMinutes: 60,
    summary: '3 executable problems',
    description: 'Fixed-shape SQL benchmark focused on applied query construction under pressure.',
  },
  python: {
    numQuestions: 2,
    timeMinutes: 50,
    summary: '2 executable problems',
    description: 'Fixed-shape Python benchmark with deeper algorithmic or data-processing problems.',
  },
  'python-data': {
    numQuestions: 2,
    timeMinutes: 50,
    summary: '2 executable problems',
    description: 'Fixed-shape Pandas benchmark with end-to-end dataframe manipulation tasks.',
  },
  statistics: {
    numQuestions: 3,
    timeMinutes: 45,
    summary: '1 numerical + 2 conceptual',
    description: 'Mixed statistics benchmark combining numerical execution with reasoning questions.',
  },
  pyspark: {
    numQuestions: 6,
    timeMinutes: 40,
    summary: '6 code-adjacent reasoning prompts',
    description: 'Code-adjacent Spark benchmark across execution behavior, debugging, and trade-offs.',
  },
  'data-engineering': {
    numQuestions: 6,
    timeMinutes: 40,
    summary: '6 constructed reasoning prompts',
    description: 'System design and operational judgment benchmark for real data-platform trade-offs.',
  },
  'data-modeling': {
    numQuestions: 5,
    timeMinutes: 40,
    summary: '5 constructed reasoning prompts',
    description: 'Data-model design benchmark across grain, dimensions, and schema trade-offs.',
  },
  'ml-fundamentals': {
    numQuestions: 6,
    timeMinutes: 40,
    summary: '6 constructed reasoning prompts',
    description: 'Applied ML reasoning benchmark across evaluation, diagnostics, and production judgment.',
  },
  experimentation: {
    numQuestions: 6,
    timeMinutes: 40,
    summary: '6 constructed reasoning prompts',
    description: 'Experiment design and causal-inference benchmark under product decision pressure.',
  },
};

export function supportsBenchmarkMode(track) {
  return Boolean(track && BENCHMARK_BLUEPRINTS[track]);
}

export function getBenchmarkBlueprint(track) {
  return BENCHMARK_BLUEPRINTS[track] ?? null;
}

export function getMockModeDisplayLabel(mode) {
  if (mode === 'benchmark') return 'Benchmark';
  if (mode === '30min') return 'Sprint drill';
  if (mode === 'custom') return 'Custom drill';
  if (mode === '60min') return 'Full (legacy)';
  return mode;
}

export function isBenchmarkMockMode(mode) {
  return mode === 'benchmark';
}

export function getMockModeCards(track) {
  const benchmark = getBenchmarkBlueprint(track);

  return [
    {
      key: 'benchmark',
      label: 'Benchmark',
      sublabel: benchmark ? `${benchmark.timeMinutes} min · ${benchmark.summary}` : 'Single-track only',
      desc: benchmark ? 'Fixed-shape benchmark session' : 'Benchmark mode is available on single-track mocks only.',
      disabled: !benchmark,
    },
    {
      key: '30min',
      label: 'Sprint drill',
      sublabel: '30 min · 2 questions',
      desc: 'Short diagnostic session for speed and calibration.',
      disabled: false,
    },
    {
      key: 'custom',
      label: 'Custom drill',
      sublabel: 'You choose',
      desc: 'Tune time and depth for targeted follow-up practice.',
      disabled: false,
    },
  ];
}

export function getSessionQuestionCount(mode, track, customCount) {
  if (mode === 'benchmark') return getBenchmarkBlueprint(track)?.numQuestions ?? 0;
  if (mode === '30min') return 2;
  if (mode === '60min') return 3;
  if (mode === 'custom') return customCount;
  return customCount;
}

export function getSessionTimeMinutes(mode, track, customMinutes) {
  if (mode === 'benchmark') return getBenchmarkBlueprint(track)?.timeMinutes ?? 0;
  if (mode === '30min') return 30;
  if (mode === '60min') return 60;
  if (mode === 'custom') return customMinutes;
  return customMinutes;
}

export function getMockSessionDescriptor(mode, track) {
  const modeLabel = getMockModeDisplayLabel(mode);
  const benchmark = getBenchmarkBlueprint(track);

  if (mode === 'benchmark' && benchmark) {
    return {
      modeLabel,
      phaseLabel: 'Benchmark session',
      title: 'Fixed-shape track benchmark',
      summaryLine: `${benchmark.summary} · ${benchmark.timeMinutes} min fixed session`,
      description: benchmark.description,
      isBenchmark: true,
    };
  }

  if (mode === '30min') {
    return {
      modeLabel,
      phaseLabel: 'Drill session',
      title: 'Short calibration drill',
      summaryLine: '2 questions · 30 min cap',
      description: 'Use sprint drills to pressure-test pace, warm up before a benchmark, or quickly diagnose weak spots.',
      isBenchmark: false,
    };
  }

  if (mode === 'custom') {
    return {
      modeLabel,
      phaseLabel: 'Drill session',
      title: 'Custom follow-up drill',
      summaryLine: 'Flexible timing and scope',
      description: 'Use custom drills when you want to tune depth, duration, or concept coverage after reviewing a benchmark.',
      isBenchmark: false,
    };
  }

  if (mode === '60min') {
    return {
      modeLabel,
      phaseLabel: 'Legacy drill session',
      title: 'Legacy full-length drill',
      summaryLine: '3 questions · 60 min cap',
      description: 'Older full-length sessions remain reviewable, but new setup flows now separate benchmark and drill more explicitly.',
      isBenchmark: false,
    };
  }

  return {
    modeLabel,
    phaseLabel: 'Mock session',
    title: 'Interview session',
    summaryLine: '',
    description: '',
    isBenchmark: false,
  };
}

export function getMockSetupDescriptor(mode, track, customCount, customMinutes) {
  const descriptor = getMockSessionDescriptor(mode, track);

  if (mode === 'benchmark') {
    return {
      ...descriptor,
      sectionLabel: 'Benchmark setup',
      summaryLine: descriptor.summaryLine,
      detailLines: [
        'Track-specific fixed shape for clean score comparisons over time.',
      ],
    };
  }

  if (mode === '30min') {
    return {
      ...descriptor,
      sectionLabel: 'Drill plan',
      summaryLine: '2 questions · 30 min cap',
      detailLines: [
        'Best for a short calibration round, a warm-up, or a quick pace check.',
        'Drills stay separated from benchmark analytics so experimentation does not muddy comparability.',
      ],
    };
  }

  if (mode === 'custom') {
    const questionLabel = `${customCount} question${customCount === 1 ? '' : 's'}`;
    return {
      ...descriptor,
      sectionLabel: 'Drill plan',
      summaryLine: `${questionLabel} · ${customMinutes} min cap`,
      detailLines: [
        'Tune scope and time after a benchmark when you want to isolate one weakness.',
        'Use custom drills for follow-up practice without changing the benchmark baseline.',
      ],
    };
  }

  if (mode === '60min') {
    return {
      ...descriptor,
      sectionLabel: 'Drill plan',
      summaryLine: '3 questions · 60 min cap',
      detailLines: [
        'Legacy full-length drills remain reviewable, but new setup now favors benchmark plus focused drills.',
      ],
    };
  }

  return {
    ...descriptor,
    sectionLabel: 'Session setup',
    detailLines: [],
  };
}