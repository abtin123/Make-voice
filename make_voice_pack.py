#!/usr/bin/env python3
"""Build AbtinMaps .abv voice packs with Microsoft Edge neural TTS.

  pip install edge-tts num2words   (+ ffmpeg on PATH)
  python make_voice_pack.py --lang fa en tr --gender female male --out out
  python make_voice_pack.py --lang all --base-url https://github.com/abtin123/Make-voice/releases/download/voicepacks-latest/
  python make_voice_pack.py --list-voices tr
"""
import argparse, asyncio, gzip, hashlib, json, struct, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

from num2words import num2words

SR = 24000
PAD = 0.18  # seconds of silence after each cue

LANGS = {  # code: (locale, native name, female voice, male voice)
    "fa": ("fa-IR", "فارسی", "fa-IR-DilaraNeural", "fa-IR-FaridNeural"),
    "en": ("en-US", "English", "en-US-JennyNeural", "en-US-GuyNeural"),
    "ar": ("ar-SA", "العربية", "ar-SA-ZariyahNeural", "ar-SA-HamedNeural"),
    "tr": ("tr-TR", "Türkçe", "tr-TR-EmelNeural", "tr-TR-AhmetNeural"),
    "az": ("az-AZ", "Azərbaycanca", "az-AZ-BanuNeural", "az-AZ-BabekNeural"),
    "ru": ("ru-RU", "Русский", "ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"),
    "de": ("de-DE", "Deutsch", "de-DE-KatjaNeural", "de-DE-ConradNeural"),
    "fr": ("fr-FR", "Français", "fr-FR-DeniseNeural", "fr-FR-HenriNeural"),
    "es": ("es-ES", "Español", "es-ES-ElviraNeural", "es-ES-AlvaroNeural"),
}

KEYS = """turn_left turn_right turn_slight_left turn_slight_right turn_sharp_left turn_sharp_right
continue_straight u_turn u_turn_when_possible keep_left keep_right keep_straight_lane move_left_now
move_right_now prepare_lane_change_left prepare_lane_change_right roundabout_take_exit_next
roundabout_enter roundabout_continue merge_onto_highway exit_highway stay_on_highway
highway_splits_left highway_splits_right toll_booth_ahead approaching_destination arrived_destination
destination_on_left destination_on_right destination_ahead start_navigation end_navigation
recalculating_route route_found off_route back_on_route gps_signal_lost gps_signal_restored
route_search_failed battery_low voice_muted voice_unmuted traffic_ahead traffic_light_ahead
accident_ahead road_closed_ahead construction_ahead speed_camera_ahead speed_bump_ahead
red_light_camera_ahead toll_road_ahead school_zone_ahead sharp_curve_ahead steep_hill_ahead
narrow_road_ahead railway_crossing_ahead pedestrian_crossing_ahead animal_crossing_ahead fog_ahead
ice_road_warning flood_warning_ahead reduce_speed speeding_warning parking_available_nearby
stop_sign_ahead yield_sign_ahead traffic_light_ahead_stop waypoint_reached next_waypoint
final_destination_ahead police_checkpoint_ahead take_exit_next roundabout_u_turn""".split()

