import 'package:flet/flet.dart';

import 'system_tts.dart';

class Extension extends FletExtension {
  @override
  FletService? createService(Control control) {
    switch (control.type) {
      case "SystemTts":
        return SystemTtsService(control: control);
      default:
        return null;
    }
  }
}
