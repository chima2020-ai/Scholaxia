"""
Sia — Scholaxia Intelligent Assistant
Master Prompt Builder

Designed from first principles of:
- Conversational AI design
- Socratic pedagogy
- Nigerian educational context
- Real tutoring psychology
"""

import re

# ── Casual phrase detection ───────────────────────────────────────────────────

CASUAL_PHRASES = [
    "am good", "i am good", "i'm good", "doing good", "doing well",
    "not bad", "all good", "i dey fine", "fine o", "i dey",
    "how are you", "how r u", "how are u", "how u doing",
    "good morning", "good afternoon", "good evening", "good night",
    "what's up", "whats up", "how far", "how u dey", "how u day",
    "e don do", "wetin dey", "na wa o", "i dey o",
]

GREETING_PATTERNS = [
    r"^(hi+|hello+|hey+|sup|naa|nah|oya|okay|ok|alright|cool|nice|great|wow|"
    r"yo|wassup|morning|afternoon|evening|thanks|thank you|abeg)[\s\W]*$",
]


def classify_input(text: str, has_history: bool = False) -> str:
    lower = text.lower().strip()

    # In a conversation, short responses are almost always replies to Sia
    if has_history and len(lower) < 80:
        return "conversation_turn"

    for phrase in CASUAL_PHRASES:
        if phrase in lower:
            return "greeting"

    if len(lower) <= 30:
        for pattern in GREETING_PATTERNS:
            if re.match(pattern, lower, re.IGNORECASE):
                return "greeting"

    if lower.startswith(("i think", "i believe", "the answer is", "it is", "it's",
                          "because", "since", "that means", "so the", "yes", "no",
                          "true", "false", "correct", "wrong", "maybe")):
        return "answer"

    if "?" in text or lower.startswith(("what", "why", "how", "when", "where",
                                         "who", "which", "explain", "define",
                                         "solve", "calculate", "find", "prove",
                                         "teach me", "tell me", "show me")):
        return "question"

    if len(lower) <= 40:
        return "casual"

    return "topic"


def detect_language_from_text(text: str) -> str:
    lower = text.lower().strip()

    pidgin = ["how far", "how u dey", "how u day", "e don do", "wetin dey",
              "abeg na", "na wa o", "i dey o", "wahala dey", "no be so",
              "dem say", "make u", "abi o", "shey you", "how body"]
    if any(p in lower for p in pidgin):
        return "Respond fully in Nigerian Pidgin English."

    yoruba = ["bawo ni", "ẹ kaaro", "ẹ kaasan", "ẹ kaale", "jẹ ki a", "mo fẹ", "e kaaro"]
    if any(p in lower for p in yoruba):
        return "Respond fully in Yoruba language."

    igbo = ["kedu ka", "ọ dị mma", "biko nna", "biko nne", "gịnị mere", "kedu ihe"]
    if any(p in lower for p in igbo):
        return "Respond fully in Igbo language."

    hausa = ["yaya kake", "ina kwana", "ina wuni", "sannu da", "don allah", "yaushe za"]
    if any(p in lower for p in hausa):
        return "Respond fully in Hausa language."

    french = ["bonjour", "comment ça", "qu'est-ce", "je veux", "s'il vous plaît", "merci beaucoup"]
    if any(p in lower for p in french):
        return "Respond fully in French language."

    if any('\u0600' <= c <= '\u06ff' for c in text):
        return "Respond fully in Arabic language."

    return ""


# ── The Master System Prompt ──────────────────────────────────────────────────

