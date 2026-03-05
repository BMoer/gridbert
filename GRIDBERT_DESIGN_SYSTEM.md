# Gridbert Design System

> Verbindliches Designdokument für alle Gridbert-UI-Arbeiten mit Claude Code.
> Dieses Dokument definiert Brand Soul, visuelle Identität, Interaction Patterns und Komponenten.
> Bei Widersprüchen gilt dieses Dokument über allgemeine Styling-Defaults.
> Referenziert den `frontend-design` Skill für allgemeine Anti-Slop-Prinzipien — dieses Dokument ergänzt ihn mit Gridbert-spezifischen Entscheidungen.

---

## 0. Brand Soul

> Lies dieses Kapitel ZUERST. Alles was danach kommt — Farben, Fonts, Komponenten — leitet sich hieraus ab.
> Wenn eine Designentscheidung nicht zu Kapitel 0 passt, ist sie falsch.

### 0.1 Die Kernszene

Stell dir vor: Du sitzt am Küchentisch bei deiner Mama. Sie hat die Stromrechnung bekommen und versteht nicht, warum sie so hoch ist. Du setzt dich hin, nimmst einen Bleistift, drehst die Rechnung um und fängst an, auf der Rückseite zu zeichnen. Du erklärst ihr, was die Zahlen bedeuten. Du rechnest aus, ob sich ein Anbieterwechsel lohnt. Du machst es dann auch gleich für sie — weil du weißt, wie es geht und sie sich sicher fühlt.

**Gridbert übernimmt genau diese Rolle.**

Er ist nicht der "kluge AI-Assistent". Er ist der Enkel/die Enkelin, der/die sich hinsetzt und sagt: "Zeig mal her, ich schau mir das an." Das Interface ist der Küchentisch. Die Dokumente liegen darauf. Gridbert schaut durch seine Brille genau hin und erklärt, was er sieht.

### 0.2 Brand-Essenz (Ein Satz)

**"Gridbert schaut sich deine Stromrechnung an, damit du dich nicht allein damit fühlst."**

### 0.3 Emotionales Ziel

Der Nutzer soll sich nach der Interaktion fühlen wie nach einem Besuch bei einem hilfsbereiten Familienmitglied:

- **Sicher** — "Jemand hat sich das für mich angeschaut."
- **Verstanden** — "Er hat mir erklärt was Sache ist, ohne mich dumm aussehen zu lassen."
- **Versorgt** — "Die nötigen Schritte sind gemacht oder klar aufgezeigt."

Das Interface darf NIEMALS einschüchtern, belehren oder beeindrucken wollen.

### 0.4 Stilrichtung: "Küchentisch-Ingenieur"

| Eigenschaft | Bedeutung für Design |
|---|---|
| **Warm** | Papierfarben, weiche Texturen, keine kalten Flächen |
| **Analog** | Handgezeichnete Elemente, Skizzen-Ästhetik, Bleistift-Linien |
| **Österreichisch** | Lokales Produkt, österreichisches Deutsch, bodenständig |
| **Präzise** | Zahlen stimmen, Quellen sind transparent, nichts wird geraten |
| **Beruhigend** | Keine blinkenden Alerts, keine Dringlichkeit, kein Upselling |

### 0.5 Visual Anchor: Die Brille

Gridberts Brille ist das zentrale visuelle Element — sie verankert die gesamte Ästhetik.

**Was die Brille bedeutet:**
- "Ich schaue genau hin" — Präzision, Sorgfalt
- "Ich sehe was du nicht siehst" — Expertise ohne Arroganz
- "Ich bin eine Persönlichkeit" — Charakter statt Interface

**Wo die Brille auftaucht:**
- Im Avatar (offensichtlich)
- Als Icon-Motiv (z.B. "Analyse läuft" = Brille mit Lupe-Effekt)
- Im Logo/Wordmark (Gridbert-Schriftzug mit Brillen-Element)
- Als Lade-Animation (Brille die blinzelt)
- NICHT überall — sparsam einsetzen, damit sie besonders bleibt

