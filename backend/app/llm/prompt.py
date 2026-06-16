"""Prompt + template builders — ported from ssc-app.js (buildPrompt/buildTemplate).

DOM reads and global `S` state are replaced by a resolved `ctx` dict assembled
server-side from the request payload + app_settings config. Output is identical
prompt/template text to the original client.
"""
from __future__ import annotations

import re
from typing import Any


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _f2(v: Any) -> str:
    return f"{_num(v):.2f}"


def _nospace(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def build_prompt(ctx: dict, output_type_id: str) -> str:
    s = ctx["signal"]
    url = (s.get("url") or "").strip()
    title = (s.get("title") or "").strip() or "[Signal Title]"
    author = (s.get("author") or "").strip() or "[Author]"
    plat = s.get("platform") or ""
    domain = (s.get("domain") or "").strip() or "enterprise technology"
    org = (s.get("org") or "").strip()
    text = (s.get("text") or "").strip()
    tp_raw = (s.get("talking_points") or "").strip()

    fw = ctx["framework"]
    ot = ctx["output_type"]
    active_lenses = ctx.get("active_lenses") or []
    im = ctx.get("input_mode")
    personas = ctx.get("personas") or []
    povs = ctx.get("povs") or []
    pov_custom = (ctx.get("pov_custom") or "").strip()
    web_research = bool(ctx.get("web_research"))

    L = ctx.get("layers") or {}
    score_note = f"{_num(ctx.get('score')):.2f} / 1.0 ({ctx.get('tier')})"

    tp_section = f"\nTALKING POINTS TO INCORPORATE:\n{tp_raw}\n" if tp_raw else ""

    lens_section = ""
    if active_lenses:
        lens_section = (
            f"\nACTIVE LENS(ES): {', '.join(l['name'] for l in active_lenses)}\n"
            + "\n".join(f"Focus keywords for \"{l['name']}\": {', '.join(l['keywords'])}" for l in active_lenses)
            + "\nWeave the lens vocabulary naturally where relevant.\n"
        )

    input_mode_section = f"\nINPUT MODE: {im['name']}\n{im['desc']}\n" if im else ""

    persona_section = ""
    if personas:
        persona_section = "\nTARGET PERSONA(S):\n" + "\n".join(
            f"- {p['name']} ({p['archetype']}): {p['description']}\n"
            f"  Pain points: {', '.join(p['painPoints'])}\n"
            f"  Tone: {p['tone']} | Format preference: {p['formatPref']} | Platform: {p['platform']} | CTA type: {p['ctaType']}"
            for p in personas
        ) + ("\nIf multiple personas are listed, write primarily for the first persona but note in a closing line "
             "how the angle would shift for the other persona(s) (A/B variant guidance).\n" if len(personas) > 1 else "\n")

    pov_section = ""
    if povs or pov_custom:
        pov_names = [p["name"] for p in povs]
        if pov_custom:
            pov_names.append(f"Custom Spin: {pov_custom}")
        pov_section = (
            f"\nPOSITIONING / POV: {' + '.join(pov_names)}\n"
            + "\n".join(f"- {p['name']}: {p['desc']}" for p in povs)
            + (f"\n- Custom Spin: {pov_custom}" if pov_custom else "") + "\n"
        )

    research_section = (
        "\nWEB RESEARCH ENRICHMENT: ON\nBefore writing, surface 1-3 supporting data points, stats, quotes, or case "
        "studies relevant to this signal and domain (from your training knowledge). Cite the source by name inline "
        "(e.g., \"according to Gartner...\"). If you are not confident a stat is accurate, frame it as illustrative "
        "and flag it with [VERIFY]. Use this research to strengthen the argument, not just decorate it.\n"
    ) if web_research else ""

    output_spec = _output_spec(output_type_id, fw, ctx.get("social_platform") or "linkedin")

    l2_note = "\n- L2 Thought Leader Override: ACTIVE" if L.get("l2") else ""
    org_line = ("\nOrganization: " + org) if org else ""
    url_line = ("\nURL: " + url) if url else ""

    return f"""You are a B2B content strategist converting market signals into high-quality thought leadership content.

SIGNAL DETAILS:
Title: {title}
Author: {author}
Platform: {plat}{org_line}{url_line}
Domain: {domain}
Intelligence Score: {score_note}

LAYER CONTEXT:
- L1 Emergence: {_f2(L.get('l1'))} ({'highly novel, breaking' if _num(L.get('l1')) >= 0.7 else 'moderate novelty' if _num(L.get('l1')) >= 0.4 else 'recirculating content'})
- L7 Source Trust: {_f2(L.get('l7'))} ({'high credibility' if _num(L.get('l7')) >= 0.7 else 'moderate credibility'})
- L3 Question Gap: {_f2(L.get('l3'))} ({'strong unanswered question' if _num(L.get('l3')) >= 0.6 else 'weak question gap'})
- L10 Keywords: {_f2(L.get('l10'))} (domain keyword alignment){l2_note}
{lens_section}{input_mode_section}{persona_section}{pov_section}{research_section}
SIGNAL TEXT:
{text or '[No signal text provided. Generate based on available metadata and domain context.]'}
{tp_section}
SELECTED FRAMEWORK: {fw['name']}
Beat structure: {' > '.join(fw['beats'])}

OUTPUT TYPE: {ot['name']}
Task: {output_spec}

MANDATORY WRITING RULES:
1. Zero em dashes. Not one. Rewrite any sentence that would use one.
2. No AI filler phrases: "game-changer", "transformative", "in today's fast-paced", "it is worth noting"
3. Write with authority and specificity. Name companies, numbers, real dynamics.
4. B2B tone. Senior executive audience. No fluff.
5. Label each framework beat clearly in the output.

Generate the {ot['name']} now:"""


def _output_spec(ot_id: str, fw: dict, platform: str) -> str:
    name = fw["name"]
    beats = fw["beats"]
    if ot_id == "short-form-video-talking":
        return (f"Write a 30-60 second talking-head video script. Structure it as a beat map using the {name} framework. "
                f"For each beat: show the timestamp range (e.g., \"0s-12s\"), the beat label in ALL CAPS, the talk track "
                f"(exactly what to say, verbatim), and the on-screen text overlay (max 5 words). After the beats, write a "
                f"3-shot shot list (Shot 1, Shot 2, Shot 3) with camera angle and visual direction for each.")
    if ot_id == "short-form-video-sizzle":
        return (f"Write a 30-45 second sizzle/B-roll video concept with no talking head, using the {name} framework as the "
                f"narrative arc. Provide: 3 headline/hook variants for the opening text card, a beat map with timestamp "
                f"ranges mapping each framework beat to a visual moment plus on-screen text/caption, a shot list (4-5 shots) "
                f"describing the b-roll, footage, or motion graphics for each beat, and a one-paragraph storyboard summary "
                f"describing the visual flow start to finish.")
    if ot_id == "long-form-video":
        return (f"Write a long-form video outline (5-10 minutes) using the {name} framework as the story arc / segment "
                f"structure. Provide: a one-paragraph storyboard overview of the visual narrative, a segment-by-segment "
                f"breakdown mapping each framework beat to a timed segment (with approximate duration), a full script (talk "
                f"track) for each segment, and a shot list covering camera setups, b-roll, and graphics needed per segment.")
    if ot_id == "podcast":
        return (f"Write a podcast segment outline using the {name} framework to structure the conversation flow. Include: "
                f"an intro (cold open hook plus standard show intro), guest prep notes (3-4 background questions/talking "
                f"points to send the guest in advance, tied to this signal), a segment-by-segment breakdown mapping framework "
                f"beats to discussion segments with key talking points and questions for each, and an outro (recap of "
                f"takeaways plus a CTA for listeners).")

    if platform == "instagram":
        return (f"Write an Instagram caption using the {name} framework. Start with a scroll-stopping hook line, then "
                f"develop each framework beat as a short paragraph with natural line breaks, labeling each beat in ALL CAPS. "
                f"End with a CTA and 8-10 relevant hashtags on their own line. Also include a one-line visual direction note "
                f"describing the accompanying image, carousel, or Reel concept.")
    if platform == "x":
        return (f"Write an X (Twitter) thread of {len(beats) + 1} tweets using the {name} framework, one beat per tweet "
                f"(label which beat each tweet maps to in brackets, e.g. \"[{beats[0].upper()}]\"). Tweet 1 must be a "
                f"standalone hook under 280 characters that works without the rest of the thread. Every tweet must stay "
                f"under 280 characters. The final tweet must be a CTA.")
    if platform == "tiktok":
        return (f"Write a TikTok video concept using the {name} framework as the talking-point structure. Provide: 3 hook "
                f"variants for the first 2 seconds, an on-screen text plan synced to each framework beat (max 6 words per "
                f"card, labeled in ALL CAPS by beat), a spoken talk-track outline for each beat, and a caption with 4-6 hashtags.")
    return (f"Write 3 distinct hook variant lines first (labeled \"Hook A:\", \"Hook B:\", \"Hook C:\"), then the full "
            f"LinkedIn post body using the {name} framework with each beat labeled in ALL CAPS. Keep the full post under "
            f"300 words. End with 3-5 relevant hashtags and a one-sentence visual direction note for the accompanying "
            f"image or carousel.")


# ── Template generator (no API key) ──────────────────────────────────────────

DIV = "=" * 52


def build_template(ctx: dict, output_type_id: str) -> str:
    s = ctx["signal"]
    title = (s.get("title") or "").strip() or "[Signal Title]"
    author = (s.get("author") or "").strip() or "[Author]"
    plat = s.get("platform") or ""
    domain = (s.get("domain") or "").strip() or "enterprise technology"
    tp_lines = [l for l in (s.get("talking_points") or "").strip().split("\n") if l.strip()]

    fw = ctx["framework"]
    ot = ctx["output_type"]
    active_lenses = ctx.get("active_lenses") or []
    tier = ctx.get("tier")
    score_str = _f2(ctx.get("score"))
    im = ctx.get("input_mode")
    personas = ctx.get("personas") or []
    povs = ctx.get("povs") or []
    pov_custom = (ctx.get("pov_custom") or "").strip()
    web_research = bool(ctx.get("web_research"))

    urgency = ("URGENT: Publish within 24 hours." if tier == "IMMEDIATE"
               else "Publish within 48-72 hours." if tier == "ROUTE"
               else "Queue for this week." if tier == "DIGEST"
               else "Low priority. Log and monitor.")

    pov_names = [p["name"] for p in povs]
    if pov_custom:
        pov_names.append(f"Custom: {pov_custom}")

    header = (
        f"[TEMPLATE | {ot['name'].upper()} | {fw['name']} FRAMEWORK | {score_str} / {tier}]\n"
        f"[{urgency}]"
        + (f"\n[Active lens(es): {', '.join(l['name'] for l in active_lenses)} -- weave in: "
           f"{', '.join(k for l in active_lenses for k in l['keywords'][:4])}]" if active_lenses else "")
        + (f"\n[Input mode: {im['name']}]" if im else "")
        + (f"\n[Persona(s): " + " | ".join(f"{p['name']} ({p['archetype']}, tone: {p['tone']}, CTA: {p['ctaType']})" for p in personas) + "]" if personas else "")
        + (f"\n[POV: {' + '.join(pov_names)}]" if pov_names else "")
        + ("\n[Web research enrichment requested -- add 1-3 supporting stats/quotes/case studies with sources, flag unverified figures with [VERIFY]]" if web_research else "")
        + "\n[Replace all [...] blocks with your content, then run through Claude for polish.]\n\n"
    )

    if output_type_id == "short-form-video-talking":
        return header + _tmpl_talking(title, author, domain, fw, tp_lines)
    if output_type_id == "short-form-video-sizzle":
        return header + _tmpl_sizzle(title, author, domain, fw, tp_lines)
    if output_type_id == "long-form-video":
        return header + _tmpl_long(title, author, plat, domain, fw, tp_lines)
    if output_type_id == "podcast":
        return header + _tmpl_podcast(title, author, domain, fw, tp_lines)
    return header + _tmpl_social(title, author, domain, fw, tp_lines, ctx.get("social_platform") or "linkedin")


def _beat_guidance(beat: str, domain: str, author: str, plat: str, tp: str | None) -> str:
    b = beat.lower()
    tp_hint = f" [Consider: {tp}]" if tp else ""
    if b in ("signal", "attention", "hook", "stat"):
        return f"[Cite the specific signal from {author} on {plat}. Quote or paraphrase the key statement.]{tp_hint}"
    if b in ("position", "contrarian", "guide"):
        return f"[State your POV on this signal. What does it reveal about {domain}? Take a clear, defensible stance.]{tp_hint}"
    if b in ("problem", "agitation", "tension", "argument"):
        return f"[The core tension. What is the industry misunderstanding or underestimating? Name it directly.]{tp_hint}"
    if b in ("evidence", "reinforcement", "context", "interest"):
        return f"[Supporting evidence. A stat, a case, or a second signal that backs your argument about {domain}.]{tp_hint}"
    if b in ("solution", "kicker", "action", "cta", "bridge", "application"):
        return f"[Forward-looking close. What should the reader do or prepare for? Specific and actionable.]{tp_hint}"
    if b in ("trajectory", "desire", "after", "predicted outcome"):
        return f"[Where is {domain} heading based on this signal? 6-12 month trajectory. Be specific.]{tp_hint}"
    if b in ("implications", "lesson", "why", "how to prepare"):
        return f"[What this means for practitioners, buyers, or vendors in {domain}. Practical takeaways.]{tp_hint}"
    return f"[Develop the {beat} section using your signal analysis and domain expertise.]{tp_hint}"


def _tp(tps: list[str], i: int) -> str:
    return f"  [Consider: {tps[i]}]" if i < len(tps) and tps[i] else ""


def _tmpl_talking(title, author, domain, fw, tps):
    secs, beats = 45, fw["beats"]
    per = secs // len(beats)
    t = f"BEAT MAP (TALKING HEAD):\n{DIV}\n\n"
    cur = 0
    for i, beat in enumerate(beats):
        dur = secs - cur if i == len(beats) - 1 else per
        end = cur + dur
        t += f"BEAT {i + 1}: {beat.upper()} ({cur}s - {end}s)\n"
        t += f"Talk Track: [What to say verbatim during these {dur}s. Reference \"{title}\" and \"{domain}\".{_tp(tps, i)}]\n"
        t += "On-Screen Text: [Max 5 words.]\n\n"
        cur = end
    t += f"{DIV}\nSHOT LIST:\n\n"
    t += "Shot 1 (open): Medium shot, talking head, direct to camera. Clean or branded backdrop.\n\n"
    t += f"Shot 2 (mid): B-roll or screen share illustrating \"{title}\".\n\n"
    t += "Shot 3 (close): Talking head, slight push-in for the CTA beat.\n"
    return t


def _tmpl_sizzle(title, author, domain, fw, tps):
    beats = fw["beats"]
    t = "HOOK VARIANTS (opening text card):\n\n"
    t += f"Hook A: [Question format. Counterintuitive angle on {domain} or \"{title}\".]\n\n"
    t += "Hook B: [Bold on-screen statement. Contrarian or surprising.]\n\n"
    t += "Hook C: [Numeric/stat opener tied to the signal.]\n\n"
    t += f"{DIV}\nSTORYBOARD SUMMARY:\n[One paragraph describing the visual flow start to finish: how the footage/motion graphics carry the {fw['name']} arc without a presenter on camera.]\n\n"
    t += f"{DIV}\nBEAT MAP (NO TALKING HEAD):\n\n"
    secs = 30
    per = secs // len(beats)
    cur = 0
    for i, beat in enumerate(beats):
        dur = secs - cur if i == len(beats) - 1 else per
        end = cur + dur
        t += f"BEAT {i + 1}: {beat.upper()} ({cur}s - {end}s)\n"
        t += f"On-Screen Text/Caption: [Tie to {domain}.{_tp(tps, i)}]\n"
        t += "Visual: [B-roll, motion graphic, or stock footage direction for this beat.]\n\n"
        cur = end
    t += f"{DIV}\nSHOT LIST:\n"
    for i, beat in enumerate(beats):
        t += f"Shot {i + 1} ({beat}): [Footage/graphic description and transition style.]\n"
    return t


def _tmpl_long(title, author, plat, domain, fw, tps):
    beats = fw["beats"]
    t = f"STORYBOARD OVERVIEW:\n[One paragraph describing the visual narrative arc for this {fw['name']}-structured video, referencing \"{title}\" and {domain}.]\n\n"
    t += f"{DIV}\nSEGMENT BREAKDOWN ({fw['name']}):\n\n"
    total_min = 7
    per = total_min / len(beats)
    cur = 0.0
    for i, beat in enumerate(beats):
        start = round(cur, 1)
        end = total_min if i == len(beats) - 1 else round(cur + per, 1)
        t += f"SEGMENT {i + 1}: {beat.upper()} ({_fmt_min(start)}min - {_fmt_min(end)}min)\n"
        t += f"Script: [Full talk track for this segment, referencing \"{title}\" by {author} on {plat}.{_tp(tps, i)}]\n"
        t += "Shot List: [Camera setups, b-roll, and graphics needed for this segment.]\n\n"
        cur = end
    return t


def _fmt_min(v: float) -> str:
    # Mirror JS Number.toFixed(1) stripping: 0 -> "0", 3.5 -> "3.5"
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def _tmpl_podcast(title, author, domain, fw, tps):
    beats = fw["beats"]
    t = f"INTRO:\n[Cold open hook referencing \"{title}\", then standard show intro.]\n\n"
    t += f"{DIV}\nGUEST PREP NOTES:\n[3-4 background questions/talking points to send the guest in advance, tied to this signal and {domain}.]\n\n"
    t += f"{DIV}\nSEGMENT BREAKDOWN ({fw['name']}):\n\n"
    for i, beat in enumerate(beats):
        t += f"SEGMENT {i + 1}: {beat.upper()}\n"
        t += f"Talking Points: [Key points for this segment, referencing {author} / \"{title}\".{_tp(tps, i)}]\n"
        t += "Discussion Question: [1-2 open-ended questions for the guest.]\n\n"
    t += f"{DIV}\nOUTRO:\n[Recap of key takeaways plus a CTA for listeners.]\n"
    return t


def _tmpl_social(title, author, domain, fw, tps, platform):
    beats = fw["beats"]
    tag = _nospace(domain)
    if platform == "instagram":
        t = f"HOOK LINE:\n[Scroll-stopping first line for \"{title}\" / {domain}.]\n\n"
        t += f"{DIV}\nCAPTION BODY ({fw['name']}):\n\n"
        for i, beat in enumerate(beats):
            t += f"{beat.upper()}:\n[Short paragraph, natural line breaks.] {_beat_guidance(beat, domain, author, 'Instagram', tps[i] if i < len(tps) else None)}\n\n"
        t += "CTA:\n[Engagement prompt.]\n\n"
        t += f"HASHTAGS:\n#{tag} #AI #Enterprise (8-10 total)\n\n"
        t += "VISUAL DIRECTION:\n[Image, carousel, or Reel concept.]"
        return t
    if platform == "x":
        t = f"X (TWITTER) THREAD ({fw['name']}):\n{DIV}\n\n"
        for i, beat in enumerate(beats):
            lead = "Standalone hook, must work on its own. " if i == 0 else ""
            t += f"Tweet {i + 1} [{beat.upper()}] (max 280 chars):\n[{lead}{_beat_guidance(beat, domain, author, 'X', tps[i] if i < len(tps) else None)}]\n\n"
        t += f"Tweet {len(beats) + 1} [CTA] (max 280 chars):\n[Closing CTA tweet.]"
        return t
    if platform == "tiktok":
        t = "HOOK VARIANTS (first 2 seconds):\n\n"
        t += "Hook A: [Question format.]\nHook B: [Bold statement.]\nHook C: [Numeric/stat opener.]\n\n"
        t += f"{DIV}\nON-SCREEN TEXT + TALK TRACK ({fw['name']}):\n\n"
        for i, beat in enumerate(beats):
            t += f"{beat.upper()}:\nOn-Screen Text: [Max 6 words.]\nTalk Track: [What to say.] {_beat_guidance(beat, domain, author, 'TikTok', tps[i] if i < len(tps) else None)}\n\n"
        t += f"CAPTION + HASHTAGS:\n[1-2 sentence caption] #{tag} #AI (4-6 hashtags total)"
        return t

    t = "HOOK VARIANTS (pick one):\n\n"
    t += f"Hook A: [Question format. Something counterintuitive about {domain} or \"{title}\".]\n\n"
    t += "Hook B: [Bold statement. A contrarian or surprising angle from the signal.]\n\n"
    t += f"Hook C: [Numeric opener. \"X% of...\" or \"After N years in {domain}...\" based on signal context.]\n\n"
    t += f"{DIV}\n\nPOST BODY ({fw['name']}):\n\n"
    for i, beat in enumerate(beats):
        t += f"{beat.upper()}:\n[2-3 sentences max.] {_beat_guidance(beat, domain, author, 'LinkedIn', tps[i] if i < len(tps) else None)}\n\n"
    t += f"CTA: [Engagement question for comments about {domain}.]\n\n"
    t += f"HASHTAGS:\n#{tag} #AI #Enterprise\n\n"
    t += "VISUAL DIRECTION:\n[Image or carousel concept.]"
    return t
