# Prüfpaket für Ausbilder (SME-Review)

**Ziel:** Ein erfahrener CQB-Ausbilder (Polizei oder Militär) prüft, ob die Taktik-Modelle dieses
Forschungsprototyps die Techniken fair wiedergeben. Erst danach werden Modell und Hypothesen
eingefroren und präregistriert. Aufwand: etwa 45 Minuten.

**Was das Projekt ist:** eine Simulationsstudie zur Frage, wie nah etablierte Raumeintritts-
Techniken an der besten in einem vereinfachten Modell gefundenen Strategie liegen
(koordinierte Suche unter Sichtbeschränkung). Es geht um Analyse und Lehre, nicht um operative
Planung. Das Modell ist bewusst abstrakt: keine Waffenballistik, keine Türen, die sich öffnen,
keine menschlichen Stressfaktoren.

**Zum Anschauen:** `out/bench-e1b/viewer3d.html` (3D, Technik und „Geist“ wählbar) und
`out/bench-e1b/report.html` (Kennzahlen und Draufsicht-Replays). Beide entstehen mit
`python -m uv run killhouse-bench`.

---

## 1. Modellannahmen (bitte auf Plausibilität prüfen)

| Annahme | Wert | Ihre Einschätzung |
|---|---|---|
| Team | 4 Personen, Split-Stack (#1 und #3 links, #2 und #4 rechts) | |
| Türbreite / Wanddicke | 0,9 m / 0,2 m (Varianten 0,8–1,2 m) | |
| Gehtempo / Eintrittstempo | 1,35–1,55 m/s / ×1,3 beim Eintritt | |
| Abstand im Stack | 0,75 m | |
| Zeitversatz zwischen #1, #2, #3, #4 | je 0,6 s | |
| Blickfeld (Aufmerksamkeitskegel) | 100° (Varianten 80–120°) | |
| Zeit, bis ein Bereich als „wahrgenommen“ gilt | 0,3 s im Blickkegel | |
| Drehgeschwindigkeit von Blick und Waffe | 4 rad/s (≈ 230°/s) | |
| Reaktionszeit einer versteckten Bedrohung | 0,3 s ab Sichtkontakt | |
| Kleiner Raum (< 4,5 m breit) | nur #1 und #2 treten ein | |

## 2. Die vier Techniken, wie sie im Modell kodiert sind

Raumkoordinaten: Eingangswand unten, x nach rechts, y in den Raum.
„Tief“ heißt etwa 1 m von Eingangs- und Seitenwand; „flach“ heißt zwischen Tür und tiefer
Position, etwa 1,2 m von der Eingangswand.

| Technik | #1 (links) | #2 (rechts) | #3 (links) | #4 (rechts) |
|---|---|---|---|---|
| **Crisscross** | quert, tief rechts, Blick zuerst rechte Ecke | quert, tief links, Blick linke Ecke | flach rechts | flach links |
| **Buttonhook** | hakt um den Rahmen, tief links | hakt, tief rechts | flach links | flach rechts |
| **Pie + Crisscross** | schneidet vorher von außen den Kuchen (Bogen r = 1,4 m), dann wie Crisscross | wartet, dann Crisscross | wie Crisscross | wie Crisscross |
| **Limited Penetration** | ein Schritt hinein, links neben die Tür, Blick von der nahen Ecke zur fernen | rechts entsprechend | bleibt draußen | bleibt draußen |

Anpassungen, die ich selbst festgelegt habe (bitte besonders prüfen):

- **Ecktür:** Auf der kurzen Seite gibt es keine Ecke. Der Operator dieser Seite geht deshalb
  gerade tief an der Seitenwand entlang hinein, der nachfolgende nimmt eine tiefere Position auf
  der langen Seite ein.
- **#3/#4** schauen nicht in die nahe Ecke (die gehört #1/#2), sondern sofort in die fernen
  Ecken ihrer Seite.
- **Möbel / toter Winkel:** Bleibt ein Bereich hinter einem Möbel ungesehen, geht ein bereits
  eingetretener Operator (bevorzugt #3/#4) nach 0,6 s Sektorhalten an die freie Stelle, die
  diesen Bereich am besten einsieht.

## 3. Fragen

1. Entsprechen die vier Kodierungen dem, was Sie unterrichten? Was ist falsch oder fehlt?
2. Ist die Ecktür-Anpassung so, wie Sie es vorgehen würden?
3. Sind 0,6 s Zeitversatz und die Tempi realistisch, für Training und für den Einsatz?
4. Ist die 2-Mann-Regel für kleine Räume (< 4,5 m) sinnvoll? Wo liegt die Grenze?
5. Sind Blickfeld, Wahrnehmungszeit und Drehgeschwindigkeit plausibel? Gibt es Zahlen aus
   Training oder Forschung, die wir verwenden sollten?
6. Ist der Schritt „toten Winkel sichern“ so üblich? Wer übernimmt ihn typischerweise?
7. **Befund aus der Optimierung (Hypothese, keine Empfehlung):** Bei Ecktüren war die beste
   gefundene Strategie: Der Operator der kurzen Seite geht sofort und tief an der Seitenwand
   entlang hinein, #1 folgt 0,4–0,5 s später zur langen Seite. Kennen Sie das? Warum macht man
   es in der Praxis (nicht) so?
8. Bei mittigen Türen war die beste gefundene Strategie ein Crisscross mit engerem Timing
   (#1 sofort, #2 nach 0,5 s). Ist ein engeres Timing in der Praxis machbar oder eher gefährlich?
9. Welche weiteren Techniken sollten verglichen werden, zum Beispiel Einseiten-Stack oder
   Heavy Side, langsames oder deliberates Vorgehen, Two-Man-Flow?
10. Welche Kennzahlen interessieren Praktiker wirklich (Zeit, Exposition, Fratricide-Risiko,
    Kontrolle über den Raum, etwas anderes)?
11. Gibt es an der Darstellung etwas, das missverständlich oder unseriös wirken könnte?

## 3b. Fragen zum Taktik-Katalog (`docs/TACTICS.md`)

12. Einseiten-Stack mit Kombination (einer quert, einer hakt): Ist „#1 quert, #2 hakt“ die
    übliche Reihenfolge? Wann wählt man „#1 hakt“?
13. Zwei-Mann-Eintritt: Wann bleiben #3/#4 draußen, und was ist dann ihre Aufgabe?
14. Deliberates Vorgehen: Sind 0,6-faches Tempo, 1,2 s Abstand und 1,0 s Eckhalten plausibel?
15. **Befund:** Crisscross ist im Modell empfindlich für Timing-Fehler. Die beiden kreuzenden
    Operatoren berühren sich bei Verzögerungen in der Tür. Deckt sich das mit Ihrer
    Erfahrung im Training?
16. **Befund:** Der dritte Operator bringt viel, der vierte wenig. Plausibel?
17. **Flur-Disziplin:** Im Modell beobachten #3/#4 beim Vorbeigehen offene Türen ungesicherter
    Räume (bis 3,5 m). Ist das so üblich? Wer übernimmt das?

## 4. Rückmeldung

Bitte pro Frage: **stimmt / teilweise / stimmt nicht** und eine kurze Begründung. Sie werden
im Bericht namentlich oder anonym genannt, nach Ihrem Wunsch. Änderungen, die aus dem Review
folgen, werden vor der Präregistrierung mit Datum in `docs/PREREG_E1_draft.md` vermerkt.