# NOTE: key `traffic_light_ahead` = light traffic (same as the existing fa pack);
# `traffic_light_ahead_stop` = traffic light.
T = {
"fa": ["به چپ بپیچید","به راست بپیچید","کمی به چپ بپیچید","کمی به راست بپیچید","کامل به چپ بپیچید","کامل به راست بپیچید","مستقیم ادامه دهید","دور بزنید","در اولین فرصت دور بزنید","در مسیر چپ بمانید","در مسیر راست بمانید","در لاین وسط بمانید","به لاین چپ بروید","به لاین راست بروید","برای تعویض لاین به چپ آماده شوید","برای تعویض لاین به راست آماده شوید","در میدان، از خروجی بعدی خارج شوید","وارد میدان شوید","در میدان مستقیم ادامه دهید","وارد بزرگراه شوید","از بزرگراه خارج شوید","در بزرگراه بمانید","بزرگراه دو شاخه می‌شود، در مسیر چپ بمانید","بزرگراه دو شاخه می‌شود، در مسیر راست بمانید","باجه عوارضی در مسیر پیش رو","به مقصد نزدیک شدید","به مقصد رسیدید","مقصد در سمت چپ است","مقصد در سمت راست است","مقصد در مسیر پیش رو است","مسیریابی آغاز شد","مسیریابی پایان یافت","مسیر در حال محاسبه مجدد است","مسیر جدید یافت شد","شما از مسیر خارج شدید","به مسیر بازگشتید","سیگنال جی پی اس قطع شد","سیگنال جی پی اس بازیابی شد","مسیری یافت نشد","باتری دستگاه کم است","صدای مسیریاب قطع شد","صدای مسیریاب فعال شد","ترافیک سنگین در مسیر پیش رو","ترافیک سبک در مسیر پیش رو","تصادف در مسیر پیش رو","جاده مسدود در مسیر پیش رو","محدودیت راه به دلیل ساخت‌وساز در مسیر پیش رو","دوربین کنترل سرعت در مسیر پیش رو","سرعت‌گیر در مسیر پیش رو","دوربین چراغ قرمز در مسیر پیش رو","جاده عوارضی در مسیر پیش رو","منطقه مدرسه در مسیر پیش رو، سرعت را کاهش دهید","پیچ تند در مسیر پیش رو","سربالایی تند در مسیر پیش رو","جاده باریک در مسیر پیش رو","گذرگاه راه‌آهن در مسیر پیش رو","گذرگاه عابر پیاده در مسیر پیش رو","عبور حیوانات در مسیر پیش رو","مه غلیظ در مسیر پیش رو","احتمال یخ‌زدگی جاده در مسیر پیش رو","احتمال آب‌گرفتگی جاده در مسیر پیش رو","سرعت خود را کاهش دهید","شما سریع‌تر از حد مجاز حرکت می‌کنید","پارکینگ در نزدیکی مقصد موجود است","تابلوی ایست در مسیر پیش رو","تابلوی حق تقدم عبور در مسیر پیش رو","چراغ راهنمایی در مسیر پیش رو","به نقطه توقف رسیدید","به سمت نقطه توقف بعدی حرکت کنید","مقصد نهایی در مسیر پیش رو است","ایست بازرسی در مسیر پیش رو","از خروجی بعدی خارج شوید","در میدان دور بزنید"],
"en": ["Turn left","Turn right","Turn slightly left","Turn slightly right","Turn sharply left","Turn sharply right","Continue straight","Make a U-turn","Make a U-turn when possible","Keep left","Keep right","Stay in the middle lane","Move to the left lane now","Move to the right lane now","Get ready to change lanes to the left","Get ready to change lanes to the right","At the roundabout, take the next exit","Enter the roundabout","Continue straight in the roundabout","Merge onto the highway","Take the highway exit","Stay on the highway","The highway splits, keep left","The highway splits, keep right","Toll booth ahead","You are approaching your destination","You have arrived at your destination","Your destination is on the left","Your destination is on the right","Your destination is straight ahead","Navigation started","Navigation ended","Recalculating route","New route found","You are off route","You are back on route","GPS signal lost","GPS signal restored","No route found","Device battery is low","Navigation voice muted","Navigation voice unmuted","Heavy traffic ahead","Light traffic ahead","Accident ahead","Road closed ahead","Road work ahead, expect restrictions","Speed camera ahead","Speed bump ahead","Red light camera ahead","Toll road ahead","School zone ahead, reduce speed","Sharp curve ahead","Steep hill ahead","Narrow road ahead","Railway crossing ahead","Pedestrian crossing ahead","Animal crossing ahead","Dense fog ahead","Possible ice on the road ahead","Possible flooding ahead","Reduce your speed","You are exceeding the speed limit","Parking is available near your destination","Stop sign ahead","Yield sign ahead","Traffic light ahead","You have reached the waypoint","Head to the next waypoint","Your final destination is ahead","Police checkpoint ahead","Take the next exit","Make a U-turn at the roundabout"],
"ar": ["انعطف يسارًا","انعطف يمينًا","انعطف قليلًا إلى اليسار","انعطف قليلًا إلى اليمين","انعطف بشدة إلى اليسار","انعطف بشدة إلى اليمين","تابع مباشرة","قم بالدوران للخلف","قم بالدوران للخلف عند أول فرصة","ابق في المسار الأيسر","ابق في المسار الأيمن","ابق في المسار الأوسط","انتقل إلى المسار الأيسر الآن","انتقل إلى المسار الأيمن الآن","استعد لتغيير المسار إلى اليسار","استعد لتغيير المسار إلى اليمين","عند الدوار، اتخذ المخرج التالي","ادخل الدوار","تابع مباشرة في الدوار","ادخل الطريق السريع","اخرج من الطريق السريع","ابق على الطريق السريع","ينقسم الطريق السريع، ابق في المسار الأيسر","ينقسم الطريق السريع، ابق في المسار الأيمن","نقطة رسوم أمامك","أنت تقترب من وجهتك","لقد وصلت إلى وجهتك","وجهتك على اليسار","وجهتك على اليمين","وجهتك أمامك مباشرة","بدأ التوجيه","انتهى التوجيه","جارٍ إعادة حساب المسار","تم العثور على مسار جديد","لقد خرجت عن المسار","لقد عدت إلى المسار","فُقدت إشارة جي بي إس","عادت إشارة جي بي إس","لم يتم العثور على مسار","بطارية الجهاز منخفضة","تم كتم صوت التوجيه","تم تفعيل صوت التوجيه","ازدحام شديد أمامك","ازدحام خفيف أمامك","حادث أمامك","الطريق مغلق أمامك","أعمال طرق أمامك، توقع قيودًا","كاميرا سرعة أمامك","مطب صناعي أمامك","كاميرا إشارة حمراء أمامك","طريق برسوم أمامك","منطقة مدرسة أمامك، خفف السرعة","منعطف حاد أمامك","طريق شديد الانحدار أمامك","طريق ضيق أمامك","تقاطع سكة حديد أمامك","معبر مشاة أمامك","عبور حيوانات أمامك","ضباب كثيف أمامك","احتمال وجود جليد على الطريق أمامك","احتمال حدوث فيضان أمامك","خفف سرعتك","أنت تتجاوز السرعة المحددة","مواقف السيارات متوفرة بالقرب من وجهتك","علامة قف أمامك","علامة أفسح الطريق أمامك","إشارة مرور أمامك","لقد وصلت إلى نقطة التوقف","توجه إلى نقطة التوقف التالية","وجهتك النهائية أمامك","نقطة تفتيش للشرطة أمامك","اتخذ المخرج التالي","قم بالدوران للخلف عند الدوار"],
"tr": ["Sola dönün","Sağa dönün","Hafifçe sola dönün","Hafifçe sağa dönün","Keskin sola dönün","Keskin sağa dönün","Düz devam edin","U dönüşü yapın","Mümkün olan ilk yerde U dönüşü yapın","Sol şeritte kalın","Sağ şeritte kalın","Orta şeritte kalın","Şimdi sol şeride geçin","Şimdi sağ şeride geçin","Sola şerit değiştirmeye hazırlanın","Sağa şerit değiştirmeye hazırlanın","Kavşakta bir sonraki çıkıştan çıkın","Kavşağa girin","Kavşakta düz devam edin","Otoyola girin","Otoyoldan çıkın","Otoyolda kalın","Otoyol ikiye ayrılıyor, solda kalın","Otoyol ikiye ayrılıyor, sağda kalın","İleride gişe var","Hedefinize yaklaşıyorsunuz","Hedefinize ulaştınız","Hedef solunuzda","Hedef sağınızda","Hedef hemen ileride","Navigasyon başladı","Navigasyon sona erdi","Rota yeniden hesaplanıyor","Yeni rota bulundu","Rotadan çıktınız","Rotaya geri döndünüz","GPS sinyali kayboldu","GPS sinyali geri geldi","Rota bulunamadı","Cihazın pili azalıyor","Navigasyon sesi kapatıldı","Navigasyon sesi açıldı","İleride yoğun trafik var","İleride hafif trafik var","İleride kaza var","İleride yol kapalı","İleride yol çalışması var, kısıtlamalar olabilir","İleride hız kamerası var","İleride hız kesici var","İleride kırmızı ışık kamerası var","İleride ücretli yol var","İleride okul bölgesi var, hızınızı azaltın","İleride keskin viraj var","İleride dik yokuş var","İleride dar yol var","İleride demiryolu geçidi var","İleride yaya geçidi var","İleride hayvan geçişi var","İleride yoğun sis var","İleride yolda buzlanma olabilir","İleride su baskını olabilir","Hızınızı azaltın","Hız sınırını aşıyorsunuz","Hedefinizin yakınında otopark var","İleride dur levhası var","İleride yol ver levhası var","İleride trafik ışığı var","Ara durağa ulaştınız","Bir sonraki ara durağa ilerleyin","Son hedefiniz ileride","İleride polis kontrol noktası var","Bir sonraki çıkıştan çıkın","Kavşakta U dönüşü yapın"],
"az": ["Sola dönün","Sağa dönün","Bir az sola dönün","Bir az sağa dönün","Kəskin sola dönün","Kəskin sağa dönün","Düz davam edin","U-dönüşü edin","İlk imkanda U-dönüşü edin","Sol zolaqda qalın","Sağ zolaqda qalın","Orta zolaqda qalın","İndi sol zolağa keçin","İndi sağ zolağa keçin","Sola zolaq dəyişməyə hazırlaşın","Sağa zolaq dəyişməyə hazırlaşın","Dairədə növbəti çıxışdan çıxın","Dairəyə daxil olun","Dairədə düz davam edin","Magistral yola daxil olun","Magistral yoldan çıxın","Magistral yolda qalın","Magistral yol ikiyə ayrılır, solda qalın","Magistral yol ikiyə ayrılır, sağda qalın","Qabaqda ödənişli məntəqə var","Təyinat məntəqənizə yaxınlaşırsınız","Təyinat məntəqənizə çatdınız","Təyinat məntəqəsi solunuzdadır","Təyinat məntəqəsi sağınızdadır","Təyinat məntəqəsi düz qabaqdadır","Naviqasiya başladı","Naviqasiya başa çatdı","Marşrut yenidən hesablanır","Yeni marşrut tapıldı","Marşrutdan çıxdınız","Marşruta qayıtdınız","GPS siqnalı itdi","GPS siqnalı bərpa olundu","Marşrut tapılmadı","Cihazın batareyası azdır","Naviqasiya səsi söndürüldü","Naviqasiya səsi işə salındı","Qabaqda sıx tıxac var","Qabaqda yüngül tıxac var","Qabaqda qəza var","Qabaqda yol bağlıdır","Qabaqda yol işləri var, məhdudiyyətlər ola bilər","Qabaqda sürət kamerası var","Qabaqda süni maneə var","Qabaqda qırmızı işıq kamerası var","Qabaqda ödənişli yol var","Qabaqda məktəb zonası var, sürəti azaldın","Qabaqda kəskin döngə var","Qabaqda sıldırım yoxuş var","Qabaqda dar yol var","Qabaqda dəmir yolu keçidi var","Qabaqda piyada keçidi var","Qabaqda heyvanların keçidi var","Qabaqda sıx duman var","Qabaqda yolda buzlanma ola bilər","Qabaqda su basması ola bilər","Sürətinizi azaldın","Sürət həddini aşırsınız","Təyinat məntəqəsinin yaxınlığında parkinq var","Qabaqda dayan işarəsi var","Qabaqda yol ver işarəsi var","Qabaqda svetofor var","Aralıq dayanacağa çatdınız","Növbəti aralıq dayanacağa doğru hərəkət edin","Yekun təyinat məntəqəniz qabaqdadır","Qabaqda polis yoxlama məntəqəsi var","Növbəti çıxışdan çıxın","Dairədə U-dönüşü edin"],
"ru": ["Поверните налево","Поверните направо","Плавно поверните налево","Плавно поверните направо","Резко поверните налево","Резко поверните направо","Продолжайте движение прямо","Развернитесь","Развернитесь при первой возможности","Держитесь левее","Держитесь правее","Держитесь средней полосы","Перестройтесь в левую полосу","Перестройтесь в правую полосу","Приготовьтесь перестроиться влево","Приготовьтесь перестроиться вправо","На кольце съезжайте на следующем съезде","Въезжайте на кольцо","Продолжайте движение прямо по кольцу","Въезжайте на шоссе","Съезжайте с шоссе","Оставайтесь на шоссе","Шоссе разделяется, держитесь левее","Шоссе разделяется, держитесь правее","Впереди пункт оплаты проезда","Вы приближаетесь к пункту назначения","Вы прибыли в пункт назначения","Пункт назначения слева","Пункт назначения справа","Пункт назначения прямо по ходу движения","Навигация начата","Навигация завершена","Маршрут пересчитывается","Найден новый маршрут","Вы сошли с маршрута","Вы вернулись на маршрут","Сигнал GPS потерян","Сигнал GPS восстановлен","Маршрут не найден","Низкий заряд батареи","Голос навигации отключён","Голос навигации включён","Впереди сильная пробка","Впереди небольшая пробка","Впереди авария","Впереди дорога закрыта","Впереди дорожные работы, возможны ограничения","Впереди камера контроля скорости","Впереди лежачий полицейский","Впереди камера на красный свет","Впереди платная дорога","Впереди школьная зона, снизьте скорость","Впереди крутой поворот","Впереди крутой подъём","Впереди узкая дорога","Впереди железнодорожный переезд","Впереди пешеходный переход","Впереди переход животных","Впереди густой туман","Впереди возможен гололёд","Впереди возможно затопление дороги","Снизьте скорость","Вы превышаете скорость","Рядом с пунктом назначения есть парковка","Впереди знак «Стоп»","Впереди знак «Уступите дорогу»","Впереди светофор","Вы достигли промежуточной точки","Следуйте к следующей промежуточной точке","Конечный пункт назначения впереди","Впереди пост полиции","Съезжайте на следующем съезде","Развернитесь на кольце"],
"de": ["Biegen Sie links ab","Biegen Sie rechts ab","Biegen Sie leicht links ab","Biegen Sie leicht rechts ab","Biegen Sie scharf links ab","Biegen Sie scharf rechts ab","Fahren Sie geradeaus weiter","Wenden Sie","Wenden Sie, sobald es möglich ist","Halten Sie sich links","Halten Sie sich rechts","Bleiben Sie auf der mittleren Spur","Wechseln Sie jetzt auf die linke Spur","Wechseln Sie jetzt auf die rechte Spur","Bereiten Sie sich auf einen Spurwechsel nach links vor","Bereiten Sie sich auf einen Spurwechsel nach rechts vor","Nehmen Sie im Kreisverkehr die nächste Ausfahrt","Fahren Sie in den Kreisverkehr","Fahren Sie im Kreisverkehr geradeaus","Fahren Sie auf die Autobahn auf","Verlassen Sie die Autobahn","Bleiben Sie auf der Autobahn","Die Autobahn teilt sich, halten Sie sich links","Die Autobahn teilt sich, halten Sie sich rechts","Mautstelle voraus","Sie nähern sich Ihrem Ziel","Sie haben Ihr Ziel erreicht","Ihr Ziel liegt links","Ihr Ziel liegt rechts","Ihr Ziel liegt geradeaus","Navigation gestartet","Navigation beendet","Route wird neu berechnet","Neue Route gefunden","Sie sind von der Route abgekommen","Sie sind wieder auf der Route","GPS-Signal verloren","GPS-Signal wiederhergestellt","Keine Route gefunden","Der Akku ist schwach","Navigationsstimme stummgeschaltet","Navigationsstimme aktiviert","Starker Verkehr voraus","Leichter Verkehr voraus","Unfall voraus","Straße voraus gesperrt","Baustelle voraus, mit Einschränkungen rechnen","Blitzer voraus","Bodenschwelle voraus","Rotlichtkamera voraus","Mautstraße voraus","Schulzone voraus, Geschwindigkeit reduzieren","Scharfe Kurve voraus","Steile Steigung voraus","Enge Straße voraus","Bahnübergang voraus","Fußgängerüberweg voraus","Wildwechsel voraus","Dichter Nebel voraus","Glättegefahr durch Eis voraus","Überflutungsgefahr voraus","Reduzieren Sie die Geschwindigkeit","Sie fahren zu schnell","In der Nähe des Ziels gibt es Parkplätze","Stoppschild voraus","Vorfahrt-gewähren-Schild voraus","Ampel voraus","Sie haben den Zwischenstopp erreicht","Fahren Sie zum nächsten Zwischenstopp","Ihr Endziel liegt voraus","Polizeikontrolle voraus","Nehmen Sie die nächste Ausfahrt","Wenden Sie im Kreisverkehr"],
"fr": ["Tournez à gauche","Tournez à droite","Tournez légèrement à gauche","Tournez légèrement à droite","Tournez fortement à gauche","Tournez fortement à droite","Continuez tout droit","Faites demi-tour","Faites demi-tour dès que possible","Restez sur la voie de gauche","Restez sur la voie de droite","Restez sur la voie du milieu","Passez sur la voie de gauche maintenant","Passez sur la voie de droite maintenant","Préparez-vous à changer de voie vers la gauche","Préparez-vous à changer de voie vers la droite","Au rond-point, prenez la prochaine sortie","Engagez-vous dans le rond-point","Continuez tout droit dans le rond-point","Engagez-vous sur l'autoroute","Quittez l'autoroute","Restez sur l'autoroute","L'autoroute se divise, restez à gauche","L'autoroute se divise, restez à droite","Péage devant vous","Vous approchez de votre destination","Vous êtes arrivé à destination","Votre destination est à gauche","Votre destination est à droite","Votre destination est tout droit","Navigation démarrée","Navigation terminée","Recalcul de l'itinéraire","Nouvel itinéraire trouvé","Vous avez quitté l'itinéraire","Vous êtes de retour sur l'itinéraire","Signal GPS perdu","Signal GPS rétabli","Aucun itinéraire trouvé","La batterie de l'appareil est faible","Guidage vocal désactivé","Guidage vocal activé","Fort trafic devant vous","Trafic léger devant vous","Accident devant vous","Route fermée devant vous","Travaux devant vous, restrictions possibles","Radar devant vous","Ralentisseur devant vous","Radar de feu rouge devant vous","Route à péage devant vous","Zone scolaire devant vous, ralentissez","Virage serré devant vous","Forte pente devant vous","Route étroite devant vous","Passage à niveau devant vous","Passage piéton devant vous","Passage d'animaux devant vous","Brouillard dense devant vous","Risque de verglas devant vous","Risque d'inondation devant vous","Ralentissez","Vous dépassez la limite de vitesse","Un parking est disponible près de votre destination","Stop devant vous","Cédez le passage devant vous","Feu tricolore devant vous","Vous avez atteint l'étape","Dirigez-vous vers l'étape suivante","Votre destination finale est devant vous","Contrôle de police devant vous","Prenez la prochaine sortie","Faites demi-tour au rond-point"],
"es": ["Gire a la izquierda","Gire a la derecha","Gire ligeramente a la izquierda","Gire ligeramente a la derecha","Gire bruscamente a la izquierda","Gire bruscamente a la derecha","Continúe recto","Haga un cambio de sentido","Haga un cambio de sentido en cuanto sea posible","Manténgase a la izquierda","Manténgase a la derecha","Manténgase en el carril central","Cámbiese al carril izquierdo ahora","Cámbiese al carril derecho ahora","Prepárese para cambiar al carril izquierdo","Prepárese para cambiar al carril derecho","En la rotonda, tome la siguiente salida","Entre en la rotonda","Continúe recto en la rotonda","Incorpórese a la autopista","Salga de la autopista","Permanezca en la autopista","La autopista se divide, manténgase a la izquierda","La autopista se divide, manténgase a la derecha","Peaje más adelante","Se está acercando a su destino","Ha llegado a su destino","Su destino está a la izquierda","Su destino está a la derecha","Su destino está justo delante","Navegación iniciada","Navegación finalizada","Recalculando la ruta","Nueva ruta encontrada","Se ha salido de la ruta","Ha vuelto a la ruta","Señal GPS perdida","Señal GPS restablecida","No se encontró ninguna ruta","La batería del dispositivo está baja","Voz de navegación silenciada","Voz de navegación activada","Tráfico denso más adelante","Tráfico ligero más adelante","Accidente más adelante","Carretera cortada más adelante","Obras más adelante, posibles restricciones","Radar de velocidad más adelante","Resalto más adelante","Cámara de semáforo en rojo más adelante","Carretera de peaje más adelante","Zona escolar más adelante, reduzca la velocidad","Curva cerrada más adelante","Cuesta empinada más adelante","Carretera estrecha más adelante","Paso a nivel más adelante","Paso de peatones más adelante","Paso de animales más adelante","Niebla densa más adelante","Posible hielo en la carretera más adelante","Posible inundación más adelante","Reduzca la velocidad","Está superando el límite de velocidad","Hay aparcamiento cerca de su destino","Señal de stop más adelante","Señal de ceda el paso más adelante","Semáforo más adelante","Ha llegado a la parada intermedia","Diríjase a la siguiente parada intermedia","Su destino final está más adelante","Control policial más adelante","Tome la siguiente salida","Haga un cambio de sentido en la rotonda"],
}

