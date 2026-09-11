# -*- coding: utf-8 -*-
"""Hierarchiczny katalog BDOT10k: poziom 1 -> poziom 2 -> poziom 3.

Kody poziomu 2 wskazują klasę źródłową w paczce BDOT10k (np. OT_SKJZ_*).
Kody poziomu 3 odpowiadają wartościom pola x_kod w danych BDOT10k.
"""

BDOT_TREE = {
    "SW": {
        "name": "Sieć wodna",
        "classes": {
            "SWRS": {"name": "Rzeka i strumień", "source": "OT_SWRS", "objects": [
                ("SWRS01", "rzeka"),
                ("SWRS02", "strumień, potok lub struga"),
            ]},
            "SWKN": {"name": "Kanał", "source": "OT_SWKN", "objects": [
                ("SWKN01", "kanał"),
            ]},
            "SWRM": {"name": "Rów melioracyjny", "source": "OT_SWRM", "objects": [
                ("SWRM01", "rów melioracyjny zbiorczy"),
                ("SWRM02", "rów melioracyjny zwykły"),
            ]},
        },
    },

    "SK": {
        "name": "Sieć komunikacyjna",
        "classes": {
            "SKJZ": {"name": "Jezdnia", "source": "OT_SKJZ", "objects": [
                ("SKJZ01", "jezdnia autostrady"),
                ("SKJZ02", "jezdnia drogi ekspresowej"),
                ("SKJZ03", "jezdnia drogi głównej ruchu przyśpieszonego"),
                ("SKJZ04", "jezdnia drogi głównej"),
                ("SKJZ05", "jezdnia drogi zbiorczej"),
                ("SKJZ06", "jezdnia drogi lokalnej"),
                ("SKJZ07", "jezdnia drogi dojazdowej"),
                ("SKJZ08", "jezdnia drogi innej"),
            ]},
            "SKDR": {"name": "Droga", "source": "OT_SKDR", "objects": [
                ("SKDR01", "autostrada"),
                ("SKDR02", "droga ekspresowa"),
                ("SKDR03", "droga główna ruchu przyśpieszonego"),
                ("SKDR04", "droga główna"),
                ("SKDR05", "droga zbiorcza"),
                ("SKDR06", "droga lokalna"),
                ("SKDR07", "droga dojazdowa"),
                ("SKDR08", "droga inna"),
            ]},
            "SKRW": {"name": "Rondo i węzeł drogowy", "source": "OT_SKRW", "objects": [
                ("SKRW01", "rondo"),
                ("SKRW02", "węzeł drogowy"),
            ]},
            "SKRP": {"name": "Ciąg ruchu pieszego i rowerowego", "source": "OT_SKRP", "objects": [
                ("SKRP01", "alejka"),
                ("SKRP02", "pasaż"),
                ("SKRP03", "ścieżka"),
            ]},
            "SKTR": {"name": "Tor lub zespół torów", "source": "OT_SKTR", "objects": [
                ("SKTR01", "tor kolejowy"),
                ("SKTR02", "tor metra"),
                ("SKTR03", "tor tramwajowy"),
            ]},
            "SKPP": {"name": "Przeprawa", "source": "OT_SKPP", "objects": [
                ("SKPP01", "bród"),
                ("SKPP02", "przeprawa łodziami"),
                ("SKPP03", "przeprawa promowa"),
            ]},
        },
    },

    "SU": {
        "name": "Sieć uzbrojenia terenu",
        "classes": {
            "SULN": {"name": "Linia napowietrzna", "source": "OT_SULN", "objects": [
                ("SULN01", "linia elektroenergetyczna najwyższego napięcia"),
                ("SULN02", "linia elektroenergetyczna wysokiego napięcia"),
                ("SULN03", "linia elektroenergetyczna średniego napięcia"),
                ("SULN04", "linia elektroenergetyczna niskiego napięcia"),
                ("SULN05", "linia telekomunikacyjna"),
            ]},
            "SUPR": {"name": "Przewód rurowy", "source": "OT_SUPR", "objects": [
                ("SUPR01", "benzynowy"),
                ("SUPR02", "ciepłowniczy"),
                ("SUPR03", "gazowy"),
                ("SUPR04", "kanalizacyjny"),
                ("SUPR05", "naftowy"),
                ("SUPR06", "wodociągowy"),
            ]},
        },
    },

    "PT": {
        "name": "Pokrycie terenu",
        "classes": {
            "PTWP": {"name": "Woda powierzchniowa", "source": "OT_PTWP", "objects": [
                ("PTWP01", "woda morska"),
                ("PTWP02", "woda płynąca"),
                ("PTWP03", "woda stojąca"),
            ]},
            "PTZB": {"name": "Zabudowa", "source": "OT_PTZB", "objects": [
                ("PTZB01", "zabudowa wielorodzinna"),
                ("PTZB02", "zabudowa jednorodzinna"),
                ("PTZB03", "zabudowa przemysłowo-składowa"),
                ("PTZB04", "zabudowa handlowo-usługowa"),
                ("PTZB05", "pozostała zabudowa"),
            ]},
            "PTLZ": {"name": "Teren leśny i zadrzewiony", "source": "OT_PTLZ", "objects": [
                ("PTLZ01", "las"),
                ("PTLZ02", "zagajnik"),
                ("PTLZ03", "zadrzewienie"),
            ]},
            "PTRK": {"name": "Roślinność krzewiasta", "source": "OT_PTRK", "objects": [
                ("PTRK01", "kosodrzewina"),
                ("PTRK02", "krzewy"),
            ]},
            "PTUT": {"name": "Uprawa trwała", "source": "OT_PTUT", "objects": [
                ("PTUT01", "ogród działkowy"),
                ("PTUT02", "plantacja"),
                ("PTUT03", "sad"),
                ("PTUT04", "szkółka leśna"),
                ("PTUT05", "szkółka roślin ozdobnych"),
            ]},
            "PTTR": {"name": "Roślinność trawiasta i uprawa rolna", "source": "OT_PTTR", "objects": [
                ("PTTR01", "roślinność trawiasta"),
                ("PTTR02", "uprawa na gruntach ornych"),
            ]},
            "PTKM": {"name": "Teren pod drogami kołowymi, szynowymi i lotniskowymi", "source": "OT_PTKM", "objects": [
                ("PTKM01", "teren pod drogą kołową"),
                ("PTKM02", "teren pod torowiskiem"),
                ("PTKM03", "teren pod drogą kołową i torowiskiem"),
                ("PTKM04", "teren pod drogą lotniskową"),
            ]},
            "PTGN": {"name": "Grunt nieużytkowany", "source": "OT_PTGN", "objects": [
                ("PTGN01", "piarg, usypisko lub rumowisko skalne"),
                ("PTGN02", "teren kamienisty"),
                ("PTGN03", "teren piaszczysty lub żwirowy"),
                ("PTGN04", "pozostały grunt nieużytkowany"),
            ]},
            "PTPL": {"name": "Plac", "source": "OT_PTPL", "objects": [
                ("PTPL01", "plac"),
            ]},
            "PTSO": {"name": "Składowisko odpadów", "source": "OT_PTSO", "objects": [
                ("PTSO01", "teren składowania odpadów komunalnych"),
                ("PTSO02", "teren składowania odpadów przemysłowych"),
            ]},
            "PTWZ": {"name": "Wyrobisko i zwałowisko", "source": "OT_PTWZ", "objects": [
                ("PTWZ01", "wyrobisko"),
                ("PTWZ02", "zwałowisko"),
            ]},
            "PTNZ": {"name": "Pozostały teren niezabudowany", "source": "OT_PTNZ", "objects": [
                ("PTNZ01", "teren pod urządzeniami technicznymi lub budowlami"),
                ("PTNZ02", "teren przemysłowo-składowy"),
            ]},
        },
    },

    "TC": {
        "name": "Tereny chronione",
        "classes": {
            "TCON": {"name": "Obszar Natura 2000", "source": "OT_TCON", "objects": [
                ("TCON01", "obszar Natura 2000"),
            ]},
            "TCPK": {"name": "Park krajobrazowy", "source": "OT_TCPK", "objects": [
                ("TCPK01", "park krajobrazowy"),
            ]},
            "TCPN": {"name": "Park narodowy", "source": "OT_TCPN", "objects": [
                ("TCPN01", "park narodowy"),
            ]},
            "TCRZ": {"name": "Rezerwat", "source": "OT_TCRZ", "objects": [
                ("TCRZ01", "rezerwat"),
            ]},
        },
    },

    "AD": {
        "name": "Jednostki podziału terytorialnego",
        "classes": {
            "ADJA": {"name": "Jednostka podziału administracyjnego", "source": "OT_ADJA", "objects": [
                ("ADJA01", "państwo"),
                ("ADJA02", "województwo"),
                ("ADJA03", "powiat"),
                ("ADJA04", "gmina miejska"),
                ("ADJA05", "gmina wiejska"),
                ("ADJA06", "gmina miejsko-wiejska"),
                ("ADJA07", "miasto w gminie miejsko-wiejskiej"),
                ("ADJA08", "obszar wiejski w gminie miejsko-wiejskiej"),
                ("ADJA09", "dzielnica"),
                ("ADJA10", "delegatura"),
            ]},
            "ADMS": {"name": "Miejscowość", "source": "OT_ADMS", "objects": [
                ("ADMS01", "miasto"),
                ("ADMS02", "część miasta"),
                ("ADMS03", "wieś"),
                ("ADMS04", "część wsi"),
                ("ADMS05", "kolonia"),
                ("ADMS06", "część kolonii"),
                ("ADMS07", "osada"),
                ("ADMS08", "część osady"),
                ("ADMS09", "osiedle"),
                ("ADMS10", "przysiółek"),
                ("ADMS11", "leśniczówka"),
                ("ADMS12", "gajówka"),
                ("ADMS13", "inny obiekt"),
            ]},
        },
    },

    "BU": {
        "name": "Budynki, budowle i urządzenia",
        "classes": {
            "BUBD": {"name": "Budynek", "source": "OT_BUBD", "objects": [
                ("BUBD01", "budynki mieszkalne jednorodzinne"),
                ("BUBD02", "budynki o dwóch mieszkaniach"),
                ("BUBD03", "budynki o trzech i więcej mieszkaniach"),
                ("BUBD04", "budynki zbiorowego zamieszkania"),
                ("BUBD05", "budynki hoteli"),
                ("BUBD06", "budynki zakwaterowania turystycznego, pozostałe"),
                ("BUBD07", "budynki biurowe"),
                ("BUBD08", "budynki handlowo-usługowe"),
                ("BUBD09", "budynki łączności, dworców i terminali"),
                ("BUBD10", "budynki garaży"),
                ("BUBD11", "budynki przemysłowe"),
                ("BUBD12", "zbiorniki, silosy i budynki magazynowe"),
                ("BUBD13", "ogólnodostępne obiekty kulturalne"),
                ("BUBD14", "budynki muzeów i bibliotek"),
                ("BUBD15", "budynki szkół i instytucji badawczych"),
                ("BUBD16", "budynki szpitali i zakładów opieki medycznej"),
                ("BUBD17", "budynki kultury fizycznej"),
                ("BUBD18", "budynki gospodarstw rolnych"),
                ("BUBD19", "budynki przeznaczone do sprawowania kultu religijnego i czynności religijnych"),
                ("BUBD20", "obiekty budowlane wpisane do rejestru zabytków i objęte indywidualną ochroną konserwatorską oraz nieruchome, archeologiczne dobra kultury"),
                ("BUBD21", "pozostałe budynki niemieszkalne, gdzie indziej nie wymienione"),
            ]},
            "BUIN": {"name": "Budowla inżynierska", "source": "OT_BUIN", "objects": [
                ("BUIN01", "estakada"),
                ("BUIN02", "kładka dla pieszych"),
                ("BUIN03", "most"),
                ("BUIN04", "przejście podziemne dla pieszych"),
                ("BUIN05", "przepust"),
                ("BUIN06", "tunel"),
                ("BUIN07", "wiadukt"),
            ]},
            "BUHD": {"name": "Budowla hydrotechniczna", "source": "OT_BUHD", "objects": [
                ("BUHD01", "jaz ruchomy lub zastawka piętrząca"),
                ("BUHD02", "jaz stały"),
                ("BUHD03", "śluza"),
                ("BUHD04", "zapora"),
            ]},
            "BUSP": {"name": "Budowla sportowa", "source": "OT_BUSP", "objects": [
                ("BUSP01", "basen odkryty"),
                ("BUSP02", "basen z czaszą foliową"),
                ("BUSP03", "bieżnia"),
                ("BUSP04", "kort tenisowy"),
                ("BUSP05", "kort tenisowy z czaszą foliową"),
                ("BUSP06", "plac gier i zabaw"),
                ("BUSP07", "plac sportowy"),
                ("BUSP08", "skocznia narciarska"),
                ("BUSP09", "stadion"),
                ("BUSP10", "sztuczny stok"),
                ("BUSP11", "tor samochodowy"),
                ("BUSP12", "tor saneczkowy"),
                ("BUSP13", "tor żużlowy"),
            ]},
            "BUWT": {"name": "Wysoka budowla techniczna", "source": "OT_BUWT", "objects": [
                ("BUWT01", "chłodnia kominowa"),
                ("BUWT02", "komin przemysłowy"),
                ("BUWT03", "maszt oświetleniowy"),
                ("BUWT04", "maszt telekomunikacyjny"),
                ("BUWT05", "turbina wiatrowa"),
                ("BUWT06", "słup energetyczny"),
                ("BUWT07", "podpora kolei linowej"),
                ("BUWT08", "wieża ciśnień"),
                ("BUWT09", "wieża przeciwpożarowa"),
                ("BUWT10", "wieża szybu kopalnianego"),
                ("BUWT11", "wieża telekomunikacyjna"),
                ("BUWT12", "wieża widokowa"),
            ]},
            "BUZT": {"name": "Zbiornik techniczny", "source": "OT_BUZT", "objects": [
                ("BUZT01", "osadnik"),
                ("BUZT02", "zbiornik na ciecz"),
                ("BUZT03", "zbiornik na materiały pędne lub gaz"),
                ("BUZT04", "zbiornik na materiały sypkie"),
            ]},
            "BUUO": {"name": "Umocnienie drogowe, kolejowe i wodne", "source": "OT_BUUO", "objects": [
                ("BUUO01", "falochron"),
                ("BUUO02", "ostroga"),
                ("BUUO03", "ściana oporowa"),
                ("BUUO04", "umocnienie brzegu"),
            ]},
            "BUZM": {"name": "Budowla ziemna", "source": "OT_BUZM", "objects": [
                ("BUZM01", "fosa sucha lub wykop"),
                ("BUZM02", "nasyp"),
                ("BUZM03", "wał przeciwpowodziowy lub grobla"),
            ]},
            "BUTR": {"name": "Urządzenie transportowe", "source": "OT_BUTR", "objects": [
                ("BUTR01", "kolej linowa"),
                ("BUTR02", "obrotnica kolejowa"),
                ("BUTR03", "suwnica"),
                ("BUTR04", "taśmociąg"),
                ("BUTR05", "wyciąg narciarski"),
            ]},
            "BUIT": {"name": "Inne urządzenie techniczne", "source": "OT_BUIT", "objects": [
                ("BUIT01", "szyb naftowy lub gazowy"),
                ("BUIT02", "ujęcie wody"),
                ("BUIT03", "transformator"),
                ("BUIT04", "zespół transformatorów"),
                ("BUIT05", "zespół dystrybutorów paliwa"),
                ("BUIT06", "zespół urządzeń stacji meteorologicznej"),
                ("BUIT07", "zespół urządzeń terminalu ropy naftowej lub materiałów ropopochodnych"),
            ]},
            "BUCM": {"name": "Budowla cmentarna", "source": "OT_BUCM", "objects": [
                ("BUCM01", "zespół nagrobków cmentarnych"),
            ]},
            "BUIB": {"name": "Inna budowla", "source": "OT_BUIB", "objects": [
                ("BUIB01", "estrada"),
                ("BUIB02", "ogrodzenie trwałe"),
                ("BUIB03", "peron kolejowy"),
                ("BUIB04", "platforma widokowa"),
                ("BUIB05", "rampa"),
                ("BUIB06", "trybuna"),
            ]},
        },
    },

    "KU": {
        "name": "Kompleksy użytkowania terenu",
        "classes": {
            "KUMN": {"name": "Kompleks mieszkaniowy", "source": "OT_KUMN", "objects": [
                ("KUMN01", "osiedle mieszkaniowe"),
                ("KUMN02", "posesja"),
            ]},
            "KUPG": {"name": "Kompleks przemysłowo-gospodarczy", "source": "OT_KUPG", "objects": [
                ("KUPG01", "elektrociepłownia"),
                ("KUPG02", "elektrownia"),
                ("KUPG03", "gazownia"),
                ("KUPG04", "gospodarstwo hodowlane"),
                ("KUPG05", "huta"),
                ("KUPG06", "kopalnia"),
                ("KUPG07", "oczyszczalnia ścieków"),
                ("KUPG08", "podstacja elektroenergetyczna"),
                ("KUPG09", "przepompownia"),
                ("KUPG10", "rafineria"),
                ("KUPG11", "składowisko odpadów"),
                ("KUPG12", "teren ujęcia wody"),
                ("KUPG13", "zakład metalurgiczny"),
                ("KUPG14", "zakład produkcyjny, usługowy lub remontowy"),
                ("KUPG15", "zakład utylizacji"),
                ("KUPG16", "zakład wodociągowy"),
            ]},
            "KUHU": {"name": "Kompleks handlowo-usługowy", "source": "OT_KUHU", "objects": [
                ("KUHU01", "centrum handlowo-usługowe"),
                ("KUHU02", "targowisko lub bazar"),
            ]},
            "KUKO": {"name": "Kompleks komunikacyjny", "source": "OT_KUKO", "objects": [
                ("KUKO01", "dworzec autobusowy"),
                ("KUKO02", "lotnisko lub lądowisko"),
                ("KUKO03", "miejsce obsługi podróżnych"),
                ("KUKO04", "parking"),
                ("KUKO05", "port wodny lub przystań"),
                ("KUKO06", "stacja kolejowa"),
                ("KUKO07", "stacja metra"),
                ("KUKO08", "stacja paliw"),
                ("KUKO09", "teren kolejowy"),
                ("KUKO10", "zajezdnia lub baza transportowa"),
            ]},
            "KUSK": {"name": "Kompleks sportowy i rekreacyjny", "source": "OT_KUSK", "objects": [
                ("KUSK01", "ogród botaniczny"),
                ("KUSK02", "ogród zoologiczny"),
                ("KUSK03", "ośrodek sportowo-rekreacyjny"),
                ("KUSK04", "park"),
                ("KUSK05", "zespół domów letniskowych"),
            ]},
            "KUHO": {"name": "Kompleks usług hotelarskich", "source": "OT_KUHO", "objects": [
                ("KUHO01", "hotel lub motel"),
                ("KUHO02", "kemping"),
                ("KUHO03", "ośrodek wypoczynkowy"),
                ("KUHO04", "schronisko turystyczne"),
            ]},
            "KUOS": {"name": "Kompleks oświatowy", "source": "OT_KUOS", "objects": [
                ("KUOS01", "ośrodek naukowo-badawczy"),
                ("KUOS02", "przedszkole lub żłobek"),
                ("KUOS03", "szkoła lub zespół szkół"),
                ("KUOS04", "szkoła wyższa"),
            ]},
            "KUOZ": {"name": "Kompleks ochrony zdrowia i opieki społecznej", "source": "OT_KUOZ", "objects": [
                ("KUOZ01", "zakład opieki socjalnej lub dom dziecka"),
                ("KUOZ02", "zespół szpitalny lub sanatoryjny"),
            ]},
            "KUZA": {"name": "Kompleks zabytkowo-historyczny", "source": "OT_KUZA", "objects": [
                ("KUZA01", "miejsce pamięci narodowej"),
                ("KUZA02", "skansen"),
                ("KUZA03", "twierdza lub forteca"),
                ("KUZA04", "zespół muzealny"),
                ("KUZA05", "zespół pałacowy"),
                ("KUZA06", "zespół zamkowy"),
            ]},
            "KUSC": {"name": "Kompleks sakralny i cmentarz", "source": "OT_KUSC", "objects": [
                ("KUSC01", "cmentarz"),
                ("KUSC02", "zespół sakralny lub klasztorny"),
            ]},
            "KUIK": {"name": "Inny kompleks użytkowania terenu", "source": "OT_KUIK", "objects": [
                ("KUIK01", "poligon wojskowy"),
                ("KUIK02", "zakład specjalny"),
            ]},
        },
    },

    "OI": {
        "name": "Obiekty inne",
        "classes": {
            "OIPR": {"name": "Obiekt przyrodniczy", "source": "OT_OIPR", "objects": [
                ("OIPR01", "drzewo lub grupa drzew"),
                ("OIPR02", "głaz narzutowy lub grupa głazów"),
                ("OIPR03", "kępa krzewów"),
                ("OIPR04", "kępa kosodrzewiny"),
                ("OIPR05", "linia oddziałowa"),
                ("OIPR06", "mały las"),
                ("OIPR07", "odosobniona skała"),
                ("OIPR08", "pas krzewów lub żywopłot"),
                ("OIPR09", "próg skalny"),
                ("OIPR10", "rząd drzew"),
                ("OIPR11", "wejście do jaskini"),
                ("OIPR12", "wodospad"),
                ("OIPR13", "źródło"),
            ]},
            "OIKM": {"name": "Obiekt związany z komunikacją", "source": "OT_OIKM", "objects": [
                ("OIKM01", "ekran akustyczny"),
                ("OIKM02", "pas startowy"),
                ("OIKM03", "przejście graniczne"),
                ("OIKM04", "przystanek autobusowy lub tramwajowy"),
                ("OIKM05", "przystanek kolejowy"),
                ("OIKM06", "schody"),
                ("OIKM07", "sygnalizator świetlny"),
                ("OIKM08", "wejście do stacji metra"),
                ("OIKM09", "miejsce poboru opłat"),
            ]},
            "OIOR": {"name": "Obiekty o znaczeniu orientacyjnym w terenie", "source": "OT_OIOR", "objects": [
                ("OIOR01", "bunkier lub schron"),
                ("OIOR02", "figura, kapliczka lub krzyż przydrożny"),
                ("OIOR03", "fontanna"),
                ("OIOR04", "mur historyczny"),
                ("OIOR05", "odosobniona mogiła"),
                ("OIOR06", "pomnik"),
                ("OIOR07", "pomost lub molo"),
                ("OIOR08", "ruina zabytkowa"),
                ("OIOR09", "studnia głębinowa"),
                ("OIOR10", "szklarnia (niebędąca budynkiem)"),
                ("OIOR11", "wiata lub altana"),
                ("OIOR12", "wiatrak (niebędący budynkiem)"),
                ("OIOR13", "wieża obserwacyjna"),
                ("OIOR14", "wodowskaz"),
            ]},
            "OIMK": {"name": "Mokradło", "source": "OT_OIMK", "objects": [
                ("OIMK01", "bagno"),
                ("OIMK02", "teren podmokły"),
            ]},
            "OISZ": {"name": "Szuwary", "source": "OT_OISZ", "objects": [
                ("OISZ01", "szuwary"),
            ]},
        },
    },
}

# Płaska mapa klas poziomu 2 zachowana pomocniczo dla starszego kodu.
BDOT_CLASSES = {
    f"{class_code} — {class_info['name']}": class_info["source"]
    for category in BDOT_TREE.values()
    for class_code, class_info in category["classes"].items()
}


def class_info_by_source(source_code):
    """Zwraca (kod_klasy, dane_klasy) dla kodu źródłowego OT_XXXX."""
    source_code = source_code.upper()
    for category in BDOT_TREE.values():
        for class_code, class_info in category["classes"].items():
            if class_info["source"].upper() == source_code:
                return class_code, class_info
    return None, None
