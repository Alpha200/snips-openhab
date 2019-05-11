# Snips-OpenHAB

Skill für [Snips.ai](https://snips.ai) zur Ansteuerung von Geräten mit [OpenHAB](https://openhab.org).

## Parameter

* openhab_server_url: URL des OpenHAB-Servers (z.B. http://localhost:8080)
* room_of_device_default: Name des Raums, in dem sich das Snips-Gerät mit der Kennzeichnung default befindet

## Verwendung

Aktuell sind folgende Befehle implementiert:

* Geräte ein- und ausschalten
* Die Temperatur eines Raums ausgeben
* Werte erhöhen und verringern

Snips-OpenHAB verwendet [Semantic Tagging](https://community.openhab.org/t/habot-walkthrough-2-n-semantic-tagging-item-resolving/), um die korrekten Items zu finden.

### Geräte ein- und ausschalten

Geräte lassen sich wie folgt steuern:

* Schalte den Fernseher im Wohnzimmer aus
* Schalte das Licht im Schlafzimmer an
* Schalte mir bitte die Hintergrundbeleuchtung aus
* Schalte die Steckdosen in der Wohnung aus

### Temperatur

Die Temperatur eines Raums lässt sich wie folgt ausgeben:

* Wie warm ist es im Schlafzimmer?
* Ist es in der Küche Kalt?
* Wie warm ist es hier?

Um die Temperatur eines Raums zu bestimmen sucht Snips-OpenHAB nach Items vom Typ ```Number``` im gewünschten Raum, die den Tag ```Temperature``` und ```Measurement``` besitzen.

### Werte erhöhen und verringern

Items vom Typ ```Dimmer``` können mit folgenden Befehlen verändert werden.

* Verringere die Temperatur im Schlafzimmer
* Mache die Musik lauter
* Erhöhe die Helligkeit im Wohnzimmer

Die Items müssen dazu mit ihrer Eigenschaft (z.B. ```Temperature```) und dem Tag ```Setpoint``` getaggt sein.

### Wiedergabe steuern

Items vom Typ ```Player``` können ebenfalls gesteuert werden:

* Setze die Wiedergabe fort
* Pausiere die Wiedergabe im Wohnzimmer

## Multi-Room

Die App ist Multi-Room-fähig. Für jeden Befehl kann der Raum weggelassen werden.
Snips-OpenHAB sucht dann nach Geräten in dem Raum, in dem sich der angesprochene Snips-Satellit befindet.
Dazu wird die ```siteID``` als Raumname verwendet. Für das Gerät ```default``` wird als Raumname der Wert des Parameters ```room_of_device_default``` verwendet.

Snips-OpenHAB verwendet zur Raumbestimmung ebenfalls [Semantic Tagging](https://community.openhab.org/t/habot-walkthrough-2-n-semantic-tagging-item-resolving/).