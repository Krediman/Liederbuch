import jinja2 as j2
import os
from typing import Tuple, Union, List, Dict, Collection
import re
import sys
from lib.Heuristik.Heuristik import Heuristik
from lib.texttype.texttype import texttype
# Erlaubt das einfache Arbeiten mit texen zugeordneten daten

# Konfiguration:

# l: Mollakkorde in Kleinbuchstaben, m: mit m (e-> Em), (Leer): Keine Änderung
Akkordstil = 'm'

STROPHENREGEX = r'^\s?\d+([).:]|( :))*\s*'
REFRAINREGEX = r'^\s?Ref(rain)?[).: ]+\s*'
INFOREGEX = r'^\s?@?info((:\s*)|\s+)'
# muss einfach nur alles fangen, was möglicherweise ein Akkord sein könnte.
AKKORDREGEX = r'\S+'
WDHLREGEX = r'[/|]{1,2}\:'
WDHRREGEX = r'\:[/|]{1,2}'

# Liste der ersetzungen, die in den zeilen passieren soll
Ersetzungen = [(WDHLREGEX, r'\lrep'), (WDHRREGEX, r'\rrep') # Wiederholungszeichen setzen
               ]

Umgebungen = {  # Definiert die start- und endkommandos für die verwendeten latex-Umgebungen
    # wird verwendet, falls aus irgendeinem Grund kein anderer passt. Nicht entfernen!
    'standart': (r'\beginverse*',      r'\endverse'),
    'strophe*':   (r'\beginverse*',      r'\endverse'),
    'strophe':    (r'\beginverse',       r'\endverse'),
    'refrain':   (r'\beginchorus',      r'\endchorus'),
    # HACK: Die Wiederholung des Refrain nutzt keine Umgebung. Erzeugt wird eine Umgebung ohne Inhalt und endstring. Das ist ein einzelnes Kommando.
    'refrainWdh': (r'\printchorus',      r''),
    'info':     (r'\beginscripture{}', r'\endscripture')
}

# typing: Pfadspezifikation:
pfad = Union[str, os.DirEntry]


