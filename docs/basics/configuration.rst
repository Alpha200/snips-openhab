Konfiguration
=============

Damit die App verwendet werden kann müssen sowohl die Parameter der App als auch die OpenHAB Items konfiguriert werden.

.. Important::
    Die OpenHAB-Konfiguration wird für eine schnellere Reaktionszeit zwischengespeichert. Wenn die OpenHAB-Konfiguration
    geändert wird muss die App neu gestartet werden.

Snips-App
---------

Parameter
^^^^^^^^^

Folgende secret-Parameter müssen konfiguriert werden:

+-----------------------------+--------------------------------------------------------------------------------------+
| ``openhab_server_url``      | URL des OpenHAB-Servers (z.B. http://localhost:8080)                                 |
+-----------------------------+--------------------------------------------------------------------------------------+
| ``room_of_device_default``  | Name des Raums, in dem sich das Snips-Gerät mit der Kennzeichnung default befindet.  |
+-----------------------------+--------------------------------------------------------------------------------------+
| ``sound_feedback`` (off/on) | Statt der vollen Sprachausgabe, was die App gemacht hat, kann auch nur ein           |
|                             | Bestätigungston gespielt werden. Mit der Frage "Was hast du gemacht?" kann das       |
|                             | volle Sprachfeedback nachträglich gespielt werden.                                   |
+-----------------------------+--------------------------------------------------------------------------------------+

Multi-Room
^^^^^^^^^^

Die App ist Multi-Room-fähig. Wird der Raum in einem Befehl weggelassen sucht
Snips-OpenHAB nach Geräten in dem Raum, in dem sich der angesprochene Snips-Satellit befindet.
Dazu wird die ``siteID`` des Satelliten als Raumname verwendet.
Für das Gerät ``default`` wird als Raumname der Wert des Parameters ``room_of_device_default`` verwendet.


OpenHAB-Konfiguration
---------------------

Damit Snips-OpenHAB verstehen kann, welche Items geschaltet werden müssen,
müssen die Items semantisch getaggt werden. Dies wird hier_ beschrieben.

.. _hier: https://community.openhab.org/t/habot-walkthrough-2-n-semantic-tagging-item-resolving/


Synonyme
^^^^^^^^

Durch das semantische Taggen werden für die Items automatisch nützliche Synonyme hinzugefügt, über
die das Gerät angesprochen werden kann.

Sind diese nicht ausreichend lassen sich wie folgt noch weitere Synonyme manuell hinzufügen:

.. code-block::

    Switch Ventilator "Ventilator" [%.1f °C]" <temperature> (schlafzimmer) { synonyms="Propeller,Windmaschine" }


Beispiel
^^^^^^^^

Im Folgenden ist eine Beispielkonfiguration aufgeführt:

.. code-block::

    Group wohnung "Wohnung" <groundfloor> ["Indoor"] { synonyms="haus" }
    Group schlafzimmer "Schlafzimmer" <bedroom> (wohnung) ["Bedroom"]
    Group garten "Garten" <garden> ["Garden"]
    Group kueche "Küche" <kitchen> (wohnung) ["Kitchen"]
    Group esszimmer "Esszimmer" <corridor> (wohnung) ["Room"]
    Group wohnzimmer "Wohnzimmer" <corridor> (wohnung) ["LivingRoom"]

    Player Audionitrid_Control "Fernbedienung" <mediacontrol> (schlafzimmer) ["Control"]
    Player Wohnzimmer_Control "Fernbedienung" <mediacontrol> (wohnzimmer) ["Control"]

    Group Fernseher "Fernseher" <television> (wohnzimmer) ["Screen"]
    Switch Fernseher_An_Aus "Power" <television> (Fernseher) ["Switch"]
    String Fernseher_Input "Quelle" <television> (Fernseher) ["Control"]

    Group Anlage "Anlage" <player> (schlafzimmer) ["Receiver"]
    Switch Anlage_An_Aus "Power" <player> (Anlage) ["Switch"]
    Dimmer Anlage_Volume "Lautstärke" <soundvolume> (Anlage) ["SoundVolume"]

    Switch Lampe_Esszimmer "Tischlampe"<light> (esszimmer) ["Light"]
    Switch Lampe_Vitrine "Vitrine" <light> (esszimmer) ["Light"]
