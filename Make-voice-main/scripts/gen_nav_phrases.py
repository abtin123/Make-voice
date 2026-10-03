#!/usr/bin/env python3
"""Generate examples/nav_phrases.json (8 languages, fully static, TTS-friendly).

Rules that make Edge Neural read the text correctly:
  * ordinals are written as words (never "1st", "1.", "1ère", "1ª", "1-м");
  * Persian numbers are written as words;
  * every cue is a complete static sentence. Distances are separate prefix cues
    (``in_200m`` ...) that the app plays right before the maneuver cue.
Optional per-cue key ``"tts": {"fa": "..."}`` overrides ONLY what is spoken;
the normal ``fa`` text stays the clean text shown in the app.
"""
from __future__ import annotations

import json
from pathlib import Path

LANGS = ("fa", "en", "ar", "tr", "de", "fr", "es", "ru")
ROOT = Path(__file__).resolve().parents[1]
OLD = json.loads((ROOT / "examples/nav_phrases.json").read_text(encoding="utf-8")) \
    if (ROOT / "examples/nav_phrases.json").exists() else {}

# ----------------------------------------------------------------- numbers (fa)
_ONES = "صفر یک دو سه چهار پنج شش هفت هشت نه ده یازده دوازده سیزده چهارده پانزده شانزده هفده هجده نوزده".split()
_TENS = {20: "بیست", 30: "سی", 40: "چهل", 50: "پنجاه", 60: "شصت", 70: "هفتاد", 80: "هشتاد", 90: "نود"}
_HUND = {1: "صد", 2: "دویست", 3: "سیصد", 4: "چهارصد", 5: "پانصد", 6: "ششصد", 7: "هفتصد", 8: "هشتصد", 9: "نهصد"}


def fa_num(n: int) -> str:
    parts: list[str] = []
    if n >= 1000:
        t, n = divmod(n, 1000)
        parts.append("هزار" if t == 1 else f"{fa_num(t)} هزار")
    if n >= 100:
        h, n = divmod(n, 100)
        parts.append(_HUND[h])
    if n >= 20:
        t, n = divmod(n, 10)
        parts.append(_TENS[t * 10])
    if n or not parts:
        parts.append(_ONES[n])
    return " و ".join(parts)


# -------------------------------------------------------------------- ordinals
ORD = {
    "fa": "اول دوم سوم چهارم پنجم ششم هفتم هشتم نهم دهم یازدهم دوازدهم سیزدهم چهاردهم پانزدهم شانزدهم هفدهم هجدهم نوزدهم بیستم".split(),
    "en": "first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth twentieth".split(),
    "ar": ["الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس", "السابع", "الثامن", "التاسع", "العاشر",
           "الحادي عشر", "الثاني عشر", "الثالث عشر", "الرابع عشر", "الخامس عشر", "السادس عشر",
           "السابع عشر", "الثامن عشر", "التاسع عشر", "العشرين"],
    "tr": ["birinci", "ikinci", "üçüncü", "dördüncü", "beşinci", "altıncı", "yedinci", "sekizinci", "dokuzuncu", "onuncu",
           "on birinci", "on ikinci", "on üçüncü", "on dördüncü", "on beşinci", "on altıncı", "on yedinci",
           "on sekizinci", "on dokuzuncu", "yirminci"],
    "de": "erste zweite dritte vierte fünfte sechste siebte achte neunte zehnte elfte zwölfte dreizehnte vierzehnte fünfzehnte sechzehnte siebzehnte achtzehnte neunzehnte zwanzigste".split(),
    "fr": ["première", "deuxième", "troisième", "quatrième", "cinquième", "sixième", "septième", "huitième", "neuvième",
           "dixième", "onzième", "douzième", "treizième", "quatorzième", "quinzième", "seizième", "dix-septième",
           "dix-huitième", "dix-neuvième", "vingtième"],
    "es": ["primera", "segunda", "tercera", "cuarta", "quinta", "sexta", "séptima", "octava", "novena", "décima",
           "undécima", "duodécima", "decimotercera", "decimocuarta", "decimoquinta", "decimosexta",
           "decimoséptima", "decimoctava", "decimonovena", "vigésima"],
    "ru": ["первый", "второй", "третий", "четвёртый", "пятый", "шестой", "седьмой", "восьмой", "девятый", "десятый",
           "одиннадцатый", "двенадцатый", "тринадцатый", "четырнадцатый", "пятнадцатый", "шестнадцатый",
           "семнадцатый", "восемнадцатый", "девятнадцатый", "двадцатый"],
}
ROUNDABOUT_EXIT = {
    "fa": "در میدان، از خروجی {o} خارج شوید",
    "en": "At the roundabout, take the {o} exit",
    "ar": "عند الدوار، اسلك المخرج {o}",
    "tr": "Kavşakta {o} çıkışı kullanın",
    "de": "Nehmen Sie am Kreisverkehr die {o} Ausfahrt",
    "fr": "Au rond-point, prenez la {o} sortie",
    "es": "En la rotonda, tome la {o} salida",
    "ru": "На круговом движении съезжайте на {o} съезд",
}
TAKE_EXIT = {  # highway exit *number* (digits are fine outside fa)
    "fa": "از خروجی {n} خارج شوید",
    "en": "Take exit {n}",
    "ar": "اسلك المخرج رقم {n}",
    "tr": "{n} numaralı çıkışı kullanın",
    "de": "Nehmen Sie die Ausfahrt {n}",
    "fr": "Prenez la sortie {n}",
    "es": "Tome la salida {n}",
    "ru": "Съезжайте на съезд номер {n}",
}

