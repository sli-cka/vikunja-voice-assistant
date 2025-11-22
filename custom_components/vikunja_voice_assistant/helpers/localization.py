"""Localization utilities for Vikunja voice assistant responses.

Default language: English (en). All existing tests rely on English; when
`hass.config.language` is another supported language, responses will be
translated while preserving the same data-driven structure.

Only a small controlled vocabulary is translated here (status + metadata
phrases). Date / repeat phrases leverage the existing logic; if extended
natural language localization is desired in the future those functions can
accept a language parameter as well.
"""

from __future__ import annotations

from typing import Dict, Any
import json
import os

SUPPORTED_LANGS = {
    "en",
    "fr",
    "es",
    "pt",
    "ru",
    "hi",
    "zh-Hans",
    "ar",
    "bn",
    "id",
    "de",
}


def get_language(hass) -> str:  # noqa: D401
    lang = getattr(getattr(hass, "config", None), "language", "en") or "en"
    return lang if lang in SUPPORTED_LANGS else "en"


# Base message keys
_BASE: Dict[str, Dict[str, str]] = {
    "success_added": {
        "en": "Successfully added task: {title}",
        "fr": "Tâche ajoutée : {title}",
        "es": "Tarea añadida: {title}",
        "pt": "Tarefa adicionada: {title}",
        "ru": "Задача добавлена: {title}",
        "hi": "कार्य जोड़ा गया: {title}",
        "zh-Hans": "任务已添加：{title}",
        "ar": "تمت إضافة المهمة: {title}",
        "bn": "টাস্ক যোগ করা হয়েছে: {title}",
        "id": "Tugas ditambahkan: {title}",
        "de": "Aufgabe erfolgreich hinzugefügt: {title}",
    },
    "config_error": {
        "en": "Configuration error. Please check your Vikunja and Home Assistant AI settings.",
        "fr": "Erreur de configuration. Vérifiez les paramètres Vikunja et de l'IA Home Assistant.",
        "es": "Error de configuración. Verifica la configuración de Vikunja y de la IA de Home Assistant.",
        "pt": "Erro de configuração. Verifique as configurações do Vikunja e da IA do Home Assistant.",
        "ru": "Ошибка конфигурации. Проверьте настройки Vikunja и ИИ Home Assistant.",
        "hi": "कॉन्फ़िगरेशन त्रुटि। कृपया Vikunja और Home Assistant AI सेटिंग्स जाँचें।",
        "zh-Hans": "配置错误。请检查 Vikunja 和 Home Assistant AI 设置。",
        "ar": "خطأ في الإعدادات. يرجى التحقق من إعدادات Vikunja وذكاء Home Assistant الاصطناعي.",
        "bn": "কনফিগারেশন ত্রুটি। Vikunja এবং Home Assistant AI সেটিংস পরীক্ষা করুন।",
        "id": "Kesalahan konfigurasi. Periksa pengaturan Vikunja dan AI Home Assistant.",
        "de": "Konfigurationsfehler. Bitte überprüfen Sie Ihre Vikunja- und Home-Assistant-AI-Einstellungen.",
    },
    "llm_conn_error": {
        "en": "Sorry, I couldn't process your task because the AI service was unavailable. Please try again later.",
        "fr": "Désolé, impossible de traiter la tâche car le service d'IA est indisponible. Réessayez plus tard.",
        "es": "No se pudo procesar la tarea porque el servicio de IA no estaba disponible. Inténtalo más tarde.",
        "pt": "Não foi possível processar a tarefa porque o serviço de IA estava indisponível. Tente novamente mais tarde.",
        "ru": "Не удалось обработать задачу, так как сервис ИИ недоступен. Попробуйте позже.",
        "hi": "AI सेवा उपलब्ध नहीं होने के कारण कार्य संसाधित नहीं हो सका। बाद में पुनः प्रयास करें।",
        "zh-Hans": "由于 AI 服务不可用，无法处理您的任务。请稍后再试。",
        "ar": "تعذّر معالجة المهمة لأن خدمة الذكاء الاصطناعي غير متاحة. أعد المحاولة لاحقًا.",
        "bn": "AI সেবা অনুপলব্ধ থাকায় টাস্ক প্রক্রিয়া করা যায়নি। পরে আবার চেষ্টা করুন।",
        "id": "Tidak dapat memproses tugas karena layanan AI tidak tersedia. Coba lagi nanti.",
        "de": "Entschuldigung, der KI-Dienst war nicht verfügbar. Bitte versuchen Sie es später erneut.",
    },
    "llm_process_error": {
        "en": "Sorry, I couldn't process your task. Please try again.",
        "fr": "Impossible de traiter la tâche. Réessayez.",
        "es": "No se pudo procesar la tarea. Inténtalo de nuevo.",
        "pt": "Não foi possível processar a tarefa. Tente novamente.",
        "ru": "Не удалось обработать задачу. Попробуйте ещё раз.",
        "hi": "कार्य संसाधित नहीं हो सका। पुनः प्रयास करें।",
        "zh-Hans": "无法处理您的任务。请再试一次。",
        "ar": "تعذر معالجة المهمة. أعد المحاولة.",
        "bn": "টাস্ক প্রক্রিয়া করা যায়নি। আবার চেষ্টা করুন।",
        "id": "Tidak dapat memproses tugas. Coba lagi.",
        "de": "Entschuldigung, ich konnte Ihre Aufgabe nicht verarbeiten. Bitte versuchen Sie es erneut.",
    },
    "llm_missing_title": {
        "en": "Sorry, I couldn't understand what task you wanted to create. Please try again.",
        "fr": "Impossible de comprendre la tâche à créer. Réessayez.",
        "es": "No pude entender qué tarea querías crear. Inténtalo de nuevo.",
        "pt": "Não entendi qual tarefa queria criar. Tente novamente.",
        "ru": "Не удалось понять, какую задачу создать. Повторите попытку.",
        "hi": "कौन सा कार्य बनाना है समझ नहीं सका। पुनः प्रयास करें।",
        "zh-Hans": "未能理解您要创建的任务。请重试。",
        "ar": "لم أفهم المهمة التي تريد إنشاءها. أعد المحاولة.",
        "bn": "কি টাস্ক তৈরি করতে চেয়েছেন বুঝতে পারিনি। আবার চেষ্টা করুন।",
        "id": "Saya tidak memahami tugas yang ingin dibuat. Coba lagi.",
        "de": "Entschuldigung, ich konnte nicht verstehen, welche Aufgabe Sie erstellen wollten. Bitte versuchen Sie es erneut.",
    },
    "vikunja_add_error": {
        "en": "Sorry, I couldn't add the task to Vikunja. Please check your Vikunja connection.",
        "fr": "Impossible d'ajouter la tâche à Vikunja. Vérifiez la connexion.",
        "es": "No se pudo añadir la tarea a Vikunja. Verifica la conexión.",
        "pt": "Não foi possível adicionar a tarefa ao Vikunja. Verifique a conexão.",
        "ru": "Не удалось добавить задачу в Vikunja. Проверьте подключение.",
        "hi": "Vikunja में कार्य जोड़ने में विफल। कनेक्शन जाँचें।",
        "zh-Hans": "无法将任务添加到 Vikunja。请检查连接。",
        "ar": "تعذر إضافة المهمة إلى Vikunja. تحقق من الاتصال.",
        "bn": "Vikunja তে টাস্ক যোগ করা যায়নি। সংযোগ পরীক্ষা করুন।",
        "id": "Tidak dapat menambahkan tugas ke Vikunja. Periksa koneksi.",
        "de": "Entschuldigung, ich konnte die Aufgabe nicht zu Vikunja hinzufügen. Bitte überprüfen Sie Ihre Vikunja-Verbindung.",
    },
    "json_parse_error": {
        "en": "Sorry, there was an error processing your task. Please try again.",
        "fr": "Erreur lors du traitement de la tâche. Réessayez.",
        "es": "Error al procesar la tarea. Inténtalo de nuevo.",
        "pt": "Erro ao processar a tarefa. Tente novamente.",
        "ru": "Ошибка при обработке задачи. Попробуйте ещё раз.",
        "hi": "कार्य संसाधित करते समय एक त्रुटि हुई। पुनः प्रयास करें।",
        "zh-Hans": "处理您的任务时出错。请再试一次。",
        "ar": "حدث خطأ أثناء معالجة المهمة. أعد المحاولة.",
        "bn": "টাস্ক প্রক্রিয়া করতে গিয়ে ত্রুটি। আবার চেষ্টা করুন।",
        "id": "Terjadi kesalahan saat memproses tugas. Coba lagi.",
        "de": "Entschuldigung, es gab einen Fehler bei der Verarbeitung Ihrer Aufgabe. Bitte versuchen Sie es erneut.",
    },
    "unexpected_error": {
        "en": "Sorry, an unexpected error occurred. Please try again.",
        "fr": "Une erreur inattendue est survenue. Réessayez.",
        "es": "Ocurrió un error inesperado. Inténtalo de nuevo.",
        "pt": "Ocorreu um erro inesperado. Tente novamente.",
        "ru": "Произошла непредвиденная ошибка. Повторите попытку.",
        "hi": "अप्रत्याशित त्रुटि हुई। पुनः प्रयास करें।",
        "zh-Hans": "发生意外错误。请再试一次。",
        "ar": "حدث خطأ غير متوقع. أعد المحاولة.",
        "bn": "অপ্রত্যাশিত ত্রুটি ঘটেছে। আবার চেষ্টা করুন।",
        "id": "Terjadi kesalahan tak terduga. Coba lagi.",
        "de": "Entschuldigung, ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es erneut.",
    },
    "auth_error": {
        "en": "Authentication failed. Please update your Vikunja API token.",
        "fr": "Échec de l'authentification. Veuillez mettre à jour votre jeton API Vikunja.",
        "es": "Error de autenticación. Actualiza tu token API de Vikunja.",
        "pt": "Falha na autenticação. Atualize seu token API do Vikunja.",
        "ru": "Ошибка аутентификации. Обновите токен API Vikunja.",
        "hi": "प्रमाणीकरण विफल। कृपया अपना Vikunja API टोकन अपडेट करें।",
        "zh-Hans": "身份验证失败。请更新您的 Vikunja API 令牌。",
        "ar": "فشلت المصادقة. يرجى تحديث رمز API الخاص بـ Vikunja.",
        "bn": "প্রমাণীকরণ ব্যর্থ। আপনার Vikunja API টোকেন আপডেট করুন।",
        "id": "Autentikasi gagal. Perbarui token API Vikunja Anda.",
        "de": "Authentifizierung fehlgeschlagen. Bitte aktualisieren Sie Ihr Vikunja API-Token.",
    },
}


