// Platzhalter außerhalb des Browsers — dort spricht flutter_tts
// (system_tts.dart fragt kIsWeb, bevor es hierher kommt).

void warmUp() {}

Future<void> speak(String text, String language, double rate) =>
    throw UnsupportedError("web speech only");

void stop() {}

Future<bool> languageAvailable(String language) async => false;
