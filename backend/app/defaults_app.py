"""Default app-settings and ingestion config — ported from ssc-data.js.

These seed the `app_settings` and ingestion portions of `engine_config` on first
run. Like the engine defaults they are niche-specific only as a starting point;
everything is editable in the UI.
"""
from __future__ import annotations

import copy
from typing import Any

# UI metadata for the 12 layers (sliders/toggles in the Engine tab).
LAYERS: list[dict[str, Any]] = [
    {"id": "l1", "num": "L1", "name": "Emergence", "cls": "", "type": "score",
     "min": 0, "max": 1, "step": 0.05, "def": 0.5, "badge": "w: 0.30",
     "desc": "How new or novel is this signal? First surfacing = 1.0. Recirculating = 0.2."},
    {"id": "l2", "num": "L2", "name": "Thought Leader Override", "cls": "l-over", "type": "override",
     "def": False, "badge": "OVERRIDE",
     "desc": "Author is a verified Tier 0/1 thought leader. Active: floors score at 0.90."},
    {"id": "l3", "num": "L3", "name": "Question Gap", "cls": "", "type": "score",
     "min": 0, "max": 1, "step": 0.05, "def": 0.5, "badge": "w: 0.15",
     "desc": "Does this signal raise or answer an unanswered market question?"},
    {"id": "l4", "num": "L4", "name": "Practitioner vs Analyst Gap", "cls": "", "type": "score",
     "min": 0, "max": 1, "step": 0.05, "def": 0.5, "badge": "emergenceIn",
     "desc": "Gap between what analysts say and what practitioners are actually doing."},
    {"id": "l5", "num": "L5", "name": "Competitive Gap", "cls": "", "type": "score",
     "min": 0, "max": 1, "step": 0.05, "def": 0.5, "badge": "relevanceIn",
     "desc": "Are competitors silent on this topic? High white space = high score."},
    {"id": "l6", "num": "L6", "name": "Temporal", "cls": "l-mult", "type": "mult",
     "min": 1.0, "max": 1.2, "step": 0.05, "def": 1.0, "badge": "MULT",
     "desc": "Timing multiplier. Conference calendar overlap or breaking now = up to 1.35."},
    {"id": "l7", "num": "L7", "name": "Source Trust", "cls": "", "type": "score",
     "min": 0, "max": 1, "step": 0.05, "def": 0.5, "badge": "w: 0.20",
     "desc": "Platform and author credibility. Adapts via feedback."},
    {"id": "l8", "num": "L8", "name": "Engagement Velocity", "cls": "", "type": "score",
     "min": 0, "max": 1, "step": 0.05, "def": 0.5, "badge": "w: 0.10",
     "desc": "How fast is engagement accelerating relative to platform baselines?"},
    {"id": "l9", "num": "L9", "name": "Cross-Platform Heat", "cls": "l-mult", "type": "mult",
     "min": 1.0, "max": 1.2, "step": 0.05, "def": 1.0, "badge": "MULT",
     "desc": "Same signal across multiple platforms. 3+ platforms = 1.20+."},
    {"id": "l10", "num": "L10", "name": "Keywords", "cls": "", "type": "score",
     "min": 0, "max": 1, "step": 0.05, "def": 0.5, "badge": "w: 0.25",
     "desc": "Keyword density match against domain terms and the active Lens."},
    {"id": "l11", "num": "L11", "name": "Noise Filter", "cls": "l-zero", "type": "zero",
     "def": False, "badge": "ZERO-OUT",
     "desc": "Mark as noise: vendor pitch, press release, recycled or off-topic. Score becomes 0."},
    {"id": "l12", "num": "L12", "name": "Hype Cycle Position", "cls": "l-mult", "type": "mult",
     "min": 1.0, "max": 1.2, "step": 0.05, "def": 1.0, "badge": "MULT",
     "desc": "Hype cycle timing multiplier. Slope of enlightenment = 1.20-1.35."},
]

