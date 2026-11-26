// Sprachausgabe im Browser: direkt über die Web Speech API
// (window.speechSynthesis), nicht über flutter_tts.
//
// Warum nicht flutter_tts (4.2.5, flutter_tts_web.dart) — gemessen am
// 26.11.2026 in Firefox 160 und Chrome 157 unter Linux:
//
// 1. Es sucht die Stimme EINMAL, bei setLanguage. Beim Laden der Seite
//    kennt der Browser aber noch keine Stimmen (getVoices() ist leer;
//    Firefox liefert sie erst nach Sekunden, Chrome in zwei Schüben) —
//    die Stimme bleibt für immer ungesetzt.
// 2. Es vergleicht die Sprache wörtlich: "el-GR" passt weder auf "el"
//    (Firefox/Chrome mit speech-dispatcher) noch auf "el_GR" (Chrome auf
//    Android). isLanguageAvailable sagt dann „nein“, obwohl eine
//    griechische Stimme da ist.
// 3. Das Tempo: 0.5 ist bei flutter_tts auf dem Handy „normal“, im
//    Browser ist es 1.0 — alles liefe mit halbem Tempo.
// 4. Ein Fehler oder Abbruch beendet speak() nie (der Completer wird
//    verworfen statt erfüllt); ein zweites speak() während der Wiedergabe
//    wird verschluckt.
//
// Hier deshalb: Stimme bei jedem Sprechen suchen (und beim ersten Mal
// auf die Stimmenliste warten), Sprache nach ihrem Stamm vergleichen,
// je Wiedergabe ein neues Utterance, Ende und Fehler beenden speak().

import 'dart:async';
import 'dart:js_interop';

@JS('speechSynthesis')
external _Synth? get _synth;

extension type _Synth._(JSObject _) implements JSObject {
  external bool get speaking;
  external bool get pending;
  external JSArray<_Voice> getVoices();
  external void speak(_Utterance utterance);
  external void cancel();
  external void resume();
}

extension type _Voice._(JSObject _) implements JSObject {
  external String get name;
  external String get lang;
  external bool get localService;
}

@JS('SpeechSynthesisUtterance')
extension type _Utterance._(JSObject _) implements JSObject {
  external factory _Utterance(String text);
  external set voice(_Voice value);
  external set lang(String value);
  external set rate(double value);
  external set onend(JSFunction handler);
  external set onerror(JSFunction handler);
}

extension type _SpeechError._(JSObject _) implements JSObject {
  external String? get error;
}

// So lange wartet das erste Sprechen höchstens auf die Stimmenliste
// (Firefox mit speech-dispatcher: mehrere Sekunden für ~15 000 Stimmen).
const _firstWait = Duration(seconds: 12);
// Blieb die Suche einmal ohne Ergebnis, wartet jeder weitere Versuch nur
// noch kurz — der Hinweis soll dann nicht jedes Mal 12 s auf sich warten
// lassen, eine nachträglich aufgetauchte Stimme wird trotzdem gefunden.
const _laterWait = Duration(seconds: 1);
const _poll = Duration(milliseconds: 250);

bool _searchedInVain = false;
int _generation = 0;
// Hält das laufende Utterance fest: Chrome räumt es sonst weg, und
// onend kommt nie an.
// ignore: unused_element
_Utterance? _current;

String _norm(String lang) => lang.toLowerCase().replaceAll('_', '-');

/// Die beste Stimme für die Sprache — oder null. Es zählt der Sprachstamm
/// ("el-GR" passt auf "el", "el-GR", "el_GR").
_Voice? _pick(_Synth synth, String language) {
  final wanted = _norm(language);
  final base = wanted.split('-').first;
  _Voice? best;
  var bestScore = -1;
  for (final voice in synth.getVoices().toDart) {
    final lang = _norm(voice.lang);
    if (lang != base && !lang.startsWith('$base-')) continue;
    // espeak-Varianten ("Greek+Pedro", zu Tausenden) hinter die
    // Grundstimme; dann genaue Region, dann eine Stimme des Geräts
    final score = (voice.name.contains('+') ? 0 : 4) +
        (lang == wanted ? 2 : 0) +
        (voice.localService ? 1 : 0);
    if (score > bestScore) {
      best = voice;
      bestScore = score;
    }
  }
  return best;
}

Future<_Voice?> _findVoice(_Synth synth, String language) async {
  final patience = _searchedInVain ? _laterWait : _firstWait;
  final started = DateTime.now();
  while (true) {
    final voice = _pick(synth, language);
    if (voice != null) {
      _searchedInVain = false;
      return voice;
    }
    if (DateTime.now().difference(started) >= patience) {
      _searchedInVain = true;
      return null;
    }
    await Future<void>.delayed(_poll);
  }
}

/// Stößt das Laden der Stimmenliste an (beim Start der App), damit das
/// erste Antippen nicht darauf warten muss.
void warmUp() {
  _synth?.getVoices();
}

/// Spricht [text] und kehrt zurück, wenn die Wiedergabe endet oder
/// abgebrochen wird. [rate]: 1.0 = Normaltempo des Browsers.
/// Wirft "language_not_available", wenn der Browser keine Stimme für
/// [language] hat.
Future<void> speak(String text, String language, double rate) async {
  final synth = _synth;
  if (synth == null) {
    throw Exception("language_not_available: no speechSynthesis");
  }
  final mine = ++_generation;
  final voice = await _findVoice(synth, language);
  if (mine != _generation) return; // inzwischen kam ein neuerer Auftrag
  if (voice == null) {
    throw Exception("language_not_available: $language");
  }
  if (synth.speaking || synth.pending) synth.cancel();
  synth.resume(); // falls der Browser in „pausiert“ hängen geblieben ist

  final utterance = _Utterance(text);
  utterance.voice = voice;
  utterance.lang = voice.lang;
  utterance.rate = rate.clamp(0.1, 10.0).toDouble();
  final done = Completer<void>();
  utterance.onend = ((JSAny _) {
    if (!done.isCompleted) done.complete();
  }).toJS;
  utterance.onerror = ((_SpeechError event) {
    if (done.isCompleted) return;
    final error = event.error ?? "";
    // abgelöst von der nächsten Wiedergabe oder von stop(): kein Fehler
    if (error == "interrupted" || error == "canceled") {
      done.complete();
    } else {
      done.completeError(Exception("speech_error: $error"));
    }
  }).toJS;
  _current = utterance;
  synth.speak(utterance);
  return done.future;
}

void stop() {
  _generation++;
  _synth?.cancel();
}

Future<bool> languageAvailable(String language) async {
  final synth = _synth;
  if (synth == null) return false;
  return await _findVoice(synth, language) != null;
}