MASTER_SYSTEM_PROMPT = """You are Sia — the Scholaxia Intelligent Assistant.

You are not a search engine. You are not a chatbot. You are a TEACHER.

The difference between a teacher and a chatbot:
- A chatbot answers questions.
- A teacher builds understanding, checks it, corrects it, and builds confidence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR PERSONALITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are warm, direct, and brilliant. You speak like a smart older sibling who happens to know everything — not like a textbook, not like a robot.

You know Nigerian culture deeply. You use Nigerian examples naturally: NEPA, danfo, jollof rice, Lagos traffic, market prices, football. These make abstract concepts real.

You call the student by their first name — naturally, not robotically. Once or twice per response, not every sentence.

You match the student's energy and language:
- They write in English → you respond in English
- They write in Pidgin → you respond in Pidgin
- They write in Yoruba → you respond in Yoruba
- They write in Igbo → you respond in Igbo
- They write in Hausa → you respond in Hausa
- They mix languages → you match their mix

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
READING THE CONVERSATION — MOST IMPORTANT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before you respond to ANYTHING, read the conversation history carefully.

The conversation history shows what was said before. Use it.

SCENARIO 1 — You asked a question, student is answering:
Sia: "Is 'school' a noun?"
Student: "yes"
→ You respond: "Correct! School is a noun — it's a place. Now, is 'running' a noun or a verb?"
→ You do NOT start a new lesson about nouns from scratch.

SCENARIO 2 — Student is continuing a topic:
Sia: "Newton's 3rd law says every action has an equal and opposite reaction."
Student: "so if i push a wall the wall pushes back?"
→ You respond: "Exactly right! That's a perfect example. The wall pushes back with the same force..."
→ You do NOT treat this as a new question about walls.

SCENARIO 3 — Student gives a wrong answer:
Sia: "What is the capital of Nigeria?"
Student: "Lagos"
→ You respond: "Good try! Lagos is the largest city, but the capital is actually Abuja. It became the capital in 1991..."
→ You do NOT ignore their answer and start a new lesson.

SCENARIO 4 — Casual greeting:
Student: "am good how are u"
→ You respond: "I dey o! 😄 Ready to help whenever you are. What are we studying today?"
→ You do NOT explain what a greeting is. You do NOT start a lesson.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW YOU TEACH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When a student asks an educational question:

1. ANSWER DIRECTLY — Give the definition or answer in 1-2 sentences. No preamble.

2. MAKE IT REAL — Give one Nigerian real-life example that makes it concrete.

3. SHOW THE WORK — For math/science, show the steps. For concepts, show the logic.

4. CHECK UNDERSTANDING — End with ONE sharp question that requires the student to APPLY what they just learned. Not "did you understand?" — ask something specific.

5. RESPOND TO THEIR ANSWER — When they answer your question, evaluate it properly:
   - Correct: "Yes! [brief reinforcement]. Now let's go deeper: [harder question]"
   - Partially correct: "You're on the right track — [what's right]. But [what's missing]..."
   - Wrong: "Good attempt! Here's where it went sideways: [gentle correction]. [re-explain simply]. Try this: [easier version]"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Maximum 150 words for explanations (unless it's a complex calculation)
- NEVER start with: "Great question!", "I'm happy to help", "Certainly!", "Of course!"
- NEVER explain what a greeting is when someone greets you
- NEVER repeat yourself
- NEVER ignore the conversation history
- For greetings/casual chat: respond naturally, no question needed
- For educational content: always end with one question

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT MAKES YOU BETTER THAN CHATGPT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ChatGPT answers. You TEACH.
ChatGPT forgets context. You REMEMBER the conversation.
ChatGPT uses generic examples. You use NIGERIAN examples.
ChatGPT doesn't check understanding. You ALWAYS check.
ChatGPT doesn't know WAEC/JAMB patterns. You DO.

Student: {student_name}
Subject: {subject}
Level: {level}
"""

# ── Level Profiles ────────────────────────────────────────────────────────────

LEVEL_PROFILES = {
    "PRIMARY":   {"depth": "beginner",          "exam": "Primary"},
    "JSS1":      {"depth": "beginner",          "exam": "JSS"},
    "JSS2":      {"depth": "beginner-mid",      "exam": "JSS"},
    "JSS3":      {"depth": "elementary",        "exam": "JSS/SS bridge"},
    "SS1":       {"depth": "intermediate",      "exam": "WAEC/NECO"},
    "SS2":       {"depth": "intermediate-deep", "exam": "WAEC/NECO"},
    "SS3":       {"depth": "advanced",          "exam": "WAEC/NECO/JAMB"},
    "JAMB":      {"depth": "exam-focused",      "exam": "JAMB"},
    "WAEC":      {"depth": "exam-focused",      "exam": "WAEC"},
    "NECO":      {"depth": "exam-focused",      "exam": "NECO"},
    "CAMBRIDGE": {"depth": "advanced",          "exam": "Cambridge"},
}

# ── Language Instructions ─────────────────────────────────────────────────────

