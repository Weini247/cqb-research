# Roadmap

Leitfrage: **Wie nah sind etablierte Teamtaktiken für Gebäude am Optimum, und kann man
bessere, robuste und lernbare Taktiken automatisch finden?**
Rahmung nach außen: koordinierte Mehragenten-Suche unter Sichtbeschränkung, mit Menschen,
Robotern und KI-Planern als Akteuren. CQB ist die wichtigste Fallstudie.

Stand: 2026-11-02. Status pro Etappe: ✅ fertig · 🔄 läuft · ⏳ offen.

## Leitplanken (gelten für alle Etappen)

- **Fokus:** Ein anderes Forschungsprojekt hat Vorrang; Killhouse wächst in Etappen, die jeweils für sich
  etwas Fertiges ergeben. Rechenläufe immer mit einem Kern, solange andere Rechenläufe laufen.
- **Seriosität:** abstraktes Duell-Modell, keine Ballistik oder Waffenwirkung, Taktiken nur
  auf dem Niveau öffentlicher Quellen. Gefundene Taktiken sind Hypothesen, keine
  Einsatzempfehlungen. Ethik- und Dual-Use-Erklärung im Repo.
- **Wissenschaftlichkeit:** Hypothesen vor der Bestätigung präregistrieren, zurückgehaltene
  Testgeometrien, Sensitivitätsanalyse, Ausbilder-Review, Grenzen in jedem Bericht.
- **Jede Entdeckung muss vier Prüfungen bestehen:** neue Grundrisse, Sensitivität,
  adaptiver Gegner, Ausbilder.

## Etappen

### 1 · Einzelraum-Studie abschließen 🔄
- ✅ Modell, 4 Doktrinen, Optimierer, Bedrohungsmodell (eine und mehrere Bedrohungen),
  toter Winkel, Raumgenerator, Sensitivität, 2D-Report, 3D-Viewer
- ✅ Ausbilder-Prüfpaket ([SME_REVIEW.md](SME_REVIEW.md)), Präregistrierungs-Entwurf
- 🔄 Pilotlauf mit dem Ziel `risk_multi`, Bericht aktualisieren
- **Fertig, wenn:** Bericht E1-Pilot steht, Prüfpaket kann verschickt werden.

### 2 · Mehrere Räume: die Wohnung ⏳
- Allgemeine Geometrie: Wände als Segmente, Sicht über ganze Grundrisse, Bedrohungen in allen
  Räumen, Gefahr aus ungesicherten Nachbarräumen und Fluren
- Türen mit Anschlag (innen/außen, Scharnierseite), mehrere Eingänge
- Wohnungsgenerator (80–120 m², 4–7 Räume, Flur, Möbel); echte Grundrisse aus öffentlichen
  Datensätzen, nachdem deren Lizenz geprüft ist
- Gebäude-Ablauf: Reihenfolge, Flursicherung, Raumeintritte mit den Katalog-Techniken
- 3D-Viewer für Wohnungen (abgeschnittene Wände, Folgekamera, Geist)
- **Fertig, wenn:** Ein Befehl erzeugt eine Wohnung plus Episode mit Risiko-Kennzahlen, im
  3D-Viewer anschaubar, mit Tests.

### 3 · Echte Taktiken: der Katalog ⏳
- `docs/TACTICS.md`: jede Technik mit Quelle, Parametern, Anwendbarkeit und Review-Status
- Stack-Varianten (Split, Heavy Side), 1–4 Personen, Kombinationen (Cross plus Hook), Limited
  Penetration, Pie, dynamisch vs. deliberat; Flur: L-Ecke, T-Kreuzung, offene Türen passieren
- Ausführungsfehler als Verrauschung (Timing, Position, Blick)
- Ausbilder-Review, Runde 1 (Aufgabe für dich: Kontakt finden)
- **Fertig, wenn:** Der Katalog ist kodiert, getestet und hat seinen Review-Status.

### 4 · Schneller Simulator (Idee 6) ⏳
- PyTorch auf der GPU (CUDA 12.6 auf der 1070 Ti; JAX läuft unter Windows nicht nativ):
  ganze Populationen auf einmal, weiche Sicht- und Blickfunktionen für Gradienten
- Regressionstest gegen das numpy-Referenzmodell (gleiche Ergebnisse im harten Grenzfall)
- **Fertig, wenn:** mindestens 20-mal schneller als die numpy-Referenz, mit messbarer
  Gradientenoptimierung.

