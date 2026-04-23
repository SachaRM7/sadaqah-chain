MESSAGES = {
    "en": {
        "welcome": "Welcome to SadaqahChain. Use /zakat to calculate and /charities to browse vetted charities.",
        "charities": "Whitelisted charities",
        "ledger": "Recent public ledger entries",
        "admin_only": "This command is restricted to admins.",
    },
    "fr": {
        "welcome": "Bienvenue sur SadaqahChain. Utilise /zakat pour calculer et /charities pour voir les associations validées.",
        "charities": "Associations approuvées",
        "ledger": "Entrées récentes du registre public",
        "admin_only": "Cette commande est réservée aux administrateurs.",
    },
    "ar": {
        "welcome": "مرحباً بك في صدقة تشين. استخدم /zakat للحساب و /charities لعرض الجمعيات الموثقة.",
        "charities": "الجمعيات المعتمدة",
        "ledger": "أحدث قيود السجل العام",
        "admin_only": "هذا الأمر مخصص للمشرفين فقط.",
    },
}


def t(language: str, key: str) -> str:
    language = (language or "en").lower()
    return MESSAGES.get(language, MESSAGES["en"]).get(key, MESSAGES["en"].get(key, key))
