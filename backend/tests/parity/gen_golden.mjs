// Parity harness: runs the original JS engine over fixed fixtures with a frozen
// clock and dumps scored output as JSON for the Python parity test to compare.
// Run with: TZ=UTC node tests/parity/gen_golden.mjs > tests/parity/golden.json
// reference_engine.mjs is a vendored copy of the original Cloudflare
// intelligence-engine.js, kept as the parity reference for the Python port.
import { IntelligenceEngine } from './reference_engine.mjs';

const NOW = Date.UTC(2026, 5, 15, 12, 0, 0); // 2026-06-15T12:00:00Z
const realNow = Date.now;
Date.now = () => NOW;

const D = (y, m, d) => Date.UTC(y, m - 1, d, 12, 0, 0);

const fixtures = [
  {
    id: 'fx-tl', title: 'Andrej Karpathy on small models and big context',
    body: 'Why do most enterprise AI budgets go to model size instead of the context layer? How should teams rebalance?',
    author: { name: 'Andrej Karpathy', handle: '@karpathy' },
    source: { name: 'Twitter', domain: 'twitter.com', type: 'social', platform: 'twitter' },
    engagement: { platform: 'twitter', reactions: 1200, comments: 300, shares: 150 },
    topics: ['agentic ai', 'frugal ai', 'context layer'], timestamp: D(2026, 6, 10),
  },
  {
    id: 'fx-snowflake', title: 'Snowflake Cortex adds context engineering for enterprise AI agents',
    body: 'Snowflake announced governed data context for agents, framed as context engineering between raw data and agent reasoning.',
    author: { name: 'Snowflake Newsroom', handle: '' },
    source: { name: 'Snowflake', domain: 'snowflake.com', type: 'press', platform: 'press' },
    engagement: { platform: 'blog', reactions: 40, comments: 8, shares: 5 },
    topics: ['data engineering', 'snowflake', 'enterprise ai'], timestamp: D(2026, 6, 9),
  },
  {
    id: 'fx-hn', title: 'Show HN: cutting LLM inference cost with small language models',
    body: 'A practical tutorial on deploying quantized small language models in production. Lessons learned building a lean RAG pipeline.',
    author: { name: 'devuser', handle: '@devuser' },
    source: { name: 'Hacker News', domain: 'news.ycombinator.com', type: 'tech_community', platform: 'hn' },
    engagement: { platform: 'hn', reactions: 220, comments: 95, shares: 0 },
    topics: ['frugal ai', 'small language model', 'rag', 'llm'], timestamp: D(2026, 6, 12),
  },
  {
    id: 'fx-noise', title: 'For immediate release: Vendor announces AI-powered dashboard',
    body: 'Sponsored. We are pleased to announce a revolutionary new dashboard.',
    author: { name: 'Vendor PR', handle: '' },
    source: { name: 'Example Vendor', domain: 'example-vendor.com', type: 'press', platform: 'news' },
    engagement: { platform: 'news', reactions: 2, comments: 0, shares: 0 },
    topics: [], timestamp: D(2026, 6, 11),
  },
  {
    id: 'fx-analyst', title: 'McKinsey: enterprise AI adoption accelerates across data platforms',
    body: 'Analysts report strong growth and opportunity in enterprise AI and data governance investments.',
    author: { name: 'McKinsey & Company', handle: '' },
    source: { name: 'McKinsey & Company', domain: 'mckinsey.com', type: 'competitor', platform: 'blog' },
    engagement: { platform: 'blog', reactions: 30, comments: 4, shares: 10 },
    topics: ['enterprise ai', 'data governance'], timestamp: D(2026, 6, 8),
  },
];

const engine = new IntelligenceEngine();
const scored = engine.processBatch(fixtures);

const out = scored.map(s => ({
  id: s.id,
  final: s.scores.final,
  base: s.scores.base,
  tier: s.routing.tier,
  emergencePosition: s.scores.emergencePosition,
  emergenceStage: s.scores.emergenceStage,
  relevanceInput: s.scores.relevanceInput,
  emergenceInput: s.scores.emergenceInput,
  sourceAuthority: s.scores.sourceAuthority,
  questionGapBonus: s.scores.questionGapBonus,
  engagementVelocity: s.scores.engagementVelocity,
  keywords: s.scores.keywords,
  divergenceScore: s.scores.divergenceScore,
  competitiveGap: s.scores.competitiveGap,
  temporalMultiplier: s.scores.temporalMultiplier,
  crossPlatformHeat: s.scores.crossPlatformHeat,
  hypeCycleMultiplier: s.scores.hypeCycleMultiplier,
  hypeCyclePhase: s.scores.hypeCyclePhase,
  thoughtLeaderTier: s.scores.thoughtLeaderTier,
  noiseFilter: s.scores.noiseFilter,
}));

Date.now = realNow;
process.stdout.write(JSON.stringify({ now: NOW, order: scored.map(s => s.id), signals: out }, null, 2));
