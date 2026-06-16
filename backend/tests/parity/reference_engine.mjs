/**
 * Signal Scout — Intelligence Engine
 * 12-layer signal-to-noise detection, scoring, and ranking
 * Runs in Cloudflare Workers and modern browsers (ESM)
 *
 * Formula inputs (weighted):
 *   Emergence (0.30) = L1 × 0.6 + L4 × 0.4
 *   Relevance  (0.25) = L10 × 0.6 + L5 × 0.4
 *   Authority  (0.20) = L7
 *   Question Gap (0.15) = L3
 *   Velocity   (0.10) = L8
 * Post-formula multipliers: L6 × L9 × L12
 * Overrides: L2 floors at 0.90 · L11 zeros out
 */

'use strict';

// ─────────────────────────────────────────────────────────────────────────────
// CONFIGURATION
// ─────────────────────────────────────────────────────────────────────────────

const THOUGHT_LEADERS = {
  tier0: {
    weight: 0.97,
    names:   ['andrej karpathy', 'karpathy', 'andrew ng', 'andrewng',
               'jensen huang', 'sam altman', 'samaltman', 'demis hassabis'],
    handles: ['@karpathy', '@andrewng', '@jensenh', '@sama', '@demishassabis'],
  },
  tier1: {
    weight: 0.92,
    names:   ['ibm research', 'snowflake', 'databricks', 'anthropic', 'openai', 'caroline roche'],
    domains: ['research.ibm.com', 'snowflake.com', 'databricks.com',
               'anthropic.com', 'openai.com'],
  },
};

const ANALYST_ORGS = [
  'gartner', 'forrester', 'mckinsey', 'idc', 'everest group', 'hfs research',
  // Added: expanded analyst set wired via RSS feeds
  'hbr', 'technologyreview', 'harvard business review',
];

const PRACTITIONER_DOMAINS = [
  'news.ycombinator.com', 'reddit.com', 'stackoverflow.com',
  'medium.com', 'substack.com', 'dev.to',
];

const COMPETITORS = ['accenture', 'deloitte', 'mckinsey', 'bcg', 'pwc'];

// [month, day] pairs (1-indexed)
const CONFERENCE_CALENDAR = [
  { name: 'IBM Think',        start: [5,  5],  end: [5,  8],  topics: ['enterprise ai','cloud','data','watson'] },
  { name: 'Google I/O',       start: [5, 14],  end: [5, 15],  topics: ['ai','ml','gemini','vertex'] },
  { name: 'Data+AI Summit',   start: [6,  9],  end: [6, 12],  topics: ['databricks','spark','lakehouse','mlops'] },
  { name: 'Snowflake Summit', start: [6,  2],  end: [6,  5],  topics: ['snowflake','data cloud','analytics'] },
  { name: 'Dreamforce',       start: [9, 16],  end: [9, 19],  topics: ['salesforce','crm','ai','data cloud'] },
  { name: 'AWS re:Invent',    start: [12, 1],  end: [12, 5],  topics: ['aws','cloud','data engineering'] },
  { name: 'NeurIPS',          start: [12, 9],  end: [12,15],  topics: ['ml','ai research','deep learning','neural'] },
];

const SCORING_WEIGHTS = {
  emergencePosition:  0.30,
  relevanceDepth:     0.25,
  sourceAuthority:    0.20,
  questionGapBonus:   0.15,
  velocityTrajectory: 0.10,
};

const ROUTING_THRESHOLDS = { IMMEDIATE: 0.85, ROUTE: 0.70, DIGEST: 0.50 };

const PLATFORM_BASELINES = {
  linkedin: { reactions: 150, comments: 25,  shares: 30 },
  youtube:  { reactions: 500, comments: 80,  shares: 50 },
  reddit:   { reactions: 200, comments: 60,  shares: 0  },
  hn:       { reactions: 100, comments: 40,  shares: 0  },
  twitter:  { reactions: 300, comments: 30,  shares: 80 },
  blog:     { reactions: 50,  comments: 10,  shares: 20 },
  paper:    { reactions: 20,  comments: 5,   shares: 15 },
};

const SOURCE_INITIAL_TRUST = {
  'hbr.org': 0.88,       'mit.edu': 0.90,         'stanford.edu': 0.90,
  'nature.com': 0.92,    'arxiv.org': 0.85,        'acm.org': 0.87,
  'gartner.com': 0.82,   'forrester.com': 0.82,    'mckinsey.com': 0.80,
  'news.ycombinator.com': 0.76, 'reddit.com': 0.62, 'medium.com': 0.58,
  'dev.to': 0.60,        'substack.com': 0.60,
  'openai.com': 0.88,    'anthropic.com': 0.88,    'research.ibm.com': 0.87,
  'snowflake.com': 0.80, 'databricks.com': 0.80,   'deepmind.google': 0.90,
};

const HAKKODA_DOMAIN_TERMS = [
  'snowflake','databricks','data engineering','data platform','lakehouse',
  'data mesh','data fabric','mlops','feature store','data governance',
  'ai governance','enterprise ai','ai implementation','agentic ai',
  'llm','rag','fine-tuning','prompt engineering','frugal ai','small language model','data strategy',
  'modern data stack','cloud data','data migration','dbt','airflow',
  'data quality','observability','data catalog','metadata management',
];

// Layer 11 — Noise Filter
const NOISE_PATTERNS = [
  /^(press release|for immediate release|we are pleased|proud to announce|introducing our)/i,
  /\b(sponsored|advertisement|advertorial|partner content|paid promotion)\b/i,
];