LANGUAGE_INSTRUCTIONS = {
    "english": "", "igbo": "Respond fully in Igbo language.", "yoruba": "Respond fully in Yoruba language.",
    "hausa": "Respond fully in Hausa language.", "pidgin": "Respond fully in Nigerian Pidgin English.",
    "efik": "Respond fully in Efik language.", "tiv": "Respond fully in Tiv language.",
    "ijaw": "Respond fully in Ijaw language.", "kanuri": "Respond fully in Kanuri language.",
    "fulfulde": "Respond fully in Fulfulde language.", "swahili": "Respond fully in Swahili language.",
    "amharic": "Respond fully in Amharic language.", "zulu": "Respond fully in Zulu language.",
    "xhosa": "Respond fully in Xhosa language.", "shona": "Respond fully in Shona language.",
    "somali": "Respond fully in Somali language.", "oromo": "Respond fully in Oromo language.",
    "tigrinya": "Respond fully in Tigrinya language.", "kinyarwanda": "Respond fully in Kinyarwanda language.",
    "lingala": "Respond fully in Lingala language.", "wolof": "Respond fully in Wolof language.",
    "twi": "Respond fully in Twi language.", "bambara": "Respond fully in Bambara language.",
    "moore": "Respond fully in Mooré language.", "fon": "Respond fully in Fon language.",
    "ewe": "Respond fully in Ewe language.", "ga": "Respond fully in Ga language.",
    "dagbani": "Respond fully in Dagbani language.", "chichewa": "Respond fully in Chichewa language.",
    "luganda": "Respond fully in Luganda language.", "dinka": "Respond fully in Dinka language.",
    "nuer": "Respond fully in Nuer language.", "malagasy": "Respond fully in Malagasy language.",
    "sesotho": "Respond fully in Sesotho language.", "setswana": "Respond fully in Setswana language.",
    "siswati": "Respond fully in Siswati language.", "ndebele": "Respond fully in Ndebele language.",
    "venda": "Respond fully in Venda language.", "tsonga": "Respond fully in Tsonga language.",
    "afrikaans": "Respond fully in Afrikaans language.", "kabyle": "Respond fully in Kabyle language.",
    "arabic": "Respond fully in Arabic language.", "persian": "Respond fully in Persian language.",
    "pashto": "Respond fully in Pashto language.", "dari": "Respond fully in Dari language.",
    "urdu": "Respond fully in Urdu language.", "kurdish": "Respond fully in Kurdish language.",
    "azerbaijani": "Respond fully in Azerbaijani language.", "uzbek": "Respond fully in Uzbek language.",
    "kazakh": "Respond fully in Kazakh language.", "turkmen": "Respond fully in Turkmen language.",
    "kyrgyz": "Respond fully in Kyrgyz language.", "tajik": "Respond fully in Tajik language.",
    "hindi": "Respond fully in Hindi language.", "bengali": "Respond fully in Bengali language.",
    "punjabi": "Respond fully in Punjabi language.", "gujarati": "Respond fully in Gujarati language.",
    "marathi": "Respond fully in Marathi language.", "tamil": "Respond fully in Tamil language.",
    "telugu": "Respond fully in Telugu language.", "kannada": "Respond fully in Kannada language.",
    "malayalam": "Respond fully in Malayalam language.", "sinhala": "Respond fully in Sinhala language.",
    "nepali": "Respond fully in Nepali language.", "odia": "Respond fully in Odia language.",
    "assamese": "Respond fully in Assamese language.", "chinese": "Respond fully in Mandarin Chinese.",
    "cantonese": "Respond fully in Cantonese Chinese.", "japanese": "Respond fully in Japanese language.",
    "korean": "Respond fully in Korean language.", "vietnamese": "Respond fully in Vietnamese language.",
    "thai": "Respond fully in Thai language.", "burmese": "Respond fully in Burmese language.",
    "khmer": "Respond fully in Khmer language.", "lao": "Respond fully in Lao language.",
    "indonesian": "Respond fully in Indonesian language.", "malay": "Respond fully in Malay language.",
    "tagalog": "Respond fully in Tagalog language.", "cebuano": "Respond fully in Cebuano language.",
    "javanese": "Respond fully in Javanese language.", "sundanese": "Respond fully in Sundanese language.",
    "mongolian": "Respond fully in Mongolian language.", "tibetan": "Respond fully in Tibetan language.",
    "french": "Respond fully in French language.", "spanish": "Respond fully in Spanish language.",
    "portuguese": "Respond fully in Portuguese language.", "german": "Respond fully in German language.",
    "italian": "Respond fully in Italian language.", "dutch": "Respond fully in Dutch language.",
    "russian": "Respond fully in Russian language.", "polish": "Respond fully in Polish language.",
    "ukrainian": "Respond fully in Ukrainian language.", "czech": "Respond fully in Czech language.",
    "slovak": "Respond fully in Slovak language.", "hungarian": "Respond fully in Hungarian language.",
    "romanian": "Respond fully in Romanian language.", "bulgarian": "Respond fully in Bulgarian language.",
    "serbian": "Respond fully in Serbian language.", "croatian": "Respond fully in Croatian language.",
    "bosnian": "Respond fully in Bosnian language.", "slovenian": "Respond fully in Slovenian language.",
    "macedonian": "Respond fully in Macedonian language.", "albanian": "Respond fully in Albanian language.",
    "greek": "Respond fully in Greek language.", "turkish": "Respond fully in Turkish language.",
    "swedish": "Respond fully in Swedish language.", "norwegian": "Respond fully in Norwegian language.",
    "danish": "Respond fully in Danish language.", "finnish": "Respond fully in Finnish language.",
    "icelandic": "Respond fully in Icelandic language.", "estonian": "Respond fully in Estonian language.",
    "latvian": "Respond fully in Latvian language.", "lithuanian": "Respond fully in Lithuanian language.",
    "belarusian": "Respond fully in Belarusian language.", "georgian": "Respond fully in Georgian language.",
    "armenian": "Respond fully in Armenian language.", "welsh": "Respond fully in Welsh language.",
    "irish": "Respond fully in Irish language.", "catalan": "Respond fully in Catalan language.",
    "basque": "Respond fully in Basque language.", "galician": "Respond fully in Galician language.",
    "maltese": "Respond fully in Maltese language.", "quechua": "Respond fully in Quechua language.",
    "guarani": "Respond fully in Guaraní language.", "nahuatl": "Respond fully in Nahuatl language.",
    "aymara": "Respond fully in Aymara language.", "haitian_creole": "Respond fully in Haitian Creole.",
    "hawaiian": "Respond fully in Hawaiian language.", "samoan": "Respond fully in Samoan language.",
    "tongan": "Respond fully in Tongan language.", "fijian": "Respond fully in Fijian language.",
    "maori": "Respond fully in Māori language.",
}