### 5 · Robustheit und Gegner ⏳
- Robustheitsstudie: Sind optimierte Strategien fragil, Doktrinen robust?
- Gegner, der die Taktik kennt (bestmögliche Positionierung): Was kostet Vorhersagbarkeit,
  lohnt sich Mischen?
- **Fertig, wenn:** Beide Fragen sind mit Grafiken und Konfidenzintervallen beantwortet.

### 6 · Bestätigungsstudie und Preprint 1 ⏳
- Präregistrierung einfrieren (nach dem Review), git-Tag, OSF
- Läufe auf zurückgehaltenen Räumen und Wohnungen mit 3 Seeds
- Preprint (arXiv): Doktrin vs. Optimum, Robustheit, Vorhersagbarkeit
- **Fertig, wenn:** Preprint veröffentlicht, Code-Release mit DOI (Zenodo).

### 7 · KI-Planer-Benchmark (Idee 1) ⏳
- Plan-Schema (JSON), Grundriss als Text und als Bild, Bewertung durch den Simulator
- Modelle über API (Schlüssel und Budget kommen von dir), Rangliste vs. Doktrin und Optimum
- Räume und Wohnungen, Mehrschritt-Planung
- **Fertig, wenn:** reproduzierbare Rangliste, Kurzbericht, eventuell als Workshop-Paper.

### 8 · Roboter als Vorhut (Idee 4) ⏳
- Aufklärungsroboter mit Rundumsensor, die nicht bekämpfen; Einsatz in Wohnungen
- Wie stark senken sie das Risiko, wie viele lohnen sich, welche Räume zuerst
- Brücke zu einem separaten Mehr-Roboter-Projekt als Erzählung
- **Fertig, wenn:** Kurve „Risiko vs. Anzahl Roboter“ für mehrere Gebäudetypen.

### 9 · Eigene Taktiken finden ⏳
- Taktik als Programm aus Katalog-Bausteinen; Struktursuche (genetische Programmierung oder
  Baumsuche)
- Ziel: Risiko über viele Grundrisse, Max-Min gegen den Gegner, Robustheit, Strafe für
  Komplexität
- Fernziel: lernende Agenten (MARL) und deren Übersetzung in lesbare Regeln
- **Fertig, wenn:** mindestens eine neue Taktik-Familie besteht alle vier Prüfungen; Preprint 2.

### 10 · Optional ⏳
- Interaktives Web-Labor auf GitHub Pages (eigenen Plan bauen, sofort bewertet)
- Fernvision: Video eines Trainings rein, 3D-Wiederholung und minimale Gegenfakten raus

## GitHub-Strategie

**Jetzt:** lokal weiterarbeiten. Ein privates GitHub-Repo als Backup ist jederzeit möglich,
das entscheidest du.

**Erste öffentliche Version v0.1: nach Etappe 2.** Dann gibt es eine sichtbare Wohnungs-Demo.
Vorher erledigen:
- README auf Englisch mit 3D-Hero-GIF, einem Satz Leitfrage, Quickstart, Ergebnisgrafik
- Lizenz wählen (deine Entscheidung), `CITATION.cff`, Ethik- und Dual-Use-Erklärung
- CI (GitHub Actions: ruff und pytest), saubere Ordnerstruktur, keine privaten Pfade
- Den Namen prüfen: „Killhouse“ ist szenetypisch, wirkt auf Professoren aber martialisch. Ein
  neutralerer Repo-Name mit Killhouse als Projekt- oder Demo-Name ist eine Überlegung wert.

**Weitere Releases:** v0.2 mit Preprint 1 (Tag, DOI, präregistriert); v0.3 mit dem
Benchmark; v1.0 mit den entdeckten Taktiken.

**Wie viele Repos:**
1. **Hauptrepo** (Simulator, Studien, Viewer) als Flaggschiff. Alles Wissenschaftliche
   bleibt hier, damit die Geschichte zusammenhängt.
2. **Benchmark-Repo, optional ab Etappe 7:** nur wenn er als eigenständige Rangliste mit
   Website wachsen soll. Benchmarks werden als eigenes Repo eher gefunden und genutzt.
3. **Profil-README** (`<user>/<user>`): eine Seite, die mehrere Projekte und Killhouse als gemeinsames
   Forschungsprofil „Mehragenten-Koordination in Gebäuden“ zeigt, mit Bildern und Links.
   Für Recruiter ist das der Einstieg.
