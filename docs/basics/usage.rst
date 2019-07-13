Sprachbefehle
=============

Aktuell sind folgende Befehle implementiert:

* Items vom Typ Switch ein- und ausschalten
* Die Temperatur eines Raums ausgeben
* Items vom Typ Dimmer erhöhen und verringern
* Items vom Typ Player steuern (Play, Pause, Next, Previous)

Bei Anfragen muss stets der Raum genannt werden, in dem sich das Gerät befindet. Es gibt nur die folgenden Ausnahmen:

* Die Anfrage referenziert eindeutig ein Gerät (z.B. Fernseher den einzigen Fernseher). Sagt der Nutzer z.B. Tischlampe und es gibt mehr als ein Item in der Wohnung mit dem Label Tischlampe funktioniert dies nicht.
* Die angesprochenen Geräte befinden sich im aktuellen Raum

Die Trainingsdaten für die einzelnen Intens können :doc:`hier <training>` nachgeschlagen werden.

Geräte ein- und ausschalten
---------------------------

Items vom Typ ``Switch`` und ``Dimmer`` lassen sich wie folgt ein- und ausschalten:

* Schalte den Fernseher im Wohnzimmer aus
* Schalte das Licht im Schlafzimmer an
* Schalte mir bitte die Hintergrundbeleuchtung aus
* Schalte die Steckdosen in der Wohnung aus

Es ist ebenfalls möglich mehrere Items auf einmal ein- und auszuschalten:

* Schalte die Anlage und den Fernseher ein

Die Items müssen sich dazu im selben Raum befinden.
Die Angabe von mehreren Räumen auf einmal wird aktuell nicht unterstützt.


Temperatur abfragen
-------------------

Die Temperatur eines Raums lässt sich wie folgt ausgeben:

* Wie warm ist es im Schlafzimmer?
* Ist es in der Küche Kalt?
* Wie warm ist es hier?
* Wie viel Grad sind es im Badezimmer

Um die Temperatur eines Raums zu bestimmen sucht Snips-OpenHAB nach
Items vom Typ ``Number`` im gewünschten Raum, die den
Tag ``Temperature`` und ``Measurement`` besitzen.

Werte erhöhen und verringern
----------------------------

Items vom Typ ``Dimmer`` können mit folgenden Befehlen verändert werden.

* Verringere die Temperatur im Schlafzimmer
* Mache die Musik lauter
* Erhöhe die Helligkeit im Wohnzimmer

Die Items müssen dazu mit ihrer Eigenschaft (z.B. ``Temperature``) getaggt sein und vom Typ ``Point_Control`` sein.

Wiedergabe steuern
------------------

Items vom Typ ``Player`` können ebenfalls gesteuert werden:

* Setze die Wiedergabe fort
* Pausiere die Wiedergabe im Wohnzimmer
* Spiele das vorherige Lied
* Wechsle zum nächsten Lied

Sie müssen dazu vom Typ ``Point_Control`` sein (z.B. durch das taggen mit ``Control``.