class SongLaTexttype(texttype):
    '''Subklasse von texttype, die zusätzlich textblöcke erzeugt, die an jinja2 übergeben werden können'''

    def __init__(self, data: List[List[str]], gew_typ=None):
        texttype.__init__(self, data, gew_typ)
        self.blocktyp = ''
        self.text = []
        self.use_autotyp = True

    # override
    def _generateWorkingData(self):
        self.blocktyp = ''
        self.text = []
        return super()._generateWorkingData()

    __doc__ = texttype.__doc__ + '''
        Speichert die Daten, die hinterher in latex ausgegeben werden.
        typ: alle typen, die leadsheets kennt. z.B. verse, verse*, chorus, info

        text: wird 1: 1 in den latex code übernommen. '''

    def setzeBlocktyp(self, typ):
        '''typ des texttype objektes setzen'''
        self.blocktyp = typ
        self.use_autotyp = False

    def autoTyp(self) -> int:
        '''findet automatisch den typ des texttype-objektes
        gibt die nummer der Zeile zurück, in der der hinweis gefunden wurde
        Es wird angenommen, dass das ganze objekt nur einen einzelnen Block enthält.
        gibt die zeilennummer zurück, in der das label, falls vorhanden, steht,
        sonst -1'''
        self._updateWD()
        for i in range(len(self.str)):
            line = self.str[i]
            if re.match(REFRAINREGEX, line, re.IGNORECASE) is not None:
                # Auf Chorus-Wiederholungs-hinweis (Ref. ohne weiteren Text) prüfen
                if (re.sub(REFRAINREGEX, line, '', flags=re.IGNORECASE).replace(' ', '') == '' and len(self.str) == 1):
                    self.blocktyp = 'refrainWdh'
                else:
                    self.blocktyp = 'refrain'
                return i

            elif re.match(STROPHENREGEX, line, re.IGNORECASE) is not None:
                self.blocktyp = 'strophe'
                return i

            elif re.match(INFOREGEX, line, re.IGNORECASE) is not None:
                self.blocktyp = 'info'
                return i

            else:
                self.blocktyp = 'strophe*'
                # kein return, vielleicht findet man das label in der nächsten zeile
        return -1

    @staticmethod
    def akkordstil(akkord: str, stil: str) -> str:
        '''Konvertiert den Akkordstil
        im Moment werden nur Mollschreibweisen umgewandelt
        stil: 'l' oder 'm'
        'l': e -> Em
        'm': Em -> e'''
        if stil not in {'l', 'm'}:
            return akkord
        akkorde = akkord.split('/')  # für Doppelakkorde, etc.
        erg = []
        for akk in akkorde:
            if stil == 'l':
                if 'm' in akkord.lower():  # Mollakkord im m - Schreibweise
                    erg.append(akkord.lower().replace('m', ''))
                else:
                    erg.append(akk)

            elif stil == 'm':
                fund = re.search(
                    r'(^\s*)([abcdefgh])([#b]*)(m?)([\S\s]*)', akk, flags=re.IGNORECASE)
                if fund is None:
                    # seltsamer Akkord... wir nehmen ihn so, wie er ist.
                    print('WARNung: Akkord "'+akkord +
                          '" kann nicht konvertiert werden.', file=sys.stderr)
                    erg.append(akk)
                    break
                g = list(fund.groups())
                # g[0] ist leerraum vor dem Akkord
                # g[1] ist jetzt der Akkordbuchstabe
                # g[2] der halbton (# oder b)
                # g[3] 'm' falls Moll in M-schreibweise, sonst leer
                # g[4] der Rest des Akkordes
                if g[3].lower() == 'm':  # Mollakkord in m-Schreibweise: Nichts zu tun
                    pass
                elif g[1].islower():  # Akkord ist kleingeschrieben und in l-schreibweise, also Moll
                    g[1] = g[1].upper()
                    g[3] = 'm'
                # Akkord ist großgeschrieben und in l-schreibweise, also Dur. Nichts zu tun.
                elif g[1].isupper():
                    pass
                else:  # Es wurde kein Akkordbuchstabe gefunden. Konvertierung kann nicht stattfinden.
                    print('WARNung: Akkord "' + akkord +
                          '" kann nicht konvertiert werden.', file=sys.stderr)
                    pass
                erg.append(''.join(g))

        return '/'.join(erg)

    

    @staticmethod
    def akkordeInZeile(text: List[str], gew_typ: List[str], stil: str):
        '''setzt akkord- und Textzeilen zusammen, wenn möglich.
        sonst werden zeilen rein aus akkorden generiert
        Damit das funktioniert, muss der richtige typ gewählt sein.
        Die Akkorde können neu formatiert werden:
        Im Moment werden nur Mollschreibweisen umgewandelt
            stil: 'l' oder 'm'
            'l': e -> Em
            'm': Em -> e'''

        def abstandKonvertieren(zeile: str) -> str:
            '''
            Wenn in der Zeile mehrere Leerzeichen hintereinander vorkommen, 
            bilde den leerraum mittels \hspace in Latex ab.

            Wir wollen die Abstände zwischen den Akkorden einigermaßen abbilden:
            ' ' -> leerzeichen
            sonst 1em entspricht ca. 3 Leerzeichen
            '''
            lastEnd = 0  # position des vorherigen endes
            erg = ''  # Ausgabe
            for match in re.finditer(r' {2,}', zeile, flags=re.IGNORECASE):
                beg, end = match.start(), match.end()
                erg += zeile[lastEnd: beg]
                # 4 Leerzeichen entsprechen ca. 1 em
                erg += r'\hspace{'+str('%1.2f' % ((end - beg)/3)) + 'em}'
                # Der ursprüngliche Text wird ab dem ende des Leerraumes weiter übernommen
                lastEnd = end  # Hier fängt das nächste Textstück an
            # Letztes Textstück nicht vergessen:
            erg += zeile[lastEnd:]
            return erg

        def ATzeile(akkzeile: str, textzeile: str, stil='') -> str:
            '''baut Akkord- und textzeile zu einer latex-
            kompatiblen Akkordtextzeile zusammen'''

            def ATakkord(akkord: str, stil='') -> str:
                '''gibt den latex befehl zurück, der den akkord an die passende stelle in den text setzt'''
                return r'\[' + SongLaTexttype.akkordstil(akkord, stil) + ']'

            # ersetzungen auflisten:
            akkErs = SongLaTexttype.ersetzungen(akkzeile, 'Akkordzeile')
            txtErs = SongLaTexttype.ersetzungen(textzeile, 'Textzeile')
            #ersetzungen nach anfangsposition [1] sortieren (nach beg, ende oder beginn ist egal, da sie sich nicht überlappen dürfen)
            akkErs = sorted(akkErs, key=lambda ers: ers[1])
            txtErs = sorted(txtErs, key=lambda ers: ers[1])

            # einfache ersetzungen in der Textzeile
            # liste der ersetzungen rückwärz durchlaufen. Dadurch können elemente einfach aus der list entfernt werden.
            for i in range(len(txtErs) -1, -1, -1):
                beg, end, ers = txtErs[i]
                # Fall 1: Über dem zu ersetzenden teil sind nur leerzeichen in der akkordzeile oder die Akkordzeile ist schon zu ende
                if akkzeile[beg:end].replace(' ', '') == '':
                    # einsetzen, akkordzeile entsprechend verlängern oder kürzen
                    textzeile = textzeile[:beg] + ers          + textzeile[end:]
                    akkzeile = akkzeile[:beg]   + ' '*len(ers) + akkzeile[end:]
                else: #Fall 2: über dem zu ersetzenden Teil befindet sich text(z.B. ein akkord)
                    # Falls der text kürzer wird: fehlende Zeichen durch ein seltenes Sonderzeichen ersetzen, das hinterher wieder löschen
                    if len(ers) < end-beg:
                        ers = ers.ljust(end-beg, '✪')
                        textzeile = textzeile[:beg] + ers + textzeile[end:]
                    else: #text wird länger: akkord über dem text durch einfügen eines sonderzeichens entsprechend verlängern
                        akk = akkzeile[beg:end].replace(' ', '') #ende des erseten akkordes finden
                        ertesZeichen = akkzeile.find(akk[0], beg) #erstes nicht-leerzechen finden
                        index = akkzeile.find(' ', ertesZeichen) #index des erseten leerzeichens nach dem akkord
                        if index != -1: #falls es ein leerzeichen (und potenziell weitere akorde gibt):
                            akkzeile = akkzeile[:index] + '✪'*(len(ers)-(end-beg)) + akkzeile[index:]
                        textzeile = textzeile[:beg] + ers + textzeile[end:]

            # Einfache Ersetzungen in der Akkordzeile:
            for i in range(len(akkErs)-1, -1, -1): #liste der ersetzungen rückwärz durchlaufen. Dadurch können Elemente einfach aus der Liste entfernt werden.
                beg, end, ers = akkErs[i]
                if len(ers) <= end-beg: #der Akkord wird kürzer: einfach am ende mit seltenem Sonderzeichen auffüllen
                    akkzeile = akkzeile[:beg] + ers + '✪' *(end-beg-len(ers)) + akkzeile[end:]
                else:
                    # Der akkord wird länger oder bleibt gleich: 
                    # Text durch Einsetzen eines seltenen Sonderzeichens verlängern
                    akkzeile = akkzeile[:beg] + ers + akkzeile[beg+len(ers):]
                    textzeile = textzeile[:end] + '✪' * (len(ers) - (end-beg)) + textzeile[end:]
            
            # Textzeile falls nötig verlängern, bis sie wenigstens so lang ist, wie die Akkordzeile
            textzeile = textzeile.ljust(len(akkzeile))

            atz = ''  # ergebnis: die akkordtextzeile
            textpos = 0
            # iteriere über alle Akkorde der Zeile:
            for match in re.finditer(AKKORDREGEX, akkzeile, flags=re.IGNORECASE):
                beg, end = match.start(), match.end()
                atz += textzeile[textpos:beg]+ATakkord(akkzeile[beg:end], stil)
                textpos = beg

            # Den erst des textes nachd em letzten Akkord übernehmen
            atz += textzeile[textpos:]

            # Sonderzeichen wieder löschen
            atz = atz.replace('✪', '')
            # abstände für latex setzen
            atz = abstandKonvertieren(atz)
            return atz

        def Azeile(akkzeile: str, stil='') -> str:
            '''setzt die Akkordzeile so, dass Latex die Zeichen als Akkorde ohne Text setzt'''
            return r'\nolyrics{'+ATzeile(akkzeile, '', stil)+'}'

        newtext = []
        newtyp = []
        prevline = None  # text der vorherigen zeile
        prevtyp = None  # typ der vorherigen zeile
        # zu lesende Zeile (es wird jeweils die vorherige zeile verarbeitet)
        i = 0
        # füge data und gew_typ ein None-Element hinzu. Das wird hinterher nicht gelesen, das macht den Code einfacher
        text.append(None)
        gew_typ.append(None)
        while i < len(text):
            line = text[i]
            line_typ = gew_typ[i]
            # unterscheide 4 Fälle:
            # 1) Die vorherige zeile existiert nicht / wird nicht verwendet
            if prevline is None or prevtyp is None:
                # die zeile wird nicht verwendet.
                pass

            # 2) die vorherige zeile ist eine akkordzeile
            elif prevtyp == 'Akkordzeile':
                # ist die aktuelle zeile eine Textzeile?
                if line_typ == 'Textzeile':
                    # die beiden Zeilen werden zu einer Akkordtextzeile zusammengefügt.
                    newtext.append(ATzeile(prevline, line, stil))
                    # die neue zeile ist vom typ Akkordtextzeile
                    newtyp.append('AkkordTextZeile')
                    # jetzt sind beide zeilen bentzt worden.
                    # die aktuelle zeile wird im folgenden nicht mehr (als vorherige zeile) verwendet.
                    line = None
                    line_typ = None

                else:
                    # die vorherige Zeile wird als (einzelne) Akkordzeile formatiert
                    newtext.append(Azeile(prevline, stil))
                    newtyp.append(prevtyp)

            # 3) die letzte Zeile ist eine andere Zeile (infozeile, leerzeile, Überschrift) Das sollte nicht vorkommen
            else:
                # es wird nicht zusammengeführt. die vorherige zeile wird unverändert übernommen.
                # XXX Warnung ausgeben ??
                #TODO: ersetzungen
                newtext.append(prevline)
                newtyp.append(prevtyp)

            # gehe eine zeile weiter
            prevline = line
            prevtyp = line_typ
            i += 1

        return newtext, newtyp

    @staticmethod
    def preFormat(text: List[str])->List[str]:
        '''hier finden alle formatierungen statt, die vor dem setzen der akkorde nötig sind'''
        return text
    
    @staticmethod
    def postFormat(text: List[str])->List[str]:
        '''hier finden alle formatierungen statt, die nach dem setzen der akkorde nötig sind'''
        return text
    
    @staticmethod
    def ersetzungen(zeile: str, typ: str) -> Collection[Tuple[int, int, str]]:
        '''gegeben sei die Zeile zeile vom typ typ.
        alle ersetzungen, die an dieser Zeile vorgenommen werden sollen, 
        bevor ggf. Akkorde und Text zudammengesetzt werden, gibt diese 
        funktion an.
        Die ausgabe ist die liste aller ersetzungen. 
        Es wird jeweils der bereich und die ersetung angegeben.
        wird während dem zusammensetzen von akkorden und text aufgerufen.
        Die ersetzungen dürfen sich nicht überlappen'''
        erg = [] #liste aller Änderungen
        for regex, ersetzung in Ersetzungen:
            for fund in re.finditer(regex, zeile, re.IGNORECASE):
                erg.append((fund.start(), fund.end(), ersetzung))
        return erg
    
    def erstelleLatexDaten(self):
        '''erstellt den Text, der in das Latex-dokument eingefügt wird.
        es wird angenommen, dass das ganze objekt nur einen einzelenn block enthält'''
        # Zeilen automatich einrücken: regex vom anfang der zeile mit nummer linenr entfernen,
        # ohne die realive position der zeichen zur zeile darüber zu ändern.

        def labelEntfernen(self, zeilenNr, regex):
            if zeilenNr > 0:
                # vorherige Zeile muss ebenfalls gekürz werden, sonst passen die beiden nicht mehr aufeiander
                # aktuelle zeile
                akt = re.sub(
                    regex, '', self.text[zeilenNr], flags=re.IGNORECASE)
                # Anzahl der leerzeichen, die in der darüberliegenden Zeile zu viel sind.
                l = len(self.text[zeilenNr])-len(akt)
                # vorherige Zeile
                vorg = self.text[zeilenNr - 1]
                while l > 0:
                    l -= 1
                    if vorg.startswith(' '):
                        # falls möglich, die zeile vorher kürzen
                        vorg = vorg[1:]
                    else:
                        # sonst die aktuelle zeile einrücken
                        akt = ' ' + akt
                self.text[zeilenNr - 1] = vorg
                self.text[zeilenNr] = akt
            else:
                # Wenn es die erste zeile ist, muss nur das Label abgeschnitten werden, da es keine vorherige zeile gibt.
                self.text[zeilenNr] = re.sub(
                    regex, '', self.text[zeilenNr], flags=re.IGNORECASE)

        self._updateWD()
        self.text = self.str + []  # echte kopie, statt referenz
        if self.use_autotyp:
            lineNr = self.autoTyp()  # XXX: rückgabewert sollte 0, 1 oder -1 sein, sonst Warnung,
            # da das Label nicht an der richtigen stelle steht
        else:
            # Im Moment wird die Zeilennummer benötigt. Daher funktioniert das ganze nicht ohne autotyp.
            raise NotImplementedError(
                'erstelleLatexDaten ohne autotyp ist nicht implementiert.')

        # Labels aus dem text entfernen, falls vorhanden.
        if self.blocktyp == 'strophe*' or lineNr == -1:  # Kein Label gefunden -> nichts zu tun
            pass
        elif self.blocktyp == 'strophe':
            labelEntfernen(self, lineNr, STROPHENREGEX)
        elif self.blocktyp in {'refrain', 'refrainWdh'}:
            labelEntfernen(self, lineNr, REFRAINREGEX)
        elif self.blocktyp == 'info':
            labelEntfernen(self, lineNr, INFOREGEX)

        # Latex Befehle für den Anfang und das Ende der Umgebung, in die der Block geschrieben wird, setzen.
        self.umgBeg, self.umgEnd = Umgebungen.get(
            self.blocktyp, Umgebungen['standart'])

        # Akkorde und text in eine Zeile zusammensetzen, wenn möglich und Akkorde zu erwarten sind.
        if self.blocktyp in {'strophe*', 'strophe', 'refrain'}:
            # zusätzloiche Formatierungen vor dem setzen der Akkorde
            self.text = self.preFormat(self.text)
            # Akkorde passend shreiben. das ändert normalerweise einige Zeilen.
            self.text, neu_gew_typ = SongLaTexttype.akkordeInZeile(self.text, self.gew_typ, stil=Akkordstil)
            # zusätzliche Formatierungen nach dem setzen der Akkorde
            self.text = self.postFormat(self.text)

        # HACK: Der Inhalt für repchorus (der nicht existiert) soll keine zusätzliche Leerzeile verursachen
        elif self.blocktyp == "repchorus":
            self.text = []

        return