_DETAIL_TOKENS: Dict[str, Dict[str, str]] = {
    "project": {
        "en": "project '{name}'",
        "fr": "projet '{name}'",
        "es": "proyecto '{name}'",
        "pt": "projeto '{name}'",
        "ru": "проект '{name}'",
        "hi": "प्रोजेक्ट '{name}'",
        "zh-Hans": "项目 '{name}'",
        "ar": "المشروع '{name}'",
        "bn": "প্রজেক্ট '{name}'",
        "id": "proyek '{name}'",
        "de": "Projekt '{name}'",
    },
    "labels": {
        "en": "labels: {labels}",
        "fr": "étiquettes : {labels}",
        "es": "etiquetas: {labels}",
        "pt": "rótulos: {labels}",
        "ru": "метки: {labels}",
        "hi": "लेबल: {labels}",
        "zh-Hans": "标签: {labels}",
        "ar": "الوسوم: {labels}",
        "bn": "লেবেল: {labels}",
        "id": "label: {labels}",
        "de": "Labels: {labels}",
    },
    "due": {
        "en": "due {phrase}",
        "fr": "échéance {phrase}",
        "es": "vence {phrase}",
        "pt": "vence {phrase}",
        "ru": "срок {phrase}",
        "hi": "नियत {phrase}",
        "zh-Hans": "截止 {phrase}",
        "ar": "مستحق {phrase}",
        "bn": "নির্দিষ্ট {phrase}",
        "id": "jatuh tempo {phrase}",
        "de": "fällig {phrase}",
    },
    "assigned": {
        "en": "assigned to {name}",
        "fr": "assignée à {name}",
        "es": "asignada a {name}",
        "pt": "atribuída a {name}",
        "ru": "назначено {name}",
        "hi": "असाइन {name}",
        "zh-Hans": "分配给 {name}",
        "ar": "مُسندة إلى {name}",
        "bn": "কার কাছে দেওয়া: {name}",
        "id": "ditugaskan ke {name}",
        "de": "zugewiesen an {name}",
    },
    "priority": {
        "en": "priority {label}",
        "fr": "priorité {label}",
        "es": "prioridad {label}",
        "pt": "prioridade {label}",
        "ru": "приоритет {label}",
        "hi": "प्राथमिकता {label}",
        "zh-Hans": "优先级 {label}",
        "ar": "أولوية {label}",
        "bn": "অগ্রাধিকার {label}",
        "id": "prioritas {label}",
        "de": "Priorität {label}",
    },
    "repeat": {
        "en": "{phrase}",  # phrase already contains repeats wording
        "fr": "{phrase}",
        "es": "{phrase}",
        "pt": "{phrase}",
        "ru": "{phrase}",
        "hi": "{phrase}",
        "zh-Hans": "{phrase}",
        "ar": "{phrase}",
        "bn": "{phrase}",
        "id": "{phrase}",
        "de": "{phrase}",
    },
}

