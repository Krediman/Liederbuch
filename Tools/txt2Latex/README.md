# txt2latex

Konvertiert Lieder aus textdateien in Latex. 
Die Ausgabe ist kompatibel mit dem Latex-Packet leadsheets.

## Installation:
Diese Software verwendet Python3. python3 kann auf [www.python.org](www.python.org/downloads/) heruntergeladen werden.

Außerdem wird die Bibliothek jinja2 benötigt.
`$ pip install jinja2`

## Verwendung:
Der Konveriterung wird gestartet mit
```$ python3 converter.py [-o] [-a] <Eingabeverzeichnis> <Ausgabeverzeichnis>```

Das Programm liest alle Dateien im Eingabeverzeichnis und erstellt für jede Datei `Name.txt` eine Datei `Name.tex` im Ausgabeverzeichnis, die den dazugehörenden Latex code enthält. Standartmäßig werden nur Dateien verarbeitet, die auf `.txt` oder `.lied` enden.

Die Option `-o` erlaubt das Überschreiben von Dateien im Ausgabeverzeichnis, falls nötig. 
Die Option `-a` deaktiviert den Dateinamenfilter. Es werden alle Dateien unabhängig vom Suffix verarbeitet

