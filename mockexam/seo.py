"""
Pages for search engines.

The app itself is one page whose sections live behind "#/", which search engines treat as a single address. So the
things people search for have a real page of their own here: a free practice test, one page for each paper, a band
score calculator, in English, Uzbek and Russian. Each page is plain HTML (readable without running any script), has
its own title, description, canonical address and language links, and sends the reader into the app with one button.

The tests and the app are in English, like the real exam; the Uzbek and Russian pages explain them in those
languages and say so. Nothing here claims an official score: the band from the AI examiner is a practice estimate.
"""

import html
import json

from . import scoring

LANGS = ("en", "uz", "ru")
LANG_NAMES = {"en": "English", "uz": "O'zbekcha", "ru": "Русский"}
LOCALES = {"en": "en_GB", "uz": "uz_UZ", "ru": "ru_RU"}
TOPICS = ("free", "listening", "reading", "calc", "writing", "speaking")

# Where the button on each page leads inside the app.
CTA_TARGET = {
    "free": "/#/", "listening": "/#/tests/listening", "reading": "/#/tests/reading",
    "calc": "/#/tests/listening", "writing": "/#/tests/writing", "speaking": "/#/tests/speaking",
}

UI = {
    "en": {
        "free": "Free tests", "calc": "Band calculator", "price": "Price", "what": "What you get", "how": "How it works",
        "faq": "Questions and answers", "more": "More from TestDay", "langs": "Read this page in",
        "note": "", "terms": "Terms", "privacy": "Privacy", "refunds": "Refunds", "about": "About",
        "disclaimer": "TestDay is an independent practice site and is not affiliated with the IELTS partners. "
                      "Bands from the AI examiner are practice estimates, not official scores.",
        "calc_title": "Your scores", "listening": "Listening: correct answers (0–40)",
        "reading": "Academic Reading: correct answers (0–40)", "writing": "Writing band", "speaking": "Speaking band",
        "choose": "Choose", "res_l": "Listening band", "res_r": "Reading band", "res_o": "Overall band",
        "table_l": "Listening: correct answers to band", "table_r": "Academic Reading: correct answers to band",
        "col_raw": "Correct answers", "col_band": "Band", "low": "0–3", "approx": "Approximate: marks vary slightly between test versions.",
    },
    "uz": {
        "free": "Bepul testlar", "calc": "Band kalkulyatori", "price": "Narx", "what": "Nimalar bor", "how": "Qanday ishlaydi",
        "faq": "Savol va javoblar", "more": "TestDay da yana", "langs": "Bu sahifani o'qing",
        "note": "Testlar va sayt haqiqiy imtihon kabi ingliz tilida; bu sahifa ularni o'zbek tilida tushuntiradi.",
        "terms": "Shartlar", "privacy": "Maxfiylik", "refunds": "Qaytarish", "about": "Biz haqimizda",
        "disclaimer": "TestDay mustaqil mashq sayti va IELTS hamkorlariga aloqasi yo'q. "
                      "AI examiner bandi mashq uchun taxmin, rasmiy ball emas.",
        "calc_title": "Sizning ballaringiz", "listening": "Listening: to'g'ri javoblar (0–40)",
        "reading": "Academic Reading: to'g'ri javoblar (0–40)", "writing": "Writing bandi", "speaking": "Speaking bandi",
        "choose": "Tanlang", "res_l": "Listening bandi", "res_r": "Reading bandi", "res_o": "Umumiy band",
        "table_l": "Listening: to'g'ri javoblar va band", "table_r": "Academic Reading: to'g'ri javoblar va band",
        "col_raw": "To'g'ri javoblar", "col_band": "Band", "low": "0–3", "approx": "Taxminiy: test versiyasiga qarab ballar biroz farq qiladi.",
    },
    "ru": {
        "free": "Бесплатные тесты", "calc": "Калькулятор баллов", "price": "Цена", "what": "Что внутри", "how": "Как это работает",
        "faq": "Вопросы и ответы", "more": "Ещё на TestDay", "langs": "Эта страница на языках",
        "note": "Тесты и сайт на английском, как и настоящий экзамен; эта страница объясняет их по-русски.",
        "terms": "Условия", "privacy": "Конфиденциальность", "refunds": "Возвраты", "about": "О сайте",
        "disclaimer": "TestDay — независимый сайт для практики, не связан с партнёрами IELTS. "
                      "Band от ИИ-экзаменатора — тренировочная оценка, а не официальный балл.",
        "calc_title": "Ваши баллы", "listening": "Listening: верные ответы (0–40)",
        "reading": "Academic Reading: верные ответы (0–40)", "writing": "Band за Writing", "speaking": "Band за Speaking",
        "choose": "Выберите", "res_l": "Band за Listening", "res_r": "Band за Reading", "res_o": "Общий band",
        "table_l": "Listening: верные ответы и band", "table_r": "Academic Reading: верные ответы и band",
        "col_raw": "Верные ответы", "col_band": "Band", "low": "0–3", "approx": "Примерно: границы немного отличаются в разных версиях теста.",
    },
}


def _page(slug, title, description, h1, intro, points, faq, cta):
    return {"slug": slug, "title": title, "description": description, "h1": h1, "intro": intro,
            "points": points, "faq": faq, "cta": cta}


