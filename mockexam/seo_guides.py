"""
The guide pages of mockexam/seo.py that state facts about the real exam: how computer-delivered IELTS works, what it
costs in Uzbekistan, the state refund for IELTS 7.0+, and what band 7 means.

Every fact here was checked on FACTS_CHECKED against official pages (ielts.org, britishcouncil.uz, ielts.idp.com,
takeielts.britishcouncil.org, my.gov.uz, gov.uz) and national news for events, and each page lists those sources and shows the
date. Where official pages disagree, the more authoritative or the newer one is used, and a claim that could not be
verified is left out (docs/SEO_FACTS.md lists them, and how often each fact must be checked again). Prices live in the
constants below: after a check, change them (and FACTS_CHECKED) here and nowhere else.
"""

FACTS_CHECKED = "2026-11-19"

# British Council Uzbekistan booking page and IDP / Edu Action centre pages (UZS).
BC_FEE = 2_798_000          # IELTS Academic and General Training on computer
BC_OLD_FEE = 2_664_000      # before the rise reported on 3 September 2026
BC_UKVI_FEE = 3_119_000
BC_LIFE_SKILLS_FEE = 2_759_000
BC_EXTRA_TRF_FEE = 64_000
IDP_FEE = 2_800_000


def money(amount, lang):
    """2,798,000 in English, 2 798 000 (no-break spaces) in Uzbek and Russian."""
    text = f"{amount:,}"
    return text if lang == "en" else text.replace(",", " ")


def _date(lang):
    year, month, day = FACTS_CHECKED.split("-")
    return f"{day}.{month}.{year}"


def _guide(slug, title, description, h1, intro, sections, faq, cta, sources, volatile=False):
    return {"slug": slug, "title": title, "description": description, "h1": h1, "intro": intro, "points": [],
            "sections": sections, "faq": faq, "cta": cta, "sources": sources, "checked": FACTS_CHECKED,
            "volatile": volatile}


def _table(caption, head, rows):
    return {"caption": caption, "head": head, "rows": rows}


# Links to the official pages, by language where the site has one.
IELTS_GUIDE = "https://ielts.org/cdn/ielts-downloadable-assets/ielts-guidance-and-support/ielts-guides/ielts-guide-for-test-takers.pdf"
IELTS_UPDATE = "https://ielts.org/news-and-insights/updates-to-ielts-test-delivery"
IELTS_OSR = "https://ielts.org/take-a-test/booking-your-test/one-skill-retake"
IELTS_SCORING = "https://ielts.org/take-a-test/your-results/ielts-scoring-in-detail"
IDP_COMPUTER = "https://ielts.idp.com/uzbekistan/about/ielts-on-computer"
IDP_FAQ = "https://ielts.idp.com/uzbekistan/faq/ielts-faq"
IDP_DATES = "https://ielts.idp.com/uzbekistan/test-dates/tashkent"
IDP_CENTRE = "https://ielts.idp.com/uzbekistan/test-centre/edu-action"
IDP_TRANSFER = "https://ielts.idp.com/uzbekistan/transfer"
TAKE_COMPUTER = "https://takeielts.britishcouncil.org/book-ielts-test/computer"
GAZETA_PAPER = "https://www.gazeta.uz/en/2025/07/08/ielts/"
ZAMIN_FEE = "https://zamin.uz/uz/jamiyat/220026-ielts-topshirish-narxi-oshdi-endi-qancha-tolanadi.html"
MY_GOV = "https://my.gov.uz/uz/service/413"
GOV_SECTION = "https://gov.uz/oz/yoshlar/sections/view/28105"
GOV_NEWS = "https://gov.uz/oz/yoshlar/news/view/120256"
GAZETA_COMP = "https://www.gazeta.uz/oz/2026/01/07/compensation/"
LEX_209 = "https://lex.uz/docs/-5370812"

GUIDES = {}

# ---------------------------------------------------------------------------------------------------------------
# How computer-delivered IELTS works (English, Uzbek, Russian)
# ---------------------------------------------------------------------------------------------------------------

GUIDES[("format", "en")] = _guide(
    "computer-delivered-ielts-what-to-expect",
    "Computer-Delivered IELTS: What to Expect | TestDay",
    "How computer-delivered IELTS works: timing, screens, typing, Listening and Reading on screen, Speaking with an "
    "examiner, and how to practise.",
    "Computer-delivered IELTS: what to expect",
    "Computer-delivered IELTS has the same tasks, question types and 9-band scoring as the paper test. Listening, "
    "Reading and Writing are taken on a computer; Speaking is a conversation with an examiner. In Uzbekistan it is "
    "the only format: paper-based IELTS has been suspended there since 11 July 2025.",
    [
        {"h": "The test at a glance",
         "table": _table("The four papers on computer", ["Paper", "Time", "What you do"], [
             ["Listening", "About 30 minutes (IDP Uzbekistan: 30–34 minutes with short pauses)",
              "40 questions in 4 parts. You type the answers straight into the computer and get 2 minutes at the end "
              "to check them."],
             ["Reading", "60 minutes", "40 questions on 3 sections of text."],
             ["Writing", "60 minutes", "Task 1: at least 150 words (about 20 minutes). Task 2: at least 250 words "
                                       "(about 40 minutes)."],
             ["Speaking", "11–14 minutes", "3 parts with a trained examiner."]]),
         "p_after": ["ielts.org gives the total time for the four sections as 2 hours 45 minutes. Listening, Reading "
                     "and Writing are taken on the same day with no breaks between them."]},
        {"h": "What is different from paper",
         "ul": ["There is no extra 10 minutes to copy Listening answers onto an answer sheet. Some pages on "
                "britishcouncil.uz still carry this paper-era wording, so rely on the format described here.",
                "You can highlight text and make notes on screen, copy and paste within your own text and notes, and "
                "see an automatic word count in Writing. The word counter helps with length, but you still have to "
                "check your own spelling.",
                "A timer shows the time left at all times, and Reading uses a split screen with the text on one side "
                "and the questions on the other.",
                "The centre provides pens and paper for notes. Personal stationery is not allowed (British Council "
                "Uzbekistan)."]},
        {"h": "Speaking",
         "p": ["Speaking is always a conversation with a trained human examiner, not with a computer. At some centres "
               "in Uzbekistan it is held by video call (the British Council uses Zoom). It is usually on the same day "
               "as the other papers, and the British Council lets you choose a slot up to 7 days before or after. "
               "Your booking confirmation shows the date."]},
        {"h": "Results",
         "p": ["ielts.org gives 1 to 5 days for IELTS on computer. The British Council in Uzbekistan says 1 to 2 days "
               "is typical, and IDP says 1 to 5 days. Both issue an electronic Test Report Form (eTRF)."]},
        {"h": "Paper-based IELTS in Uzbekistan",
         "p": ["Paper-based IELTS has been suspended in Uzbekistan since 11 July 2025. On 5 March 2026 the IELTS "
               "partners announced that from mid-2026 IELTS will no longer be offered on paper anywhere, and all "
               "tests will be delivered on computer.",
               "ielts.org also describes a Writing on Paper option (Listening and Reading on computer, Writing "
               "handwritten) for selected countries from mid-2026. We could not confirm that it is offered in "
               "Uzbekistan: the booking pages we checked list only Writing on computer."]},
        {"h": "One Skill Retake",
         "p": ["Both the British Council and IDP offer One Skill Retake in Uzbekistan for tests taken on computer. You "
               "retake one paper (Listening, Reading, Writing or Speaking), once for each original test and within "
               "60 days of it. The new Test Report Form shows the new score for that paper and your other three "
               "original scores, and results arrive within 3 to 5 days. The price is not published and appears in the "
               "booking portal. Organisations differ in whether they accept it, so ask the one you are applying to."]},
        {"h": "How to practise",
         "p": ["TestDay's screen follows these features: split-screen Reading, a countdown timer, highlighting and "
               "notes, a word counter in Writing, and Listening answers typed straight in. Take a timed test to feel "
               "the pace, and use Practice mode to study your mistakes without the clock."]},
    ],
    [("How long is computer-delivered IELTS?",
      "The four sections take 2 hours 45 minutes in total, according to ielts.org. Listening, Reading and Writing come "
      "one after another on the same day without breaks. Speaking lasts 11 to 14 minutes with an examiner."),
     ("Is there extra time to transfer answers in Listening?",
      "No. On computer you type your answers directly, so the 10 minutes for copying answers to a sheet does not "
      "exist. You get 2 minutes at the end of Listening to check what you typed."),
     ("Is the Speaking test done on a computer?",
      "No. It is a conversation with a trained human examiner, in person or by video call. Only Listening, Reading "
      "and Writing are on the computer."),
     ("Can I still take IELTS on paper in Uzbekistan?",
      "No. Paper-based IELTS has been suspended in Uzbekistan since 11 July 2025, and the IELTS partners are "
      "ending it worldwide from mid-2026.")],
    "Practise on a computer-style screen",
    [("ielts.org: IELTS guide for test takers", IELTS_GUIDE),
     ("IDP IELTS Uzbekistan: IELTS on computer", IDP_COMPUTER),
     ("IDP IELTS Uzbekistan: FAQ", IDP_FAQ),
     ("British Council: IELTS on computer", TAKE_COMPUTER),
     ("British Council Uzbekistan: results", "https://www.britishcouncil.uz/en/exam/ielts/results"),
     ("ielts.org: updates to IELTS test delivery", IELTS_UPDATE),
     ("Gazeta.uz: paper-based IELTS suspended in Uzbekistan", GAZETA_PAPER),
     ("ielts.org: One Skill Retake", IELTS_OSR)])