_PRIORITY_WORD = {
    1: {
        "en": "low",
        "fr": "basse",
        "es": "baja",
        "pt": "baixa",
        "ru": "низкий",
        "hi": "कम",
        "zh-Hans": "低",
        "ar": "منخفضة",
        "bn": "কম",
        "id": "rendah",
        "de": "niedrig",
    },
    2: {
        "en": "medium",
        "fr": "moyenne",
        "es": "media",
        "pt": "média",
        "ru": "средний",
        "hi": "मध्यम",
        "zh-Hans": "中",
        "ar": "متوسطة",
        "bn": "মাঝারি",
        "id": "sedang",
        "de": "mittel",
    },
    3: {
        "en": "high",
        "fr": "haute",
        "es": "alta",
        "pt": "alta",
        "ru": "высокий",
        "hi": "उच्च",
        "zh-Hans": "高",
        "ar": "عالية",
        "bn": "উচ্চ",
        "id": "tinggi",
        "de": "hoch",
    },
    4: {
        "en": "urgent",
        "fr": "urgente",
        "es": "urgente",
        "pt": "urgente",
        "ru": "срочный",
        "hi": "तात्कालिक",
        "zh-Hans": "紧急",
        "ar": "عاجلة",
        "bn": "জরুরি",
        "id": "mendesak",
        "de": "dringend",
    },
    5: {
        "en": "do now",
        "fr": "faire maintenant",
        "es": "hacer ahora",
        "pt": "fazer agora",
        "ru": "сделать сейчас",
        "hi": "अभी करो",
        "zh-Hans": "立刻",
        "ar": "نفّذ الآن",
        "bn": "এখনই",
        "id": "lakukan sekarang",
        "de": "sofort erledigen",
    },
}