### 0.6 Moodboard-Adjektive

Jede Designentscheidung muss mindestens zwei dieser Adjektive erfüllen:

```
WARM · ANALOG · EHRLICH · BODENSTÄNDIG · SORGFÄLTIG
```

Und keines dieser Anti-Adjektive:

```
COOL · SLEEK · CUTTING-EDGE · SMART · DISRUPTIVE · PREMIUM
```

### 0.7 Visuelle Referenzen (Richtung, nicht Kopie)

Denk an diese Bildwelten als Orientierung:

- **Rückseite eines Briefumschlags** mit Bleistift-Skizzen — improvisiert aber klar
- **Österreichischer Heuriger** — Holztisch, warm, ehrlich, Gemütlichkeit
- **Technische Zeichnung auf Karopapier** — präzise aber handgemacht
- **Die Küche deiner Oma** — Wachstuch, warmes Licht, Sicherheit
- **Strichzeichnungen von Sempé oder Loriot** — Charakter durch Reduktion

Explizit NICHT:
- Silicon Valley SaaS Dashboard
- Notion/Linear/Arc-Ästhetik
- Dunkle Glasmorphism-UIs
- Neobrutalism (zu ironisch für den Kontext)

---

## 1. Designphilosophie

### 1.1 Drei Säulen

- **Vertrauenswürdig** — Energie ist kein Spielzeug. Zahlen müssen stimmen, Quellen transparent sein.
- **Menschlich** — Gridbert ist ein Charakter, kein Dashboard. Der Nutzer interagiert mit einer Persönlichkeit.
- **Wachsend** — Das Interface startet fast leer und füllt sich mit dem Wissen, das Gridbert über den Nutzer aufbaut.

### 1.2 Anti-Slop-Manifest

Gridbert darf **niemals** aussehen wie eine generische AI-App:

| Verboten | Stattdessen |
|---|---|
| Purple Gradients auf Weiß | Warme, erdige Palette mit gezielten Akzenten |
| Inter, Roboto, Arial, System-Fonts als Headline | Charaktervolle Display-Fonts |
| Einheitliche Border-Radius (8px überall) | Bewusste Variation: rund wo weich, eckig wo technisch |
| Gleiche Schatten auf allen Elementen | Shadow Hierarchy — Tiefe kommuniziert Wichtigkeit |
| Emoji als UI-Elemente | Gridbert-eigene Illustrationen und Icons |
| Chat-Bubble als primäres Interface | Tisch-Metapher + wachsendes Dashboard |
| "Sparkle"-Icons für AI | Gridbert hat ein Gesicht — das IST der AI-Indikator |
| Blaue Links und generische Buttons | Kontextspezifische Interaktionselemente |
| Dunkler "Pro"-Modus als Default | Heller, warmer Papier-Hintergrund |
| "Powered by AI"-Badges | Gridbert erklärt einfach was er tut |

---

## 2. Visuelle Identität

### 2.1 Farbpalette

Die Palette leitet sich aus der Küchentisch-Welt ab: Papier, Bleistift, warmes Licht, Stromrechnung.

```css
:root {
  /* === Küchentisch-Basis === */
  --gridbert-bone:        #E8E0D4;   /* Papierton, Grundfläche, Wärme */
  --gridbert-ink:         #2C2C2C;   /* Bleistift, Text, Zeichnungen */
  --gridbert-terracotta:  #C4654A;   /* Akzent, CTAs, "schau hier" */

  /* === Energie-Farben (funktional, nicht dekorativ) === */
  --gridbert-strom-blau:  #3B7DD8;   /* Verbrauchsdaten, Charts */
  --gridbert-solar-gelb:  #E8B931;   /* PV, Einspeisung, Positives */
  --gridbert-gruen:       #4A8B6E;   /* Einsparung, Erfolg */

  /* === Neutrals === */
  --gridbert-warm-grau:   #A89B8C;   /* Sekundärtext, Borders */
  --gridbert-kreide:      #F5F1EB;   /* Karten, erhöhte Flächen */
  --gridbert-dunkel:      #1A1A1A;   /* Nur wenn Dark Mode explizit gewünscht */

  /* === Funktional === */
  --gridbert-warnung:     #D4842A;   /* Achtung, hoher Verbrauch */
  --gridbert-fehler:      #B83A3A;   /* Fehler, kritisch */
  --gridbert-info:        #5B8FA8;   /* Hinweise */
}
```