GUIDES[("format", "uz")] = _guide(
    "ielts-kompyuterda-topshirish",
    "IELTS kompyuterda: format va farqlar | TestDay",
    "IELTS on Computer qanday o'tadi: Listening, Reading, Writing kompyuterda, Speaking examiner bilan. Vaqt, "
    "interfeys va qog'ozdan farqlari.",
    "IELTS kompyuterda qanday topshiriladi",
    "Kompyuterda topshiriladigan IELTS qog'ozdagi test bilan bir xil topshiriqlar, savol turlari va 9 ballik baholash "
    "tizimiga ega. Listening, Reading va Writing kompyuterda topshiriladi, Speaking esa examiner bilan suhbat. "
    "O'zbekistonda bu yagona format: qog'ozdagi IELTS 2025-yil 11-iyuldan to'xtatilgan.",
    [
        {"h": "Test bir qarashda",
         "table": _table("Kompyuterdagi to'rt bo'lim", ["Bo'lim", "Vaqt", "Nima qilasiz"], [
             ["Listening", "Taxminan 30 daqiqa (IDP O'zbekiston: qisqa pauzalar bilan 30–34 daqiqa)",
              "4 qismda 40 ta savol. Javoblarni to'g'ridan-to'g'ri kompyuterga yozasiz, oxirida tekshirish uchun 2 "
              "daqiqa beriladi."],
             ["Reading", "60 daqiqa", "3 ta matn bo'yicha 40 ta savol."],
             ["Writing", "60 daqiqa", "Task 1: kamida 150 so'z (taxminan 20 daqiqa). Task 2: kamida 250 so'z "
                                       "(taxminan 40 daqiqa)."],
             ["Speaking", "11–14 daqiqa", "Tayyorlangan examiner bilan 3 qism."]]),
         "p_after": ["ielts.org ma'lumotiga ko'ra, to'rt bo'limning umumiy vaqti 2 soat 45 daqiqa. Listening, Reading "
                     "va Writing bir kunda, tanaffussiz ketma-ket topshiriladi."]},
        {"h": "Qog'ozdagi testdan farqlar",
         "ul": ["Javoblarni javoblar varaqasiga ko'chirish uchun qo'shimcha 10 daqiqa yo'q. britishcouncil.uz ning "
                "ayrim sahifalarida bu eski qoida hali yozilgan, shuning uchun bu yerdagi tavsifga tayaning.",
                "Ekranda matnni ajratib belgilash, qayd yozish, o'z matningiz va qaydlaringizdan nusxa olib qo'yish "
                "hamda Writing da avtomatik so'z hisoblagichdan foydalanish mumkin. Hisoblagich hajmni ko'rsatadi, "
                "imlo xatolarini esa o'zingiz tekshirasiz.",
                "Qolgan vaqt doim ekranda ko'rinib turadi. Reading ikkiga bo'lingan ekranda: bir tomonda matn, "
                "ikkinchi tomonda savollar.",
                "Qaydlar uchun qalam va qog'ozni test markazi beradi. Shaxsiy yozuv buyumlari mumkin emas (British "
                "Council O'zbekiston)."]},
        {"h": "Speaking",
         "p": ["Speaking har doim tayyorlangan haqiqiy examiner bilan suhbat, kompyuter bilan emas. O'zbekistonning "
               "ayrim markazlarida u video qo'ng'iroq orqali o'tadi (British Council Zoom ishlatadi). Odatda boshqa "
               "bo'limlar bilan bir kunda bo'ladi, British Council esa bo'limdan 7 kungacha oldin yoki keyin slot "
               "tanlashga ruxsat beradi. Sana ro'yxatdan o'tish tasdig'ida ko'rsatiladi."]},
        {"h": "Natijalar",
         "p": ["ielts.org kompyuterdagi IELTS uchun 1–5 kun deb yozadi. British Council O'zbekiston odatda 1–2 kun, "
               "IDP esa 1–5 kun deydi. Ikkala provayder ham elektron natija varaqasini (eTRF) beradi."]},
        {"h": "Qog'ozdagi IELTS O'zbekistonda",
         "p": ["Qog'ozdagi IELTS O'zbekistonda 2025-yil 11-iyuldan to'xtatilgan. 2026-yil 5-martda IELTS hamkorlari "
               "2026-yil o'rtasidan boshlab IELTS qog'ozda topshirilmasligini, barcha testlar kompyuterda "
               "o'tkazilishini e'lon qildi.",
               "ielts.org tanlangan mamlakatlar uchun 2026-yil o'rtasidan Writing on Paper variantini ham "
               "tavsiflaydi (Listening va Reading kompyuterda, Writing qo'lda yoziladi). Uning O'zbekistonda taklif "
               "etilishini tasdiqlay olmadik: biz ko'rgan ro'yxatdan o'tish sahifalarida faqat kompyuterda Writing "
               "ko'rsatilgan."]},
        {"h": "One Skill Retake",
         "p": ["British Council ham, IDP ham O'zbekistonda kompyuterda topshirilgan testlar uchun One Skill Retake "
               "ni taklif qiladi: bitta bo'limni (Listening, Reading, Writing yoki Speaking) qayta topshirasiz. Har "
               "bir asl test uchun faqat bir marta va asl testdan keyin 60 kun ichida. Yangi sertifikatda qayta "
               "topshirilgan bo'lim bali va boshqa uch bo'limning avvalgi ballari ko'rsatiladi, natija 3–5 kunda "
               "chiqadi. Narxi ochiq e'lon qilinmagan va ro'yxatdan o'tish portalida ko'rinadi. Tashkilotlar buni "
               "turlicha qabul qiladi, shuning uchun murojaat qilmoqchi bo'lgan tashkilotdan so'rang."]},
        {"h": "Qanday mashq qilish kerak",
         "p": ["TestDay ekrani shu xususiyatlarga o'xshash: ikkiga bo'lingan Reading, teskari sanovchi taymer, "
               "ajratib belgilash va qaydlar, Writing da so'z hisoblagich, Listening javoblari to'g'ridan-to'g'ri "
               "yoziladi. Tezlikni sezish uchun vaqtli testni yeching, xatolar ustida ishlash uchun esa vaqtsiz "
               "Mashq rejimidan foydalaning."]},
    ],
    [("Kompyuterdagi IELTS necha soat davom etadi?",
      "ielts.org ma'lumotiga ko'ra, to'rt bo'lim jami 2 soat 45 daqiqa davom etadi. Listening, Reading va Writing "
      "bir kunda, tanaffussiz ketma-ket o'tadi. Speaking examiner bilan 11–14 daqiqa."),
     ("Listening da javoblarni ko'chirish uchun qo'shimcha vaqt bormi?",
      "Yo'q. Kompyuterda javoblarni to'g'ridan-to'g'ri yozasiz, shuning uchun javoblarni varaqaga ko'chirish uchun "
      "10 daqiqa yo'q. Listening oxirida yozganlaringizni tekshirish uchun 2 daqiqa beriladi."),
     ("Speaking ham kompyuterda topshiriladimi?",
      "Yo'q. Bu tayyorlangan haqiqiy examiner bilan yuzma-yuz yoki video qo'ng'iroq orqali suhbat. Faqat Listening, "
      "Reading va Writing kompyuterda."),
     ("O'zbekistonda hali ham qog'ozda IELTS topshirsa bo'ladimi?",
      "Yo'q. Qog'ozdagi IELTS O'zbekistonda 2025-yil 11-iyuldan to'xtatilgan, IELTS hamkorlari esa uni 2026-yil "
      "o'rtasidan butun dunyoda to'xtatmoqda.")],
    "Kompyuter ekranida mashq qiling",
    [("British Council O'zbekiston: kompyuterda IELTS ga tayyorlanish",
      "https://www.britishcouncil.uz/exam/ielts/prepare/computer-delivered"),
     ("British Council O'zbekiston: natijalar", "https://www.britishcouncil.uz/exam/ielts/results-new"),
     ("ielts.org: IELTS test topshiruvchilar uchun qo'llanma", IELTS_GUIDE),
     ("IDP IELTS Uzbekistan: IELTS on computer", IDP_COMPUTER),
     ("British Council: IELTS on computer", TAKE_COMPUTER),
     ("ielts.org: IELTS yetkazib berish usullari yangilanishi", IELTS_UPDATE),
     ("Gazeta.uz: qog'ozdagi IELTS to'xtatildi", GAZETA_PAPER),
     ("British Council O'zbekiston: One Skill Retake", "https://www.britishcouncil.uz/exam/ielts/one-skill-retake"),
     ("ielts.org: One Skill Retake", IELTS_OSR)])