// Layer 12 — Hype Cycle
const MAINSTREAM_DOMAINS = [
  'techcrunch.com','forbes.com','businessinsider.com','wired.com','theverge.com',
  'venturebeat.com','wsj.com','nytimes.com','zdnet.com','fortune.com','bloomberg.com',
];
const HYPE_VOCAB      = ['revolutionary','game-changing','unprecedented','disrupts','breakthrough','transforms everything','next big thing','game changer'];
const TROUGH_VOCAB    = ['fails','overhyped','reality check','not ready','limited','disappointing','hype died','struggled','fell short'];
const PRACTICAL_VOCAB = ['tutorial','how to','implementation','best practice','case study','lessons learned','production','step by step','hands-on','deploying','building'];
const PLATEAU_VOCAB   = ['standard','established','commodity','table stakes','baseline','widely adopted','mature','expected','de facto'];

// ─────────────────────────────────────────────────────────────────────────────
// STATE STORE  (swap get/set for Cloudflare KV in production)
// ─────────────────────────────────────────────────────────────────────────────

class StateStore {
  constructor(initial = {}) {
    this._data = Object.assign({
      conceptHistory:      {},  // { concept: [{ ts, count }] }
      questionClusters:    {},  // { fp: { question, count, sources, answered } }
      sourceTrust:         {},  // { domain: { score, hits, misses, signals } }
      topicSentiment:      {},  // { topic: { analyst: number[], practitioner: number[] } }
      competitorCoverage:  {},  // { topic: string[] }
      platformTopicWindow: {},  // { topic: [{ platform, ts }] }
    }, initial);
  }
  get(key)      { return this._data[key]; }
  set(key, val) { this._data[key] = val; }
  snapshot()    { return JSON.parse(JSON.stringify(this._data)); }
  restore(snap) { this._data = snap; }
}

// ─────────────────────────────────────────────────────────────────────────────
// UTILITIES
// ─────────────────────────────────────────────────────────────────────────────

const clamp    = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));
const normalize = (v, min, max) => max === min ? 0 : clamp((v - min) / (max - min));

const STOPWORDS = new Set([
  'the','a','an','and','or','but','in','on','at','to','for','of','with',
  'by','from','as','is','are','was','were','be','been','have','has','had',
  'do','does','did','will','would','could','should','this','that','it','its',
  'we','you','he','she','they','our','your','their','i','me','my',
]);