# rx: roundabout exit ({o}=ordinal,{n}=number) · tx: exit · inn: distance prefix ·
# arr: remaining distance · sl: speed limit.  U = unit forms (one, few, many).
N = {
"fa": dict(rx="در میدان، از خروجی {o} خارج شوید", tx="از خروجی {n} خارج شوید", inn="در {d} {u} دیگر،", arr="{d} {u} تا مقصد باقی مانده", sl="محدودیت سرعت {d} {u} است",
           U=dict(m="متر", km="کیلومتر", ft="فوت", mi="مایل", kmh="کیلومتر بر ساعت", mph="مایل بر ساعت")),
"en": dict(rx="At the roundabout, take the {o} exit", tx="Take exit {n}", inn="In {d} {u},", arr="{d} {u} to your destination", sl="The speed limit is {d} {u}",
           U=dict(m=("meter", "meters"), km=("kilometer", "kilometers"), ft=("foot", "feet"), mi=("mile", "miles"), kmh=("kilometer per hour", "kilometers per hour"), mph=("mile per hour", "miles per hour"))),
"ar": dict(rx="عند الدوار، اتخذ المخرج رقم {n}", tx="اتخذ المخرج رقم {n}", inn="بعد {d} {u}،", arr="تبقى {d} {u} للوصول إلى الوجهة", sl="السرعة القصوى {d} {u}",
           U=dict(m="متر", km="كيلومتر", ft="قدم", mi="ميل", kmh="كيلومتر في الساعة", mph="ميل في الساعة")),
"tr": dict(rx="Kavşakta {o} çıkıştan çıkın", tx="{n} numaralı çıkıştan çıkın", inn="{d} {u} sonra,", arr="Hedefe {d} {u} kaldı", sl="Hız sınırı saatte {d} {u}",
           U=dict(m="metre", km="kilometre", ft="fit", mi="mil", kmh="kilometre", mph="mil")),
"az": dict(rx="Dairədə {o} çıxışdan çıxın", tx="{n} nömrəli çıxışdan çıxın", inn="{d} {u} sonra,", arr="Təyinat məntəqəsinə {d} {u} qalıb", sl="Sürət həddi: saatda {d} {u}",
           U=dict(m="metr", km="kilometr", ft="fut", mi="mil", kmh="kilometr", mph="mil")),
"ru": dict(rx="На кольце съезжайте на {o} съезд", tx="Съезжайте на съезд номер {n}", inn="Через {d} {u},", arr="До пункта назначения {d} {u}", sl="Ограничение скорости {d} {u}",
           U=dict(m=("метр", "метра", "метров"), km=("километр", "километра", "километров"), ft=("фут", "фута", "футов"), mi=("миля", "мили", "миль"),
                  kmh=("километр в час", "километра в час", "километров в час"), mph=("миля в час", "мили в час", "миль в час"))),
"de": dict(rx="Nehmen Sie im Kreisverkehr die {o} Ausfahrt", tx="Nehmen Sie die Ausfahrt {n}", inn="In {d} {u},", arr="Noch {d} {u} bis zum Ziel", sl="Tempolimit: {d} {u}",
           U=dict(m="Meter", km="Kilometer", ft="Fuß", mi=("Meile", "Meilen"), kmh="Kilometer pro Stunde", mph=("Meile pro Stunde", "Meilen pro Stunde"))),
"fr": dict(rx="Au rond-point, prenez la {o} sortie", tx="Prenez la sortie {n}", inn="Dans {d} {u},", arr="Il reste {d} {u} jusqu'à destination", sl="Limitation de vitesse : {d} {u}",
           U=dict(m=("mètre", "mètres"), km=("kilomètre", "kilomètres"), ft=("pied", "pieds"), mi=("mile", "miles"), kmh=("kilomètre par heure", "kilomètres par heure"), mph=("mile par heure", "miles par heure"))),
"es": dict(rx="En la rotonda, tome la salida número {n}", tx="Tome la salida {n}", inn="En {d} {u},", arr="Distancia al destino: {d} {u}", sl="El límite de velocidad es de {d} {u}",
           U=dict(m=("metro", "metros"), km=("kilómetro", "kilómetros"), ft=("pie", "pies"), mi=("milla", "millas"), kmh=("kilómetro por hora", "kilómetros por hora"), mph=("milla por hora", "millas por hora"))),
}