CONTENT = {
    ("free", "en"): _page(
        "free-ielts-computer-based-practice-test",
        "Free IELTS Computer-Based Practice Test | TestDay",
        "Practise IELTS on screen: Listening, Academic Reading, Writing and Speaking. 5 free tests per module, "
        "explained answers, instant band estimates.",
        "Free computer-based IELTS practice tests",
        "Practise the four IELTS papers on a screen that follows the computer-delivered exam: split-screen passages "
        "and questions, a countdown timer, a question navigator and highlighting. The first five tests in every "
        "module are free.",
        [("Listening and Reading", "Timed tests with instant marking: your band estimate, results by part and by "
                                   "question type, and an explanation for every answer."),
         ("Writing", "Academic Task 1 and Task 2 with a word counter and automatic checks. With a free account, the AI "
                     "examiner scores the four official criteria and suggests corrections."),
         ("Speaking", "All three parts, spoken to a recorded examiner. The AI examiner listens to your answers and "
                      "gives a practice band."),
         ("On any device", "Everything runs in the browser, on a computer or a phone. Your answers are saved in the "
                           "browser, so a refresh does not lose them.")],
        [("Are the tests really free?", "Yes. The first five tests in each of Listening, Reading, Writing and "
                                        "Speaking are free. Listening, Reading and Writing need no account. Speaking "
                                        "needs a free account because your recordings are saved to it. Further tests "
                                        "are part of a pass."),
         ("Is this the same as the real computer-delivered IELTS?", "The layout follows the computer-delivered exam, "
                                                                    "so the timing and screens feel familiar. TestDay "
                                                                    "is an independent practice site, not affiliated "
                                                                    "with the IELTS partners, and all its tests are "
                                                                    "original. Only an official test centre issues a "
                                                                    "real IELTS result."),
         ("Is the band score official?", "No. Listening and Reading bands are converted from your raw score with the "
                                         "usual approximate tables. Writing and Speaking bands from the AI examiner "
                                         "are practice estimates. Use them to see progress, not as a promise of your "
                                         "exam result.")],
        "Start a free test"),
    ("free", "uz"): _page(
        "ielts-mock-test-bepul",
        "IELTS mock test bepul: kompyuterda onlayn | TestDay",
        "Listening, Reading, Writing va Speaking bo'yicha bepul IELTS mock test. Har modulda 5 ta bepul test, "
        "javoblar izohi va AI band baholash.",
        "Bepul IELTS mock test (kompyuter formatida)",
        "IELTS ning to'rt bo'limini kompyuterda topshiriladigan imtihonga o'xshash ekranda mashq qiling: matn va "
        "savollar yonma-yon, teskari sanovchi taymer, savollar paneli va ajratib belgilash. Har modulda dastlabki "
        "beshta test bepul.",
        [("Listening va Reading", "Vaqt bilan test, natija darhol: taxminiy band, qism va savol turlari bo'yicha "
                                  "tahlil, har bir javobga izoh."),
         ("Writing", "Academic Task 1 va Task 2, so'z hisoblagich va avtomatik tekshiruvlar bilan. Bepul akkauntda AI "
                     "examiner to'rtta rasmiy mezon bo'yicha baho beradi va tuzatishlarni ko'rsatadi."),
         ("Speaking", "Uchala qism: yozib olingan examiner savol beradi, siz ovoz chiqarib javob berasiz. AI examiner "
                      "javoblaringizni tinglab, mashq bahosini beradi."),
         ("Istalgan qurilmada", "Hammasi brauzerda ishlaydi: kompyuterda ham, telefonda ham. Javoblaringiz brauzerda "
                                "saqlanadi, sahifani yangilasangiz ham yo'qolmaydi.")],
        [("Testlar rostdan ham bepulmi?", "Ha. Listening, Reading, Writing va Speaking modullarining har birida "
                                          "dastlabki beshta test bepul. Listening, Reading va Writing uchun akkaunt "
                                          "shart emas. Speaking uchun bepul akkaunt kerak, chunki yozuvlaringiz unda "
                                          "saqlanadi. Qolgan testlar obunaga kiradi."),
         ("Bu haqiqiy kompyuterdagi IELTS bilan bir xilmi?", "Ekran kompyuterda topshiriladigan imtihon tartibiga "
                                                             "o'xshash, shuning uchun vaqt va interfeys tanish "
                                                             "bo'ladi. TestDay mustaqil mashq sayti, IELTS "
                                                             "hamkorlariga aloqasi yo'q, barcha testlar original. "
                                                             "Rasmiy natijani faqat imtihon markazi beradi."),
         ("Band rasmiy hisoblanadimi?", "Yo'q. Listening va Reading bandi to'g'ri javoblar sonidan taxminiy jadval "
                                        "bo'yicha hisoblanadi. Writing va Speaking bo'yicha AI bahosi mashq uchun "
                                        "taxmin. Undan o'sishingizni kuzatish uchun foydalaning, imtihon natijasi "
                                        "kafolati sifatida emas.")],
        "Bepul testni boshlash"),
    ("free", "ru"): _page(
        "ielts-probnyj-test-onlajn-besplatno",
        "Пробный тест IELTS онлайн бесплатно | TestDay",
        "Бесплатный пробный IELTS на компьютере: Listening, Reading, Writing, Speaking. 5 бесплатных тестов на "
        "модуль, разбор ответов, оценка band от ИИ.",
        "Бесплатный пробный тест IELTS онлайн",
        "Отработайте четыре раздела IELTS на экране, похожем на компьютерный экзамен: текст и вопросы рядом, "
        "обратный отсчёт, панель вопросов и выделение текста. Первые пять тестов в каждом модуле бесплатны.",
        [("Listening и Reading", "Тест на время и мгновенная проверка: примерный band, разбор по частям и типам "
                                 "вопросов, объяснение к каждому ответу."),
         ("Writing", "Academic Task 1 и Task 2 со счётчиком слов и автоматическими проверками. С бесплатным "
                     "аккаунтом ИИ-экзаменатор оценивает по четырём критериям и показывает исправления."),
         ("Speaking", "Все три части: записанный экзаменатор задаёт вопросы, вы отвечаете вслух. ИИ-экзаменатор "
                      "слушает ответы и выставляет тренировочный band."),
         ("На любом устройстве", "Всё работает в браузере, на компьютере и на телефоне. Ответы сохраняются в "
                                 "браузере и не пропадут при обновлении страницы.")],
        [("Тесты действительно бесплатные?", "Да. Первые пять тестов в каждом из модулей Listening, Reading, Writing "
                                             "и Speaking бесплатны. Для Listening, Reading и Writing аккаунт не "
                                             "нужен. Для Speaking нужен бесплатный аккаунт: в нём сохраняются ваши "
                                             "записи. Остальные тесты входят в подписку."),
         ("Это то же самое, что настоящий IELTS на компьютере?", "Экран повторяет компьютерный формат, поэтому время "
                                                                 "и интерфейс будут знакомы. TestDay — независимый "
                                                                 "сайт для практики, не связан с партнёрами IELTS, "
                                                                 "все тесты оригинальные. Официальный результат "
                                                                 "выдаёт только экзаменационный центр."),
         ("Band — официальный балл?", "Нет. Band за Listening и Reading считается по числу верных ответов с помощью "
                                      "примерных таблиц. Оценка ИИ за Writing и Speaking — тренировочная. "
                                      "Используйте её, чтобы видеть прогресс, а не как гарантию результата на "
                                      "экзамене.")],
        "Начать бесплатный тест"),

    ("listening", "en"): _page(
        "ielts-listening-practice-test-with-answers",
        "IELTS Listening Practice Test with Answers | TestDay",
        "Take a timed IELTS Listening test on screen: 4 parts, 40 questions, audio plays once. See answers with "
        "explanations and your band estimate.",
        "IELTS Listening practice test with answers",
        "Take a full IELTS Listening test on screen: four parts, 40 questions, original recordings that play once. "
        "When you finish you see your band estimate, every answer with an explanation and the full transcript.",
        [("Test conditions", "A sound check first. In the timed test the recording plays once, straight through, and "
                             "you get two minutes at the end to check your answers."),
         ("Practice mode", "No time limit, with a full player: pause, jump back ten seconds, change speed and choose "
                           "a part. Use it to study the recordings you missed."),
         ("Every question type", "Form, note, table and flow-chart completion, map and plan labelling, multiple "
                                 "choice, choose two, and matching."),
         ("Feedback", "Your band estimate, results by part and by question type, and a transcript with each answer "
                      "highlighted and a Listen again button.")],
        [("How many questions are in an IELTS Listening test?", "Forty questions in four parts. Part 1 is an everyday "
                                                                "conversation, Part 2 a monologue, Part 3 a "
                                                                "discussion between students and Part 4 a "
                                                                "university-style lecture. TestDay's tests follow "
                                                                "the same pattern, and each correct answer is worth "
                                                                "one mark."),
         ("How is the Listening band score worked out?", "Your correct answers out of 40 are converted to a band. For "
                                                         "example, about 30 correct is band 7 and about 23 is band "
                                                         "6. Exact marks vary slightly between test versions, so "
                                                         "treat the table as approximate. The band calculator "
                                                         "does the conversion for you."),
         ("Does the audio play more than once?", "In the real test and in TestDay's timed mode it plays once. "
                                                 "Practice mode lets you replay and slow down the recording, which "
                                                 "is useful for learning from your mistakes.")],
        "Start the free Listening test"),
    ("listening", "uz"): _page(
        "ielts-listening-test-onlayn",
        "IELTS Listening test onlayn, javoblar bilan | TestDay",
        "IELTS Listening testini kompyuterda vaqt bilan yeching: 4 qism, 40 savol. Natijada javoblar izohi va "
        "taxminiy band ko'rsatiladi.",
        "IELTS Listening test onlayn",
        "To'liq IELTS Listening testini ekranda topshiring: to'rt qism, 40 savol, original audioyozuvlar bir marta "
        "eshittiriladi. Tugagach taxminiy band, har bir javobga izoh va to'liq matn (transkript) ko'rsatiladi.",
        [("Imtihon sharoiti", "Avval ovoz tekshiriladi. Vaqtli testda yozuv to'xtovsiz bir marta eshittiriladi, "
                              "oxirida javoblarni tekshirish uchun ikki daqiqa beriladi."),
         ("Mashq rejimi", "Vaqt cheklovisiz va to'liq pleyer bilan: pauza, 10 soniya orqaga, tezlikni o'zgartirish, "
                          "qismni tanlash. Xatolar ustida ishlash qulay."),
         ("Barcha savol turlari", "Forma, qaydlar, jadval va sxemani to'ldirish, xarita va reja bo'yicha belgilash, "
                                  "variant tanlash, ikkita javob tanlash, moslashtirish."),
         ("Natija tahlili", "Taxminiy band, qismlar va savol turlari bo'yicha natija, javoblar belgilangan "
                            "transkript va Listen again tugmasi.")],
        [("IELTS Listening testida nechta savol bor?", "To'rtta qismda 40 ta savol: kundalik suhbat, monolog, "
                                                       "talabalar muhokamasi va universitet ma'ruzasi. TestDay "
                                                       "testlari ham shunday tuzilgan, har bir to'g'ri javob bir "
                                                       "ball."),
         ("Listening bandi qanday hisoblanadi?", "40 tadan to'g'ri javoblar soni bandga aylantiriladi. Masalan, "
                                                 "taxminan 30 ta to'g'ri javob band 7, 23 ta band 6. Test "
                                                 "versiyasiga qarab chegara biroz farq qiladi, shuning uchun jadval "
                                                 "taxminiy. Band kalkulyatori hisobni o'zi bajaradi."),
         ("Audio bir martadan ortiq eshittiriladimi?", "Haqiqiy imtihonda va vaqtli rejimda bir marta. Mashq "
                                                       "rejimida yozuvni qayta eshitish va sekinlashtirish mumkin, "
                                                       "bu xatolardan o'rganishga yordam beradi.")],
        "Bepul Listening testini boshlash"),
    ("listening", "ru"): _page(
        "ielts-listening-test-onlajn",
        "IELTS Listening тест онлайн с ответами | TestDay",
        "Пройдите IELTS Listening на компьютере: 4 части, 40 вопросов, аудио звучит один раз. После теста — ответы "
        "с разбором и примерный band.",
        "IELTS Listening: тест онлайн с ответами",
        "Пройдите полный тест Listening на экране: четыре части, 40 вопросов, оригинальные записи звучат один раз. "
        "После теста вы увидите примерный band, каждый ответ с разбором и полную расшифровку записи.",
        [("Условия экзамена", "Сначала проверка звука. В тесте на время запись звучит один раз без остановок, а в "
                              "конце дают две минуты, чтобы проверить ответы."),
         ("Режим практики", "Без ограничения времени и с полным плеером: пауза, перемотка на 10 секунд назад, смена "
                            "скорости, выбор части. Так удобно разбирать ошибки."),
         ("Все типы вопросов", "Заполнение формы, заметок, таблицы и схемы, подписи к карте и плану, выбор ответа, "
                               "выбор двух ответов, соотнесение."),
         ("Обратная связь", "Примерный band, результаты по частям и по типам вопросов, расшифровка с выделенными "
                            "ответами и кнопкой Listen again.")],
        [("Сколько вопросов в IELTS Listening?", "Сорок вопросов в четырёх частях: бытовой диалог, монолог, "
                                                 "обсуждение студентов и университетская лекция. Тесты TestDay "
                                                 "устроены так же, каждый верный ответ даёт один балл."),
         ("Как считается band за Listening?", "Число верных ответов из 40 переводится в band. Например, около 30 "
                                              "верных — это band 7, около 23 — band 6. Точные границы немного "
                                              "отличаются в разных версиях теста, поэтому таблица примерная. "
                                              "Калькулятор баллов сделает перевод за вас."),
         ("Запись звучит один раз?", "В настоящем тесте и в режиме на время — один раз. В режиме практики запись "
                                     "можно переслушать и замедлить: это полезно, чтобы учиться на ошибках.")],
        "Начать бесплатный тест Listening"),

    ("reading", "en"): _page(
        "ielts-academic-reading-practice-test",
        "IELTS Academic Reading Practice Test Online | TestDay",
        "Practise IELTS Academic Reading on a computer: 3 passages, 40 questions, 60 minutes. Explained answers and "
        "an instant band estimate.",
        "IELTS Academic Reading practice test",
        "Practise Academic Reading under exam conditions: three passages, 40 questions and a 60-minute countdown. "
        "The screen is split so the passage and the questions stay side by side.",
        [("Built like the computer test", "A draggable divider, a question navigator at the bottom, flags to review "
                                          "questions, highlighting and notes. On a phone the two panes switch with "
                                          "one tap."),
         ("Every question type", "True/False/Not Given, Yes/No/Not Given, matching headings, matching information, "
                                 "completion tasks, multiple choice and more."),
         ("An explanation for every answer", "After the test you see which answers were right, why, and how you did "
                                             "by passage and by question type."),
         ("Practise one question type", "Pick the type you find hardest, for example Matching headings, and work "
                                        "only on that, with no timer.")],
        [("How long is the IELTS Academic Reading test?", "Sixty minutes for three passages and 40 questions. There "
                                                          "is no extra time to transfer answers, so manage your "
                                                          "time per passage. TestDay's timed mode warns you at 10 "
                                                          "and 5 minutes and submits your answers when time is up."),
         ("How do I convert my Reading score to a band?", "Count your correct answers out of 40 and look up the "
                                                          "band. About 30 correct is band 7 and about 23 is band 6 "
                                                          "in the Academic table. The band calculator on TestDay "
                                                          "does this for you."),
         ("Is this the Academic or the General Training test?", "TestDay has Academic Reading only. General Training "
                                                                "Reading uses different texts and a different score "
                                                                "table, so do not use these results for a General "
                                                                "Training target.")],
        "Start the free Reading test"),
    ("reading", "uz"): _page(
        "ielts-reading-test-onlayn-javoblar-bilan",
        "IELTS Reading test onlayn, javoblar bilan | TestDay",
        "Academic Reading testini kompyuterda yeching: 3 ta matn, 40 savol, 60 daqiqa. Har javob izohi va band "
        "baholash darhol ko'rsatiladi.",
        "IELTS Reading test onlayn (javoblar bilan)",
        "Academic Reading ni imtihon sharoitida mashq qiling: uchta matn, 40 savol va 60 daqiqalik taymer. Ekran "
        "ikkiga bo'lingan, matn va savollar doim yonma-yon.",
        [("Kompyuter testiga o'xshash", "Siljitiladigan ajratgich, pastda savollar paneli, tekshirish uchun "
                                        "belgilar, ajratib belgilash va qaydlar. Telefonda ikki panel bir bosishda "
                                        "almashadi."),
         ("Barcha savol turlari", "True/False/Not Given, Yes/No/Not Given, sarlavhalarni moslashtirish, ma'lumot "
                                  "qidirish, to'ldirish topshiriqlari, variant tanlash va boshqalar."),
         ("Har bir javobga izoh", "Test tugagach qaysi javoblar to'g'ri ekani, nima uchun, matnlar va savol turlari "
                                  "bo'yicha natijangiz ko'rinadi."),
         ("Bitta savol turi", "Eng qiyin turni tanlang, masalan Matching headings, va faqat shu ustida taymersiz "
                              "ishlang.")],
        [("IELTS Academic Reading necha daqiqa davom etadi?", "Uchta matn va 40 savol uchun 60 daqiqa. Javoblarni "
                                                              "ko'chirish uchun qo'shimcha vaqt yo'q, shuning uchun "
                                                              "har bir matnga vaqtni taqsimlang. TestDay vaqtli "
                                                              "rejimida 10 va 5 daqiqa qolganda ogohlantiradi, vaqt "
                                                              "tugaganda javoblarni topshiradi."),
         ("Reading ballini bandga qanday aylantiraman?", "40 tadan to'g'ri javoblar sonini sanang va jadvaldan "
                                                         "bandni toping. Academic jadvalida taxminan 30 ta to'g'ri "
                                                         "javob band 7, 23 ta band 6. TestDay band kalkulyatori "
                                                         "buni sizning o'rningizga qiladi."),
         ("Bu Academic yoki General Training testimi?", "TestDay da faqat Academic Reading bor. General Training "
                                                        "boshqa matnlar va boshqa jadval ishlatadi, shuning uchun "
                                                        "General Training maqsadingiz bo'lsa, bu natijalarga "
                                                        "tayanmang.")],
        "Bepul Reading testini boshlash"),
    ("reading", "ru"): _page(
        "ielts-reading-test-onlajn-s-otvetami",
        "IELTS Reading тест онлайн с ответами | TestDay",
        "Academic Reading на компьютере: 3 текста, 40 вопросов, 60 минут. Разбор каждого ответа и мгновенная оценка "
        "band.",
        "IELTS Reading: тест онлайн с ответами",
        "Тренируйте Academic Reading как на экзамене: три текста, 40 вопросов, 60 минут на обратном отсчёте. Экран "
        "разделён, поэтому текст и вопросы всегда рядом.",
        [("Как на компьютерном тесте", "Перетаскиваемый разделитель, панель вопросов внизу, пометки для проверки, "
                                       "выделение текста и заметки. На телефоне две панели переключаются одним "
                                       "касанием."),
         ("Все типы вопросов", "True/False/Not Given, Yes/No/Not Given, заголовки к абзацам, поиск информации, "
                               "заполнение пропусков, выбор ответа и другие."),
         ("Объяснение к каждому ответу", "После теста видно, какие ответы верны, почему, и как вы справились по "
                                         "текстам и типам вопросов."),
         ("Один тип вопросов", "Выберите самый сложный тип, например Matching headings, и тренируйтесь только на нём, "
                               "без таймера.")],
        [("Сколько длится IELTS Academic Reading?", "60 минут на три текста и 40 вопросов. Дополнительного времени "
                                                    "на перенос ответов нет, поэтому следите за временем по каждому "
                                                    "тексту. В режиме на время TestDay предупреждает за 10 и 5 минут "
                                                    "и сдаёт ответы по окончании."),
         ("Как перевести баллы Reading в band?", "Посчитайте верные ответы из 40 и найдите band в таблице. В таблице "
                                                 "Academic около 30 верных — band 7, около 23 — band 6. Калькулятор "
                                                 "баллов TestDay делает это за вас."),
         ("Это Academic или General Training?", "В TestDay только Academic Reading. General Training использует "
                                                "другие тексты и другую таблицу, поэтому не ориентируйтесь на эти "
                                                "результаты, если вам нужен General Training.")],
        "Начать бесплатный тест Reading"),

    ("calc", "en"): _page(
        "ielts-band-score-calculator",
        "IELTS Band Score Calculator (Listening & Reading) | TestDay",
        "Convert your Listening and Reading raw score (out of 40) to a band and work out your overall IELTS band "
        "with official rounding.",
        "IELTS band score calculator",
        "Enter your Listening and Reading raw scores (out of 40) and your Writing and Speaking bands. You get each "
        "band and your overall band, rounded the way the IELTS partners round it.",
        [("Listening and Reading", "Your correct answers out of 40 are converted with the standard tables below. They "
                                   "are approximate, because the marks for a band can differ slightly between test "
                                   "versions. The Reading table is for Academic Reading."),
         ("Writing and Speaking", "These are marked by examiners as bands, not as raw scores, so enter the bands you "
                                  "got or expect."),
         ("Overall band", "The four bands are averaged and rounded to the nearest half band. An average ending in "
                          ".25 rounds up to the next half band, and one ending in .75 rounds up to the next whole "
                          "band. For example 6.125 becomes 6.0, 6.25 becomes 6.5 and 6.75 becomes 7.0.")],
        [("How do I calculate my IELTS band score?", "Convert your Listening and Reading raw scores to bands with the "
                                                     "tables, add your Writing and Speaking bands, divide the four by "
                                                     "four, then round to the nearest half band. The calculator on "
                                                     "this page does all of it."),
         ("What is 27 out of 40 in IELTS Reading?", "In the Academic Reading table 27 correct answers is band 6.5. "
                                                    "In Listening it is also band 6.5, because 26 to 29 correct "
                                                    "answers give 6.5."),
         ("Is the calculator an official result?", "No. It is a planning tool based on the published conversion "
                                                   "tables. Only your official test report counts.")],
        "Practise with a free test"),
    ("calc", "uz"): _page(
        "ielts-band-score-hisoblash",
        "IELTS band score hisoblash: kalkulyator | TestDay",
        "Listening va Reading to'g'ri javoblar sonini bandga aylantiring va IELTS umumiy ballingizni rasmiy "
        "yaxlitlash qoidasi bilan hisoblang.",
        "IELTS band score kalkulyatori",
        "Listening va Reading bo'yicha to'g'ri javoblar sonini (40 tadan) hamda Writing va Speaking bandlarini "
        "kiriting. Har bir bo'lim bandi va IELTS qoidasi bo'yicha yaxlitlangan umumiy band ko'rsatiladi.",
        [("Listening va Reading", "40 tadan to'g'ri javoblar quyidagi standart jadvallar bo'yicha aylantiriladi. "
                                  "Jadvallar taxminiy: test versiyasiga qarab band chegarasi biroz farq qiladi. "
                                  "Reading jadvali Academic Reading uchun."),
         ("Writing va Speaking", "Bu bo'limlarni examinerlar ball emas, band bilan baholaydi, shuning uchun olgan "
                                 "yoki kutgan bandingizni kiriting."),
         ("Umumiy band", "To'rtta band qo'shilib, to'rtga bo'linadi va eng yaqin yarim bandga yaxlitlanadi. .25 bilan "
                         "tugaydigan o'rtacha keyingi yarim bandga, .75 bilan tugagani keyingi butun bandga "
                         "ko'tariladi. Masalan: 6,125 → 6,0; 6,25 → 6,5; 6,75 → 7,0.")],
        [("IELTS ballini qanday hisoblayman?", "Listening va Reading to'g'ri javoblarini jadval bo'yicha bandga "
                                               "aylantiring, Writing va Speaking bandlarini qo'shing, to'rtta sonni "
                                               "qo'shib to'rtga bo'ling va yarim bandgacha yaxlitlang. Sahifadagi "
                                               "kalkulyator buni o'zi bajaradi."),
         ("IELTS Reading da 40 dan 27 qancha?", "Academic Reading jadvalida 27 ta to'g'ri javob band 6,5. Listening "
                                                "da ham shunday: 26–29 oralig'i 6,5 beradi."),
         ("Kalkulyator rasmiy natijami?", "Yo'q, bu e'lon qilingan jadvallarga asoslangan rejalashtirish vositasi. "
                                          "Faqat rasmiy natija varaqasi hisobga olinadi.")],
        "Bepul test bilan mashq qiling"),
    ("calc", "ru"): _page(
        "ielts-kalkulyator-ballov",
        "Калькулятор баллов IELTS: Listening, Reading | TestDay",
        "Переведите число правильных ответов Listening и Reading в band и посчитайте общий балл IELTS по "
        "официальным правилам округления.",
        "Калькулятор баллов IELTS",
        "Введите число верных ответов Listening и Reading (из 40) и ваши баллы Writing и Speaking. Вы получите band "
        "за каждый раздел и общий band, округлённый по правилам IELTS.",
        [("Listening и Reading", "Верные ответы из 40 переводятся по стандартным таблицам ниже. Они примерные: "
                                 "границы band могут немного отличаться в разных версиях теста. Таблица Reading — "
                                 "для Academic Reading."),
         ("Writing и Speaking", "Эти разделы оценивают экзаменаторы сразу в band, а не в сырых баллах, поэтому "
                                "введите полученный или ожидаемый band."),
         ("Общий band", "Четыре band складываются, делятся на четыре и округляются до ближайшей половины. Среднее с "
                        "хвостом .25 округляется до следующей половины, с хвостом .75 — до следующего целого. "
                        "Например: 6,125 → 6,0; 6,25 → 6,5; 6,75 → 7,0.")],
        [("Как посчитать балл IELTS?", "Переведите верные ответы Listening и Reading в band по таблицам, добавьте band "
                                       "за Writing и Speaking, сложите четыре числа, разделите на четыре и "
                                       "округлите до половины. Калькулятор на странице делает всё это сам."),
         ("Что такое 27 из 40 в IELTS Reading?", "По таблице Academic Reading 27 верных ответов — это band 6,5. В "
                                                 "Listening тоже: диапазон 26–29 даёт 6,5."),
         ("Это официальный результат?", "Нет, это инструмент для планирования на основе опубликованных таблиц. "
                                        "Считается только официальный отчёт о результатах.")],
        "Потренироваться на бесплатном тесте"),

    ("writing", "en"): _page(
        "ielts-writing-task-2-checker",
        "IELTS Writing Task 2 Checker with Band Estimate | TestDay",
        "Write your essay and get an AI band estimate on the four official criteria, with corrections. A practice "
        "estimate, not an official score.",
        "IELTS Writing Task 2 checker",
        "Write an Academic Writing task on screen with a word counter, then ask the AI examiner to mark it. It scores "
        "the four official criteria and shows corrections, so you can see what to fix in your next attempt.",
        [("Task 1 and Task 2", "Academic Task 1 (line graph, bar chart, process, pie charts, table) and Task 2 "
                               "essays, with the timing of the real paper."),
         ("Four criteria", "Task Achievement or Response, Coherence and Cohesion, Lexical Resource, and Grammatical "
                           "Range and Accuracy, each with a band."),
         ("Automatic checks", "Length, overview, position, paragraphing, linking and register are checked straight "
                              "away, and model answers let you compare your own."),
         ("A free account", "The AI examiner needs you to sign in, and it has a monthly limit.")],
        [("Is the AI band the same as an examiner's band?", "No. It is a practice estimate based on the public band "
                                                            "descriptors. Real examiners can differ by half a band "
                                                            "or more. Use it to spot patterns, such as weak linking "
                                                            "or limited vocabulary, and to track progress over "
                                                            "several essays."),
         ("How many words do I need?", "At least 150 words for Task 1 and 250 for Task 2. Shorter answers lose marks. "
                                       "The word counter on screen shows your total as you type."),
         ("Is it free?", "You can write the free tests without an account. The AI examiner needs a free account and "
                         "has a monthly limit.")],
        "Start the free Writing test"),
    ("writing", "uz"): _page(
        "ielts-writing-tekshirish",
        "IELTS Writing tekshirish: AI band baholash | TestDay",
        "Essengizni yozing va to'rt rasmiy mezon bo'yicha AI band baholash va tuzatishlarni oling. Bu mashq bahosi, "
        "rasmiy natija emas.",
        "IELTS Writing ni AI bilan tekshirish",
        "Academic Writing topshirig'ini ekranda so'z hisoblagich bilan yozing, so'ng AI examinerdan tekshirishni "
        "so'rang. U ishingizni to'rtta mezon bo'yicha baholaydi va tuzatishlarni ko'rsatadi, shunda keyingi "
        "urinishda nimani o'zgartirishni bilasiz.",
        [("Task 1 va Task 2", "Academic Task 1 (chiziqli grafik, ustunli diagramma, jarayon, doira diagrammalar, "
                              "jadval) va Task 2 esselari, imtihondagi vaqt bilan."),
         ("To'rtta mezon", "Task Achievement yoki Response, Coherence and Cohesion, Lexical Resource, Grammatical "
                           "Range and Accuracy, har biri uchun band."),
         ("Avtomatik tekshiruvlar", "Hajm, umumiy tavsif, pozitsiya, xatboshilar, bog'lovchilar va uslub darhol "
                                    "tekshiriladi, o'z ishingizni namunaviy javoblar bilan solishtirishingiz "
                                    "mumkin."),
         ("Bepul akkaunt", "AI examiner uchun akkauntga kirish kerak, uning oylik limiti bor.")],
        [("AI bandi examiner bandi bilan bir xilmi?", "Yo'q. Bu ommaviy band tavsiflariga asoslangan mashq bahosi. "
                                                      "Haqiqiy examinerlar yarim band yoki undan ko'proq farq "
                                                      "qilishi mumkin. Undan takrorlanadigan kamchiliklarni, "
                                                      "masalan bog'lovchilar yoki lug'at kamligini topish va "
                                                      "bir nechta essedagi o'sishni kuzatish uchun foydalaning."),
         ("Nechta so'z yozish kerak?", "Task 1 da kamida 150, Task 2 da kamida 250 so'z. Qisqa javoblar uchun ball "
                                       "kamaytiriladi. Ekrandagi so'z hisoblagich yozayotganda hajmni ko'rsatadi."),
         ("Bu bepulmi?", "Bepul testlarni akkauntsiz yozish mumkin. AI examiner uchun bepul akkaunt kerak va uning "
                         "oylik limiti bor.")],
        "Bepul Writing testini boshlash"),
    ("writing", "ru"): _page(
        "ielts-writing-proverka-esse-onlajn",
        "Проверка IELTS Writing онлайн: оценка band | TestDay",
        "Напишите эссе и получите оценку band от ИИ по четырём критериям IELTS с исправлениями. Это тренировочная "
        "оценка, не официальная.",
        "Проверка эссе IELTS Writing онлайн",
        "Напишите задание Academic Writing на экране со счётчиком слов, затем попросите ИИ-экзаменатора проверить "
        "его. Он оценит работу по четырём критериям и покажет исправления, чтобы вы поняли, что менять в следующей "
        "попытке.",
        [("Task 1 и Task 2", "Academic Task 1 (линейный график, столбчатая диаграмма, процесс, круговые диаграммы, "
                             "таблица) и эссе Task 2 с таким же временем, как на экзамене."),
         ("Четыре критерия", "Task Achievement или Response, Coherence and Cohesion, Lexical Resource, Grammatical "
                             "Range and Accuracy, по каждому — band."),
         ("Автоматические проверки", "Объём, обзор, позиция, абзацы, связки и стиль проверяются сразу, а образцы "
                                     "ответов можно сравнить со своим."),
         ("Бесплатный аккаунт", "ИИ-экзаменатору нужен вход в аккаунт, и у него есть месячный лимит.")],
        [("Band от ИИ равен band экзаменатора?", "Нет. Это тренировочная оценка по публичным дескрипторам. Реальные "
                                                 "экзаменаторы могут отличаться на полбалла и больше. Используйте "
                                                 "её, чтобы замечать повторяющиеся проблемы, например слабые связки "
                                                 "или бедный словарь, и следить за прогрессом по нескольким эссе."),
         ("Сколько слов нужно писать?", "Не менее 150 слов в Task 1 и 250 в Task 2. За меньший объём баллы снижают. "
                                        "Счётчик слов на экране показывает объём по мере набора."),
         ("Это бесплатно?", "Писать бесплатные тесты можно без аккаунта. Для ИИ-экзаменатора нужен бесплатный "
                            "аккаунт, и у него есть месячный лимит.")],
        "Начать бесплатный тест Writing"),

    ("speaking", "en"): _page(
        "ielts-speaking-practice-ai-examiner",
        "IELTS Speaking Practice with an AI Examiner | TestDay",
        "Practise all 3 parts of IELTS Speaking out loud and get an AI band estimate for fluency, vocabulary, "
        "grammar and pronunciation.",
        "IELTS Speaking practice with an AI examiner",
        "Sit a full Speaking test in your browser. A recorded examiner asks the questions, you answer out loud, and "
        "the AI examiner listens, adapts the questions to how you are doing and gives a practice band.",
        [("All three parts", "Part 1 interview, Part 2 cue card with one minute to prepare and two minutes to speak, "
                             "and Part 3 discussion."),
         ("An examiner that adapts", "The number of Part 1 and Part 3 questions depends on how you are doing, so a "
                                     "strong candidate is asked more. Part 2 is always asked."),
         ("Four criteria", "Fluency and Coherence, Lexical Resource, Grammatical Range and Accuracy, and "
                           "Pronunciation, with notes on each."),
         ("Private recordings", "A microphone check comes first. Your recordings are saved to your account and only "
                                "you can listen back.")],
        [("How does IELTS Speaking work?", "It is an 11 to 14 minute interview with an examiner in three parts: an "
                                           "introduction and familiar topics, a talk of up to two minutes on a cue "
                                           "card, and a discussion of more abstract questions. TestDay follows the "
                                           "same three parts."),
         ("Can an AI examiner give a real band?", "It gives a practice estimate from your recorded answers, not an "
                                                  "official score. An accent is not penalised, only how easy you are "
                                                  "to understand. Use the estimate to find weak areas and to see "
                                                  "change over several attempts."),
         ("Do I need an account?", "Yes, a free one, because your recordings are saved to it. The AI examiner has a "
                                   "monthly limit.")],
        "Start the free Speaking test"),
    ("speaking", "uz"): _page(
        "ielts-speaking-mock-bepul",
        "IELTS Speaking mock bepul: AI bilan mashq | TestDay",
        "IELTS Speaking ning 3 qismini ovoz chiqarib mashq qiling va ravonlik, lug'at, grammatika va talaffuz "
        "bo'yicha AI band baholash oling.",
        "IELTS Speaking mock (AI bilan)",
        "To'liq Speaking testini brauzerda topshiring. Yozib olingan examiner savol beradi, siz ovoz chiqarib javob "
        "berasiz, AI examiner esa tinglaydi, savollarni javoblaringizga moslaydi va mashq bahosini beradi.",
        [("Uchala qism", "Part 1 — suhbat, Part 2 — mavzu kartochkasi: bir daqiqa tayyorlanish va ikki daqiqa "
                         "gapirish, Part 3 — muhokama."),
         ("Moslashuvchan examiner", "Part 1 va Part 3 dagi savollar soni javoblaringizga bog'liq: kuchli nomzodga "
                                    "ko'proq savol beriladi. Part 2 har doim bor."),
         ("To'rtta mezon", "Fluency and Coherence, Lexical Resource, Grammatical Range and Accuracy va "
                           "Pronunciation, har biri bo'yicha izoh bilan."),
         ("Shaxsiy yozuvlar", "Avval mikrofon tekshiriladi. Yozuvlar akkauntingizda saqlanadi, ularni faqat siz "
                              "eshitasiz.")],
        [("IELTS Speaking qanday o'tadi?", "Bu examiner bilan 11–14 daqiqalik suhbat, uch qismdan iborat: tanishuv va "
                                           "tanish mavzular, kartochka bo'yicha ikki daqiqagacha hikoya va mavhum "
                                           "savollar muhokamasi. TestDay shu uch qismni takrorlaydi."),
         ("AI haqiqiy band bera oladimi?", "U yozuvlaringiz asosida mashq bahosini beradi, rasmiy ball emas. Aksent "
                                           "bahoni tushirmaydi, nutqning tushunarliligi muhim. Bahodan zaif "
                                           "joylarni topish va bir necha urinish bo'yicha o'zgarishni kuzatish "
                                           "uchun foydalaning."),
         ("Akkaunt kerakmi?", "Ha, bepul akkaunt, chunki yozuvlaringiz unda saqlanadi. AI examinerning oylik limiti "
                              "bor.")],
        "Bepul Speaking testini boshlash"),
    ("speaking", "ru"): _page(
        "ielts-speaking-trenazher-onlajn",
        "IELTS Speaking тренажёр онлайн с оценкой ИИ | TestDay",
        "Отработайте все 3 части IELTS Speaking вслух и получите оценку band от ИИ: беглость, лексика, грамматика, "
        "произношение.",
        "IELTS Speaking: тренажёр онлайн",
        "Пройдите полный тест Speaking в браузере. Записанный экзаменатор задаёт вопросы, вы отвечаете вслух, а "
        "ИИ-экзаменатор слушает, подстраивает вопросы под ваши ответы и выставляет тренировочный band.",
        [("Все три части", "Part 1 — интервью, Part 2 — карточка с темой: минута на подготовку и две минуты на "
                           "рассказ, Part 3 — обсуждение."),
         ("Адаптивный экзаменатор", "Число вопросов в Part 1 и Part 3 зависит от того, как вы отвечаете: сильному "
                                    "кандидату задают больше. Part 2 есть всегда."),
         ("Четыре критерия", "Fluency and Coherence, Lexical Resource, Grammatical Range and Accuracy и "
                             "Pronunciation, с комментарием по каждому."),
         ("Личные записи", "Сначала проверка микрофона. Записи сохраняются в вашем аккаунте, слушать их можете "
                           "только вы.")],
        [("Как проходит IELTS Speaking?", "Это интервью с экзаменатором на 11–14 минут из трёх частей: знакомство и "
                                          "привычные темы, рассказ до двух минут по карточке и обсуждение "
                                          "абстрактных вопросов. TestDay повторяет эти три части."),
         ("Может ли ИИ поставить настоящий band?", "Он даёт тренировочную оценку по вашим записям, а не официальный "
                                                   "балл. Акцент не снижает оценку, важна понятность речи. "
                                                   "Используйте оценку, чтобы найти слабые места и следить за "
                                                   "изменениями по нескольким попыткам."),
         ("Нужен ли аккаунт?", "Да, бесплатный: в нём сохраняются ваши записи. У ИИ-экзаменатора есть месячный "
                               "лимит.")],
        "Начать бесплатный тест Speaking"),
}