# ----------------------------------------------------------- unit words / plural
def _ru_plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


UNIT = {  # (unit) -> lang -> function(n) -> unit word
    "m": {"fa": lambda n: "متر", "en": lambda n: "meters", "ar": lambda n: "متر", "tr": lambda n: "metre",
          "de": lambda n: "Metern", "fr": lambda n: "mètres", "es": lambda n: "metros", "ru": lambda n: "метров"},
    "km": {"fa": lambda n: "کیلومتر", "en": lambda n: "kilometer" if n == 1 else "kilometers",
           "ar": lambda n: "كيلومتر", "tr": lambda n: "kilometre",
           "de": lambda n: "Kilometer" if n == 1 else "Kilometern",
           "fr": lambda n: "kilomètre" if n == 1 else "kilomètres",
           "es": lambda n: "kilómetro" if n == 1 else "kilómetros",
           "ru": lambda n: _ru_plural(n, "километр", "километра", "километров")},
    "ft": {"fa": lambda n: "فوت", "en": lambda n: "feet", "ar": lambda n: "قدم", "tr": lambda n: "fit",
           "de": lambda n: "Fuß", "fr": lambda n: "pieds", "es": lambda n: "pies", "ru": lambda n: "футов"},
    "mi": {"fa": lambda n: "مایل", "en": lambda n: "mile" if n == 1 else "miles", "ar": lambda n: "ميل",
           "tr": lambda n: "mil", "de": lambda n: "Meile" if n == 1 else "Meilen",
           "fr": lambda n: "mile" if n == 1 else "milles", "es": lambda n: "milla" if n == 1 else "millas",
           "ru": lambda n: _ru_plural(n, "милю", "мили", "миль")},
}
# the prefix cue: "In 200 meters,"  (comma keeps the intonation open for the maneuver)
PREFIX = {
    "fa": "در {n} {u} دیگر،", "en": "In {n} {u},", "ar": "بعد {n} {u}،", "tr": "{n} {u} sonra,",
    "de": "In {n} {u},", "fr": "Dans {n} {u},", "es": "En {n} {u},", "ru": "Через {n} {u},",
}
ARRIVE = {
    "fa": "{n} {u} تا مقصد باقی مانده", "en": "{n} {u} to your destination",
    "ar": "تبقى {n} {u} للوصول إلى الوجهة", "tr": "Varış noktasına {n} {u} kaldı",
    "de": "Noch {n} {u} bis zum Ziel", "fr": "Il reste {n} {u} jusqu'à la destination",
    "es": "Faltan {n} {u} para llegar al destino", "ru": "До пункта назначения: {n} {u}",
}
SPEED = {
    "kmh": {"fa": "محدودیت سرعت {n} کیلومتر بر ساعت است", "en": "Speed limit is {n} kilometers per hour",
            "ar": "الحد الأقصى للسرعة {n} كيلومترًا في الساعة", "tr": "Hız sınırı saatte {n} kilometre",
            "de": "Tempolimit {n} Kilometer pro Stunde", "fr": "Limitation de vitesse à {n} kilomètres par heure",
            "es": "El límite de velocidad es de {n} kilómetros por hora",
            "ru": "Ограничение скорости {n} километров в час"},
    "mph": {"fa": "محدودیت سرعت {n} مایل بر ساعت است", "en": "Speed limit is {n} miles per hour",
            "ar": "الحد الأقصى للسرعة {n} ميلًا في الساعة", "tr": "Hız sınırı saatte {n} mil",
            "de": "Tempolimit {n} Meilen pro Stunde", "fr": "Limitation de vitesse à {n} milles à l'heure",
            "es": "El límite de velocidad es de {n} millas por hora",
            "ru": "Ограничение скорости {n} миль в час"},
}


def num(lang: str, n: int) -> str:
    return fa_num(n) if lang == "fa" else str(n)


def fam(template: dict, n: int, unit: str | None = None) -> dict:
    out = {}
    for lang in LANGS:
        out[lang] = template[lang].format(n=num(lang, n), u=UNIT[unit][lang](n) if unit else "")
    return out