**Regeln:**
- `--gridbert-bone` ist die Basis — nicht Weiß, nicht Grau. Papier.
- Akzentfarben sparsam: eine dominante Farbe pro View.
- `--gridbert-strom-blau` und `--gridbert-terracotta` sind das primäre Chart-Paar.
- Grün nur für echte Einsparungen, nie dekorativ.
- Hintergrund soll sich anfühlen wie ein Tisch, nicht wie ein Screen. Subtile Papier-Textur (CSS noise/grain) ist erlaubt und erwünscht.

### 2.2 Typografie

```css
:root {
  /* Display / Headlines — warm, charaktervoll, nicht steril */
  --font-display: 'Fraunces', serif;

  /* Body / Fließtext — lesbar, freundlich */
  --font-body: 'Source Serif 4', serif;

  /* Mono / Daten / KPIs — Zahlen müssen präzise wirken */
  --font-mono: 'JetBrains Mono', monospace;

  /* Sizing */
  --text-xs:   0.75rem;    /* 12px — Labels, Captions */
  --text-sm:   0.875rem;   /* 14px — Sekundärtext */
  --text-base: 1rem;       /* 16px — Body */
  --text-lg:   1.25rem;    /* 20px — Subheads */
  --text-xl:   1.5rem;     /* 24px — Section Headers */
  --text-2xl:  2rem;       /* 32px — Page Titles */
  --text-3xl:  2.75rem;    /* 44px — Hero / Statement */
}
```

**Regeln:**
- `Fraunces` für Headlines — hat optische Größenvariationen und einen warmen, leicht verspielten Charakter. Passt zur Küchentisch-Welt.
- `Source Serif 4` für Body — Serifen-Font der Wärme gibt ohne altmodisch zu wirken.
- `JetBrains Mono` für Zahlen/KPIs — technische Präzision, gut lesbare Ziffern.
- Keine Font unter 14px für lesbaren Content. Mama muss es lesen können.
- **Fallbacks**: Georgia (Display), Charter (Body), Menlo (Mono).

### 2.3 Spacing & Layout

```css
:root {
  --space-xs:   0.5rem;    /* 8px */
  --space-sm:   1rem;      /* 16px */
  --space-md:   1.5rem;    /* 24px */
  --space-lg:   2.5rem;    /* 40px */
  --space-xl:   4rem;      /* 64px */
  --space-2xl:  6rem;      /* 96px */

  --content-max:    1200px;
  --content-narrow: 720px;
}
```

**Layout-Prinzipien:**
- **Kein starres Grid.** Layout passt sich Gridberts Wissensstand an.
- **Großzügiger Whitespace** — lieber zu viel Luft als zu wenig. Nicht einschüchtern.
- **Karten-basiert** — Jedes Wissens-Element ist eine Karte auf dem "Tisch".
- **Asymmetrie erlaubt** — Gridbert darf aus dem Grid ausbrechen.

### 2.4 Schatten & Tiefe

```css
:root {
  --shadow-flat:     none;
  --shadow-card:     0 1px 3px rgba(44,44,44,0.08),
                     0 4px 12px rgba(44,44,44,0.06);
  --shadow-raised:   0 2px 8px rgba(44,44,44,0.10),
                     0 8px 24px rgba(44,44,44,0.08);
  --shadow-floating: 0 4px 16px rgba(44,44,44,0.12),
                     0 16px 48px rgba(44,44,44,0.10);
  --shadow-inset:    inset 0 1px 3px rgba(44,44,44,0.10);
}
```