PAGES = [dict(CONTENT[(topic, lang)], topic=topic, lang=lang) for topic in TOPICS for lang in LANGS]
BY_PATH = {(p["lang"], p["slug"]): p for p in PAGES}


def find(lang, slug):
    return BY_PATH.get((lang, slug))


def path_of(page):
    return f"/{page['lang']}/{page['slug']}"


def path_for(topic, lang):
    return path_of(CONTENT[(topic, lang)] | {"lang": lang})


def landing_path(lang):
    """Where /en, /uz and /ru lead: the free practice page of that language."""
    return path_for("free", lang) if lang in LANGS else None


# --------------------------------------------------------------------------
# Score tables and rounding (the calculator page and its script use these)
# --------------------------------------------------------------------------

def band_ranges(table):
    """[(first, last, band)] from a table of (lowest raw score, band), highest first, down to band 2.5."""
    out, upper = [], 40
    for minimum, band in table:
        if band < 2.5:
            break
        out.append((minimum, upper, band))
        upper = minimum - 1
    return out


def overall_band(listening, reading, writing, speaking):
    """The four bands averaged and rounded to the nearest half band: .25 up to .5, .75 up to the next whole band."""
    eighths = round((listening + reading + writing + speaking) * 2)  # each band in half-bands; average = sum / 8
    whole, rest = divmod(eighths, 8)
    return whole + (0.0 if rest < 2 else 0.5 if rest < 6 else 1.0)


