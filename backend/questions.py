"""The interview Kaam conducts, in each supported language.

Questions are short and conversational because Timbre reads them aloud and the
worker answers by voice. Translations other than English and Hindi should be
checked by a native speaker before recording demos.
"""

# id → what the answer is used for in the resume
QUESTION_IDS = ["intro", "work", "history", "strengths", "preferences", "languages"]

LANGUAGES = {
    "hi-IN": {"label": "हिन्दी", "name": "Hindi"},
    "en-IN": {"label": "English", "name": "English"},
    "ta-IN": {"label": "தமிழ்", "name": "Tamil"},
    "bn-IN": {"label": "বাংলা", "name": "Bengali"},
    "mr-IN": {"label": "मराठी", "name": "Marathi"},
}

QUESTIONS = {
    "hi-IN": [
        "नमस्ते! आपका नाम क्या है, और आप कहाँ से हैं?",
        "आप कौन सा काम करते हैं, और कितने साल से कर रहे हैं?",
        "अब तक आपने कहाँ-कहाँ काम किया है? थोड़ा बताइए।",
        "आप किस काम में सबसे अच्छे हैं? कोई ऐसी बात बताइए जिस पर आपको गर्व हो।",
        "आप किस इलाके में काम करना चाहते हैं, और कितनी तनख़्वाह की उम्मीद रखते हैं?",
        "आप कौन-कौन सी भाषाएँ बोल लेते हैं?",
    ],
    "en-IN": [
        "Hello! What's your name, and where are you from?",
        "What work do you do, and for how many years have you done it?",
        "Where have you worked so far? Tell me a little about it.",
        "What are you best at? Tell me about something you're proud of.",
        "Which area would you like to work in, and what salary do you expect?",
        "Which languages can you speak?",
    ],
    "ta-IN": [
        "வணக்கம்! உங்கள் பெயர் என்ன, நீங்கள் எந்த ஊர்?",
        "நீங்கள் என்ன வேலை செய்கிறீர்கள், எத்தனை வருடங்களாக செய்கிறீர்கள்?",
        "இதுவரை எங்கெல்லாம் வேலை செய்திருக்கிறீர்கள்? கொஞ்சம் சொல்லுங்கள்.",
        "எந்த வேலையில் நீங்கள் மிகவும் திறமையானவர்? உங்களுக்குப் பெருமையான ஒரு விஷயம் சொல்லுங்கள்.",
        "எந்தப் பகுதியில் வேலை செய்ய விரும்புகிறீர்கள், எவ்வளவு சம்பளம் எதிர்பார்க்கிறீர்கள்?",
        "நீங்கள் எந்தெந்த மொழிகள் பேசுவீர்கள்?",
    ],
    "bn-IN": [
        "নমস্কার! আপনার নাম কী, আর আপনি কোথা থেকে এসেছেন?",
        "আপনি কী কাজ করেন, আর কত বছর ধরে করছেন?",
        "এখন পর্যন্ত কোথায় কোথায় কাজ করেছেন? একটু বলুন।",
        "কোন কাজে আপনি সবচেয়ে দক্ষ? এমন কিছু বলুন যা নিয়ে আপনি গর্বিত।",
        "আপনি কোন এলাকায় কাজ করতে চান, আর কত মাইনে আশা করেন?",
        "আপনি কোন কোন ভাষা বলতে পারেন?",
    ],
    "mr-IN": [
        "नमस्कार! तुमचं नाव काय, आणि तुम्ही कुठले आहात?",
        "तुम्ही कोणतं काम करता, आणि किती वर्षांपासून करताय?",
        "आत्तापर्यंत तुम्ही कुठे कुठे काम केलं आहे? थोडं सांगा.",
        "कोणत्या कामात तुम्ही सगळ्यात जास्त हुशार आहात? ज्याचा तुम्हाला अभिमान आहे असं काहीतरी सांगा.",
        "तुम्हाला कोणत्या भागात काम करायचं आहे, आणि किती पगाराची अपेक्षा आहे?",
        "तुम्ही कोणकोणत्या भाषा बोलता?",
    ],
}

assert all(len(qs) == len(QUESTION_IDS) for qs in QUESTIONS.values())
assert QUESTIONS.keys() == LANGUAGES.keys()


def questions_for(lang: str) -> list[dict]:
    return [{"id": qid, "text": text} for qid, text in zip(QUESTION_IDS, QUESTIONS[lang])]


def stt_lang_for(lang: str) -> str:
    """Prisma language setting for answers in `lang`.

    Workers mix English trade words into every language ("AC repair",
    "four-wheeler"). Prisma handles that within a single locale and keeps those
    words in Latin script, and it rejects comma-separated lists in `lang_code`.
    """
    return lang