function tokenize(text) {
  return (text || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter(t => t.length > 2);
}

function extractQuestions(text) {
  return (text || '')
    .split(/(?<=[.!?])\s+|[\n]+/)
    .filter(s => {
      const t = s.trim();
      return t.endsWith('?') ||
        /^(what|why|how|when|where|who|which|can|could|should|is|are|do|does|will|would)\b/i.test(t);
    })
    .map(s => s.trim())
    .filter(s => s.length > 10);
}

function questionFingerprint(question) {
  return tokenize(question)
    .filter(t => !STOPWORDS.has(t))
    .sort()
    .slice(0, 8)
    .join('|');
}

function jaccardSim(arrA, arrB) {
  const a = new Set(arrA), b = new Set(arrB);
  let inter = 0;
  for (const x of a) if (b.has(x)) inter++;
  const union = a.size + b.size - inter;
  return union === 0 ? 0 : inter / union;
}

function simpleSentiment(text) {
  const POS = ['breakthrough','revolutionary','transformative','success','growth',
               'adoption','improve','opportunity','innovative','leader','efficient'];
  const NEG = ['fail','failure','hype','overhyped','broken','risk','struggle',
               'concern','disappointment','unreliable','bias','problem','challenge'];
  const tokens = tokenize(text);
  let pos = 0, neg = 0;
  for (const t of tokens) {
    if (POS.some(p => t.includes(p))) pos++;
    if (NEG.some(n => t.includes(n))) neg++;
  }
  const total = pos + neg || 1;
  return (pos - neg) / total; // -1..1
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 1 — EMERGENCE DETECTION
// ─────────────────────────────────────────────────────────────────────────────
// Identifies topics in the critical 5% window: past "too early" but before
// mainstream saturation. Uses 45-day rolling windows to position each concept
// on the hype cycle and derive an emergence score.

function detectEmergence(signal, store) {
  const history = store.get('conceptHistory');
  const now     = signal.timestamp;
  const topics  = signal.topics || [];

  const topicScores = [];

  for (const topic of topics) {
    const key = topic.toLowerCase().trim();
    if (!history[key]) history[key] = [];

    // Weight by engagement so saturation reflects actual audience volume, not just mention count.
    // log2 scale: 0 pts→1, 3pts→2, 7pts→3, 63pts→6, 1023pts→10. Academic papers default to 1.
    const engPts = (signal.engagement?.reactions ?? signal.engagement?.points ?? 0)
                 + (signal.engagement?.comments ?? 0);
    const engWeight = Math.max(1, Math.round(Math.log2(1 + engPts)));
    history[key].push({ ts: now, count: engWeight });

    // Prune to 90-day window
    const cutoff90 = now - 90 * 86400000;
    history[key]   = history[key].filter(e => e.ts > cutoff90);

    const entries = history[key];

    if (entries.length < 3) {
      topicScores.push({ topic: key, score: 0.62, stage: 'pre-emergence' });
      continue;
    }

    const midpoint = now - 45 * 86400000;
    const recent   = entries.filter(e => e.ts >= midpoint).length;
    const prior    = entries.filter(e => e.ts  < midpoint).length || 1;

    const growthRate = (recent - prior) / prior;
    const totalHits  = entries.reduce((s, e) => s + e.count, 0);
    const peakWindow = Math.max(...entries.map(e => e.count));
    const saturation = clamp(totalHits / Math.max(peakWindow * entries.length, 1));

    let stage, score;

    if (saturation < 0.20 && growthRate > 0.5) {
      // Pre-emergence: growing fast, still obscure — highest forward value
      stage = 'pre-emergence';
      score = clamp(0.55 + growthRate * 0.25);
    } else if (saturation < 0.50 && growthRate > 0.2) {
      // Emergence window — the critical 5%
      stage = 'emergence';
      score = clamp(0.80 + (0.50 - saturation) * 0.40);
    } else if (saturation < 0.85) {
      // Mainstream — contextualization value only
      stage = 'mainstream';
      score = clamp(0.50 - (saturation - 0.50) * 0.60);
    } else {
      // Saturated — minimal signal value
      stage = 'saturated';
      score = 0.15;
    }

    topicScores.push({ topic: key, score, stage, growthRate, saturation });
  }

  store.set('conceptHistory', history);

  if (!topicScores.length) return { score: 0.50, stage: 'unknown', topics: [] };

  const best = topicScores.reduce((a, b) => (a.score > b.score ? a : b));
  const avg  = topicScores.reduce((s, t) => s + t.score, 0) / topicScores.length;

  return {
    score:  clamp(best.score * 0.60 + avg * 0.40),
    stage:  best.stage,
    topics: topicScores,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 2 — THOUGHT LEADER WATCHLIST
// ─────────────────────────────────────────────────────────────────────────────
// Tier 0/1 activation auto-elevates final score to ≥0.90.

function checkThoughtLeader(signal) {
  // Support both object ({ name, handle }) and legacy plain-string author fields
  const rawAuthor = signal.author;
  const name   = (typeof rawAuthor === 'string' ? rawAuthor : (rawAuthor?.name   || '')).toLowerCase();
  const handle = (typeof rawAuthor === 'string' ? ''        : (rawAuthor?.handle || '')).toLowerCase();
  const domain = (signal.source?.domain || '').toLowerCase();
  const org    = (signal.source?.name   || '').toLowerCase();

  for (const n of THOUGHT_LEADERS.tier0.names) {
    if (name.includes(n) || handle.includes(n.replace(/\s/g, ''))) {
      return { tier: 0, weight: THOUGHT_LEADERS.tier0.weight, matched: n, elevate: true };
    }
  }
  for (const h of THOUGHT_LEADERS.tier0.handles) {
    if (handle === h || handle.includes(h.replace('@', ''))) {
      return { tier: 0, weight: THOUGHT_LEADERS.tier0.weight, matched: h, elevate: true };
    }
  }

  for (const n of THOUGHT_LEADERS.tier1.names) {
    if (name.includes(n) || org.includes(n)) {
      return { tier: 1, weight: THOUGHT_LEADERS.tier1.weight, matched: n, elevate: true };
    }
  }
  for (const d of THOUGHT_LEADERS.tier1.domains) {
    if (domain.includes(d)) {
      return { tier: 1, weight: THOUGHT_LEADERS.tier1.weight, matched: d, elevate: true };
    }
  }

  return { tier: null, weight: 0, matched: null, elevate: false };
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 3 — QUESTION GAP DETECTOR
// ─────────────────────────────────────────────────────────────────────────────
// Questions that appear across multiple sources with no satisfying answer
// represent the highest forward-looking talk track value.

function detectQuestionGaps(signal, store) {
  const clusters = store.get('questionClusters');
  const now      = signal.timestamp;
  const cutoff7d = now - 7  * 86400000;
  const cutoff48 = now - 48 * 3600000;
  const fullText = [signal.title, signal.body].filter(Boolean).join(' ');
  const questions = extractQuestions(fullText);

  let maxGapScore = 0;
  const detected  = [];

  for (const q of questions) {
    const fp = questionFingerprint(q);
    if (!fp) continue;

    if (!clusters[fp]) {
      clusters[fp] = { question: q, count: 0, sources: [], answered: false };
    }

    const cluster = clusters[fp];
    cluster.count++;
    cluster.sources.push({ platform: signal.source?.platform || 'unknown', ts: now });
    cluster.sources = cluster.sources.filter(s => s.ts > cutoff7d);

    const uniquePlatforms = new Set(cluster.sources.map(s => s.platform)).size;
    const recentActivity  = cluster.sources.some(s => s.ts > cutoff48) ? 1.10 : 1.0;

    // Gap score: frequency × cross-platform breadth × unanswered state
    const freqScore     = Math.min(cluster.count, 10) / 10;
    const platformScore = Math.min(uniquePlatforms, 4) / 4;
    const unanswered    = cluster.answered ? 0 : 0.20;
    const gapScore      = clamp((freqScore * 0.40 + platformScore * 0.40 + unanswered) * recentActivity);

    if (gapScore > maxGapScore) maxGapScore = gapScore;
    if (gapScore > 0.30) {
      detected.push({ question: q, score: gapScore, platforms: uniquePlatforms, count: cluster.count });
    }
  }

  store.set('questionClusters', clusters);

  return {
    score:     clamp(maxGapScore),
    questions: detected.sort((a, b) => b.score - a.score).slice(0, 5),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 4 — PRACTITIONER vs. ANALYST DIVERGENCE
// ─────────────────────────────────────────────────────────────────────────────
// High divergence between analyst optimism and practitioner reality is a
// Hakkoda positioning opportunity (e.g. "73% of AI projects fail to reach
// production" vs adoption narratives).

function classifySourceType(signal) {
  // Explicit type set by normalizer takes precedence over domain heuristics.
  // 'competitor' feeds (Accenture, Deloitte, McKinsey) feed the analyst bucket in L4
  // so divergence captures consulting-firm optimism vs. practitioner reality.
  const srcType = signal.source?.type;
  if (srcType === 'analyst' || srcType === 'competitor') return 'analyst';
  if (srcType === 'research' || srcType === 'academic')  return 'research';

  const domain = (signal.source?.domain || '').toLowerCase();
  const org    = (signal.source?.name   || '').toLowerCase();

  if (ANALYST_ORGS.some(a => domain.includes(a) || org.includes(a))) return 'analyst';
  if (PRACTITIONER_DOMAINS.some(d => domain.includes(d)))            return 'practitioner';
  if (domain.endsWith('.edu') || domain.includes('arxiv'))           return 'research';
  return 'practitioner';
}

function measureDivergence(signal, store) {
  const sentiment  = store.get('topicSentiment');
  const sourceType = classifySourceType(signal);
  const fullText   = [signal.title, signal.body].filter(Boolean).join(' ');
  const sig        = simpleSentiment(fullText);
  const topics     = signal.topics || [];

  for (const topic of topics) {
    if (!sentiment[topic]) sentiment[topic] = { analyst: [], practitioner: [] };
    const bucket = sourceType === 'analyst' ? 'analyst' : 'practitioner';
    sentiment[topic][bucket].push(sig);
    if (sentiment[topic][bucket].length > 20) sentiment[topic][bucket].shift();
  }

  store.set('topicSentiment', sentiment);

  let maxDiv = 0;
  const divergentTopics = [];

  for (const topic of topics) {
    const s = sentiment[topic];
    if (!s || s.analyst.length < 2 || s.practitioner.length < 2) continue;

    const avgAnalyst  = s.analyst.reduce((a, b) => a + b, 0) / s.analyst.length;
    const avgPrac     = s.practitioner.reduce((a, b) => a + b, 0) / s.practitioner.length;
    const divergence  = Math.abs(avgAnalyst - avgPrac);

    if (divergence > maxDiv) maxDiv = divergence;
    if (divergence > 0.30) {
      divergentTopics.push({ topic, divergence, analystSentiment: avgAnalyst, practitionerSentiment: avgPrac });
    }
  }

  return {
    score:           clamp(maxDiv),
    sourceType,
    divergentTopics: divergentTopics.sort((a, b) => b.divergence - a.divergence),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 5 — COMPETITIVE GAP INTELLIGENCE
// ─────────────────────────────────────────────────────────────────────────────
// Topics no competitor covers → own the conversation (score 1.0).
// Topics all five cover → add depth (score ~0.20).
// Topics one or two cover → exploit the gap.

function scoreCompetitiveGap(signal, store) {
  const coverage = store.get('competitorCoverage');
  const topics   = signal.topics || [];
  const sourceOrg = (signal.source?.name || signal.author?.name || '').toLowerCase();

  // If this signal originates from a competitor, record their coverage
  for (const comp of COMPETITORS) {
    if (sourceOrg.includes(comp)) {
      for (const topic of topics) {
        if (!coverage[topic]) coverage[topic] = [];
        if (!coverage[topic].includes(comp)) coverage[topic].push(comp);
      }
    }
  }

  store.set('competitorCoverage', coverage);

  const scores = topics.map(topic => {
    const coveredBy  = coverage[topic] ? coverage[topic].length : 0;
    const gapRatio   = 1 - coveredBy / COMPETITORS.length;
    return { topic, gapRatio, coveredBy };
  });

  if (!scores.length) return { score: 0.50, topics: [] };

  const maxGap = Math.max(...scores.map(s => s.gapRatio));
  const avgGap = scores.reduce((s, t) => s + t.gapRatio, 0) / scores.length;

  return { score: clamp(maxGap * 0.70 + avgGap * 0.30), topics: scores };
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 6 — TEMPORAL & CALENDAR INTELLIGENCE
// ─────────────────────────────────────────────────────────────────────────────
// Returns a multiplier (1.0–1.5) applied to the base score after Layer 7.

function getTemporalMultiplier(signal) {
  const date   = new Date(signal.timestamp);
  const month  = date.getMonth() + 1;
  const topics = (signal.topics || []).map(t => t.toLowerCase());

  let multiplier = 1.0;
  const reasons  = [];

  // Q4 compliance/governance season (Oct–Dec)
  if (month >= 10) {
    const govTerms = ['governance','compliance','regulation','policy','risk','audit','security'];
    if (topics.some(t => govTerms.some(g => t.includes(g)))) {
      multiplier = Math.max(multiplier, 1.35);
      reasons.push('Q4 governance season');
    }
  }

  // Year-end predictions window (Nov–Dec)
  if (month >= 11) {
    const predTerms = ['prediction','trend','forecast','2025','2026','2027','future','outlook'];
    if (topics.some(t => predTerms.some(p => t.includes(p)))) {
      multiplier = Math.max(multiplier, 1.25);
      reasons.push('Year-end predictions window');
    }
  }

  // Pre-conference boost (2 weeks before each conference)
  for (const conf of CONFERENCE_CALENDAR) {
    const [cMonth, cDay] = conf.start;
    const confDate  = new Date(date.getFullYear(), cMonth - 1, cDay);
    const daysUntil = Math.ceil((confDate - date) / 86400000);

    if (daysUntil >= 0 && daysUntil <= 14) {
      const topicMatch = conf.topics.some(ct =>
        topics.some(t => t.includes(ct) || ct.includes(t))
      );
      if (topicMatch) {
        const boost = 1.0 + 0.30 * (1 - daysUntil / 14);
        multiplier = Math.max(multiplier, boost);
        reasons.push(`Pre-${conf.name} (${daysUntil}d out)`);
      }
    }
  }

  return { multiplier: clamp(multiplier, 1.0, 1.5), reasons };
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 10 — KEYWORDS  (relevance input for scoring formula)
// ─────────────────────────────────────────────────────────────────────────────

function scoreRelevanceDepth(signal) {
  const fullText = [signal.title, signal.body, ...(signal.topics || [])].join(' ').toLowerCase();
  const tokens   = tokenize(fullText);

  const matches = HAKKODA_DOMAIN_TERMS.filter(term => fullText.includes(term)).length;
  const breadth  = clamp(matches / 5); // 5+ matches = full score

  // Substantive content heuristic: content density via unique token ratio + length
  const uniqueRatio = tokens.length ? new Set(tokens).size / tokens.length : 0;
  const lengthScore = clamp((tokens.length - 50) / 450); // 50–500 token range

  return clamp(breadth * 0.60 + uniqueRatio * 0.20 + lengthScore * 0.20);
}

// ─────────────────────────────────────────────────────────────────────────────
// SCORING FORMULA  (engine mechanic — not a numbered layer)
// ─────────────────────────────────────────────────────────────────────────────
// emergenceInput  = L1 × 0.6 + L4 × 0.4
// relevanceInput  = L10 × 0.6 + L5 × 0.4
// base = emergenceInput×0.30 + relevanceInput×0.25 + L7×0.20 + L3×0.15 + L8×0.10
// Post-formula: base × L6 × L9 × L12  →  floor(L2)  →  zero(L11)

function computeScore({ emergenceInput, relevanceInput, sourceAuthority,
                        questionGapBonus, velocityTrajectory }) {
  const base =
    emergenceInput     * SCORING_WEIGHTS.emergencePosition  +
    relevanceInput     * SCORING_WEIGHTS.relevanceDepth     +
    sourceAuthority    * SCORING_WEIGHTS.sourceAuthority    +
    questionGapBonus   * SCORING_WEIGHTS.questionGapBonus   +
    velocityTrajectory * SCORING_WEIGHTS.velocityTrajectory;
  return { base: clamp(base) };
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 8 — ROUTING THRESHOLDS
// ─────────────────────────────────────────────────────────────────────────────

function routeSignal(finalScore) {
  if (finalScore >= ROUTING_THRESHOLDS.IMMEDIATE) {
    return { tier: 'IMMEDIATE', action: 'Talk track to Ink within 24h',          priority: 'P0', sla: '24h' };
  }
  if (finalScore >= ROUTING_THRESHOLDS.ROUTE) {
    return { tier: 'ROUTE',     action: 'Route to Ink for talk track generation', priority: 'P1', sla: '72h' };
  }
  if (finalScore >= ROUTING_THRESHOLDS.DIGEST) {
    return { tier: 'DIGEST',    action: 'Include in weekly digest',               priority: 'P2', sla: '7d'  };
  }
  return   { tier: 'LOG',       action: 'Logged, not surfaced',                   priority: 'P3', sla: null  };
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 9 — SOURCE TRUST REGISTRY
// ─────────────────────────────────────────────────────────────────────────────
// Trust decays (-0.02) for low-signal submissions, repairs (+0.05) for
// validated signals. New sources enter at neutral 0.55.

function getSourceTrust(signal, store) {
  const trustMap = store.get('sourceTrust');
  const domain   = (signal.source?.domain || '').toLowerCase().replace(/^www\./, '');

  if (!trustMap[domain]) {
    const initial = SOURCE_INITIAL_TRUST[domain] ?? 0.55;
    trustMap[domain] = { score: initial, hits: 0, misses: 0, signals: 0 };
  }

  const entry = trustMap[domain];
  entry.signals++;
  store.set('sourceTrust', trustMap);

  return { score: clamp(entry.score), domain, signals: entry.signals };
}

function updateSourceTrust(domain, wasValuable, store) {
  const trustMap = store.get('sourceTrust');
  const key      = domain.replace(/^www\./, '');
  if (!trustMap[key]) {
    const initial = SOURCE_INITIAL_TRUST[key] ?? 0.55;
    trustMap[key] = { score: initial, hits: 0, misses: 0, signals: 0 };
  }

  const entry = trustMap[key];
  if (wasValuable) {
    entry.hits++;
    entry.score = clamp(entry.score + 0.05, 0, 1.0);
  } else {
    entry.misses++;
    entry.score = clamp(entry.score - 0.02, 0.30, 1.0);
  }

  store.set('sourceTrust', trustMap);
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 10 — ENGAGEMENT VELOCITY
// ─────────────────────────────────────────────────────────────────────────────
// Normalizes engagement against platform-specific baselines to detect
// topics resonating with real audiences right now.

function scoreEngagementVelocity(signal) {
  const platform  = (signal.source?.platform || 'blog').toLowerCase();
  const eng       = signal.engagement || {};
  const baseline  = PLATFORM_BASELINES[platform] || PLATFORM_BASELINES.blog;

  // Age in hours — clamp to at least 0.5 to avoid inflating brand-new content
  const ageHours  = Math.max((Date.now() - signal.timestamp) / 3600000, 0.5);

  const reactionRate = (eng.reactions || 0) / ageHours;
  const commentRate  = (eng.comments  || 0) / ageHours;
  const shareRate    = (eng.shares    || 0) / ageHours;

  // Per-hour baselines (assuming baseline figures are for a 24h-old post)
  const expectedR = baseline.reactions / 24;
  const expectedC = baseline.comments  / 24;
  const expectedS = Math.max(baseline.shares, 1) / 24;

  const rScore = normalize(reactionRate, 0, expectedR * 3);
  const cScore = normalize(commentRate,  0, expectedC * 3);
  const sScore = normalize(shareRate,    0, expectedS * 3);

  const velocity = rScore * 0.40 + cScore * 0.40 + sScore * 0.20;

  return {
    score:    clamp(velocity),
    platform,
    rates:    { reactions: reactionRate, comments: commentRate, shares: shareRate },
    expected: { reactions: expectedR,    comments: expectedC,    shares: expectedS },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 11 — CROSS-PLATFORM HEAT
// ─────────────────────────────────────────────────────────────────────────────
// Same topic trending on 2+ platforms within 48 hours → multiplier applied.
// Single reputable source: strong.  LinkedIn + HN + Reddit + YouTube: fire.

const HEAT_MULTIPLIERS = [1.0, 1.0, 1.30, 1.60, 2.0]; // index = unique platform count

function measureCrossPlatformHeat(signal, store) {
  const window = store.get('platformTopicWindow');
  const now     = signal.timestamp;
  const cutoff  = now - 48 * 3600000;
  const platform = (signal.source?.platform || 'unknown').toLowerCase();
  const topics   = signal.topics || [];

  let maxPlatCount = 1;
  const hotTopics  = [];

  for (const topic of topics) {
    if (!window[topic]) window[topic] = [];

    window[topic].push({ platform, ts: now });
    window[topic] = window[topic].filter(e => e.ts > cutoff);

    const platforms = [...new Set(window[topic].map(e => e.platform))];
    const count     = platforms.length;

    if (count > maxPlatCount) maxPlatCount = count;
    if (count >= 2) {
      hotTopics.push({ topic, platforms, count, sightings: window[topic].length });
    }
  }

  store.set('platformTopicWindow', window);

  const multiplier = HEAT_MULTIPLIERS[Math.min(maxPlatCount, 4)];

  return {
    multiplier,
    platformCount: maxPlatCount,
    hotTopics:     hotTopics.sort((a, b) => b.count - a.count),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 11 — NOISE FILTER  (override: zeros final score to 0 when triggered)
// ─────────────────────────────────────────────────────────────────────────────
// Requires 2+ noise signals before zeroing — prevents false positives.

function detectNoise(signal, store) {
  const fullText   = [signal.title, signal.body].filter(Boolean).join(' ');
  const fullTextLC = fullText.toLowerCase();
  const topics     = signal.topics || [];
  const domain     = (signal.source?.domain || '').toLowerCase().replace(/^www\./, '');
  const trust      = store.get('sourceTrust');
  const reasons    = [];

  if (NOISE_PATTERNS.some(p => p.test(fullText))) reasons.push('promotional content');

  const hasRelevance = HAKKODA_DOMAIN_TERMS.some(t => fullTextLC.includes(t)) || topics.length > 0;
  if (!hasRelevance) reasons.push('no domain relevance');

  const trustEntry = trust[domain];
  if (trustEntry && trustEntry.score < 0.35 && trustEntry.signals >= 5) reasons.push('chronically low-trust source');

  if (tokenize(fullText).length < 8) reasons.push('insufficient content');

  return { isNoise: reasons.length >= 2, reasons };
}

// ─────────────────────────────────────────────────────────────────────────────
// LAYER 12 — GARTNER HYPE CYCLE POSITION  (multiplier: 0.7×–1.5×)
// ─────────────────────────────────────────────────────────────────────────────
// Infers phase from our own accumulated signal data — no Gartner subscription
// needed. Gartner subscription (Tier 2 source) validates position when available.
//
// Innovation Trigger  (1.5×): practitioner-only, not in mainstream press, early growth
// Peak                (0.7×): 3+ platforms + mainstream + hype vocab + rapid growth
// Trough              (1.2×): declining volume, disillusionment vocabulary
// Slope of Enlighten. (1.3×): practical/how-to content rising, practitioners leading
// Plateau             (0.8×): commoditized, flat engagement, established vocabulary

function detectHypeCyclePhase(signal, store) {
  const topics         = signal.topics || [];
  const platformWindow = store.get('platformTopicWindow');
  const conceptHistory = store.get('conceptHistory');
  const sentiment      = store.get('topicSentiment');
  const now            = signal.timestamp;
  const cutoff7d       = now - 7  * 86400000;
  const cutoff30d      = now - 30 * 86400000;

  const fullTextLC   = [signal.title, signal.body].filter(Boolean).join(' ').toLowerCase();
  const sourceDomain = (signal.source?.domain || '').toLowerCase();
  const isMainstream = MAINSTREAM_DOMAINS.some(d => sourceDomain.includes(d));

  const hyypeScore   = HYPE_VOCAB.filter(w    => fullTextLC.includes(w)).length;
  const troughScore  = TROUGH_VOCAB.filter(w  => fullTextLC.includes(w)).length;
  const practScore   = PRACTICAL_VOCAB.filter(w => fullTextLC.includes(w)).length;
  const plateauScore = PLATEAU_VOCAB.filter(w => fullTextLC.includes(w)).length;

  // Cross-platform presence across 7-day window
  let maxPlatforms = 1;
  for (const topic of topics) {
    const recent = (platformWindow[topic] || []).filter(e => e.ts > cutoff7d);
    const n = new Set(recent.map(e => e.platform)).size;
    if (n > maxPlatforms) maxPlatforms = n;
  }

  // Practitioner ratio from accumulated sentiment data
  let totalA = 0, totalP = 0;
  for (const topic of topics) {
    const s = sentiment[topic];
    if (s) { totalA += s.analyst.length; totalP += s.practitioner.length; }
  }
  const practRatio = (totalA + totalP) > 0 ? totalP / (totalA + totalP) : 0.5;

  // Volume growth rate from concept history (30-day window, two 15-day halves)
  let growthRate = 0, saturation = 0.5;
  for (const topic of topics) {
    const history = (conceptHistory[topic.toLowerCase()] || []).filter(e => e.ts > cutoff30d);
    if (history.length >= 4) {
      const mid    = now - 15 * 86400000;
      const recent = history.filter(e => e.ts >= mid).length;
      const prior  = Math.max(history.filter(e => e.ts <  mid).length, 1);
      const gr     = (recent - prior) / prior;
      if (Math.abs(gr) > Math.abs(growthRate)) growthRate = gr;
      const peak   = Math.max(...history.map(e => e.count));
      const total  = history.reduce((s, e) => s + e.count, 0);
      saturation   = Math.max(saturation, clamp(total / Math.max(peak * history.length, 1)));
    }
  }

  let phase, multiplier, confidence;

  if (!isMainstream && maxPlatforms <= 2 && practRatio > 0.70 && growthRate > 0) {
    phase = 'Innovation Trigger'; multiplier = 1.5;
    confidence = clamp(practRatio * Math.min(growthRate + 0.5, 1.0));

  } else if (maxPlatforms >= 3 && isMainstream && hyypeScore > troughScore && growthRate > 0.2) {
    phase = 'Peak of Inflated Expectations'; multiplier = 0.7;
    confidence = clamp(maxPlatforms / 5 * 0.8 + 0.2);

  } else if (troughScore > hyypeScore && (growthRate < -0.1 || saturation > 0.65)) {
    phase = 'Trough of Disillusionment'; multiplier = 1.2;
    confidence = clamp(troughScore / 4 + (growthRate < 0 ? 0.2 : 0));

  } else if (practScore > hyypeScore && practScore > troughScore && practRatio > 0.55 && growthRate > -0.2) {
    phase = 'Slope of Enlightenment'; multiplier = 1.3;
    confidence = clamp(Math.min(practScore, 5) / 5 * practRatio);

  } else if (saturation > 0.70 && plateauScore >= practScore && growthRate <= 0.05) {
    phase = 'Plateau of Productivity'; multiplier = 0.8;
    confidence = clamp(saturation);

  } else {
    phase = 'Innovation Trigger'; multiplier = 1.1; confidence = 0.25;
  }

  return {
    phase, multiplier, confidence,
    signals: { maxPlatforms, practRatio, growthRate, saturation,
               hyypeScore, troughScore, practScore, plateauScore, isMainstream },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// RANKING ENGINE
// ─────────────────────────────────────────────────────────────────────────────

function rankSignals(scoredSignals) {
  return [...scoredSignals].sort((a, b) => {
    // Primary: final score descending
    const scoreDiff = b.scores.final - a.scores.final;
    if (Math.abs(scoreDiff) > 0.01) return scoreDiff;

    // Tiebreak 1: emergence stage (emergence > pre-emergence > mainstream > saturated)
    const stageRank = { emergence: 3, 'pre-emergence': 2, mainstream: 1, saturated: 0, unknown: 0 };
    const stageDiff = (stageRank[b.scores.emergenceStage] || 0) - (stageRank[a.scores.emergenceStage] || 0);
    if (stageDiff !== 0) return stageDiff;

    // Tiebreak 2: TL tier (0 > 1 > null)
    const tlA = a.scores.thoughtLeaderTier ?? 99;
    const tlB = b.scores.thoughtLeaderTier ?? 99;
    if (tlA !== tlB) return tlA - tlB;

    // Tiebreak 3: most recent
    return b.timestamp - a.timestamp;
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// INTELLIGENCE ENGINE  (orchestrator)
// ─────────────────────────────────────────────────────────────────────────────

class IntelligenceEngine {
  constructor(initialState = {}) {
    this.store = new StateStore(initialState);
  }

  /**
   * Run a single signal through all 12 layers.
   * Returns a ScoredSignal with scores, routing decision, and layer trace.
   */
  process(signal) {
    const s = {
      ...signal,
      timestamp: signal.timestamp || Date.now(),
      id:        signal.id        || (typeof crypto !== 'undefined' ? crypto.randomUUID() : Math.random().toString(36).slice(2)),
    };

    const trace = [];

    // ── Formula input layers ───────────────────────────────────────────────
    const L1  = detectEmergence(s, this.store);
    trace.push({ layer: 1,  name: 'Emergence Detection',             score: L1.score,       meta: { stage: L1.stage } });

    const L2  = checkThoughtLeader(s);
    trace.push({ layer: 2,  name: 'Thought Leader Watchlist',        score: L2.weight,      meta: { tier: L2.tier, matched: L2.matched } });

    const L3  = detectQuestionGaps(s, this.store);
    trace.push({ layer: 3,  name: 'Question Gap Detector',           score: L3.score,       meta: { questions: L3.questions.length } });

    const L4  = measureDivergence(s, this.store);
    trace.push({ layer: 4,  name: 'Practitioner/Analyst Divergence', score: L4.score,       meta: { sourceType: L4.sourceType } });

    const L5  = scoreCompetitiveGap(s, this.store);
    trace.push({ layer: 5,  name: 'Competitive Gap Intelligence',    score: L5.score });

    // ── Post-formula multiplier layers ────────────────────────────────────
    const L6  = getTemporalMultiplier(s);
    trace.push({ layer: 6,  name: 'Temporal Intelligence',           score: L6.multiplier,  meta: { reasons: L6.reasons } });

    const L7  = getSourceTrust(s, this.store);
    trace.push({ layer: 7,  name: 'Source Trust',                    score: L7.score,       meta: { domain: L7.domain } });

    const L8  = scoreEngagementVelocity(s);
    trace.push({ layer: 8,  name: 'Engagement Velocity',             score: L8.score,       meta: { platform: L8.platform } });

    const L9  = measureCrossPlatformHeat(s, this.store);
    trace.push({ layer: 9,  name: 'Cross-Platform Heat',             score: L9.multiplier,  meta: { platforms: L9.platformCount } });

    const L10 = scoreRelevanceDepth(s);
    trace.push({ layer: 10, name: 'Keywords',                        score: L10 });

    // ── Override layers ────────────────────────────────────────────────────
    const L11 = detectNoise(s, this.store);
    trace.push({ layer: 11, name: 'Noise Filter',                    score: L11.isNoise ? 0 : 1, meta: { reasons: L11.reasons } });

    const L12 = detectHypeCyclePhase(s, this.store);
    trace.push({ layer: 12, name: 'Hype Cycle Position',             score: L12.multiplier, meta: { phase: L12.phase, confidence: L12.confidence } });

    // ── Scoring formula ────────────────────────────────────────────────────
    const emergenceInput = clamp(L1.score * 0.60 + L4.score * 0.40);
    const relevanceInput = clamp(L10      * 0.60 + L5.score * 0.40);

    const scoring = computeScore({
      emergenceInput,
      relevanceInput,
      sourceAuthority:    L7.score,
      questionGapBonus:   L3.score,
      velocityTrajectory: L8.score,
    });

    // Post-formula multipliers: L6 (temporal) × L9 (heat) × L12 (hype cycle)
    let score = scoring.base * L6.multiplier * L9.multiplier * L12.multiplier;

    // Overrides
    if (L2.elevate)    score = Math.max(score, 0.90); // L2: thought leader floor
    if (L11.isNoise)   score = 0;                      // L11: noise filter zeros out

    const finalScore = clamp(score);
    const routing    = routeSignal(finalScore);

    return {
      ...s,
      scores: {
        emergencePosition:  L1.score,
        emergenceStage:     L1.stage,
        thoughtLeaderBoost: L2.weight,
        thoughtLeaderTier:  L2.tier,
        questionGapBonus:   L3.score,
        divergenceScore:    L4.score,
        competitiveGap:     L5.score,
        temporalMultiplier: L6.multiplier,
        sourceAuthority:    L7.score,
        engagementVelocity: L8.score,
        crossPlatformHeat:  L9.multiplier,
        keywords:           L10,
        noiseFilter:        L11.isNoise,
        hypeCyclePhase:     L12.phase,
        hypeCycleMultiplier: L12.multiplier,
        emergenceInput,
        relevanceInput,
        base:               scoring.base,
        final:              finalScore,
      },
      routing,
      enrichment: {
        emergenceTopics:   L1.topics,
        gapQuestions:      L3.questions,
        divergentTopics:   L4.divergentTopics,
        competitorGaps:    L5.topics,
        temporalReasons:   L6.reasons,
        hotTopics:         L9.hotTopics,
        noiseReasons:      L11.reasons,
        hypeCycleSignals:  L12.signals,
      },
      layerTrace: trace,
    };
  }

  /**
   * Process a batch of signals and return them sorted by final score.
   */
  processBatch(signals) {
    return rankSignals(signals.map(s => this.process(s)));
  }

  /**
   * Feedback loop: mark a signal as high-value or noise.
   * Updates source trust for the signal's domain.
   */
  feedback(signalId, scoredSignals, wasValuable) {
    const signal = scoredSignals.find(s => s.id === signalId);
    if (!signal?.source?.domain) return false;
    updateSourceTrust(signal.source.domain, wasValuable, this.store);
    return true;
  }

  /** Export state snapshot for KV/D1 persistence. */
  exportState()         { return this.store.snapshot(); }

  /** Restore from a previously exported snapshot. */
  importState(snapshot) { this.store.restore(snapshot); }
}

// ─────────────────────────────────────────────────────────────────────────────
// EXPORTS
// ─────────────────────────────────────────────────────────────────────────────

export {
  IntelligenceEngine,
  rankSignals,
  // Individual layers (unit testing / selective use)
  detectEmergence,
  checkThoughtLeader,
  detectQuestionGaps,
  measureDivergence,
  scoreCompetitiveGap,
  getTemporalMultiplier,
  getSourceTrust,
  updateSourceTrust,
  scoreEngagementVelocity,
  measureCrossPlatformHeat,
  scoreRelevanceDepth,
  detectNoise,
  detectHypeCyclePhase,
  computeScore,
  routeSignal,
  // Constants
  THOUGHT_LEADERS,
  COMPETITORS,
  CONFERENCE_CALENDAR,
  ROUTING_THRESHOLDS,
  SCORING_WEIGHTS,
  HAKKODA_DOMAIN_TERMS,
  MAINSTREAM_DOMAINS,
  NOISE_PATTERNS,
};