# Relative due date short phrases (only small set we currently generate)
_DUE_BASE = {
    "today": {
        "en": "today",
        "fr": "aujourd'hui",
        "es": "hoy",
        "pt": "hoje",
        "ru": "сегодня",
        "hi": "आज",
        "zh-Hans": "今天",
        "ar": "اليوم",
        "bn": "আজ",
        "id": "hari ini",
        "de": "heute",
    },
    "tomorrow": {
        "en": "tomorrow",
        "fr": "demain",
        "es": "mañana",
        "pt": "amanhã",
        "ru": "завтра",
        "hi": "कल",
        "zh-Hans": "明天",
        "ar": "غدًا",
        "bn": "আগামীকাল",
        "id": "besok",
        "de": "morgen",
    },
    "like currently": {
        "en": "like currently",
        "fr": "en cours",
        "es": "en curso",
        "pt": "em andamento",
        "ru": "в процессе",
        "hi": "वर्तमान",
        "zh-Hans": "当前",
        "ar": "جارٍ",
        "bn": "চলমান",
        "id": "sedang berlangsung",
        "de": "aktuell",
    },
    # Patterns with {n} and optional years/days composite handled in function
}

_RELATIVE_PHRASES: Dict[str, Any] | None = None
_RELATIVE_LOAD_TRIED = False


def _load_relative():  # lazy load
    global _RELATIVE_PHRASES, _RELATIVE_LOAD_TRIED
    if _RELATIVE_LOAD_TRIED:
        return
    _RELATIVE_LOAD_TRIED = True
    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))  # helpers/ -> vikunja/
        rel_path = os.path.join(base_dir, "translations", "relative_phrases.json")
        with open(rel_path, "r", encoding="utf-8") as f:  # noqa: PTH123
            _RELATIVE_PHRASES = json.load(f)
    except Exception:  # noqa: BLE001
        _RELATIVE_PHRASES = None


