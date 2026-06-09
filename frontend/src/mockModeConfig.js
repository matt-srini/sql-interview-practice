// The 7 universal follow-up (chain pivot) dimensions — canonical source:
// docs/concept-taxonomy.md §"The 7 universal follow-up dimensions". `label` is the
// human-readable name shown in the pivot card heading and analytics; `blurb` is the
// interviewer-voiced framing shown in the pivot card body.
export const FOLLOW_UP_DIMENSIONS = {
  scale_pivot:         { label: 'Scale',            blurb: 'The interviewer pushes the data far past what your first answer assumed. Does your approach still hold?' },
  business_rule_pivot: { label: 'Business rules',   blurb: 'A business rule just changed. Adapt your solution to the new requirement.' },
  ambiguity_pivot:     { label: 'Ambiguity',        blurb: 'The ask is deliberately underspecified now. State your assumptions, then proceed.' },
  edge_case_pivot:     { label: 'Edge cases',       blurb: 'The interviewer probes the cases your first answer glossed over.' },
  performance_pivot:   { label: 'Performance',      blurb: 'It works — now make it efficient under real-world constraints.' },
  data_quality_pivot:  { label: 'Data quality',     blurb: 'The data is dirtier than implied. Handle what your first answer assumed away.' },
  stakeholder_pivot:   { label: 'Stakeholder needs',blurb: 'A stakeholder with a different agenda enters. How does that change what you deliver?' },
};

// Some chain children in the bank use the `_pivot`-less form of the same dimension; alias them.
const DIMENSION_ALIASES = {
  data_quality: 'data_quality_pivot',
  business_rule: 'business_rule_pivot',
  performance: 'performance_pivot',
  ambiguity: 'ambiguity_pivot',
  edge_case: 'edge_case_pivot',
  stakeholder: 'stakeholder_pivot',
  scale: 'scale_pivot',
};

function resolveDimension(token) {
  if (!token) return null;
  const key = DIMENSION_ALIASES[token] || token;
  return FOLLOW_UP_DIMENSIONS[key] || null;
}