class SongKonverter():
    def __init__(self, templatePfad: pfad) -> None:
        self.template = self.templateLaden(templatePfad)

    def templateLaden(self, templatePfad: pfad) -> None:
        #  Jinja konfigurieren
        self.latex_jinja_env = j2.Environment(
            block_start_string=r'\BLOCK{',
            block_end_string=r'}',
            variable_start_string=r'\VAR{',
            variable_end_string=r'}',
            comment_start_string=r'\#{',
            comment_end_string=r'}',
            line_statement_prefix=r'%%',
            line_comment_prefix=r'%#',
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
            # Pfad des Ordners, in dem diese Datei (converter.py) liegt.
            loader=j2.FileSystemLoader(
                os.path.dirname(os.path.abspath(__file__)))
        )
        #  Template laden
        return self.latex_jinja_env.get_template(templatePfad)

    def konvertiere(self, lied: str) -> str:
        ''' Diese funktion erledigt die Konvertierungsarbeit für eine einzelne datei. 
            lied: [str] Inhalt der Datei '''
        lied = lied.split('\n')  # in zeilen zerlegen
        # Jeder zeile die beiden wahrscheinlichsten typen zuordnen
        typen = Heuristik(lied)
        # Klasse zum einfahcen zeilenweisen verwalten der Daten
        zeilen = SongKonverter.finde_zeilentypen(SongLaTexttype(typen))
        # In Blöcke (Überschrift, Strophen, etc.) teilen.
        bloecke = zeilen.split('Leer')
        # Jeder Block entspricht einem Liedblock, also Liedtext/Akkorde, Überschrift oder Info
        # alle Blöcke, die in den latex Code übertragen werden.
        inhalt = list()

        # Speziell für den Titelblock
        titel = ''  # wenn dieser titel nicht ersetzt wird, ist etwas falsch...
        # titel, Worte, Weise, alternativtitel, genre, tags, etc.
        metadaten = dict()

        # Jeden Block für die Ausgabe durch jinja2 vorbereiten
        for i in range(len(bloecke)):
            block = bloecke[i]
            # Der erste block enthält die Überschrift und alle metadaten und wird deshalb gesondert behandelt.
            if i == 0:
                # Erster Block: Hier sollte die Überschrift und die metadaten stehen.
                # Wenn der erste block keine Überschrift ist,
                if ('Überschrift' not in block.types()):
                    # gibt das kein sinnvolles Ergebnis.
                    print('Keine Überschrift gefunden', block, file=sys.stderr)
                    raise Exception()
                metadaten = SongKonverter.meta_aus_titel(block)
                titel = metadaten.pop('title')
                continue

            # für latex konvertieren
            block.erstelleLatexDaten()
            inhalt.append(block)

        return self.templateFuellen(titel, metadaten, inhalt)

    @staticmethod
    def finde_zeilentypen(zeilen: texttype) -> texttype:
        # XXX: Hier kann man auch eine Simple Grammatik implementieren
        # Für jede Zeile den Wahrscheinlichsten typ wählen
        for zeilenNr in range(len(zeilen)):
            zeilentypen = zeilen.choices(zeilenNr)
            if zeilentypen[0] is None:
                if len(zeilentypen) > 1 and zeilentypen[1] is not None:
                    print('typ von zeile', zeilenNr,
                          'konnte nicht ermittelt werden. es wird \"'+zeilentypen[1]+'\" angenommen')
                    zeilen.choose(zeilenNr, zeilentypen[1])
                else:
                    print('typ von zeile', zeilenNr,
                          'konnte nicht ermittelt werden. es wird \"Leer\" angenommen')
                    zeilen.choose(zeilenNr, 'Leer')
                continue
            zeilen.choose(zeilenNr, zeilentypen[0])
        return zeilen

    @staticmethod
    def meta_aus_titel(block: texttype) -> dict:
        # Aufbau des Titelblockes: TITEL [Alternativtitel1]
        # key: value
        # …
        # Text, wie in der Eingabedatei, zeilenweise als liste, nur dieser Block
        text = str(block).split('\n')
        # Marker:
        titelz = text[0]
        metatext = text[1:]
        lk = titelz.find('[')
        rk = titelz.find(']', lk)
        # HACK: zeichen nicht gefunden:
        # Wenn das zeichen nicht gefunden wird, gibt find -1 zurück.
        # Das führt zu dem Problem, dass das Minimum (siehe unten)
        # den wert -1 hat (offset von 1 vom hinteren ende des Strings).
        # Dadurch fehlt das letzte zeichen des Titels, wenn nichts dahinter kommt.
        # Setze die Zeichenposition in diesem Fall auf das len(text)-te Zeichen
        # des Textes. Diese Position kann zwar nicht gelesen werden, das passiert
        # aber auch nicht. Es löst das Problem
        if lk <= 0:
            lk = len(titelz)

        # metadaten dictionary
        meta = dict()
        # Titel finden:
        meta['title'] = titelz[:min((lk, len(titelz)))].strip()
        # alternativtitel finden
        if rk > lk:
            meta['index'] = titelz[lk + 1:rk].strip()

        # restliche metadaten:
        # Hier weden alle metadaten gelistet, die in der überschrift enthalten sein können
        metakeys = dict(  # Siehe auch liste in Heuristik.py
            ww='wuw',  # Worte und weise
            wuw='wuw',
            jahr='jahr',  # jahr des Liedes
            j='jahr',
            mel='mel',  # Autor der Melodie
            melodie='mel',
            weise='mel',
            melj='meljahr',  # Jahr der Melodie
            meljahr='meljahr',
            weisej='meljahr',
            weisejahr='meljahr',
            txt='txt',  # Autor des Textes
            text='txt',
            worte='txt',
            txtj='txtjahr',  # Jahr des Textes
            textj='txtjahr',
            txtjahr='txtjahr',
            textjahr='txtjahr',
            wortejahr='txtjahr',
            wortej='txtjahr',
            alb='alb',  # Album, auf dem das Lied erschienen ist.
            album='alb',
            lager='lager',  # Lager, auf dem / für das das Lied geschrieben
            tonart='tonart',  # originaltonart
            key='tonart',
            bo='bo',  # Seite im Bock
            bock='bo',
            pf1='pfi',  # Seite im Pfadiralala1
            pfi='pfi',
            pf='pfi',
            pf2='pfii',  # Seite im Pfadiralala2
            pfii='pfii',
            pf3='pfiii',  # Seite im Pfadiralala3
            pfiii='pfiii',
            ju='ju',  # Seite in der Jurtenburg
            jurten='ju',
            jurtenburg='ju',
            gruen='gruen',  # Seite Im Grünen (Liederbuch)
            grün='gruen',
            gruenes='gruen',
            grünes='gruen',
            kss4='kssiv',  # Seite in Kinder-Schoko-Songs 4
            kssiv='kssiv',
            kssiiii='kssiv',
            siru='siru',  # Seite in Die singende Runde
            biest='biest',  # Seite im Biest
            eg='eg',  # Seite im evangelischen Gesangbuch
            evg='eg',
            egplus='egplus',  # Seite Im evangelischen Gesangbuch +
            evgplus='egplus')
        # Weiter Seite im evangelischen Gesangbuch plus, umständliche codeschreibseise. um das Pluszeichen zu unterstützen
        metakeys['eg+'] = 'egplus'
        metakeys['evg+'] = 'egplus'

        for line in metatext:
            if ':' in line:
                # davor ist der schlüssel, danach der wert
                i = line.index(':')  # in [0, len(ll)-1]
                keystr = line[:i].lower().replace(' ', '')
                # schlägt fehl wernn der wert nicht angegeben wird.
                valstr = line[i+1:].strip()
                if keystr in metakeys.keys():
                    key = metakeys[keystr]
                    meta[key] = valstr
                else:
                    # das sollte nicht passieren
                    print('ungültiger schlüssel', keystr)
            else:
                if line == '':
                    # die Zeile ist leer. Kein Problem, wird nicht verarbeitet
                    pass
                else:
                    print('Falsch Formatierte metazeile:', line)
        return meta

    konvertiere.__doc__ = '''lied: Ein string, der ein ganzes lied enthält. 
        Siehe hierzu die Dokumentation für Lieder im Eingabeverzeichnis. 
        Die funktion konvertiert das lied in latex. die ausgabe ist ein latex-dokument 
        das das lied darstellt.'''

    def templateFuellen(self, title: str, metadaten: Dict[str, str], inhalt: List[SongLaTexttype]) -> str:
        '''füllt das jinja2-template mit den metadaten uund dem Inhalt
        erlaubte Schlüssel für metadaten: index, wuw, mel, txt, meljahr, txtjahr, alb, lager, ...'''
        return self.template.render(title=title, metadata=metadaten, inhalt=inhalt)

    __doc__ = 'Erlaubt das konvertieren von Liedern in textform in Latex_dokumente'