GUIDES[("format", "ru")] = _guide(
    "ielts-na-kompyutere-format",
    "IELTS на компьютере: формат и отличия | TestDay",
    "Как проходит IELTS on Computer: Listening, Reading и Writing на компьютере, Speaking с экзаменатором. Время, "
    "интерфейс, отличия от бумаги.",
    "IELTS на компьютере: как проходит экзамен",
    "IELTS на компьютере — те же задания, типы вопросов и 9-балльная шкала, что и на бумаге. Listening, Reading и "
    "Writing сдают на компьютере, а Speaking — это разговор с экзаменатором. В Узбекистане это единственный формат: "
    "бумажный IELTS приостановлен с 11 июля 2025 года.",
    [
        {"h": "Тест в одной таблице",
         "table": _table("Четыре раздела на компьютере", ["Раздел", "Время", "Что нужно делать"], [
             ["Listening", "Около 30 минут (IDP Узбекистан: 30–34 минуты с короткими паузами)",
              "40 вопросов в 4 частях. Ответы вводятся прямо в компьютер, в конце даётся 2 минуты на проверку."],
             ["Reading", "60 минут", "40 вопросов к 3 текстам."],
             ["Writing", "60 минут", "Task 1: не менее 150 слов (около 20 минут). Task 2: не менее 250 слов "
                                     "(около 40 минут)."],
             ["Speaking", "11–14 минут", "3 части с обученным экзаменатором."]]),
         "p_after": ["По данным ielts.org, общее время четырёх разделов — 2 часа 45 минут. Listening, Reading и "
                     "Writing сдают в один день, без перерывов между ними."]},
        {"h": "Чем отличается от бумаги",
         "ul": ["Дополнительных 10 минут на перенос ответов Listening в бланк нет. На некоторых страницах "
                "britishcouncil.uz это правило эпохи бумаги ещё осталось, поэтому ориентируйтесь на описание здесь.",
                "На экране можно выделять текст, делать заметки, копировать и вставлять внутри своего текста и "
                "заметок, а в Writing виден автоматический счётчик слов. Счётчик помогает с объёмом, но орфографию "
                "вы проверяете сами.",
                "Оставшееся время всегда видно на экране, а Reading открывается в разделённом окне: текст с одной "
                "стороны, вопросы с другой.",
                "Ручки и бумагу для заметок выдаёт центр. Личные канцелярские принадлежности не разрешены (British "
                "Council Узбекистан)."]},
        {"h": "Speaking",
         "p": ["Speaking — всегда разговор с обученным живым экзаменатором, а не с компьютером. В некоторых центрах "
               "Узбекистана он проходит по видеосвязи (British Council использует Zoom). Обычно он в тот же день, "
               "что и остальные разделы, а British Council позволяет выбрать слот в пределах 7 дней до или после. "
               "Дата указана в подтверждении регистрации."]},
        {"h": "Результаты",
         "p": ["Ielts.org называет срок 1–5 дней для IELTS на компьютере. British Council в Узбекистане пишет, что "
               "обычно это 1–2 дня, IDP — 1–5 дней. Оба выдают электронную форму результатов (eTRF)."]},
        {"h": "Бумажный IELTS в Узбекистане",
         "p": ["Бумажный IELTS в Узбекистане приостановлен с 11 июля 2025 года. 5 марта 2026 года партнёры IELTS "
               "объявили, что с середины 2026 года IELTS нигде не будет проводиться на бумаге: все тесты пройдут на "
               "компьютере.",
               "Ielts.org также описывает вариант Writing on Paper (Listening и Reading на компьютере, Writing от "
               "руки) в отдельных странах с середины 2026 года. Подтвердить, что он есть в Узбекистане, мы не "
               "смогли: на страницах регистрации, которые мы проверили, указан только Writing на компьютере."]},
        {"h": "One Skill Retake",
         "p": ["И British Council, и IDP предлагают в Узбекистане One Skill Retake для тестов, сданных на "
               "компьютере. Вы пересдаёте один раздел (Listening, Reading, Writing или Speaking) один раз для "
               "каждого исходного теста и в течение 60 дней после него. В новой форме результатов будет новый балл "
               "за этот раздел и три прежних балла, а результаты приходят за 3–5 дней. Цена не публикуется, она "
               "показывается в портале при записи. Организации по-разному принимают такой результат, поэтому "
               "уточните у той, куда подаёте документы."]},
        {"h": "Как тренироваться",
         "p": ["Экран TestDay повторяет эти возможности: Reading в разделённом окне, обратный отсчёт, выделение "
               "текста и заметки, счётчик слов в Writing и ответы Listening, которые вводятся сразу. Пройдите тест "
               "на время, чтобы почувствовать темп, а режим практики используйте для разбора ошибок без таймера."]},
    ],
    [("Сколько длится IELTS на компьютере?",
      "По данным ielts.org, четыре раздела занимают 2 часа 45 минут. Listening, Reading и Writing идут подряд в один "
      "день без перерывов, а Speaking с экзаменатором длится 11–14 минут."),
     ("Дают ли в Listening время на перенос ответов?",
      "Нет. На компьютере вы вводите ответы сразу, поэтому 10 минут на перенос в бланк не предусмотрены. В конце "
      "Listening есть 2 минуты, чтобы проверить введённое."),
     ("Speaking тоже сдают на компьютере?",
      "Нет. Это разговор с обученным живым экзаменатором лично или по видеосвязи. На компьютере только Listening, "
      "Reading и Writing."),
     ("Можно ли в Узбекистане сдать IELTS на бумаге?",
      "Нет. Бумажный IELTS в Узбекистане приостановлен с 11 июля 2025 года, а партнёры IELTS прекращают его по всему "
      "миру с середины 2026 года.")],
    "Потренироваться на экране как на экзамене",
    [("British Council Узбекистан: подготовка к IELTS на компьютере",
      "https://www.britishcouncil.uz/ru/exam/ielts/prepare/computer-delivered"),
     ("British Council Узбекистан: результаты IELTS", "https://www.britishcouncil.uz/ru/exam/ielts/results"),
     ("ielts.org: руководство для сдающих тест", IELTS_GUIDE),
     ("IDP IELTS Uzbekistan: IELTS on computer", IDP_COMPUTER),
     ("British Council: IELTS on computer", TAKE_COMPUTER),
     ("ielts.org: изменения в формате проведения IELTS", IELTS_UPDATE),
     ("Gazeta.uz: бумажный IELTS приостановлен", GAZETA_PAPER),
     ("British Council Узбекистан: One Skill Retake", "https://www.britishcouncil.uz/exam/ielts/one-skill-retake"),
     ("ielts.org: One Skill Retake", IELTS_OSR)])