# -------------------------------------------------------- static sentences kept
KEEP_FROM_OLD = """
turn_left turn_right turn_slight_left turn_slight_right turn_sharp_left turn_sharp_right
continue_straight u_turn u_turn_when_possible
keep_left keep_right keep_straight_lane move_left_now move_right_now
prepare_lane_change_left prepare_lane_change_right
roundabout_take_exit_next roundabout_enter roundabout_continue
merge_onto_highway exit_highway stay_on_highway highway_splits_left highway_splits_right toll_booth_ahead
approaching_destination arrived_destination destination_on_left destination_on_right destination_ahead
start_navigation end_navigation recalculating_route route_found off_route back_on_route
gps_signal_lost gps_signal_restored route_search_failed battery_low voice_muted voice_unmuted
traffic_ahead traffic_light_ahead accident_ahead road_closed_ahead construction_ahead
speed_camera_ahead speed_bump_ahead red_light_camera_ahead toll_road_ahead school_zone_ahead
sharp_curve_ahead steep_hill_ahead narrow_road_ahead railway_crossing_ahead pedestrian_crossing_ahead
animal_crossing_ahead fog_ahead ice_road_warning flood_warning_ahead
reduce_speed speeding_warning parking_available_nearby stop_sign_ahead yield_sign_ahead
traffic_light_ahead_stop waypoint_reached next_waypoint final_destination_ahead
""".split()

NEW_STATIC = {
    "police_checkpoint_ahead": {
        "fa": "ایست بازرسی در مسیر پیش رو", "en": "Police checkpoint ahead",
        "ar": "نقطة تفتيش للشرطة في الطريق أمامك", "tr": "İleride polis kontrol noktası var",
        "de": "Polizeikontrolle voraus", "fr": "Contrôle de police en avant",
        "es": "Control policial más adelante", "ru": "Впереди пост полиции"},
    "take_exit_next": {
        "fa": "از خروجی بعدی خارج شوید", "en": "Take the next exit", "ar": "اسلك المخرج التالي",
        "tr": "Bir sonraki çıkışı kullanın", "de": "Nehmen Sie die nächste Ausfahrt",
        "fr": "Prenez la prochaine sortie", "es": "Tome la siguiente salida",
        "ru": "Съезжайте на следующем съезде"},
    "roundabout_u_turn": {
        "fa": "در میدان دور بزنید", "en": "At the roundabout, make a U-turn",
        "ar": "عند الدوار، قم بالدوران للخلف", "tr": "Kavşakta U dönüşü yapın",
        "de": "Wenden Sie am Kreisverkehr", "fr": "Au rond-point, faites demi-tour",
        "es": "En la rotonda, haga un cambio de sentido", "ru": "На круговом движении развернитесь"},
}
# small wording fixes that matter to TTS
OVERRIDE = {
    "gps_signal_lost": {"fa": "سیگنال جی پی اس قطع شد"},
    "gps_signal_restored": {"fa": "سیگنال جی پی اس بازیابی شد"},
}


def build() -> dict:
    out: dict[str, dict] = {}

    def add(cue: str, texts: dict) -> None:
        assert set(texts) >= set(LANGS), cue
        out[cue] = {lang: texts[lang] for lang in LANGS}

    # 1) core maneuvers / states / alerts
    for cue in KEEP_FROM_OLD:
        old = OLD.get(cue)
        assert old and all(old.get(l) for l in LANGS), f"missing in old json: {cue}"
        texts = {l: old[l] for l in LANGS}
        texts.update(OVERRIDE.get(cue, {}))
        add(cue, texts)
    for cue, texts in NEW_STATIC.items():
        add(cue, texts)
    # 2) roundabout exits 1..20 (ordinals as WORDS)
    for i in range(1, 21):
        add(f"roundabout_take_exit_{i}", {l: ROUNDABOUT_EXIT[l].format(o=ORD[l][i - 1]) for l in LANGS})
    # 3) highway exit numbers 1..15
    for i in range(1, 16):
        add(f"take_exit_{i}", fam(TAKE_EXIT, i))
    # 4) distance prefixes (played before a maneuver cue)
    for n in (20, 30, 50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900):
        add(f"in_{n}m", fam(PREFIX, n, "m"))
    for n in (1, 2):
        add(f"in_{n}km", fam(PREFIX, n, "km"))
    for n in (100, 200, 300, 500, 800, 1000, 1500):
        add(f"in_{n}ft", fam(PREFIX, n, "ft"))
    for n in (1, 2):
        add(f"in_{n}mi", fam(PREFIX, n, "mi"))
    # 5) distance to destination
    for n in (1, 2, 3, 5, 10, 15, 20):
        add(f"arrive_in_{n}km", fam(ARRIVE, n, "km"))
    for n in (1, 2, 3, 5, 10, 15, 20):
        add(f"arrive_in_{n}mi", fam(ARRIVE, n, "mi"))
    # 6) speed limits
    for n in range(30, 140, 10):
        add(f"speed_limit_{n}kmh", fam(SPEED["kmh"], n))
    for n in range(20, 75, 5):
        add(f"speed_limit_{n}mph", fam(SPEED["mph"], n))
    return out


if __name__ == "__main__":
    data = build()
    target = ROOT / "examples/nav_phrases.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(data)} cues x {len(LANGS)} languages -> {target}")