for _l in LANGS:
    assert len(T[_l]) == len(KEYS), (_l, len(T[_l]), len(KEYS))


def unit(lang, u, n):
    f = N[lang]["U"][u]
    if isinstance(f, str):
        return f
    if lang == "ru":
        i = (0 if n % 10 == 1 and n % 100 != 11 else 1 if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else 2)
        return f[i]
    return f[0] if n == 1 else f[-1]


AR = {"m": ("متر", "مترين", "أمتار"), "km": ("كيلومتر", "كيلومترين", "كيلومترات"),
      "ft": ("قدم", "قدمين", "أقدام"), "mi": ("ميل", "ميلين", "أميال")}
DE_DAT = {"m": "Metern", "km": "Kilometern", "ft": "Fuß", "mi": "Meilen"}


def num_unit(lang, n, u, kind="arr"):
    """Number words + unit with per-language agreement. kind: inn | arr | sl."""
    w, un = num2words(n, lang=lang), unit(lang, u, n)
    if lang == "ru":
        if u == "mi" and n == 1:
            w, un = ("одну", "милю") if kind == "inn" else ("одна", "миля")
        elif u == "mi" and n == 2:
            w = "две"
        elif n == 1000 and kind == "inn":
            w = "одну тысячу"
    elif lang == "de":
        w = w.replace("einhundert", "hundert").replace("eintausend", "tausend")
        if kind == "inn" and u in DE_DAT:
            un = DE_DAT[u]
            if n == 1:
                w, un = ("einer", "Meile") if u == "mi" else ("einem", {"m": "Meter", "km": "Kilometer", "ft": "Fuß"}[u])
        elif w == "eins":
            w = "eine" if u == "mi" else "ein"
    elif lang == "es" and w == "uno":
        w = "una" if u == "mi" else "un"
    elif lang == "ar" and u in AR:
        one, dual, plural = AR[u]
        if n == 1:
            w, un = "", one + " واحد"
        elif n == 2:
            w, un = "", dual if kind == "inn" else dual.replace("ين", "ان")
        elif 3 <= n <= 10:
            un = plural
    return w, un