# ---------------------------------------------------------------------------------------------------------------
# What the exam costs in Uzbekistan (Uzbek, Russian)
# ---------------------------------------------------------------------------------------------------------------

_bc_uz, _idp_uz, _old_uz = money(BC_FEE, "uz"), money(IDP_FEE, "uz"), money(BC_OLD_FEE, "uz")
_bc_ru, _idp_ru, _old_ru = money(BC_FEE, "ru"), money(IDP_FEE, "ru"), money(BC_OLD_FEE, "ru")
_rise = money(BC_FEE - BC_OLD_FEE, "uz")

GUIDES[("fees", "uz")] = _guide(
    "ielts-imtihon-narxi-2026",
    "IELTS imtihon narxi 2026: O'zbekistonda | TestDay",
    f"IELTS narxi O'zbekistonda: British Council {_bc_uz} so'm, IDP {_idp_uz} so'm ({_date('uz')}). To'lov, "
    "bekor qilish va rasmiy havolalar.",
    "IELTS imtihon narxi O'zbekistonda (2026)",
    f"{_date('uz')} holatiga kompyuterda topshiriladigan IELTS Academic va General Training narxi British Councilda "
    f"{_bc_uz} so'm, IDP/Edu Action markazlarida {_idp_uz} so'm. Narxlar rasmiy ro'yxatdan o'tish sahifalaridan "
    "olingan; manbalar va tekshiruv sanasi pastda.",
    [
        {"h": "Narxlar",
         "table": _table("Kompyuterda topshiriladigan IELTS narxlari", ["Test va provayder", "Narx", "Izoh"], [
             ["British Council: IELTS Academic", f"{_bc_uz} so'm",
              f"2026-yil sentabrda {_old_uz} so'mdan oshirilgan (Zamin.uz, 3-sentabr)."],
             ["British Council: IELTS General Training", f"{_bc_uz} so'm", "Academic bilan bir xil narx."],
             ["British Council: IELTS for UKVI (Academic va General Training)", f"{money(BC_UKVI_FEE, 'uz')} so'm",
              "Buyuk Britaniya UKVI talablari uchun."],
             ["British Council: IELTS for UKVI Life Skills (A1 va B1)", f"{money(BC_LIFE_SKILLS_FEE, 'uz')} so'm", ""],
             ["IDP / Edu Action: IELTS Academic", f"{_idp_uz} so'm",
              "Toshkent, Urganch, Termiz va Samarqand sessiyalarida tasdiqlangan. Buxoro va Andijon uchun narx "
              "ko'rsatilmagan."],
             ["IDP / Edu Action: IELTS General Training", f"{_idp_uz} so'm", "Academic bilan bir xil narx."],
             ["One Skill Retake (British Council va IDP)", "Ochiq e'lon qilinmagan",
              "Narx ro'yxatdan o'tish portalida ko'rinadi. IDP ga ko'ra narx to'rtala bo'lim uchun bir xil."],
             ["Qo'shimcha TRF nusxasi (British Council)", f"{money(BC_EXTRA_TRF_FEE, 'uz')} so'm",
              "Dastlabki 5 ta tashkilot nusxasi bepul."]]),
         "p_after": ["IDP O'zbekiston bron sahifalarida UKVI va Life Skills testlari ro'yxatda ko'rsatilmagan."]},
        {"h": "Eski narx haqida",
         "p": [f"britishcouncil.uz ning ba'zi modul sahifalarida (masalan, which-test) hali eski {_old_uz} so'm "
               f"yozilgan. Amaldagi narx ro'yxatdan o'tish sahifasidagi {_bc_uz} so'm."]},
        {"h": "Ro'yxatdan o'tish va to'lov (British Council)",
         "steps": ["Pasport yoki ID-karta skanini yuklab, onlayn ro'yxatdan o'ting. Hujjat ro'yxatdan o'tishda ham, "
                   "test kuni ham amal qilishi kerak. Ismingiz hujjatdagi bilan, apostroflargacha bir xil bo'lishi "
                   "lozim. 18 yoshgacha bo'lganlar ota-ona roziligi shaklini topshiradi.",
                   "Ro'yxatdan o'tgach 3 ish kuni ichida to'lang. To'lovda 'IELTS Application Summary' xatidagi UZ "
                   "bilan boshlanadigan 15 xonali raqamni ko'rsating.",
                   "To'lov usullari: Payme, Xazna, Click va Uzum ilovalari; bank o'tkazmasi; JSC KDB Bank Uzbekistan "
                   "Yunusobod filialida naqd pul yoki so'mdagi debet karta; onlayn to'lovda xorijiy banklar bergan "
                   "Visa va Mastercard kartalari (funt sterlingda).",
                   "Tasdiq xatlarida test vaqti va joyi, Speaking sanasi va Test Taker Portal ma'lumotlari keladi."],
         "p_after": ["IDP/Edu Action: onlayn bron qilinadi (shahar, test turi va sana tanlanadi, pasport skani "
                     "yuklanadi, kredit karta bilan to'lanadi) yoki filialda naqd pul yoki bank o'tkazmasi bilan. IDP "
                     "saytida mahalliy to'lov ilovalari (Payme, Click va boshqalar) ko'rsatilmagan; ular qabul "
                     "qilinishini markazdan so'rang."]},
        {"h": "Bekor qilish va sanani ko'chirish (British Council)",
         "ul": ["Test sanasidan 15 kun yoki undan ko'p oldin bekor qilsangiz, to'langan summaning 75% qaytariladi "
                "(25% ma'muriy to'lov).",
                "Test sanasiga 14 kun va undan kam qolgan bo'lsa, pul qaytarilmaydi.",
                "Sanani ko'chirish: 15 kun va undan ko'p oldin bepul; 5–14 kun oldin 25% ma'muriy to'lov bilan; 5 "
                "kundan kam qolganda ko'chirib bo'lmaydi va u bekor qilish deb hisoblanadi.",
                "Ro'yxatdan o'tishga kechikib kelganlar testga qo'yilmaydi va to'lovni yo'qotadi.",
                "Sog'liq yoki boshqa jiddiy sabab bo'lsa, hujjatlar bilan alohida ko'rib chiqish uchun murojaat "
                "qilish mumkin. Muddatlarni siyosat sahifasidan tekshiring."],
         "p_after": ["IDP O'zbekistonning ko'chirish sahifasi 2021-yildagi, shuning uchun amaldagi shartlarni Edu "
                     "Action markazidan so'rang."]},
        {"h": "Davlat kompensatsiyasi",
         "p": ["IELTS dan 7.0 va undan yuqori ball olgan yoshlarga imtihon to'lovi davlat dasturi orqali qaytariladi. "
               "Shartlar va ariza tartibi uchun 'IELTS 7.0 uchun kompensatsiya' sahifasiga qarang."]},
    ],
    [("IELTS imtihoni O'zbekistonda qancha turadi?",
      f"{_date('uz')} holatiga British Councilda IELTS Academic va General Training kompyuterda {_bc_uz} so'm, "
      f"IDP/Edu Action markazlarida {_idp_uz} so'm."),
     ("Narx qachon oshgan?",
      f"Zamin.uz 2026-yil 3-sentabrda British Council narxi {_old_uz} so'mdan {_bc_uz} so'mga, ya'ni {_rise} "
      "so'mga oshganini yozgan. britishcouncil.uz da o'zgarish sanasi e'lon qilinmagan."),
     ("Imtihon sanasini o'tkazib yuborsam, pul qaytariladimi?",
      "British Council: ro'yxatdan o'tishga kechikib kelgan nomzod testga qo'yilmaydi va to'lovni yo'qotadi. Jiddiy "
      "sabab bo'lsa, hujjatlar bilan alohida ko'rib chiqish uchun murojaat qilish mumkin. Test sanasidan 15 kun va "
      "undan ko'p oldin bekor qilsangiz, 75% qaytariladi."),
     ("To'lovni Payme yoki Click orqali qilsa bo'ladimi?",
      "British Council uchun ha: Payme, Click, Xazna va Uzum ilovalari qabul qilinadi. IDP saytida mahalliy ilovalar "
      "ro'yxatda yo'q, shuning uchun markazdan so'rang.")],
    "To'lashdan oldin bepul test yeching",
    [("British Council O'zbekiston: ro'yxatdan o'tish va narxlar", "https://www.britishcouncil.uz/exam/ielts/book-test"),
     ("British Council O'zbekiston: bekor qilish va ko'chirish",
      "https://www.britishcouncil.uz/en/exam/ielts/cancellation-refund-and-transfer-policy"),
     ("British Council O'zbekiston: natijalar va qo'shimcha TRF", "https://www.britishcouncil.uz/exam/ielts/results-new"),
     ("IDP IELTS Uzbekistan: Toshkentdagi test sanalari va narx", IDP_DATES),
     ("IDP IELTS Uzbekistan: Edu Action markazi", IDP_CENTRE),
     ("IDP IELTS Uzbekistan: sanani ko'chirish", IDP_TRANSFER),
     ("Zamin.uz: IELTS topshirish narxi oshdi", ZAMIN_FEE)],
    volatile=True)

