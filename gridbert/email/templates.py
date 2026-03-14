# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Email templates — German, Küchentisch-Ingenieur tone."""

from __future__ import annotations

from gridbert.config import APP_URL

# Gridbert brand colors
_BONE = "#F5F0E8"
_INK = "#2A2A28"
_TERRACOTTA = "#C4633F"
_KREIDE = "#FAF8F4"
_WARM_GRAU = "#A89F91"


# Gridbert avatar as hosted PNG (Gmail/Outlook block inline SVG)
_GRIDBERT_IMG = (
    '<img src="https://app.gridbert.at/gridbert-icon-1024.png" '
    'alt="Gridbert" width="72" height="72" '
    'style="display:block;margin:0 auto;border-radius:12px;" />'
)


def _wrap(body_html: str) -> str:
    """Wrap email body in a branded container with Gridbert avatar."""
    return f"""\
<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:{_BONE};font-family:Georgia,'Source Serif 4',serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{_BONE};padding:32px 16px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:{_KREIDE};border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
  <tr><td style="background:{_TERRACOTTA};padding:20px 32px;text-align:center;">
    {_GRIDBERT_IMG}
    <span style="display:block;margin-top:8px;font-size:1.6rem;font-weight:700;color:white;font-family:Georgia,serif;">Gridbert</span>
  </td></tr>
  <tr><td style="padding:32px;color:{_INK};font-size:1rem;line-height:1.6;">
    {body_html}
  </td></tr>
  <tr><td style="padding:16px 32px 24px;color:{_WARM_GRAU};font-size:0.8rem;text-align:center;">
    Gridbert — Dein persönlicher Energie-Agent<br>
    <a href="https://www.gridbert.at" style="color:{_WARM_GRAU};">www.gridbert.at</a>
  </td></tr>
</table>
</td></tr></table>
</body>
</html>"""


def waitlist_confirmation(name: str | None = None) -> tuple[str, str]:
    """Email after waitlist signup."""
    greeting = f"Hallo {name}" if name else "Hallo"
    subject = "Gridbert hier — du bist auf der Liste ⚡"
    body = _wrap(f"""\
<p>{greeting},</p>
<p>Schön, dass du dabei bist!</p>
<p>Gridbert ist dein persönlicher Energie-Agent — ich helfe dir,
bei Strom und Gas zu sparen. Lad einfach deine Stromrechnung hoch
und ich sag dir in 30 Sekunden, ob du zu viel zahlst.</p>
<p>Sobald dein Platz frei wird, bekommst du eine Einladung per Mail.
Bis dahin: <strong>Stromrechnung bereitlegen!</strong></p>
<p style="margin-top:24px;">Bis bald,<br>
<span style="color:{_TERRACOTTA};font-weight:600;">Gridbert</span></p>""")
    return subject, body


def allowlist_invitation(email: str) -> tuple[str, str]:
    """Email when admin adds user to allowlist (can now register)."""
    subject = "Dein Zugang zu Gridbert ist da 🎉"
    register_url = f"{APP_URL}/register"
    body = _wrap(f"""\
<p>Hallo,</p>
<p>Gute Nachrichten — <strong>du kannst dich jetzt bei Gridbert registrieren!</strong></p>
<p>Leg dir einen Account an und lad deine letzte Stromrechnung hoch —
ich sag dir in 30 Sekunden, ob du zu viel zahlst.</p>
<p style="margin:24px 0;">
  <a href="{register_url}" style="display:inline-block;background:{_TERRACOTTA};
    color:white;padding:12px 28px;border-radius:8px;text-decoration:none;
    font-weight:600;font-size:1rem;">Jetzt registrieren</a>
</p>
<p style="font-size:0.9rem;color:{_WARM_GRAU};">
Ein kleiner Hinweis: Gridbert ist ein Hobbyprojekt und KI-Anfragen kosten Geld.
Bitte geh sparsam mit den Nachrichten um — oder hinterleg deinen eigenen
API-Schlüssel in den Einstellungen. Danke!</p>
<p style="margin-top:24px;">Freut mich, dass du dabei bist!<br>
<span style="color:{_TERRACOTTA};font-weight:600;">Gridbert</span></p>""")
    return subject, body


def welcome_after_registration(name: str) -> tuple[str, str]:
    """Email right after successful registration."""
    greeting = f"Willkommen, {name}" if name else "Willkommen"
    subject = "Willkommen bei Gridbert — los geht's! 🔌"
    body = _wrap(f"""\
<p>{greeting}!</p>
<p>Dein Account steht — du kannst sofort loslegen.</p>
<p><strong>Nächster Schritt:</strong> Lad deine letzte Stromrechnung hoch
(PDF oder Foto). Ich analysiere sie und zeige dir, wo du sparen kannst.</p>
<p style="margin:24px 0;">
  <a href="{APP_URL}" style="display:inline-block;background:{_TERRACOTTA};
    color:white;padding:12px 28px;border-radius:8px;text-decoration:none;
    font-weight:600;font-size:1rem;">Gridbert öffnen</a>
</p>
<p style="font-size:0.9rem;color:{_WARM_GRAU};">
Tipp: Wenn du einen eigenen API-Schlüssel hast (Anthropic oder OpenAI),
kannst du ihn unter Einstellungen hinterlegen. Damit hilfst du,
Gridbert am Laufen zu halten.</p>
<p style="font-size:0.85rem;color:{_WARM_GRAU};">
<strong>Hinweis zum Datenschutz:</strong> Deine Konversationen mit Gridbert werden
gespeichert und können zur Verbesserung der Probeversion verwendet werden.
Lade keine sensiblen Dokumente hoch, die du nicht teilen möchtest.</p>
<p style="margin-top:24px;">Viel Spaß beim Sparen!<br>
<span style="color:{_TERRACOTTA};font-weight:600;">Gridbert</span></p>""")
    return subject, body