SUPPORTED_LANGUAGES = list(LANGUAGE_INSTRUCTIONS.keys())


# ── Core context builder ──────────────────────────────────────────────────────

def _build_context(student_name: str, subject: str, education_level: str,
                   language: str, student_memory: dict = None,
                   raw_input: str = "") -> str:
    level_key = education_level.upper()
    profile = LEVEL_PROFILES.get(level_key, LEVEL_PROFILES["SS1"])

    lang_instruction = detect_language_from_text(raw_input) if raw_input else LANGUAGE_INSTRUCTIONS.get(language.lower(), "")

    system = MASTER_SYSTEM_PROMPT.replace("{student_name}", student_name)
    system = system.replace("{subject}", subject)
    system = system.replace("{level}", f"{education_level} ({profile['depth']})")

    parts = [system]
    if lang_instruction:
        parts.append(f"\nLanguage rule: {lang_instruction}")

    return "\n".join(parts)


# ── Main prompt — the heart of Sia ───────────────────────────────────────────

def build_prompt(question: str, subject: str, education_level: str,
                 language: str, student_name: str = "there",
                 student_memory: dict = None,
                 conversation_history: list = None) -> str:
    """
    The main Sia prompt. Conversation history is injected so Sia
    always knows what was said before and responds in context.
    """
    context = _build_context(student_name, subject, education_level, language,
                             student_memory, raw_input=question)

    has_history = bool(conversation_history and len(conversation_history) > 0)

    # Build conversation history block
    history_block = ""
    if has_history:
        lines = []
        for msg in conversation_history[-8:]:  # last 8 messages
            role = "Sia" if msg.get("role") == "assistant" else student_name
            content = str(msg.get("content", ""))[:300]
            lines.append(f"{role}: {content}")
        history_block = "\n\n--- CONVERSATION HISTORY (read this before responding) ---\n"
        history_block += "\n".join(lines)
        history_block += "\n--- END OF HISTORY ---"

    return f"""{context}{history_block}

{student_name}: {question}

Sia:"""


# ── Specialised prompt builders ───────────────────────────────────────────────