def localize_due_phrase(raw: str, lang: str) -> str:
    _load_relative()
    rp = _RELATIVE_PHRASES.get("due") if isinstance(_RELATIVE_PHRASES, dict) else None  # type: ignore
    # direct map
    if raw in _DUE_BASE and lang in _DUE_BASE[raw]:
        return _DUE_BASE[raw][lang]
    if rp and raw in rp and isinstance(rp[raw], dict) and lang in rp[raw]:
        return rp[raw][lang]
    # Patterns: in X days / in Y year(s) (Z days)
    if raw.startswith("in ") and raw.endswith(" days") and "year" not in raw:
        # in 3 days
        try:
            num = raw.split()[1]
            if rp and "in_days" in rp:
                templates = rp["in_days"]
            else:
                templates = {
                    "en": "in {n} days",
                    "fr": "dans {n} jours",
                    "es": "en {n} días",
                    "pt": "em {n} dias",
                    "ru": "через {n} дней",
                    "hi": "{n} दिन में",
                    "zh-Hans": "{n} 天后",
                    "ar": "خلال {n} يومًا",
                    "bn": "{n} দিনে",
                    "id": "dalam {n} hari",
                    "de": "in {n} Tagen",
                }
            tpl = templates.get(lang, templates["en"])
            return tpl.format(n=num)
        except Exception:  # noqa: BLE001
            return raw
    if raw.startswith("in ") and "year" in raw:
        # in 2 years (800 days)
        try:
            parts = raw.split()
            years = parts[1]
            rest = raw[raw.find("(") :]
            if rp and "in_years" in rp:
                templates = rp["in_years"]
            else:
                templates = {
                    "en": "in {y} years {rest}",
                    "fr": "dans {y} ans {rest}",
                    "es": "en {y} años {rest}",
                    "pt": "em {y} anos {rest}",
                    "ru": "через {y} лет {rest}",
                    "hi": "{y} वर्ष में {rest}",
                    "zh-Hans": "{y} 年后 {rest}",
                    "ar": "خلال {y} سنوات {rest}",
                    "bn": "{y} বছরে {rest}",
                    "id": "dalam {y} tahun {rest}",
                    "de": "in {y} Jahren {rest}",
                }
            # singular detection
            if years == "1":
                if rp and "in_year" in rp:
                    templates_sing = rp["in_year"]
                else:
                    templates_sing = {
                        "en": "in {y} year {rest}",
                        "fr": "dans {y} an {rest}",
                        "es": "en {y} año {rest}",
                        "pt": "em {y} ano {rest}",
                        "ru": "через {y} год {rest}",
                        "hi": "{y} वर्ष में {rest}",
                        "zh-Hans": "{y} 年后 {rest}",
                        "ar": "خلال {y} سنة {rest}",
                        "bn": "{y} বছরে {rest}",
                        "id": "dalam {y} tahun {rest}",
                        "de": "in {y} Jahr {rest}",
                    }
                templates.update({k: v for k, v in templates_sing.items()})
            tpl = templates.get(lang, templates["en"])
            return tpl.format(y=years, rest=rest)
        except Exception:  # noqa: BLE001
            return raw
    return raw


