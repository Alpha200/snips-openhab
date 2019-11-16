Tests
#####

Mocks generieren
----------------

Im Unterordner ``test`` befindet sich eine Docker-Compose-Konfiguration,
mit der sich mit ``docker-compose up`` eine openHAB-Instanz mit ein paar Testitems
erstellen lässt. Über die Datei ``getMocks.sh`` lassen sich die openHAB-Items
über die REST-API abrufen und in einer JSON-Datei speichern, sodass diese beim
Testen als Mocks verwenden lassen.

Tests aufrufen
--------------

Die Tests lassen sich wie folgt aufrufen:

.. code-block:: console

    $ coverage run --source openhab test_openHAB.py

Mit dem folgenden Befehl lässt sich anschließend ein HTML-Report erstellen,
welcher Im Unterordner ``htmlcov`` abgelegt wird.

.. code-block:: console

    $ coverage html