def feedback_nudge(name: str) -> tuple[str, str]:
    """Nudge email a few days after registration."""
    greeting = f"Hey {name}" if name else "Hey"
    subject = "Gridbert hier — alles klar bei dir? 💡"
    body = _wrap(f"""\
<p>{greeting},</p>
<p>Du hast dich vor ein paar Tagen registriert — wie ist es dir ergangen?</p>
<p>Falls du noch keine Stromrechnung hochgeladen hast: Das dauert
30 Sekunden und ich zeige dir sofort dein Sparpotential.</p>
<p style="margin:24px 0;">
  <a href="{APP_URL}" style="display:inline-block;background:{_TERRACOTTA};
    color:white;padding:12px 28px;border-radius:8px;text-decoration:none;
    font-weight:600;font-size:1rem;">Zur Analyse</a>
</p>
<p style="font-size:0.9rem;color:{_WARM_GRAU};">
Ich freue mich über jedes Feedback — was hat gut funktioniert,
was nicht? Antworte einfach auf diese Mail oder schreib mir im Chat.</p>
<p style="margin-top:24px;">Bis bald,<br>
<span style="color:{_TERRACOTTA};font-weight:600;">Gridbert</span></p>""")
    return subject, body


def switching_initiated(
    name: str,
    target_lieferant: str,
    target_tarif: str,
    savings_eur: float,
) -> tuple[str, str]:
    """Email when tariff switch request is created."""
    greeting = f"Hallo {name}" if name else "Hallo"
    savings_str = f"{savings_eur:.0f}" if savings_eur == int(savings_eur) else f"{savings_eur:.2f}"
    subject = "Dein Tarifwechsel wurde eingeleitet ⚡"
    body = _wrap(f"""\
<p>{greeting},</p>
<p>Dein Tarifwechsel ist in Bearbeitung!</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0;">
  <tr><td style="padding:6px 0;color:{_WARM_GRAU};">Neuer Anbieter</td>
      <td style="padding:6px 0;font-weight:600;">{target_lieferant}</td></tr>
  <tr><td style="padding:6px 0;color:{_WARM_GRAU};">Tarif</td>
      <td style="padding:6px 0;font-weight:600;">{target_tarif}</td></tr>
  <tr><td style="padding:6px 0;color:{_WARM_GRAU};">Geschätzte Ersparnis</td>
      <td style="padding:6px 0;font-weight:600;color:{_TERRACOTTA};">{savings_str} €/Jahr</td></tr>
</table>
<p>Ben kümmert sich in den nächsten Tagen um den Wechsel.
Die Vollmacht findest du in deinem Gridbert-Dashboard unter „Dokumente".</p>
<p style="font-size:0.9rem;color:{_WARM_GRAU};">
Du kannst den Status jederzeit im Dashboard verfolgen.
Bei Fragen antworte einfach auf diese Mail oder schreib im Chat.</p>
<p style="margin-top:24px;">Wir melden uns,<br>
<span style="color:{_TERRACOTTA};font-weight:600;">Gridbert</span></p>""")
    return subject, body


def switching_completed(
    name: str,
    target_lieferant: str,
    target_tarif: str,
    savings_eur: float,
) -> tuple[str, str]:
    """Email when tariff switch is completed."""
    greeting = f"Hallo {name}" if name else "Hallo"
    savings_str = f"{savings_eur:.0f}" if savings_eur == int(savings_eur) else f"{savings_eur:.2f}"
    subject = "Tarifwechsel abgeschlossen! 🎉"
    body = _wrap(f"""\
<p>{greeting},</p>
<p><strong>Dein Tarifwechsel ist abgeschlossen!</strong></p>
<table style="width:100%;border-collapse:collapse;margin:16px 0;">
  <tr><td style="padding:6px 0;color:{_WARM_GRAU};">Neuer Anbieter</td>
      <td style="padding:6px 0;font-weight:600;">{target_lieferant}</td></tr>
  <tr><td style="padding:6px 0;color:{_WARM_GRAU};">Tarif</td>
      <td style="padding:6px 0;font-weight:600;">{target_tarif}</td></tr>
  <tr><td style="padding:6px 0;color:{_WARM_GRAU};">Ersparnis</td>
      <td style="padding:6px 0;font-weight:600;color:{_TERRACOTTA};">{savings_str} €/Jahr</td></tr>
</table>
<p>Der neue Lieferant übernimmt die Kündigung bei deinem alten Anbieter —
du musst nichts weiter tun. Die Umstellung passiert nahtlos.</p>
<p style="margin-top:24px;">Viel Freude mit dem neuen Tarif!<br>
<span style="color:{_TERRACOTTA};font-weight:600;">Gridbert</span></p>""")
    return subject, body