// Always returns a human string — never a raw snake_case token. Unknown tokens
// (e.g. a drifted `abstraction_pivot`) are humanized: strip a trailing `_pivot`,
// replace underscores with spaces, capitalize the first letter.
export function dimensionLabel(token) {
  const d = resolveDimension(token);
  if (d) return d.label;
  if (!token) return '';
  const s = String(token).replace(/_pivot$/, '').replace(/_/g, ' ').trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

export function dimensionBlurb(token) {
  const d = resolveDimension(token);
  return d ? d.blurb : 'The interviewer shifts focus to a different dimension of the same problem.';
}

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
  'pandas': {
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

// Mixed-track benchmark blueprints per role (mirrors MIXED_BENCHMARK_CONFIGS on the backend)
export const MIXED_BENCHMARK_BLUEPRINTS = {
  data_analyst: {
    timeMinutes: 55,
    summary: '4 questions across SQL · Pandas · Statistics',
    description: 'Role-based benchmark calibrated for analytical workflows.',
  },
  data_engineer: {
    timeMinutes: 55,
    summary: '4 questions across SQL · Python · PySpark · Data Engineering',
    description: 'Role-based benchmark covering the full data-engineering tool stack.',
  },
  analytics_engineer: {
    timeMinutes: 55,
    summary: '4 questions across SQL · Data Modeling · Pandas',
    description: 'Role-based benchmark for modeling, transformation, and analytical SQL.',
  },
  data_scientist: {
    timeMinutes: 55,
    summary: '4 questions across Python · Pandas · Statistics · ML Fundamentals',
    description: 'Role-based benchmark spanning modeling, statistics, and algorithmic implementation.',
  },
};

export function supportsBenchmarkMode(track) {
  return track === 'mixed' || Boolean(track && BENCHMARK_BLUEPRINTS[track]);
}

export function getBenchmarkBlueprint(track, role) {
  if (track === 'mixed') return role ? (MIXED_BENCHMARK_BLUEPRINTS[role] ?? null) : null;
  return BENCHMARK_BLUEPRINTS[track] ?? null;
}

export function getMockModeDisplayLabel(mode) {
  if (mode === 'benchmark') return 'Benchmark';
  if (mode === 'interview_loop') return 'Interview Loop';
  if (mode === 'custom') return 'Custom drill';
  if (mode === '60min') return 'Full (legacy)';
  // legacy label kept for history rendering
  if (mode === '30min') return 'Sprint drill';
  return mode;
}

export function isBenchmarkMockMode(mode) {
  return mode === 'benchmark';
}

/**
 * Returns the three mode cards shown in MockHub.
 * plan is used to derive locked state for plan-gated modes (Custom, Interview Loop).
 */
export function getMockModeCards(track, plan = 'free') {
  const normalised = plan?.replace('lifetime_', '') ?? 'free';
  const isElite = normalised === 'elite';
  const isPro = normalised === 'pro' || isElite;

  // Benchmark is always available as a card; for mixed track it requires role selection
  const benchmarkCard = {
    key: 'benchmark',
    label: 'Benchmark',
    sublabel: track === 'mixed'
      ? '55 min · Role-based mix'
      : (BENCHMARK_BLUEPRINTS[track]
          ? `${BENCHMARK_BLUEPRINTS[track].timeMinutes} min · ${BENCHMARK_BLUEPRINTS[track].summary}`
          : 'Select a track to see blueprint'),
    desc: track === 'mixed'
      ? 'Role-based fixed-shape benchmark across your track mix.'
      : (BENCHMARK_BLUEPRINTS[track]
          ? 'Fixed-shape benchmark session'
          : 'Benchmark mode requires a single track.'),
    disabled: false,
    locked: false,
    lockedReason: null,
    requiredTier: null,
  };

  const customCard = {
    key: 'custom',
    label: 'Custom drill',
    sublabel: isPro ? 'You choose' : 'Pro+',
    desc: 'Tune time and depth for targeted follow-up practice.',
    disabled: false,
    locked: !isPro,
    lockedReason: isPro ? null : 'Custom drills require a Pro or Elite plan.',
    requiredTier: 'pro',
  };

  const loopCard = {
    key: 'interview_loop',
    label: 'Interview Loop',
    sublabel: isElite ? 'Chain of follow-ups' : 'Elite only',
    desc: 'One iterative chain — the interviewer digs deeper after each answer.',
    disabled: track === 'mixed',
    locked: !isElite,
    lockedReason: isElite ? null : 'Interview Loop requires an Elite plan.',
    requiredTier: 'elite',
  };

  return [benchmarkCard, customCard, loopCard];
}

export function getSessionQuestionCount(mode, track, customCount, role) {
  if (mode === 'benchmark') {
    if (track === 'mixed') {
      // All role blueprints have 4 slots
      return 4;
    }
    return getBenchmarkBlueprint(track)?.numQuestions ?? 0;
  }
  if (mode === '60min') return 3;
  if (mode === 'custom') return customCount;
  // interview_loop: variable (chain length shown after start)
  return customCount;
}

export function getSessionTimeMinutes(mode, track, customMinutes, role) {
  if (mode === 'benchmark') {
    if (track === 'mixed') {
      return MIXED_BENCHMARK_BLUEPRINTS[role]?.timeMinutes ?? 55;
    }
    return getBenchmarkBlueprint(track)?.timeMinutes ?? 0;
  }
  if (mode === '60min') return 60;
  if (mode === 'custom') return customMinutes;
  if (mode === 'interview_loop') return null; // determined at session start
  return customMinutes;
}

export function getMockSessionDescriptor(mode, track, role) {
  const modeLabel = getMockModeDisplayLabel(mode);
  const benchmark = getBenchmarkBlueprint(track, role);

  if (mode === 'benchmark') {
    if (track === 'mixed' && role && benchmark) {
      return {
        modeLabel,
        phaseLabel: 'Benchmark session',
        title: 'Role-based mixed benchmark',
        summaryLine: `${benchmark.summary} · ${benchmark.timeMinutes} min fixed session`,
        description: benchmark.description,
        isBenchmark: true,
      };
    }
    if (benchmark) {
      return {
        modeLabel,
        phaseLabel: 'Benchmark session',
        title: 'Fixed-shape track benchmark',
        summaryLine: `${benchmark.summary} · ${benchmark.timeMinutes} min fixed session`,
        description: benchmark.description,
        isBenchmark: true,
      };
    }
  }

  if (mode === 'interview_loop') {
    return {
      modeLabel,
      phaseLabel: 'Interview Loop',
      title: 'Iterative interview chain',
      summaryLine: '1 chain · 15 min per question',
      description: 'Simulates a real interview: the interviewer follows up on your answer, probing deeper with each round.',
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

  // legacy read-only
  if (mode === '30min') {
    return {
      modeLabel,
      phaseLabel: 'Legacy drill session',
      title: 'Legacy sprint drill',
      summaryLine: '2 questions · 30 min cap',
      description: 'Older sprint sessions remain reviewable. New sessions use Custom drill instead.',
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

export function getMockSetupDescriptor(mode, track, customCount, customMinutes, role) {
  const descriptor = getMockSessionDescriptor(mode, track, role);

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

  if (mode === 'interview_loop') {
    return {
      ...descriptor,
      sectionLabel: 'Loop setup',
      summaryLine: '1 chain · 15 min per question',
      detailLines: [
        'The full chain is drawn at session start — you cannot skip follow-ups.',
        'Chains are consumed once and do not repeat.',
      ],
    };
  }

  if (mode === 'custom') {
    const questionLabel = `${customCount} question${customCount === 1 ? '' : 's'}`;
    return {
      ...descriptor,
      sectionLabel: 'Drill plan',
      summaryLine: `${questionLabel} · ${customMinutes} min cap`,
      detailLines: [],
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

  if (mode === '30min') {
    return {
      ...descriptor,
      sectionLabel: 'Drill plan',
      summaryLine: '2 questions · 30 min cap',
      detailLines: [
        'Legacy sprint sessions remain reviewable. New sessions use Custom drill instead.',
      ],
    };
  }

  return {
    ...descriptor,
    sectionLabel: 'Session setup',
    detailLines: [],
  };
}