GUIDES[("fees", "ru")] = _guide(
    "ielts-stoimost-ekzamena-uzbekistan",
    "Стоимость IELTS в Узбекистане 2026 | TestDay",
    f"Сколько стоит IELTS в Узбекистане: British Council {_bc_ru} сум, IDP {_idp_ru} сум ({_date('ru')}). Оплата, "
    "отмена и официальные ссылки.",
    "Сколько стоит IELTS в Узбекистане в 2026 году",
    f"По состоянию на {_date('ru')} IELTS Academic и General Training на компьютере стоит {_bc_ru} сум в British "
    f"Council и {_idp_ru} сум в центрах IDP/Edu Action. Цены взяты со страниц регистрации; источники и дата проверки "
    "указаны ниже.",
    [
        {"h": "Цены",
         "table": _table("Стоимость IELTS на компьютере", ["Тест и организатор", "Цена", "Примечание"], [
             ["British Council: IELTS Academic", f"{_bc_ru} сум",
              f"В сентябре 2026 года выросла с {_old_ru} сум (Zamin.uz, 3 сентября)."],
             ["British Council: IELTS General Training", f"{_bc_ru} сум", "Та же цена, что и за Academic."],
             ["British Council: IELTS for UKVI (Academic и General Training)", f"{money(BC_UKVI_FEE, 'ru')} сум",
              "Для требований UKVI (Великобритания)."],
             ["British Council: IELTS for UKVI Life Skills (A1 и B1)", f"{money(BC_LIFE_SKILLS_FEE, 'ru')} сум", ""],
             ["IDP / Edu Action: IELTS Academic", f"{_idp_ru} сум",
              "Подтверждено для сессий в Ташкенте, Ургенче, Термезе и Самарканде. Для Бухары и Андижана цена не "
              "показана."],
             ["IDP / Edu Action: IELTS General Training", f"{_idp_ru} сум", "Та же цена, что и за Academic."],
             ["One Skill Retake (British Council и IDP)", "Не публикуется",
              "Цена видна в портале при регистрации. По данным IDP, она одинакова для всех четырёх разделов."],
             ["Дополнительная копия TRF (British Council)", f"{money(BC_EXTRA_TRF_FEE, 'ru')} сум",
              "Первые 5 копий для организаций бесплатны."]]),
         "p_after": ["На страницах бронирования IDP Узбекистан тесты UKVI и Life Skills не указаны."]},
        {"h": "О старой цене",
         "p": [f"На некоторых страницах britishcouncil.uz (например, which-test) всё ещё указано {_old_ru} сум. "
               f"Действует цена со страницы регистрации — {_bc_ru} сум."]},
        {"h": "Регистрация и оплата (British Council)",
         "steps": ["Зарегистрируйтесь онлайн и загрузите скан паспорта или ID-карты. Документ должен действовать и при "
                   "регистрации, и в день теста. Имя должно полностью совпадать с документом, включая апострофы. "
                   "Кандидаты младше 18 лет подают форму согласия родителей.",
                   "Оплатите в течение 3 рабочих дней после регистрации. При оплате укажите 15-значный номер, "
                   "начинающийся с UZ, из письма «IELTS Application Summary».",
                   "Способы оплаты: приложения Payme, Xazna, Click и Uzum; банковский перевод; наличные или дебетовая "
                   "карта в сумах в Юнусабадском филиале JSC KDB Bank Uzbekistan; при онлайн-оплате — карты Visa и "
                   "Mastercard иностранных банков (в фунтах стерлингов).",
                   "В письмах с подтверждением придут время и место теста, дата Speaking и доступ к Test Taker "
                   "Portal."],
         "p_after": ["IDP/Edu Action: запись онлайн (выбираются город, тип теста и дата, загружается скан паспорта, "
                     "оплата кредитной картой) либо в филиале наличными или банковским переводом. На сайте IDP "
                     "местные платёжные приложения (Payme, Click и др.) не указаны, поэтому уточните в центре."]},
        {"h": "Отмена и перенос (British Council)",
         "ul": ["Если отменить за 15 дней и более до теста, возвращается 75% оплаты (25% — административный сбор).",
                "Если до теста осталось 14 дней или меньше, деньги не возвращаются.",
                "Перенос даты: за 15 дней и более — бесплатно; за 5–14 дней — с административным сбором 25%; "
                "менее чем за 5 дней перенос невозможен и считается отменой.",
                "Опоздавших на регистрацию к тесту не допускают, оплата не возвращается.",
                "При болезни или другой серьёзной причине можно подать заявку с документами на отдельное "
                "рассмотрение. Сроки проверьте на странице правил."],
         "p_after": ["Страница IDP Узбекистан о переносе датирована 2021 годом, поэтому действующие условия "
                     "уточняйте в центре Edu Action."]},
        {"h": "Государственная компенсация",
         "p": ["Молодым людям, получившим по IELTS 7.0 и выше, расходы на экзамен возмещает государство. Условия и "
               "порядок подачи заявки смотрите на странице «Компенсация за IELTS 7.0» (она на узбекском языке)."]},
    ],
    [("Сколько стоит IELTS в Узбекистане?",
      f"По состоянию на {_date('ru')} IELTS Academic и General Training на компьютере стоит {_bc_ru} сум в British "
      f"Council и {_idp_ru} сум в центрах IDP/Edu Action."),
     ("Когда подорожал IELTS?",
      f"Zamin.uz сообщил 3 сентября 2026 года, что цена British Council выросла с {_old_ru} до {_bc_ru} сум, то есть "
      f"на {money(BC_FEE - BC_OLD_FEE, 'ru')} сум. Дата изменения на britishcouncil.uz не указана."),
     ("Вернут ли деньги, если я пропущу дату экзамена?",
      "British Council: опоздавшего на регистрацию кандидата к тесту не допускают, оплата не возвращается. При "
      "серьёзной причине можно подать заявку с документами на отдельное рассмотрение. Если отменить за 15 дней и "
      "более до даты теста, вернут 75%."),
     ("Можно ли оплатить через Payme или Click?",
      "Для British Council да: принимаются приложения Payme, Click, Xazna и Uzum. На сайте IDP местные приложения не "
      "указаны, поэтому уточните в центре.")],
    "Перед оплатой пройдите бесплатный тест",
    [("British Council Узбекистан: регистрация и цены", "https://www.britishcouncil.uz/ru/exam/ielts/book-test"),
     ("British Council Узбекистан: отмена, возврат и перенос",
      "https://www.britishcouncil.uz/en/exam/ielts/cancellation-refund-and-transfer-policy"),
     ("British Council Узбекистан: результаты и копии TRF", "https://www.britishcouncil.uz/ru/exam/ielts/results"),
     ("IDP IELTS Uzbekistan: даты и цена в Ташкенте", IDP_DATES),
     ("IDP IELTS Uzbekistan: центр Edu Action", IDP_CENTRE),
     ("IDP IELTS Uzbekistan: перенос и отмена", IDP_TRANSFER),
     ("Zamin.uz: цена IELTS выросла", ZAMIN_FEE)],
    volatile=True)