**Regeln:**
- Jedes Element bekommt genau EINE Schattenstufe.
- Gridbert-Sprechblase = `--shadow-floating` (schwebt über dem Tisch).
- Karten = `--shadow-card`, auf Hover `--shadow-raised`.

### 2.5 Borders & Radii

```css
:root {
  --radius-sm:    4px;     /* Technische Elemente: Inputs, Tags */
  --radius-md:    8px;     /* Standard-Karten */
  --radius-lg:    16px;    /* Gridbert-Sprechblase, Feature-Cards */
  --radius-full:  9999px;  /* Avatar, Badges */

  --border-thin:   1px solid var(--gridbert-warm-grau);
  --border-sketch: 1.5px solid var(--gridbert-ink); /* Handzeichnung-Stil */
}
```

**Regeln:**
- Nicht alles gleich rund. Daten = `--radius-sm/md`. Gridberts Welt = `--radius-lg/full`.
- `--border-sketch` für handgezeichnet wirkende Elemente (Sprechblase, leere Zustände, Onboarding-Hinweise).

### 2.6 Texturen & Atmosphäre

Der Hintergrund ist nicht flat. Er soll sich wie ein Tisch anfühlen.

**Erlaubte Texturen:**
- Subtiles CSS-Noise auf `--gridbert-bone` (Papier-Grain)
- Leichte Schatten an Karten-Rändern die "Aufliegen" suggerieren
- Gestrichelte Linien (`stroke-dasharray`) für skizzenhafte Elemente

**Verbotene Texturen:**
- Glasmorphism / Blur-Effekte
- Neon-Glows
- Gradient Meshes
- Photorealistische Texturen (kein echtes Holzfoto als Hintergrund)

---

## 3. Gridbert — Der Avatar

### 3.1 Charakter-Spezifikation

Gridbert ist ein quadratisches Wesen mit:
- **Quadratische Grundform** mit leicht abgerundeten Ecken
- **Große runde Brille** — DAS Erkennungsmerkmal (= Visual Anchor)
- **Fliege (Bow-Tie)** — er gibt sich Mühe, er nimmt dich ernst
- **Strichzeichnung-Stil** — wie mit Bleistift am Küchentisch skizziert
- **Arme und Hände** — kann Dinge halten, zeigen, gestikulieren

**Gridbert ist KEIN:**
- 3D-Charakter
- Photorealistisch
- Zu niedlich/kindlich (kein Maskottchen, sondern eine Persönlichkeit)
- Genderisiert (bewusst neutral)

### 3.2 Emotionale Zustände

Emotionen über **Augen** (hinter der Brille) und **Körperhaltung**:

| Zustand | Augen | Körper | Einsatz |
|---|---|---|---|
| `neutral` | Offen, freundlich | Aufrecht | Default, Idle |
| `thinking` | Halb geschlossen, Blick oben | Leicht geneigt | Daten werden gelesen |
| `excited` | Weit offen, Glanz | Leicht hüpfend | Einsparung gefunden |
| `concerned` | Zusammengezogen | Zurückgelehnt | Hoher Verbrauch, Warnung |
| `explaining` | Offen, direkt | Arm zeigt/deutet | Erklärung, Empfehlung |
| `sleeping` | Geschlossen, Z-z-z | Zusammengesunken | Wartet auf Input |
| `confused` | Ungleich groß, ? | Kopf schief | Braucht Nutzerhilfe |

### 3.3 Technische Umsetzung

- **Format**: SVG mit CSS-Klassen für Zustandswechsel
- **Animation**: Nur CSS-Transitions, kein Lottie/Canvas
- **Übergänge**: 300ms ease-in-out zwischen Zuständen
- **Größen**: Klein (32px, in KPI-Kacheln), Mittel (64px, Sprechblasen), Groß (128px, Onboarding)
- **Sprechblase**: `--shadow-floating`, `--radius-lg`, Dreieck-Pointer Richtung Gridbert

