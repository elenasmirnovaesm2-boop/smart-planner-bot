def render_routine_card(r):
    steps = r.get("steps", [])
    lines = [f"🔁 Рутина: {r['name']}", ""]
    for i, s in enumerate(steps, start=1):
        lines.append(f"{i}. {s}")
    return "\n".join(lines)


def render_template_card(tpl):
    blocks = tpl.get("blocks", [])
    lines = [f"📋 Шаблон дня: {tpl['name']}", ""]
    for b in blocks:
        lines.append(f"- {b}")
    return "\n".join(lines)


def render_project_card(p):
    steps = p.get("steps", [])
    lines = [f"📂 Проект: {p['name']}", ""]
    if not steps:
        lines.append("Пока без разбивки на шаги.")
    else:
        for s in steps:
            mark = "✅" if s.get("done") else "⬜"
            lines.append(f"{mark} {s['id']}. {s['text']}")
    return "\n".join(lines)


def render_sos_card(s):
    steps = s.get("steps", [])
    lines = [f"🆘 SOS: {s['name']}", ""]
    for i, st in enumerate(steps, start=1):
        lines.append(f"{i}. {st}")
    return "\n".join(lines)


def render_habit_card(h):
    return f"📊 Привычка: {h['name']}\n\nПлан: {h.get('schedule', '')}"