# ---------------------------------------------------------------------------------------------------------------
# The state refund for IELTS 7.0+ (Uzbek)
# ---------------------------------------------------------------------------------------------------------------

GUIDES[("refund", "uz")] = _guide(
    "ielts-kompensatsiya-7-ball",
    "IELTS 7.0 uchun to'lovni qaytarish: qo'llanma | TestDay",
    "IELTS 7.0 va undan yuqori ball olganlar uchun xarajatni qoplash: kim huquqli, qanday ariza beriladi, hujjatlar, "
    "muddatlar. Rasmiy havolalar.",
    "IELTS 7.0 uchun kompensatsiya qanday olinadi",
    "Xalqaro imtihon tizimlari bo'yicha yuqori ball olgan yoshlarga imtihon topshirish xarajatlari davlat dasturi "
    "orqali to'liq qoplanadi. IELTS bo'yicha kamida 7.0 kerak. Quyida rasmiy manbalardagi shartlar, ariza tartibi va "
    "muddatlar; asosiy manba — my.gov.uz va Yoshlar ishlari agentligi sahifalari.",
    [
        {"h": "Kim olishi mumkin",
         "ul": ["O'zbekiston Respublikasi fuqarolari va O'zbekistonda doimiy yashovchi fuqaroligi bo'lmagan "
                "shaxslar, agar imtihon topshirish paytida 31 yoshga to'lmagan bo'lsa (gov.uz).",
                "IELTS bo'yicha umumiy ball kamida 7.0 bo'lishi kerak (Gazeta.uz, 2026-yil 7-yanvar).",
                "16 yoshga to'lmagan shaxs nomidan uning qonuniy vakili ariza beradi."],
         "p_after": ["Diqqat: British Council o'quv qo'llanmasida yosh chegarasi «30 dan kichik» deb yozilgan. my.gov.uz "
                     "va gov.uz sahifalarida esa imtihon paytida 31 yoshga to'lmagan bo'lish kerakligi ko'rsatilgan; "
                     "qonuniy chegara sifatida shularni asos qiling. Shubha bo'lsa, arizadan oldin Yoshlar ishlari "
                     "agentligidan so'rang."]},
        {"h": "Nima qaytariladi",
         "p": ["Imtihon uchun to'langan summaning 100% i qaytariladi, my.gov.uz xizmati bepul. Bu sahifa imtihon "
               "to'lovi haqida. Tayyorgarlik kurslari yoki o'qish xarajatlarini qoplash qoidalari o'zgargan va "
               "manbalarda farq qiladi, ularni my.gov.uz sahifasida tekshiring."]},
        {"h": "Qanday ariza beriladi",
         "steps": ["my.gov.uz ga OneID yoki MyID orqali kiring va «Xalqaro imtihon tizimlari bo'yicha imtihon "
                   "topshirish xarajatlarini qoplab berishga ariza yuborish» xizmatini toping (413-xizmat).",
                   "Sertifikat ma'lumotlarini kiriting va ikkita PDF fayl yuklang: imtihon to'lovi kvitansiyasi va "
                   "IELTS Test Report Form (TRF yoki eTRF).",
                   "Yoshlar ishlari agentligi sertifikatni tekshiradi. Tasdiqlangach sizga tasdiqnoma beriladi va "
                   "SMS keladi.",
                   "Mablag'ni Xalq banki «Xazna» ilovasida olasiz: shaxsingizni tasdiqlang, bank kartangizni ulang va "
                   "Xizmatlar → Ijtimoiy xizmatlar → Xalqaro imtihon (qoplab berish) bo'limida hujjatni biriktiring."],
         "p_after": ["Ba'zi eski sahifalarda to'lov Xalq banki filiali orqali deb yozilgan. Yoshlar ishlari agentligi "
                     "(2026-yil yanvar) mablag' «Xazna» mobil ilovasi orqali berilishini ko'rsatadi."]},
        {"h": "Muddatlar",
         "ul": ["Ariza odatda 15 ish kuni ichida ko'rib chiqiladi. Qo'shimcha tekshiruv kerak bo'lsa, muddat 45 "
                "kungacha uzaytirilishi mumkin (Yoshlar ishlari agentligi, 2026-yil 15-yanvar).",
                "Tasdiqnoma berilgan sanadan boshlab 15 kun ichida mablag' moliyalashtiriladi. Mablag' hali mavjud "
                "bo'lmasa, ilovada «Xizmat vaqtinchalik mavjud emas» xabari chiqadi.",
                "Tasdiqnoma berilgan sanadan boshlab 180 kun davomida mablag'ni istalgan vaqtda olish mumkin.",
                "Ariza berish muddati va boshqa shartlarni my.gov.uz hamda lex.uz dagi Vazirlar Mahkamasining "
                "209-sonli qarorida tekshiring."]},
        {"h": "Dastur ko'lami",
         "p": ["Gazeta.uz Yoshlar ishlari agentligi ma'lumotlarini keltiradi: 2025-yilda 17 324 nafar yoshga imtihon "
               "xarajatlari qaytarilgan (38,7 mlrd so'm), ularning 13 720 nafari IELTS topshirganlar."]},
    ],
    [("7.0 dan past ball olsam, kompensatsiya bormi?",
      "IELTS bo'yicha rasmiy manbalarda minimal ball 7.0 deb ko'rsatilgan. Past ball uchun kompensatsiya haqida "
      "ma'lumot topmadik."),
     ("General Training, UKVI yoki One Skill Retake sertifikati ham mos keladimi?",
      "my.gov.uz va gov.uz sahifalarida faqat «IELTS» deb yozilgan, bu test turlari alohida ko'rsatilmagan. Ariza "
      "berishdan oldin Yoshlar ishlari agentligidan so'rang."),
     ("Pulni qancha kutish kerak?",
      "Rasmiy ma'lumotga ko'ra, ko'rib chiqish 15 ish kuni (45 kungacha uzayishi mumkin), undan keyin tasdiqnomadan "
      "boshlab 15 kun ichida mablag' moliyalashtiriladi."),
     ("Xaznada mablag' ko'rinmasa nima qilaman?",
      "Mablag' hali mavjud bo'lmasa, ilova «Xizmat vaqtinchalik mavjud emas» deb yozadi. Moliyalashtirish tasdiqnomadan "
      "keyin 15 kun ichida bo'lishi kerak. Xazna yordam liniyasi: 1106.")],
    "Bepul mock bilan 7.0 ga tayyorlaning",
    [("my.gov.uz: imtihon xarajatlarini qoplash xizmati (413)", MY_GOV),
     ("gov.uz: Yoshlar ishlari agentligi, xizmat tavsifi", GOV_SECTION),
     ("gov.uz: Yoshlar ishlari agentligi, savol va javoblar (2026-yil 15-yanvar)", GOV_NEWS),
     ("Gazeta.uz: kompensatsiya statistikasi (2026-yil 7-yanvar)", GAZETA_COMP),
     ("lex.uz: Vazirlar Mahkamasining 209-sonli qarori", LEX_209),
     ("British Council O'zbekiston: IELTS 7 uchun to'lovni qaytarish", "https://www.britishcouncil.uz/en/exam/ielts/results/ielts7")],
    volatile=True)