def ordinal(lang, n):
    if n == 1 and lang in ("fa", "fr"):
        return {"fa": "اول", "fr": "première"}[lang]
    try:
        return num2words(n, lang=lang, to="ordinal")
    except Exception:
        return num2words(n, lang=lang)


def build_texts(lang):
    t, d = dict(zip(KEYS, T[lang])), N[lang]
    for i in range(1, 21):
        t[f"roundabout_take_exit_{i}"] = d["rx"].format(o=ordinal(lang, i), n=num2words(i, lang=lang))
    for i in range(1, 16):
        t[f"take_exit_{i}"] = d["tx"].format(n=num2words(i, lang=lang))

    def fmt(tpl, n, u, kind):
        w, un = num_unit(lang, n, u, kind)
        return " ".join(tpl.format(d=w, u=un).split())

    for u, vals in dict(m=[20, 30, 50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900], km=[1, 2],
                        ft=[100, 200, 300, 500, 800, 1000, 1500], mi=[1, 2]).items():
        for n in vals:
            t[f"in_{n}{u}"] = fmt(d["inn"], n, u, "inn")
    for u in ("km", "mi"):
        for n in (1, 2, 3, 5, 10, 15, 20):
            t[f"arrive_in_{n}{u}"] = fmt(d["arr"], n, u, "arr")
    for n in range(30, 131, 10):
        t[f"speed_limit_{n}kmh"] = fmt(d["sl"], n, "kmh", "sl")
    for n in range(20, 71, 5):
        t[f"speed_limit_{n}mph"] = fmt(d["sl"], n, "mph", "sl")
    return t


