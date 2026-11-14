"""AI Coach chat: answers from the Big Brain dashboard and the module engines only.

1. Route the question (spend / why / cook / what-if / data).
2. Build the answer from structured facts (template, always available, numbers exact).
3. If Gemini is configured, let it rephrase in the user's language; the reply is kept only if every number
   in it already appears in the facts (same number check as the explanations). Otherwise the template stays.
What-if questions are calculated by the water or electricity engine, never by the language model.
"""
import json
import logging
import re

from .explain import _numbers

log = logging.getLogger(__name__)

SUGGESTIONS = ["How can I spend less?", "Why this forecast?", "What can I cook?",
               "What if I use 10% less water?", "What if I use the AC 1 hour less?", "What information is missing?"]


def _money(x):
    return "not available yet" if x is None else f"Rs {x:,.0f}"


def _route(text):
    t = text.lower()
    if re.search(r"what if|scenario|less water|less electricity|hour less|%|cut", t):
        return "what_if"
    if re.search(r"cook|recipe|pantry|meal|eat|expir", t):
        return "cook"
    if re.search(r"why|forecast|estimate|explain|how .*calculat|change", t):
        return "why"
    if re.search(r"missing|unlock|information|data|question", t):
        return "data"
    if re.search(r"spend|save|saving|budget|reduce|cheaper|money|bill", t):
        return "spend"
    return "help"


def _what_if(text):
    """Run the scenario in the right engine. Returns (answer, facts)."""
    t = text.lower()
    pct = re.search(r"(\d+(?:\.\d+)?)\s*%", t)
    hours = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hour|hours)\b", t)
    from fastapi import HTTPException

    from integration.gateway import run_scenario_for_ui
    try:
        if ("ac" in t.split() or "air" in t or "aircon" in t) and hours:
            r = run_scenario_for_ui("electricity", scenario="appliance_hours",
                                    params={"appliance": "air_conditioner", "hours_less_per_day": float(hours.group(1))})
        elif pct:
            kind = "electricity" if re.search(r"electric|power|kwh", t) else "water"
            r = run_scenario_for_ui(kind, reduction_percent=float(pct.group(1)))
        else:
            return ("Tell me the change to test, for example \"What if I use 10% less water?\" or "
                    "\"What if I use the AC 1 hour less?\"", {})
    except HTTPException as exc:
        return (exc.detail.get("message") if isinstance(exc.detail, dict) else str(exc.detail)), {}
    if r.get("status") == "needs_input":
        return r["message"], r
    if r.get("baseline") is None:
        return r.get("message", "Add a bill first so I can calculate this."), r
    return (f"{r['message']} Before: {_money(r['baseline'])}; with the change: {_money(r['adjusted'])} "
            f"(difference {_money(r['delta'])}). This is a plan, not a measured saving.", r)


def answer(dash, message):
    intent = _route(message)
    o = dash["outlook"]
    actions = [a for a in dash["actions"] if a.get("kind") != "unlock"]
    unlocks = [a for a in dash["actions"] if a.get("kind") == "unlock" or a["action_id"].startswith("collect_")]
    facts, used = {}, []
    if intent == "spend":
        top = [a for a in actions if a.get("estimated_savings_mur")][:3] or actions[:3]
        lines = [f"Water estimate: {_money(o['water'].get('cost_rs'))}, electricity estimate: "
                 f"{_money(o['electricity'].get('cost_rs'))}, groceries confirmed this month: "
                 f"{_money(o['groceries']['recorded_rs'])}."]
        for a in top:
            lines.append(f"- {a['title']}" + (f" (about {_money(a['estimated_savings_mur'])}, {a['module']})"
                                              if a.get("estimated_savings_mur") else f" ({a['module']})"))
        if not top:
            lines.append("Add a bill or a receipt first so I can find savings that apply to your home.")
        text = "\n".join(lines)
        facts, used = {"outlook": o, "actions": top}, ["dashboard"]
    elif intent == "why":
        parts = []
        for k, label in (("water", "Water"), ("electricity", "Electricity")):
            x = o[k]
            if x["label"] == "forecast":
                parts.append(f"{label}: {x['amount']} {x['unit']} for {x['period_start']} to {x['period_end']}, "
                             f"{_money(x['cost_rs'])} from the official tariff ({x['status']}).")
            else:
                parts.append(f"{label}: no estimate yet. {x.get('status_message') or ''}".strip())
        parts.append("Each estimate uses your confirmed bills (cost per day x days in the next cycle), shown with its "
                     "assumptions in the Utilities screen. More bills and meter readings make it more reliable.")
        text = " ".join(parts)
        facts, used = {"outlook": o}, ["dashboard"]
    elif intent == "cook":
        food = [a for a in dash["actions"] if a["module"] == "food" and a.get("kind") != "data_quality"]
        text = " ".join(a["explanation"].rstrip(".") + "." for a in food) or \
            "No recipe can be cooked fully from your pantry yet. Add items or confirm a grocery receipt."
        facts, used = {"food_actions": food}, ["food module"]
    elif intent == "what_if":
        text, facts = _what_if(message)
        used = ["scenario engine"]
    elif intent == "data":
        text = "To improve your estimates: " + " ".join(f"- {a['title']}." for a in unlocks[:5]) if unlocks else \
            "Nothing important is missing right now."
        facts, used = {"missing": [a["evidence"] for a in unlocks[:5]]}, ["dashboard"]
    else:
        text = "I can explain your water and electricity estimates, suggest savings, find recipes from your pantry " \
               "and test what-if changes. Try one of the suggestions."
    return {"answer": text, "intent": intent, "source": "template", "verified_numbers": True,
            "actions": [{"module": a["module"], "action_id": a["action_id"], "title": a["title"],
                         "estimated_savings_mur": a.get("estimated_savings_mur")} for a in (facts.get("actions") or [])],
            "evidence": facts, "used": used, "suggestions": SUGGESTIONS}


def rephrase(result, language="en"):
    """Optional Gemini wording. Kept only if it adds no new number."""
    try:
        from core.config import get_settings
        from core.llm import gemini_generate
        if not get_settings().gemini_api_key:
            return result
        lang = {"en": "English", "fr": "French", "mfe": "Mauritian Creole (Kreol Morisien)"}.get(language, "English")
        prompt = (f"Rewrite this household assistant answer in friendly, simple {lang}. Keep every number, unit, date "
                  "and rupee amount exactly as written. Do not add advice, numbers or claims. Return JSON "
                  '{"answer": "..."}.\nANSWER:\n' + result["answer"])
        new = json.loads(gemini_generate([prompt], json_output=True, temperature=0.3))["answer"]
        if _numbers(new) <= _numbers(result["answer"]) and _numbers(result["answer"]) <= _numbers(new):
            return {**result, "answer": new, "source": "gemini", "language": language}
    except Exception as exc:
        log.info("Coach rephrase skipped: %s", exc)
    return result
