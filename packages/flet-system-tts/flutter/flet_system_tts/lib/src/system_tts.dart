import 'package:flet/flet.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';

// Im Browser spricht nicht flutter_tts, sondern die eigene, kleine
// Anbindung an die Web Speech API — Gründe in web_speech_web.dart.
import 'web_speech_stub.dart'
    if (dart.library.js_interop) 'web_speech_web.dart' as web_speech;

class SystemTtsService extends FletService {
  SystemTtsService({required super.control});

  // late: im Browser wird flutter_tts nie angefasst
  late final FlutterTts _tts = FlutterTts();
  String? _language;
  double? _rate;

  @override
  void init() {
    super.init();
    debugPrint("SystemTts(${control.id}).init: ${control.properties}");
    control.addInvokeMethodListener(_invokeMethod);
    if (kIsWeb) {
      web_speech.warmUp();
    } else {
      // speak() soll erst zurückkehren, wenn die Wiedergabe fertig ist —
      // so kann die Python-Seite darauf warten.
      _tts.awaitSpeakCompletion(true);
    }
    update();
  }

  @override
  void update() {
    var language = control.getString("language", "el-GR")!;
    if (language != _language) {
      _language = language;
      if (!kIsWeb) _tts.setLanguage(language);
    }
  }

  // Nicht jede Plattform implementiert isLanguageAvailable (z.B. Windows) —
  // dann lieber optimistisch sprechen als fälschlich blockieren.
  Future<bool> _languageAvailable() async {
    if (kIsWeb) return web_speech.languageAvailable(_language!);
    try {
      return await _tts.isLanguageAvailable(_language!) == true;
    } catch (_) {
      return true;
    }
  }

  Future<dynamic> _invokeMethod(String name, dynamic args) async {
    debugPrint("SystemTts.$name($args)");
    switch (name) {
      case "speak":
        var text = args["text"] as String;
        var rate = (args["rate"] as num?)?.toDouble() ?? 1.0;
        if (kIsWeb) {
          // prüft die Stimme selbst und wirft "language_not_available"
          await web_speech.speak(text, _language!, rate);
          break;
        }
        if (!await _languageAvailable()) {
          throw Exception("language_not_available: $_language");
        }
        // flutter_tts: 0.5 ist das Normaltempo der Plattform-Engine;
        // rate ist unser Faktor darauf (1.0 normal, 0.65 langsam)
        if (rate != _rate) {
          _rate = rate;
          await _tts.setSpeechRate(0.5 * rate);
        }
        await _tts.stop();
        await _tts.speak(text);
        break;
      case "stop":
        if (kIsWeb) {
          web_speech.stop();
          break;
        }
        await _tts.stop();
        break;
      case "is_language_available":
        return await _languageAvailable();
      default:
        throw Exception("Unknown SystemTts method: $name");
    }
  }

  @override
  void dispose() {
    debugPrint("SystemTts(${control.id}).dispose()");
    control.removeInvokeMethodListener(_invokeMethod);
    if (kIsWeb) {
      web_speech.stop();
    } else {
      _tts.stop();
    }
    super.dispose();
  }
}