---

## 4. Interaction Patterns

### 4.1 Der Tisch (Document Sharing)

Die Küchentisch-Metapher: Der Nutzer legt Dokumente hin, Gridbert schaut sie sich an.

**Verhalten:**
- Drag-and-Drop oder Click-to-Upload
- Akzeptierte Formate als Sketch-Icons dargestellt (PDF, CSV — im Bleistift-Stil)
- Nach Upload: Gridbert wechselt zu `excited` → `thinking`, Dokument "rutscht" auf den Tisch
- Gridbert kommentiert den Vorgang: "Ah, eine Stromrechnung! Lass mich mal schauen..."

**Leerer Zustand:**
- Gridbert `neutral` in der Mitte, groß
- Handgezeichnete gestrichelte Umrisse wo Karten erscheinen werden
- Text: "Leg deine Stromrechnung auf den Tisch — ich schau mir das an."
- Keine Dringlichkeit, kein "Jetzt starten!". Einladend.

### 4.2 Wachsendes Dashboard

Das Dashboard ist Gridberts wachsendes Wissen, visuell dargestellt.

**Phasen:**

| Phase | Gridbert weiß | UI zeigt |
|---|---|---|
| 0 — Leer | Nichts | Nur Gridbert + Tisch + Einladung |
| 1 — Kennenlernen | Name, Netzbetreiber | Begrüßung, Profil-Karte |
| 2 — Verbrauch | Lastgang-Daten | Verbrauchs-Chart, erste KPIs |
| 3 — Tarif | Aktueller Tarif | Tarif-Vergleich, Einsparpotenzial |
| 4 — Empfehlung | Genug für Analyse | Proaktive Vorschläge (Speicher, PV, BEG) |
| 5 — Vollständig | Langzeit-Profil | Trends, News, vollständiges Dashboard |

**Übergänge:**
- Neue Karten erscheinen mit `fadeInUp` (400ms ease-out)
- Gridbert kommentiert jede neue Karte
- Kein Zustand fühlt sich "unfertig" an — jede Phase ist in sich vollständig

### 4.3 Proaktive Empfehlungen

Gridbert wartet nicht auf Fragen. Er verhält sich wie das Familienmitglied das sagt: "Weißt du was, ich hab mir das angeschaut und..."

**Intent Preview Pattern:**
- Gridbert zeigt in der Sprechblase: Was er vorschlägt + Warum
- Nutzer kann: Akzeptieren, Ablehnen, Nachfragen
- Beispiel: "Dein Nachtverbrauch ist 40% vom Ganzen. Soll ich einen Speicher durchrechnen?"
- Buttons: `[Ja, schau mal]` `[Später]` `[Was heißt das?]`

**Confidence Signal:**
- Hohe Sicherheit: Gridbert `excited`, klare Aussage
- Mittlere Sicherheit: Gridbert `explaining`, mit Einschränkungen
- Niedrige Sicherheit: Gridbert `confused`, fragt nach mehr Daten

### 4.4 KPI-Kacheln

```
┌─────────────────────────────────┐
│  Label                    [ⓘ]  │
│  ████████  2.847 kWh           │
│  ▾ -12% ggü. Vorjahr           │
└─────────────────────────────────┘
```

- **Label**: `--font-body`, `--text-sm`, `--gridbert-warm-grau`
- **Wert**: `--font-mono`, `--text-2xl`, `--gridbert-ink`
- **Trend**: `--font-mono`, `--text-sm`, farbkodiert (Grün = Einsparung, Terracotta = Anstieg)
- **[ⓘ]**: Öffnet Gridbert-Erklärung (nicht generischer Hilfetext)
- **Schatten**: `--shadow-card`, Hover `--shadow-raised`

### 4.5 Explainability (ⓘ-Pattern)

Jede Zahl, jede Empfehlung muss erklärbar sein. Gridbert versteckt nichts.