def _num(value):
    return f"{value:.1f}"


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def _e(text):
    return html.escape(str(text), quote=True)


def _table(ui, caption, table):
    rows = "".join(
        f"<tr><td>{first if first == last else f'{first}–{last}'}</td><td>{_num(band)}</td></tr>"
        for first, last, band in band_ranges(table))
    rows += f"<tr><td>{_e(ui['low'])}</td><td>&lt; 2.5</td></tr>"
    return (f'<table class="ld-table"><caption>{_e(caption)}</caption>'
            f'<thead><tr><th scope="col">{_e(ui["col_raw"])}</th><th scope="col">{_e(ui["col_band"])}</th></tr></thead>'
            f"<tbody>{rows}</tbody></table>")


def _band_options(ui):
    options = "".join(f'<option value="{v / 2:.1f}">{v / 2:.1f}</option>' for v in range(2, 19))
    return f'<option value="">{_e(ui["choose"])}</option>{options}'


def _calculator(ui):
    listening = json.dumps([[m, b] for m, b in scoring.LISTENING_BANDS])
    reading = json.dumps([[m, b] for m, b in scoring.ACADEMIC_READING_BANDS])
    return f"""
    <section class="ld-calc-wrap" aria-labelledby="calc-h">
      <h2 id="calc-h">{_e(ui['calc_title'])}</h2>
      <form class="ld-calc" data-calc data-listening="{_e(listening)}" data-reading="{_e(reading)}">
        <label>{_e(ui['listening'])}<input type="number" name="l" min="0" max="40" step="1" inputmode="numeric"></label>
        <label>{_e(ui['reading'])}<input type="number" name="r" min="0" max="40" step="1" inputmode="numeric"></label>
        <label>{_e(ui['writing'])}<select name="w">{_band_options(ui)}</select></label>
        <label>{_e(ui['speaking'])}<select name="s">{_band_options(ui)}</select></label>
        <dl class="ld-result" aria-live="polite">
          <div><dt>{_e(ui['res_l'])}</dt><dd><output data-out="l">–</output></dd></div>
          <div><dt>{_e(ui['res_r'])}</dt><dd><output data-out="r">–</output></dd></div>
          <div class="ld-overall"><dt>{_e(ui['res_o'])}</dt><dd><output data-out="o">–</output></dd></div>
        </dl>
      </form>
      <div class="ld-tables">
        {_table(ui, ui['table_l'], scoring.LISTENING_BANDS)}
        {_table(ui, ui['table_r'], scoring.ACADEMIC_READING_BANDS)}
      </div>
      <p class="ld-small">{_e(ui['approx'])}</p>
    </section>"""