# ---------------------------------------------------------------------------------------------------------------
# What band 7 means and how to work towards it (English)
# ---------------------------------------------------------------------------------------------------------------

GUIDES[("band7", "en")] = _guide(
    "how-to-get-band-7-in-ielts",
    "How to Get Band 7 in IELTS: 30-Day Plan | TestDay",
    "A practical band 7 plan: what to practise in each module, how raw scores convert to bands, and how to track "
    "progress with mock tests.",
    "How to get band 7 in IELTS",
    "ielts.org describes band 7 as a Good level: operational command of the language and a good handling of complex "
    "language. This guide shows what that means in each paper, how many Listening and Reading answers you need, and "
    "how to practise for four weeks with timed tests.",
    [
        {"h": "What band 7 means",
         "p": ["According to ielts.org, a band 7 test taker has operational command of the language, though with "
               "occasional inaccuracies, inappropriate usage and misunderstandings in some situations. They generally "
               "handle complex language well and understand detailed reasoning."]},
        {"h": "The marks you need",
         "table": _table("Band 7 in each paper", ["Paper", "What band 7 needs"], [
             ["Listening", "About 30 out of 40 correct. The British Council table gives 30–31 for band 7.0."],
             ["Academic Reading", "About 30 out of 40 correct (30–32 for band 7.0). General Training Reading needs "
                                  "more correct answers for the same band."],
             ["Writing", "Band 7 on four criteria: Task Achievement (Task 1) or Task Response (Task 2), Coherence "
                         "and Cohesion, Lexical Resource, and Grammatical Range and Accuracy."],
             ["Speaking", "Band 7 on four criteria: Fluency and Coherence, Lexical Resource, Grammatical Range and "
                          "Accuracy, and Pronunciation."]]),
         "p_after": ["The exact number of marks varies slightly between test versions. The overall band is the "
                     "average of the four bands, rounded to the nearest half band: an average ending in .25 rounds up "
                     "to the next half band, and one ending in .75 rounds up to the next whole band. So bands of "
                     "6.5, 7.0, 7.0 and 7.0 average 6.875 and give an overall 7.0, while 6.5, 6.5, 6.5 and 7.0 "
                     "average 6.625 and give 6.5. Try your own numbers in the band score calculator."]},
        {"h": "Writing at band 7",
         "ul": ["Task: the main parts of the prompt are addressed with a clear, developed position. Ideas are "
                "extended and supported, though they may be over-generalised or lack some focus and precision. In "
                "Academic Task 1 you give a clear overview and cover and highlight the key features.",
                "Coherence and cohesion: information and ideas are logically organised with a clear progression. A "
                "range of linking devices is used flexibly, with some over- or under-use, and paragraphing is "
                "generally effective.",
                "Vocabulary: enough range for some flexibility and precision, some less common and idiomatic items, "
                "an awareness of style and collocation, and only a few spelling or word-formation errors.",
                "Grammar: a variety of complex structures used with some flexibility and accuracy, frequent "
                "error-free sentences, and a few errors that do not impede communication."],
         "p_after": ["ielts.org says the step from band 6 to band 7 is a move from functional to confident academic "
                     "writing."]},
        {"h": "Speaking at band 7",
         "ul": ["Fluency: you keep going and produce long turns without noticeable effort. Some hesitation, "
                "repetition or self-correction may occur but does not affect coherence, and you use discourse markers "
                "and connectives flexibly.",
                "Vocabulary: used flexibly across a variety of topics, with some less common and idiomatic items and "
                "effective paraphrase.",
                "Grammar: a range of structures used flexibly, with frequent error-free sentences and a few basic "
                "errors.",
                "Pronunciation: all the positive features of band 6 and some, but not all, of band 8: a range of "
                "phonological features, generally appropriate chunking, some effective use of stress and "
                "intonation, and speech that is understood without much effort."],
         "p_after": ["ielts.org notes that a candidate must fully fit the positive features of a level and is rated on "
                     "their average performance across all parts. It also says band 7 speakers can express nuanced "
                     "opinions and handle interruptions or follow-up questions."]},
        {"h": "A four-week routine with TestDay",
         "steps": ["Week 1: take one timed Listening test and one timed Academic Reading test. Compare each with 30 "
                   "out of 40, then look at your results by question type to see where you lose marks.",
                   "Week 2: write a Task 2 essay and a Task 1 report against the clock. Use the AI examiner to see "
                   "which of the four criteria is lowest, and work on that one, comparing your essay with the model "
                   "answer.",
                   "Week 3: take a Speaking test and listen back to your recording. Note hesitation, repeated words "
                   "and basic errors, then take a different Speaking test.",
                   "Week 4: take a full set of all four papers with timing, enter your results in the band score "
                   "calculator and compare them with your target."],
         "p_after": ["The AI bands on TestDay are practice estimates, not official scores. Use them to see the "
                     "direction of your progress and to find weak spots."]},
    ],
    [("How many correct answers do I need for band 7 in Listening?",
      "About 30 out of 40. The British Council gives 30–31 for band 7.0, and ielts.org gives an average of 30. The "
      "exact mark varies slightly between test versions."),
     ("Can I get band 7 overall if one skill is lower?",
      "Yes, if the average works out. The overall band is the average of the four skills rounded to the nearest half "
      "band, so 6.5, 7.0, 7.0 and 7.0 give an overall 7.0. Check whether your university or visa authority also sets "
      "a minimum for each skill."),
     ("Do the AI bands on TestDay predict my real score?",
      "No. They are practice estimates based on the public band descriptors. A real examiner can differ, so use them "
      "to track progress and find weak areas, not to predict your exact result.")],
    "Practise for band 7 for free",
    [("ielts.org: IELTS scoring in detail", IELTS_SCORING),
     ("ielts.org: Writing band descriptors (PDF)", "https://ielts.org/cdn/Guides/ielts-writing-band-descriptors.pdf"),
     ("ielts.org: Speaking band descriptors (PDF)", "https://ielts.org/cdn/ielts-guides/ielts-speaking-band-descriptors.pdf"),
     ("ielts.org: differences between IELTS 6 and 7 for productive skills",
      "https://ielts.org/news-and-insights/differences-between-ielts-6-and-7-for-productive-skills"),
     ("British Council: how IELTS is assessed", "https://takeielts.britishcouncil.org/results/how-is-ielts-assessed")])