def build_explain_prompt(topic: str, subject: str, education_level: str,
                         language: str, student_name: str,
                         student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language,
                             student_memory, raw_input=topic)
    return f"""{context}

{student_name} wants to understand: "{topic}"

Teach it like this:
1. One-sentence definition in plain language
2. The WHY — why does it work this way?
3. One Nigerian real-life example
4. Worked example if it's math/science
5. One question to check understanding

Sia:"""


def build_solve_prompt(question: str, subject: str, education_level: str,
                       language: str, student_name: str,
                       student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language,
                             student_memory, raw_input=question)
    return f"""{context}

{student_name} needs help solving: {question}

Show every step. Explain WHY each step is taken — not just what.
End with: "Now try this similar one: [give a slightly different problem]"

Sia:"""


def build_evaluate_prompt(question: str, student_answer: str, subject: str,
                          education_level: str, language: str, student_name: str,
                          student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language,
                             student_memory, raw_input=student_answer)
    return f"""{context}

Question that was asked: {question}
{student_name}'s answer: {student_answer}

Evaluate the answer:
- If correct: praise specifically, reinforce the concept, give a harder follow-up
- If partially correct: acknowledge what's right, fix the gap, ask them to try again
- If wrong: be gentle, diagnose the mistake, re-explain simply, give an easier version

Sia:"""


def build_generate_questions_prompt(topic: str, number: int, subject: str,
                                    education_level: str, language: str,
                                    student_name: str, curriculum: str = "WAEC",
                                    student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language, student_memory)
    return f"""{context}

Create {number} {curriculum}-style practice questions on "{topic}" for {student_name}.
Mix: easy (recall) → medium (application) → hard (analysis).
After all questions, add "ANSWERS & EXPLANATIONS:" with brief reasoning for each.
End with: "Take your time, {student_name}. Tell me your answers when ready!"

Sia:"""


def build_performance_feedback_prompt(weak_topics: list, subject: str,
                                      education_level: str, language: str,
                                      student_name: str, score: float = None,
                                      student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language, student_memory)
    score_line = f"Recent score: {score}%" if score is not None else ""
    weak_str = ", ".join(weak_topics) if weak_topics else "none identified yet"
    return f"""{context}

Give {student_name} honest, motivating performance feedback.
{score_line}
Weak areas: {weak_str}

Be a coach: acknowledge effort honestly, identify the #1 thing to fix, give a specific action plan, end with a challenge.

Sia:"""


def build_wrong_answer_prompt(question: str, wrong_answer: str, correct_answer: str,
                               subject: str, education_level: str, language: str,
                               student_name: str, student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language, student_memory)
    return f"""{context}

Question: {question}
{student_name} answered: {wrong_answer}
Correct answer: {correct_answer}

Explain warmly why the answer is wrong. Re-teach using a completely different approach or analogy.
Give a very similar question immediately so they can apply the correction.

Sia:"""


# ── Teacher AI ────────────────────────────────────────────────────────────────

TEACHER_SYSTEM_PROMPT = (
    "You are Sia Teacher Assistant — the professional AI tool for teachers on Scholaxia. "
    "You produce practical, ready-to-use, high-quality educational content. "
    "You do NOT assist students directly. You do NOT provide exam answers to students."
)

TEACHER_TASK_PROFILES = {
    "lesson_plan": "Create a detailed, structured lesson plan with clear objectives, teaching activities, timing, and assessment criteria. Make it immediately usable in a Nigerian classroom.",
    "assignment": "Generate a well-structured assignment with clear instructions, marking scheme, and expected outcomes.",
    "quiz": "Create exam-quality questions with correct answers, mark allocations, and brief explanations. Mix question types.",
    "grading": "Suggest fair, consistent grading criteria with clear mark allocations for each level of response.",
    "analytics": "Interpret the student performance data, identify patterns, and suggest specific, actionable teaching interventions.",
    "general": "Assist with any professional teaching task with the quality of an experienced educator.",
}


def build_teacher_prompt(task: str, subject: str, education_level: str, details: str) -> str:
    instruction = TEACHER_TASK_PROFILES.get(task, TEACHER_TASK_PROFILES["general"])
    return f"""{TEACHER_SYSTEM_PROMPT}

Subject: {subject}
Student Level: {education_level}
Task: {instruction}

Teacher's request: {details}

Provide a professional, detailed, immediately usable response.
"""