def _json_ld(data):
    """Structured data as JSON that cannot end its own <script> element early."""
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def _head(page, base, versioned):
    lang, url = page["lang"], f"{base}{path_of(page)}"
    alternates = "".join(
        f'<link rel="alternate" hreflang="{l}" href="{_e(base + path_for(page["topic"], l))}">\n  ' for l in LANGS)
    alternates += f'<link rel="alternate" hreflang="x-default" href="{_e(base + path_for(page["topic"], "en"))}">'
    ld = {"@context": "https://schema.org", "@type": "WebPage", "name": page["title"], "url": url,
          "description": page["description"], "inLanguage": lang,
          "isPartOf": {"@type": "WebSite", "name": "TestDay", "url": base + "/"}}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "TestDay", "item": base + "/"},
        {"@type": "ListItem", "position": 2, "name": page["h1"], "item": url}]}
    ld_json, crumbs_json = _json_ld(ld), _json_ld(crumbs)
    return f"""<meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{_e(page['title'])}</title>
  <meta name="description" content="{_e(page['description'])}">
  <meta name="theme-color" content="#0f1a30">
  <link rel="canonical" href="{_e(url)}">
  {alternates}
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="TestDay">
  <meta property="og:title" content="{_e(page['title'])}">
  <meta property="og:description" content="{_e(page['description'])}">
  <meta property="og:url" content="{_e(url)}">
  <meta property="og:locale" content="{LOCALES[lang]}">
  <meta property="og:image" content="{_e(base)}/img/og.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
  <link rel="stylesheet" href="/{_e(versioned('css/portal.css'))}">
  <link rel="stylesheet" href="/{_e(versioned('css/landing.css'))}">
  <script type="application/ld+json">{ld_json}</script>
  <script type="application/ld+json">{crumbs_json}</script>"""