def localize_repeat_phrase(raw: str, lang: str) -> str:
    _load_relative()
    rp = (
        _RELATIVE_PHRASES.get("repeat") if isinstance(_RELATIVE_PHRASES, dict) else None
    )  # type: ignore
    if not raw:
        return raw
    # raw patterns: repeats in X day(s); repeats in Y years (Z days); repeats every N seconds
    if raw.startswith("repeats every ") and raw.endswith(" seconds"):
        num = raw.split()[2]
        if rp and "every_seconds" in rp:
            templates = rp["every_seconds"]
        else:
            templates = {
                "en": "repeats every {n} seconds",
                "fr": "se répète toutes les {n} secondes",
                "es": "se repite cada {n} segundos",
                "pt": "repete a cada {n} segundos",
                "ru": "повторяется каждые {n} секунд",
                "hi": "हर {n} सेकंड में दोहराता है",
                "zh-Hans": "每 {n} 秒重复",
                "ar": "يتكرر كل {n} ثانية",
                "bn": "প্রতি {n} সেকেন্ডে পুনরাবৃত্তি",
                "id": "berulang setiap {n} detik",
                "de": "wiederholt sich alle {n} Sekunden",
            }
        return templates.get(lang, templates["en"]).format(n=num)
    if raw.startswith("repeats in ") and raw.endswith(" days") and "year" not in raw:
        num = raw.split()[2]
        if rp and "in_days" in rp:
            templates = rp["in_days"]
        else:
            templates = {
                "en": "repeats in {n} days",
                "fr": "se répète dans {n} jours",
                "es": "se repite en {n} días",
                "pt": "repete em {n} dias",
                "ru": "повтор через {n} дней",
                "hi": "{n} दिन में दोहराता है",
                "zh-Hans": "{n} 天后重复",
                "ar": "يتكرر خلال {n} يومًا",
                "bn": "{n} দিনে পুনরাবৃত্তি",
                "id": "berulang dalam {n} hari",
                "de": "wiederholt sich in {n} Tagen",
            }
        if num == "1":
            if rp and "in_day" in rp:
                templates_sing = rp["in_day"]
            else:
                templates_sing = {
                    "en": "repeats in {n} day",
                    "fr": "se répète dans {n} jour",
                    "es": "se repite en {n} día",
                    "pt": "repete em {n} dia",
                    "ru": "повтор через {n} день",
                    "hi": "{n} दिन में दोहराता है",
                    "zh-Hans": "{n} 天后重复",
                    "ar": "يتكرر خلال {n} يوم",
                    "bn": "{n} দিনে পুনরাবৃত্তি",
                    "id": "berulang dalam {n} hari",
                    "de": "wiederholt sich in {n} Tag",
                }
            templates.update(templates_sing)
        return templates.get(lang, templates["en"]).format(n=num)
    if raw.startswith("repeats in ") and "year" in raw:
        years = raw.split()[2]
        rest = raw[raw.find("(") :]
        if rp and "in_years" in rp:
            templates = rp["in_years"]
        else:
            templates = {
                "en": "repeats in {y} years {rest}",
                "fr": "se répète dans {y} ans {rest}",
                "es": "se repite en {y} años {rest}",
                "pt": "repete em {y} anos {rest}",
                "ru": "повтор через {y} лет {rest}",
                "hi": "{y} वर्ष में दोहराता है {rest}",
                "zh-Hans": "{y} 年后重复 {rest}",
                "ar": "يتكرر خلال {y} سنوات {rest}",
                "bn": "{y} বছরে পুনরাবৃত্তি {rest}",
                "id": "berulang dalam {y} tahun {rest}",
                "de": "wiederholt sich in {y} Jahren {rest}",
            }
        if years == "1":
            if rp and "in_year" in rp:
                templates_sing = rp["in_year"]
            else:
                templates_sing = {
                    "en": "repeats in {y} year {rest}",
                    "fr": "se répète dans {y} an {rest}",
                    "es": "se repite en {y} año {rest}",
                    "pt": "repete em {y} ano {rest}",
                    "ru": "повтор через {y} год {rest}",
                    "hi": "{y} वर्ष में दोहराता है {rest}",
                    "zh-Hans": "{y} 年后重复 {rest}",
                    "ar": "يتكرر خلال {y} سنة {rest}",
                    "bn": "{y} বছরে पुनরাবৃত্তি {rest}",
                    "id": "berulang dalam {y} tahun {rest}",
                    "de": "wiederholt sich in {y} Jahr {rest}",
                }
            templates.update(templates_sing)
        return templates.get(lang, templates["en"]).format(y=years, rest=rest)
    return raw


def L(key: str, lang: str, **kwargs) -> str:
    table = _BASE.get(key, {})
    template = table.get(lang) or table.get("en", key)
    return template.format(**kwargs)


def localized_priority(priority: int, lang: str) -> str | None:
    mapping = _PRIORITY_WORD.get(priority)
    if not mapping:
        return None
    return mapping.get(lang) or mapping.get("en")


def build_detailed_parts(
    lang: str,
    project_name: str | None,
    labels_part: str | None,
    due_phrase: str | None,
    assignee: str | None,
    priority_word: str | None,
    repeat_phrase: str | None,
):
    parts = []
    if project_name:
        parts.append(
            _DETAIL_TOKENS["project"]
            .get(lang, _DETAIL_TOKENS["project"]["en"])
            .format(name=project_name)
        )
    if labels_part:
        parts.append(
            _DETAIL_TOKENS["labels"]
            .get(lang, _DETAIL_TOKENS["labels"]["en"])
            .format(labels=labels_part)
        )
    if due_phrase:
        parts.append(
            _DETAIL_TOKENS["due"]
            .get(lang, _DETAIL_TOKENS["due"]["en"])
            .format(phrase=due_phrase)
        )
    if assignee:
        parts.append(
            _DETAIL_TOKENS["assigned"]
            .get(lang, _DETAIL_TOKENS["assigned"]["en"])
            .format(name=assignee)
        )
    if priority_word:
        parts.append(
            _DETAIL_TOKENS["priority"]
            .get(lang, _DETAIL_TOKENS["priority"]["en"])
            .format(label=priority_word)
        )
    if repeat_phrase:
        parts.append(
            _DETAIL_TOKENS["repeat"]
            .get(lang, _DETAIL_TOKENS["repeat"]["en"])
            .format(phrase=repeat_phrase)
        )
    return parts