def ff(args, data):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", *args], input=data, capture_output=True)
    if r.returncode:
        raise RuntimeError(r.stderr.decode(errors="replace"))
    return r.stdout


TRIM = ("silenceremove=start_periods=1:start_silence=0.03:start_threshold=-45dB,areverse,"
        "silenceremove=start_periods=1:start_silence=0.03:start_threshold=-45dB,areverse")


def to_pcm(mp3):
    args = lambda af: ["-i", "pipe:0", *(["-af", af] if af else []), "-f", "s16le", "-ar", str(SR), "-ac", "1", "pipe:1"]
    pcm = ff(args(TRIM), mp3)
    return pcm if len(pcm) > SR // 10 else ff(args(None), mp3)


async def synth(text, voice, rate, volume, pitch):
    import edge_tts
    last = None
    for attempt in range(5):
        try:
            buf = b""
            async for ch in edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch).stream():
                if ch["type"] == "audio":
                    buf += ch["data"]
            if buf:
                return buf
            last = RuntimeError("empty audio")
        except Exception as e:
            last = e
        await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"TTS failed for {text!r}: {last}")


async def build_pack(lang, gender, voice, out, cache, rate, volume, pitch, conc, synth_fn=synth):
    locale, native, *_ = LANGS[lang]
    texts = build_texts(lang)
    sem = asyncio.Semaphore(conc)
    key = hashlib.sha1(f"{voice}|{rate}|{volume}|{pitch}".encode()).hexdigest()[:8]

    async def one(name, text):
        f = cache / f"{lang}_{gender}_{key}_{hashlib.sha1(text.encode()).hexdigest()[:12]}.pcm"
        if f.exists():
            return name, f.read_bytes()
        async with sem:
            pcm = to_pcm(await synth_fn(text, voice, rate, volume, pitch))
        f.write_bytes(pcm)
        return name, pcm

    res = dict(await asyncio.gather(*(one(k, v) for k, v in texts.items())))
    pad = b"\0\0" * int(SR * PAD)
    pcm_all, cues, pos = [], {}, 0
    for k, text in texts.items():
        seg = res[k] + pad
        cues[k] = {"start": round(pos / 2 / SR, 3), "end": round((pos + len(seg)) / 2 / SR, 3), "text": text}
        pcm_all.append(seg)
        pos += len(seg)
    mp3 = ff(["-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0", "-c:a", "libmp3lame", "-b:a", "48k", "-f", "mp3", "pipe:1"], b"".join(pcm_all))
    speaker = voice.split("-")[-1].removesuffix("Neural")
    meta = {"version": 2, "engine": "edge-neural", "lang": lang, "locale": locale, "speaker": speaker, "gender": gender,
            "voice_name": voice, "duration": round(pos / 2 / SR, 3), "cue_format": "seconds", "distance_speech": True,
            "cue_count": len(cues), "generated_at": datetime.now(timezone.utc).isoformat(), "cues": cues}
    j = gzip.compress(json.dumps(meta, ensure_ascii=False).encode(), 9)
    a = gzip.compress(mp3, 9)
    path = out / f"{lang}_{gender}.abv"
    path.write_bytes(b"ABV1" + struct.pack("<II", len(j), len(a)) + j + a)
    return path, meta