DEFAULT_FRAMEWORKS = [
    {"id": "spark", "name": "SPARK", "beats": ["Signal", "Position", "Argument", "Reinforcement", "Kicker"], "best": "Thought leadership", "custom": False},
    {"id": "pas", "name": "PAS", "beats": ["Problem", "Agitation", "Solution"], "best": "Pain-point content", "custom": False},
    {"id": "bab", "name": "BAB", "beats": ["Before", "After", "Bridge"], "best": "Transformation stories", "custom": False},
    {"id": "storybrand", "name": "StoryBrand", "beats": ["Guide", "Problem", "Plan", "Action", "Success"], "best": "Customer-centric POV", "custom": False},
    {"id": "aida", "name": "AIDA", "beats": ["Attention", "Interest", "Desire", "Action"], "best": "Top-of-funnel", "custom": False},
    {"id": "data-driven", "name": "Data-Driven", "beats": ["Stat", "Context", "Implication", "Action"], "best": "Research-backed", "custom": False},
    {"id": "hot-take", "name": "Hot Take", "beats": ["Contrarian", "Evidence", "CTA"], "best": "High-engagement debate", "custom": False},
    {"id": "story-arc", "name": "Story Arc", "beats": ["Hook", "Tension", "Resolution", "Lesson"], "best": "Narrative, personal", "custom": False},
    {"id": "listicle", "name": "Listicle", "beats": ["Intro Hook", "Point 1", "Point 2", "Point 3", "Punchline"], "best": "Quick-win tips", "custom": False},
    {"id": "trend-piece", "name": "Trend Piece", "beats": ["Signal", "Context", "Trajectory", "Implications"], "best": "Market analysis", "custom": False},
    {"id": "case-study", "name": "Case Study", "beats": ["Challenge", "Approach", "Outcome", "Lesson"], "best": "Social proof, ROI", "custom": False},
    {"id": "comparison", "name": "Comparison", "beats": ["Option A", "Option B", "Verdict", "Why"], "best": "Decision content", "custom": False},
    {"id": "prediction", "name": "Prediction", "beats": ["Current State", "Forces", "Predicted Outcome", "How to Prepare"], "best": "Forward-looking", "custom": False},
    {"id": "explainer", "name": "Explainer", "beats": ["Concept", "Analogy", "Example", "Application"], "best": "Education, demystify", "custom": False},
]

OUTPUT_TYPES = [
    {"id": "short-form-video-talking", "icon": "&#127908;", "name": "Short-Form Video (Talking Head)", "desc": "Talk track + beat map with timestamps, on-screen text, and a shot list."},
    {"id": "short-form-video-sizzle", "icon": "&#127916;", "name": "Short-Form Video (Sizzle)", "desc": "No-talking-head: hook variants, storyboard, beat map, and shot list."},
    {"id": "long-form-video", "icon": "&#127909;", "name": "Long-Form Video", "desc": "Storyboard overview, segment breakdown, full script, and shot list."},
    {"id": "podcast", "icon": "&#127897;", "name": "Podcast", "desc": "Intro, guest prep notes, segment talking points, and outro."},
    {"id": "social-post", "icon": "&#128241;", "name": "Social Post", "desc": "Platform-specific copy + hooks + visual direction."},
]

SOCIAL_PLATFORMS = [
    {"id": "linkedin", "name": "LinkedIn"},
    {"id": "instagram", "name": "Instagram"},
    {"id": "x", "name": "X (Twitter)"},
    {"id": "tiktok", "name": "TikTok"},
]

DEFAULT_PRESETS = {
    "frugal-ai": {
        "label": "Frugal AI",
        "hn": ["frugal AI LLM inference efficiency cost",
               "small language model SLM on-device edge deployment",
               "LLM quantization compression distillation inference",
               "efficient AI GPU-poor budget enterprise deployment",
               "LLM cost reduction inference optimization enterprise"],
        "reddit": "LocalLLaMA+MachineLearning+artificial+datascience",
    },
    "agentic-ai": {
        "label": "Agentic AI",
        "hn": ["agentic AI workflow automation enterprise production",
               "multi-agent LLM orchestration framework deployment",
               "autonomous AI agent tool use coding pipeline",
               "agentic data engineering RAG enterprise workflow",
               "AI agent memory planning reasoning production"],
        "reddit": "MachineLearning+artificial+LocalLLaMA+dataengineering",
    },
    "data-engineering": {
        "label": "Data Engineering",
        "hn": ["Snowflake Databricks data engineering lakehouse",
               "dbt data mesh modern data stack medallion architecture",
               "MLOps feature store data quality observability",
               "data governance enterprise AI production deployment",
               "data platform strategy cloud migration modernization"],
        "reddit": "dataengineering+snowflake+dbt+MachineLearning+datascience",
    },
}