def render(page, base, versioned):
    """The full HTML page. `base` is the public address of the site, `versioned` adds the cache hash to an asset."""
    lang, topic = page["lang"], page["topic"]
    ui = UI[lang]
    nav = (f'<a href="/#/">{_e(ui["free"])}</a>'
           f'<a href="{path_for("calc", lang)}">{_e(ui["calc"])}</a>'
           f'<a href="/#/pricing">{_e(ui["price"])}</a>')
    points = "".join(f"<li><h3>{_e(h)}</h3><p>{_e(t)}</p></li>" for h, t in page["points"])
    faq = "".join(f"<div class=\"ld-q\"><h3>{_e(q)}</h3><p>{_e(a)}</p></div>" for q, a in page["faq"])
    switch = " · ".join(
        f'<span aria-current="page">{_e(LANG_NAMES[l])}</span>' if l == lang else
        f'<a href="{path_for(topic, l)}" hreflang="{l}" lang="{l}">{_e(LANG_NAMES[l])}</a>' for l in LANGS)
    more = "".join(
        f'<li><a href="{path_for(t, lang)}">{_e(CONTENT[(t, lang)]["h1"])}</a></li>' for t in TOPICS if t != topic)
    note = f'<p class="ld-note">{_e(ui["note"])}</p>' if ui["note"] else ""
    calc = _calculator(ui) if topic == "calc" else ""
    script = f'<script src="/{_e(versioned("js/seo-calc.js"))}" defer></script>' if topic == "calc" else ""
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  {_head(page, base, versioned)}
</head>
<body class="theme-default text-regular ld-body">
  <header class="ld-head">
    <a class="ld-brand" href="/#/"><img src="/img/logo-mark.svg" alt="" width="28" height="28"><span>TestDay</span></a>
    <nav class="ld-nav" aria-label="Main">{nav}</nav>
  </header>
  <main class="ld-main">
    <article>
      <h1>{_e(page['h1'])}</h1>
      <p class="ld-lead">{_e(page['intro'])}</p>
      <p><a class="btn-primary ld-cta" href="{CTA_TARGET[topic]}">{_e(page['cta'])}</a></p>
      {note}
      {calc}
      <section aria-labelledby="what-h">
        <h2 id="what-h">{_e(ui['how'] if topic == 'calc' else ui['what'])}</h2>
        <ul class="ld-points">{points}</ul>
      </section>
      <section aria-labelledby="faq-h">
        <h2 id="faq-h">{_e(ui['faq'])}</h2>
        {faq}
      </section>
      <p><a class="btn-secondary ld-cta" href="{CTA_TARGET[topic]}">{_e(page['cta'])}</a></p>
      <section aria-labelledby="more-h">
        <h2 id="more-h">{_e(ui['more'])}</h2>
        <ul class="ld-more">{more}</ul>
      </section>
    </article>
  </main>
  <footer class="ld-foot">
    <p>{_e(ui['langs'])}: {switch}</p>
    <p><a href="/terms">{_e(ui['terms'])}</a> · <a href="/privacy">{_e(ui['privacy'])}</a> · <a href="/refunds">{_e(ui['refunds'])}</a> · <a href="/about">{_e(ui['about'])}</a></p>
    <p class="ld-small">{_e(ui['disclaimer'])}</p>
  </footer>
  {script}
</body>
</html>
"""


def sitemap(base):
    """sitemap.xml: the home page and every page here, each with links to its other-language versions."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
           f'  <url><loc>{html.escape(base)}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>']
    for page in PAGES:
        alternates = "".join(
            f'<xhtml:link rel="alternate" hreflang="{l}" href="{html.escape(base + path_for(page["topic"], l))}"/>'
            for l in LANGS)
        alternates += (f'<xhtml:link rel="alternate" hreflang="x-default" '
                       f'href="{html.escape(base + path_for(page["topic"], "en"))}"/>')
        out.append(f'  <url><loc>{html.escape(base + path_of(page))}</loc>{alternates}'
                   f'<changefreq>monthly</changefreq><priority>0.8</priority></url>')
    out.append("</urlset>")
    return "\n".join(out) + "\n"
