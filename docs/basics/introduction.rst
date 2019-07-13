Einführung
==========

Diese Snips-App verwendet `semantisches Taggen`_,
um zu bestimmten, welche Items für einen Sprachbefehl angesprochen werden müssen.

Hierzu werden Items in die Kategorien ``Location``, ``Equipment`` und ``Point`` kategorisiert.

``Points`` und ``Equipments`` können Teil einer ``Location`` sein. ``Locations`` können Teil einer anderen
``Location`` sein und ``Equipments`` Teil eines anderen ``Equipments``. ``Points`` können desweiteren mit einer
``Property`` versehen werden.

Die Relationen zwischen ``Locations``, ``Equipments`` und ``Points`` werden durch Gruppen modelliert.
Durch Tags in der Item-Konfiguration in OpenHAB können die Items annotiert werden. Es können die Tags
aus der folgenden Grafik verwendet werden:

.. figure:: https://community-openhab-org.s3.dualstack.eu-central-1.amazonaws.com/original/3X/4/2/424749375f6d51214475ac0d2b9000a957d718a7.jpeg

    Die Eclipse Smart Home Ontologie. Quelle_

So kann z.B. der Sprachbefehl "Schalte die Anlage im Schlafzimmer an" mit folgender Konfiguration verwendet werden:

.. code-block::

    Group schlafzimmer "Schlafzimmer" <bedroom> ["Bedroom"]
    Group Anlage "Anlage" <player> (schlafzimmer) ["Receiver"]
    Switch Anlage_An_Aus "Power" <player> (Anlage) ["Switch"]
    Dimmer Anlage_Volume "Lautstärke" <soundvolume> (Anlage) ["SoundVolume"]

Zunächst sucht die Snips-App nach dem Raum Schlafzimmer. Durch den Tag ``Bedroom`` an der Gruppe ``schlafzimmer`` erkennt
die App, dass es sich bei dieser Gruppe um eine ``Location`` handelt. Nun sucht er nach einem Item, welches direkt oder
indirekt in der Gruppe ``schlafzimmer`` ist und als "Anlage" identifiziert werden kann.
Dazu bezieht die Anwendung das Label des Items und Synonyme ein. Schließlich findet es die Anlage, welche
durch den Tag ``Receiver`` vom Typ ``Equipment`` ist. Da die App die Gruppe nicht direkt einschalten kann
sucht sie nach einem Item innerhalb der Gruppe ``Anlage``, welches vom Typ ``Point_Control_Switch`` ist.
Durch den Tag ``Switch`` ist dies beim Item ``Anlage_An_Aus`` der Fall und die App sendet über die REST-API von
OpenHAB den Command ``ON`` an das Item.

In den Kapiteln :doc:`Konfiguration <configuration>` und :doc:`Sprachbefehle <usage>` gibt es weitere Informationen zur
Einrichtung und Verwendung der App.

.. _`semantisches Taggen`: https://community.openhab.org/t/habot-walkthrough-2-n-semantic-tagging-item-resolving/
.. _Quelle: https://community.openhab.org/t/habot-walkthrough-2-n-semantic-tagging-item-resolving/