DEFAULT_INGESTION = {
    "hn_queries": [
        "enterprise AI data platform strategy",
        "agentic AI workflow automation",
        "LLM efficiency frugal AI inference",
        "Snowflake Databricks lakehouse data engineering",
        "AI governance data quality observability",
        "small language model SLM deployment",
        "MLOps feature store production AI",
        "RAG retrieval augmented generation enterprise",
    ],
    "reddit_subs": "MachineLearning+LocalLLaMA+datascience+artificial+dataengineering+snowflake+dbt",
    "arxiv_feeds": [
        "https://export.arxiv.org/rss/cs.AI",
        "https://export.arxiv.org/rss/cs.LG",
    ],
    "analyst_feeds": [
        {"name": "MIT Technology Review", "domain": "technologyreview.com", "url": "https://www.technologyreview.com/feed/"},
        {"name": "Harvard Business Review", "domain": "hbr.org", "url": "https://feeds.hbr.org/harvardbusiness"},
    ],
    "competitor_feeds": [
        {"name": "Accenture", "domain": "accenture.com", "url": "https://newsroom.accenture.com/rss/"},
        {"name": "Deloitte", "domain": "deloitte.com", "url": "https://www2.deloitte.com/global/en/insights/rss.xml"},
        {"name": "McKinsey & Company", "domain": "mckinsey.com", "url": "https://www.mckinsey.com/featured-insights/rss"},
        {"name": "PwC", "domain": "pwc.com", "url": "https://www.pwc.com/gx/en/rss/insights.xml"},
        {"name": "BCG", "domain": "bcg.com", "url": "https://www.bcg.com/rss/insights.xml"},
    ],
    "news_feeds": [
        {"name": "TechCrunch AI", "domain": "techcrunch.com", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
        {"name": "VentureBeat AI", "domain": "venturebeat.com", "url": "https://venturebeat.com/category/ai/feed/"},
    ],
    "presets": DEFAULT_PRESETS,
}

DEFAULT_LENSES = [
    {"id": "frugal-ai", "name": "Frugal AI", "weight": 0.90, "active": False,
     "keywords": ["frugal ai", "llm inference cost", "small language model", "quantization", "model distillation",
                  "on-device llm", "gpu-poor", "cost-aware inference", "right-sized models", "inference optimization"]},
    {"id": "lean-ai", "name": "Lean AI", "weight": 0.85, "active": False,
     "keywords": ["lean ai", "efficient ai", "minimal viable model", "resource-constrained ai", "sustainable ai",
                  "energy-efficient inference", "model pruning", "edge ai", "low-latency inference"]},
    {"id": "context-layer", "name": "Context Layer", "weight": 0.92, "active": False,
     "keywords": ["context layer", "semantic layer", "data context", "context engineering", "rag",
                  "retrieval augmented generation", "knowledge graph", "data semantics", "context window", "grounding"]},
    {"id": "agentic-ai", "name": "Agentic AI", "weight": 0.85, "active": False,
     "keywords": ["agentic ai", "ai agent", "multi-agent", "autonomous agent", "agent orchestration",
                  "tool use", "agent memory", "workflow automation", "agent planning"]},
    {"id": "data-engineering", "name": "Data Engineering / Core", "weight": 0.80, "active": False,
     "keywords": ["snowflake", "databricks", "data engineering", "data platform", "lakehouse", "data mesh",
                  "data fabric", "mlops", "feature store", "data governance", "dbt", "airflow", "data quality",
                  "observability", "data catalog", "metadata management", "modern data stack"]},
]

INPUT_MODES = [
    {"id": "market-signal", "icon": "&#128225;", "name": "Market Signal", "desc": "Automated ingestion, scored and routed by the 12-layer engine."},
    {"id": "manual-input", "icon": "&#9999;", "name": "Manual Input", "desc": "Idea, paragraph, topic, client brief, URL, or uploaded file."},
    {"id": "freeform-prompt", "icon": "&#128172;", "name": "Freeform Prompt", "desc": "\"Talk about X in the style of Y\" — open creative brief."},
    {"id": "web-research", "icon": "&#128269;", "name": "Web Research", "desc": "System finds supporting data, stats, and proof points to enrich the brief."},
    {"id": "repurposed-asset", "icon": "&#9851;", "name": "Repurposed Asset", "desc": "Existing output fed back in for a new treatment."},
]

POV_OPTIONS = [
    {"id": "agree", "name": "Agree", "desc": "Authority, thought leadership — \"here's how\""},
    {"id": "disagree", "name": "Disagree", "desc": "Contrarian, myth-buster — \"everyone's wrong about\""},
    {"id": "challenge", "name": "Challenge", "desc": "Provocative, debate-starter — \"what if\""},
    {"id": "neutral", "name": "Neutral", "desc": "Educational, explainer — \"here's what you need to know\""},
    {"id": "visionary", "name": "Visionary", "desc": "Prediction, future-state — \"what's coming\""},
    {"id": "custom", "name": "Custom Spin", "desc": "User-defined angle or specific framing"},
]

DEFAULT_PERSONAS = [
    {"id": "enterprise-cdo", "name": "Enterprise CDO / CIO", "archetype": "Executive Buyer",
     "description": "VP/C-level data or technology leader at a large enterprise, accountable for data strategy and AI ROI to the board.",
     "painPoints": ["Proving AI ROI to the board", "Data quality and governance debt", "Vendor sprawl and integration cost"],
     "tone": "Executive, concise, ROI-focused", "formatPref": "Executive summary, LinkedIn article, talk track",
     "platform": "LinkedIn, conference", "ctaType": "Book a strategy call", "custom": False},
    {"id": "senior-data-engineer", "name": "Senior Data Engineer", "archetype": "Practitioner",
     "description": "Hands-on engineer building and maintaining the data platform (Snowflake, Databricks, dbt, Airflow).",
     "painPoints": ["Pipeline reliability and cost", "Tooling fatigue", "Keeping up with new frameworks"],
     "tone": "Technical, direct, no fluff", "formatPref": "Deep-dive article, technical carousel",
     "platform": "Reddit, LinkedIn, Hacker News", "ctaType": "Read the technical breakdown", "custom": False},
    {"id": "industry-analyst", "name": "Industry Analyst / Press", "archetype": "Influencer",
     "description": "Analyst or journalist covering enterprise AI and data trends, independent newsletter or research firm.",
     "painPoints": ["Finding differentiated narratives", "Access to real customer data", "Separating signal from hype"],
     "tone": "Balanced, evidence-based, citation-heavy", "formatPref": "Trend piece, data-driven post",
     "platform": "Substack, LinkedIn, press", "ctaType": "Subscribe / cite source", "custom": False},
    {"id": "sales-prospect", "name": "Sales Prospect (Mid-Market IT Director)", "archetype": "Buyer / Champion",
     "description": "IT or data director evaluating vendors, influences but does not always hold final budget authority.",
     "painPoints": ["Justifying spend internally", "Risk of choosing the wrong vendor", "Limited internal bandwidth"],
     "tone": "Practical, reassuring, peer-to-peer", "formatPref": "Case study, discovery call talk track",
     "platform": "LinkedIn, email, discovery call", "ctaType": "Schedule a discovery call", "custom": False},
]

OUTPUT_DEFAULTS_BY_MODE = {
    "market-signal": ["social-post", "short-form-video-talking", "podcast"],
    "manual-input": ["social-post", "long-form-video", "short-form-video-talking", "short-form-video-sizzle", "podcast"],
    "freeform-prompt": ["social-post", "long-form-video", "short-form-video-sizzle"],
    "web-research": ["long-form-video", "social-post"],
    "repurposed-asset": ["short-form-video-sizzle", "short-form-video-talking"],
}

DEFAULT_APP_SETTINGS: dict[str, Any] = {
    "layers": LAYERS,
    "frameworks": DEFAULT_FRAMEWORKS,
    "output_types": OUTPUT_TYPES,
    "social_platforms": SOCIAL_PLATFORMS,
    "lenses": DEFAULT_LENSES,
    "input_modes": INPUT_MODES,
    "pov_options": POV_OPTIONS,
    "personas": DEFAULT_PERSONAS,
    "output_defaults_by_mode": OUTPUT_DEFAULTS_BY_MODE,
}


def default_app_settings() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_APP_SETTINGS)


def default_ingestion() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_INGESTION)