async def list_voices(prefix):
    import edge_tts
    for v in await edge_tts.list_voices():
        if v["Locale"].lower().startswith(prefix.lower()):
            print(f'{v["ShortName"]:32} {v["Gender"]:7} {v["Locale"]}')


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="+", default=["fa"], help=f"codes ({', '.join(LANGS)}) or 'all'")
    ap.add_argument("--gender", nargs="+", default=["female", "male"], choices=["female", "male"])
    ap.add_argument("--out", default="voicepacks")
    ap.add_argument("--voice", action="append", default=[], metavar="LANG_GENDER=VoiceShortName", help="override, e.g. en_male=en-GB-RyanNeural")
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--volume", default="+0%")
    ap.add_argument("--pitch", default="+0Hz")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--base-url", default="", help="download URL prefix written into manifest.json")
    ap.add_argument("--list-voices", metavar="LOCALE_PREFIX")
    a = ap.parse_args()
    if a.list_voices:
        return await list_voices(a.list_voices)
    langs = list(LANGS) if "all" in a.lang else a.lang
    bad = [l for l in langs if l not in LANGS]
    if bad:
        sys.exit(f"unknown lang {bad}; supported: {list(LANGS)}")
    over = dict(v.split("=", 1) for v in a.voice)
    out = Path(a.out); cache = out / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    voices = []
    for l in langs:
        for g in a.gender:
            voice = over.get(f"{l}_{g}") or LANGS[l][2 if g == "female" else 3]
            print(f"[{l}/{g}] {voice} ...", flush=True)
            path, meta = await build_pack(l, g, voice, out, cache, a.rate, a.volume, a.pitch, a.concurrency)
            print(f"  -> {path} ({path.stat().st_size / 1e6:.2f} MB, {meta['duration']:.0f}s, {meta['cue_count']} cues)")
            voices.append({"name": path.name, "language": LANGS[l][1], "language_code": l, "gender_label": "زن" if g == "female" else "مرد",
                           "voice_name": voice, "display_name": f"{LANGS[l][1]} {meta['speaker']}", "size": path.stat().st_size,
                           "download_url": a.base_url + path.name})
    mf = out / "manifest.json"
    old = json.loads(mf.read_text("utf-8"))["voices"] if mf.exists() else []
    merged = {v["name"]: v for v in old}
    merged.update({v["name"]: v for v in voices})
    mf.write_text(json.dumps({"voices": list(merged.values())}, ensure_ascii=False, indent=2), "utf-8")


if __name__ == "__main__":
    asyncio.run(main())