- Klick auf [ⓘ] öffnet Flyout mit `--shadow-floating`, `--radius-lg`
- Gridbert-Mini-Avatar (32px) im Flyout-Header
- Inhalt: Woher der Wert kommt, wie er berechnet wurde, was der Nutzer tun kann
- Geschrieben in Gridberts Stimme, nicht in Hilfetext-Deutsch

### 4.6 News-Feed

Kontextuell relevante Energie-News. Gridbert kuratiert, kein generischer RSS-Feed.

- Maximal 3 Items sichtbar
- Jede News: Headline, 1-Satz-Summary, Quelle, Relevanz-Tag ("Betrifft deinen Tarif")
- `--border-sketch` links als Akzentlinie
- Gridbert-Kommentar möglich: "Das mit der neuen PV-Förderung könnte für dich interessant sein."

---

## 5. Zustände & Empty States

### 5.1 Leerer Zustand

- `--gridbert-bone` mit subtiler Papier-Textur
- Gridbert groß und zentral, `sleeping` oder `neutral`
- Handgezeichnete gestrichelte Umrisse als Platzhalter
- Einladender Text, keine Dringlichkeit
- Fühlt sich an wie ein aufgeräumter Küchentisch — leer aber bereit

### 5.2 Lade-Zustand

- Gridbert `thinking`, leichtes Wippen
- Sprechblase: "Ich lese gerade deine Daten..." (KEIN Spinner)
- Gridbert kommentiert Zwischenschritte

### 5.3 Fehler-Zustand

- Gridbert `confused`
- Sprechblase erklärt das Problem einfach
- Immer ein konkreter nächster Schritt
- Nie technische Fehlercodes, nie Schuldzuweisung

---

## 6. Motion & Animation

### 6.1 Prinzipien

- **Zweckmäßig, nicht dekorativ.** Jede Animation hat eine Funktion.
- **CSS-only wo möglich.** Kein JS für visuelle Animationen.
- **Beruhigend.** Nie hektisch. Nie blinkend. Nie "Attention-grabbing".
- **Maximal 400ms** für UI-Transitions. Gridbert-Emotionswechsel: 300ms.
- **Easing**: `cubic-bezier(0.25, 0.1, 0.25, 1)` Standard. Nie `linear`.

### 6.2 Animationen

| Element | Animation | Dauer | Easing |
|---|---|---|---|
| Karte erscheint | fadeInUp | 400ms | ease-out |
| Karte Hover | scale(1.02) + shadow | 200ms | ease |
| Gridbert Emotion | crossfade | 300ms | ease-in-out |
| Sprechblase | scale(0.95→1) + fadeIn | 250ms | ease-out |
| KPI-Wert Update | countUp (Zahl rollt) | 600ms | ease-out |
| Upload Drag-Over | Border pulsiert | 1000ms | ease-in-out, infinite |
| Neue Empfehlung | slideInRight | 500ms | ease-out |

---

## 7. Responsive Verhalten

```css
--bp-sm:  640px;    /* Smartphone landscape */
--bp-md:  768px;    /* Tablet */
--bp-lg:  1024px;   /* Desktop */
--bp-xl:  1280px;   /* Großer Desktop */
```

- **Mobile (< 640px):** Gridbert oben, Karten als Stack. Tisch = Upload-Button.
- **Tablet (768–1024px):** 2-Spalten. Gridbert in Sidebar oder oben.
- **Desktop (> 1024px):** Volles Dashboard. Gridbert frei positioniert.

Auf allen Größen: **Gridbert bleibt sichtbar.** Er verschwindet nie hinter einem Menü.

---

## 8. Textstimme (Microcopy)

Gridbert spricht wie das Familienmitglied das sich auskennt — nicht wie ein Chatbot, nicht wie ein Beamter, nicht wie ein Startup.

### Regeln

- **Du-Form.** Immer.
- **Kurz.** Maximal 2 Sätze pro Sprechblase.
- **Konkret.** "Du sparst ca. 340 € pro Jahr" statt "Du könntest sparen".
- **Ehrlich.** "Ich bin mir nicht ganz sicher — zeig mir mehr Daten."
- **Kein Buzzword-Bullshit.** Nie "KI-gestützt", "datengetrieben", "smart".
- **Österreichisch-Deutsch.** Natürlich, nicht Dialekt. "Strom" statt "Elektrizität".
- **Beruhigend.** Nie Panikmache, nie Dringlichkeit, nie FOMO.

### Beispiele

| Kontext | Schlecht | Gut |
|---|---|---|
| Begrüßung | "Willkommen bei Gridbert, Ihrem KI-gestützten Energieberater!" | "Hi! Ich bin Gridbert. Leg deine Stromrechnung auf den Tisch, ich schau mir das an." |
| Einsparung | "Unsere AI hat ein Optimierungspotenzial von 12,4% identifiziert." | "Du zahlst ca. 340 € im Jahr zu viel. Soll ich dir zeigen warum?" |
| Fehler | "Error 422: Unprocessable Entity" | "Das Format kenne ich nicht. Hast du vielleicht ein PDF oder CSV?" |
| Warten | "Bitte warten, Ihre Daten werden verarbeitet..." | "Ich les mir das gerade durch, Moment..." |
| Empfehlung | "Basierend auf Ihrer Verbrauchsanalyse empfehlen wir die Installation eines Batteriespeichers." | "Dein Nachtverbrauch ist ziemlich hoch. Lass uns mal durchrechnen ob sich ein Speicher auszahlt." |
| Unsicherheit | "Ergebnis: Keine ausreichende Datenbasis für Empfehlung." | "Für eine gute Empfehlung brauch ich noch deinen Lastgang. Kannst du den vom Netzbetreiber holen?" |
| News | "Relevante Marktinformationen für Sie" | "Neue PV-Förderung seit Jänner — könnte für dich passen." |

---

## 9. Design-Entscheidungstest

Bevor du ein Element implementierst, stell diese Fragen:

1. **Küchentisch-Test:** Würde dieses Element auf einem Küchentisch Sinn machen? (Karte = ja. Glasmorphism-Popup = nein.)
2. **Mama-Test:** Würde meine Mama verstehen was das bedeutet? (Konkrete Zahl = ja. "Optimierungspotenzial" = nein.)
3. **Bleistift-Test:** Könnte man das mit einem Bleistift skizzieren? (Strichzeichnung = ja. Gradient Mesh = nein.)
4. **Zwei-Adjektive-Test:** Erfüllt es mindestens zwei von: warm, analog, ehrlich, bodenständig, sorgfältig?
5. **Anti-Slop-Test:** Würde ein generischer AI-App-Generator das gleiche produzieren? Wenn ja → nochmal.

---

## Anhang A: Datei-Referenzen für Claude Code

Wenn du an der Gridbert-UI arbeitest:

1. Lies ZUERST dieses Design System (insbesondere Kapitel 0)
2. Lies den `frontend-design` SKILL.md für allgemeine Anti-Slop-Techniken
3. Verwende die CSS-Variablen aus Kapitel 2 — keine eigenen Farben/Fonts erfinden
4. Jede neue Komponente muss den Entscheidungstest aus Kapitel 9 bestehen
5. Gridbert-Avatar-Zustände aus Kapitel 3.2 verwenden, keine eigenen erfinden

## Anhang B: Tooling-Empfehlungen

- **Fonts laden**: Google Fonts CDN (Fraunces, Source Serif 4, JetBrains Mono)
- **Icons**: Eigene SVG-Icons im Sketch-Stil, NICHT Font Awesome / Lucide / Heroicons
- **Charts**: Recharts oder D3, gestylt mit Gridbert-Farben. Keine Default-Themes.
- **Avatar**: Einzelne SVG-Datei mit CSS-Klassen für Zustände
