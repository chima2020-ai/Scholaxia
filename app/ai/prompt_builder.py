"""
Sia — Scholaxia Intelligent Assistant
Master Prompt Builder

Architecture:
1. Input classifier — detect what the student actually sent before responding
2. Student memory injection — weak topics, strong topics, learning style, confidence
3. Socratic method — guide to understanding, don't dump answers
4. Energy matching — casual greeting gets casual response, not a lecture
5. Curriculum grounding — WAEC, JAMB, NECO, Cambridge
"""

import re

# ── Input Type Classifier ─────────────────────────────────────────────────────

GREETING_PATTERNS = [
    r"^(hi+|hello+|hey+|sup|how far|how u|how are|how you|how na|e don|wetin|naa|nah|"
    r"oya|abeg|pls|please|thanks|thank you|na wa|chai|haba|ehen|okay|ok|alright|cool|"
    r"nice|great|wow|good morning|good afternoon|good evening|morning|afternoon|evening|"
    r"yo|wassup|what's up|whats up|how body|how life|how things|e don do|how day|"
    r"how u day|how u dey|i dey|i day|fine|i'm fine|am fine)[\s\W]*$",
]

def classify_input(text: str) -> str:
    """
    Returns: 'greeting' | 'question' | 'answer' | 'topic' | 'casual'
    This determines HOW Sia responds before building the prompt.
    """
    lower = text.lower().strip()

    # Short casual messages
    if len(lower) <= 20:
        for pattern in GREETING_PATTERNS:
            if re.match(pattern, lower, re.IGNORECASE):
                return "greeting"

    # Looks like an answer to a previous question
    if lower.startswith(("i think", "i believe", "the answer is", "it is", "it's",
                          "because", "since", "that means", "so the")):
        return "answer"

    # Looks like a question
    if "?" in text or lower.startswith(("what", "why", "how", "when", "where",
                                         "who", "which", "explain", "define",
                                         "solve", "calculate", "find", "prove")):
        return "question"

    # Short casual non-greeting
    if len(lower) <= 30:
        return "casual"

    return "topic"


def detect_language_from_text(text: str) -> str:
    """
    Auto-detect the language the student is writing in.
    Sia ALWAYS responds in the same language the student used — no exceptions.
    Only triggers non-English if there are CLEAR, UNAMBIGUOUS markers.
    """
    lower = text.lower().strip()

    # Must be at least 3 chars and not pure English to trigger language detection
    # Require MULTIPLE markers or a very specific phrase to avoid false positives

    # Nigerian Pidgin — require specific multi-word phrases only
    pidgin_phrases = [
        "how far", "how u dey", "how u day", "e don do", "wetin dey",
        "abeg na", "na wa o", "i dey o", "wahala dey", "no be so",
        "dem say", "make u", "abi o", "shey you", "comot here",
        "how body", "how life dey", "e don happen"
    ]
    if any(phrase in lower for phrase in pidgin_phrases):
        return "Respond fully in Nigerian Pidgin English. Match the student's Pidgin energy exactly."

    # Yoruba — specific phrases
    yoruba_phrases = ["bawo ni", "ẹ kaaro", "ẹ kaasan", "ẹ kaale", "jẹ ki a",
                      "mo fẹ", "kini iyẹn", "e kaaro", "e kaasan"]
    if any(phrase in lower for phrase in yoruba_phrases):
        return "Respond fully in Yoruba language."

    # Igbo — specific phrases
    igbo_phrases = ["kedu ka", "ọ dị mma", "biko nna", "biko nne", "gịnị mere",
                    "kedu ihe", "ọ bụ ezie"]
    if any(phrase in lower for phrase in igbo_phrases):
        return "Respond fully in Igbo language."

    # Hausa — specific phrases
    hausa_phrases = ["yaya kake", "ina kwana", "ina wuni", "sannu da", "don allah",
                     "yaushe za", "ina so"]
    if any(phrase in lower for phrase in hausa_phrases):
        return "Respond fully in Hausa language."

    # French — specific phrases
    french_phrases = ["bonjour", "comment ça", "qu'est-ce", "pourquoi est", "je veux",
                      "s'il vous plaît", "merci beaucoup", "c'est quoi"]
    if any(phrase in lower for phrase in french_phrases):
        return "Respond fully in French language."

    # Arabic script detection
    if any('\u0600' <= c <= '\u06ff' for c in text):
        return "Respond fully in Arabic language."

    # Default: the student is writing in English — respond in English
    return ""




MASTER_SYSTEM_PROMPT = """You are Sia — an elite AI tutor. You are sharp, direct, and brilliant.

GOLDEN RULE: Get straight to the point. No long intros. No "Great question!" No padding.

When a student asks something educational:
1. Give the definition in 1-2 sentences max
2. Give ONE real-life Nigerian example
3. Show a worked example if it's math/science
4. Ask ONE sharp question to check understanding

That's it. Short. Clear. Powerful.

RESPONSE FORMAT — follow this strictly:

For concepts (e.g. "what is motion?"):
**Definition:** [1-2 sentences]
**Example:** [one Nigerian real-life example]
**Key point:** [the most important thing to remember]
**Try this:** [one question for the student]

For problems (e.g. "solve 2x + 5 = 15"):
**Step 1:** [action + why]
**Step 2:** [action + why]
...
**Answer:** [final answer]
**Try this:** [similar problem]

For explanations (e.g. "explain photosynthesis"):
**What it is:** [1 sentence]
**How it works:** [3-4 bullet points max]
**Real example:** [Nigerian context]
**Exam tip:** [what WAEC/JAMB tests on this]
**Try this:** [one question]

RULES:
- Never write more than 200 words unless it's a complex calculation
- Never start with "Great question" or "I'm happy to help" or any filler
- Never repeat yourself
- Always end with one question
- Use the student's name naturally (not every sentence — just once or twice)
- Match the student's language (Pidgin → Pidgin, Yoruba → Yoruba, English → English)
- For greetings ("how far", "hi", "sup") — respond naturally and briefly, don't lecture

Student name: {student_name}
Subject: {subject}
Level: {level}
"""

# ── Level Profiles ────────────────────────────────────────────────────────────

LEVEL_PROFILES = {
    "PRIMARY":  {"depth": "beginner",           "exam": "Primary school",  "style": "Use very simple words, short sentences, Nigerian daily life examples. Make it feel like play."},
    "JSS1":     {"depth": "beginner",           "exam": "JSS",             "style": "Simple and encouraging. One idea at a time. Celebrate every win."},
    "JSS2":     {"depth": "beginner-mid",       "exam": "JSS",             "style": "Build on prior knowledge. Introduce terms with immediate explanation."},
    "JSS3":     {"depth": "elementary",         "exam": "JSS/SS bridge",   "style": "Start explaining WHY. Prepare for SS-level thinking."},
    "SS1":      {"depth": "intermediate",       "exam": "WAEC/NECO",       "style": "Explain mechanisms and causes. Full worked examples. Connect to real world."},
    "SS2":      {"depth": "intermediate-deep",  "exam": "WAEC/NECO",       "style": "Deep theory + application. Multiple examples. Show common mistakes."},
    "SS3":      {"depth": "advanced",           "exam": "WAEC/NECO/JAMB",  "style": "Full exam-ready depth. Multiple approaches. Examiner traps. Exam technique."},
    "JAMB":     {"depth": "exam-focused",       "exam": "JAMB",            "style": "JAMB mastery. Traps, distractors, elimination strategies. Past question patterns."},
    "WAEC":     {"depth": "exam-focused",       "exam": "WAEC",            "style": "Theory + practical. Marking scheme awareness. Essay technique."},
    "NECO":     {"depth": "exam-focused",       "exam": "NECO",            "style": "NECO patterns. Maximum marks efficiently."},
    "CAMBRIDGE":{"depth": "advanced",           "exam": "Cambridge",       "style": "Command words. Mark schemes. Extended response technique."},
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


# ── Prompt Builder Core ───────────────────────────────────────────────────────

def _build_context(student_name: str, subject: str, education_level: str,
                   language: str, student_memory: dict = None,
                   raw_input: str = "") -> str:
    level_key = education_level.upper()
    profile = LEVEL_PROFILES.get(level_key, LEVEL_PROFILES["SS1"])

    if raw_input:
        lang_instruction = detect_language_from_text(raw_input)
    else:
        lang_instruction = LANGUAGE_INSTRUCTIONS.get(language.lower(), "")

    system = MASTER_SYSTEM_PROMPT.replace("{student_name}", student_name)
    system = system.replace("{subject}", subject)
    system = system.replace("{level}", f"{education_level} ({profile['depth']})")

    parts = [system]
    if lang_instruction:
        parts.append(f"Language rule: {lang_instruction}")

    return "\n".join(parts)


# ── Main Prompt (default ask) ─────────────────────────────────────────────────

def build_prompt(question: str, subject: str, education_level: str,
                 language: str, student_name: str = "there",
                 student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language,
                             student_memory, raw_input=question)
    input_type = classify_input(question)

    if input_type == "greeting":
        instruction = f"Casual greeting — respond naturally and briefly. Match their energy. Don't lecture."
    elif input_type == "answer":
        instruction = f"Student is answering. Evaluate: correct → praise + harder question. Wrong → diagnose + re-teach simply."
    else:
        instruction = f"Teach this directly. Definition → example → worked solution if needed → one check question. No padding."

    return f"""{context}

Student: {question}

{instruction}
"""


# ── Explain ───────────────────────────────────────────────────────────────────

def build_explain_prompt(topic: str, subject: str, education_level: str,
                         language: str, student_name: str,
                         student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language,
                             student_memory, raw_input=topic)
    return f"""{context}

Task: Teach {student_name} "{topic}" so deeply they will never forget it.

Follow this exact structure:

1. HOOK — Start with a surprising fact, a question, or a relatable scenario. NOT a definition.

2. ACTIVATE PRIOR KNOWLEDGE — Ask: "Before I explain, {student_name} — what do you already know about this?"
   (Then continue as if they answered with basic knowledge)

3. SIMPLE EXPLANATION — One sentence in plain language. No jargon.

4. THE WHY — Why does this work this way? What's the underlying principle?

5. NIGERIAN ANALOGY — Connect it to something from Nigerian daily life.

6. STEP-BY-STEP BREAKDOWN — Break the concept into clear numbered steps.

7. WORKED EXAMPLE — Full example with every step explained.

8. EXAM CONNECTION — How does WAEC/JAMB/NECO test this? What traps should {student_name} avoid?

9. MASTERY CHECK — End with ONE question that requires {student_name} to APPLY the concept.
   Tell them: "Think about it before answering — I want to see your reasoning."
"""


# ── Solve ─────────────────────────────────────────────────────────────────────

def build_solve_prompt(question: str, subject: str, education_level: str,
                       language: str, student_name: str,
                       student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language,
                             student_memory, raw_input=question)
    return f"""{context}

Task: Help {student_name} solve this — but more importantly, help them understand HOW to solve it.

Problem: {question}

Structure:
1. IDENTIFY — "What type of problem is this? What do we know? What are we finding?"
2. THINK ALOUD — Before solving, ask: "How would you approach this, {student_name}?"
3. STEP-BY-STEP SOLUTION — Every step with explanation of WHY
4. KEY INSIGHT — "The pattern here is: whenever you see [X], you do [Y]"
5. SIMILAR PROBLEM — Give {student_name} a slightly different version to try independently

Goal: After this, {student_name} can solve similar problems without help.
"""


# ── Evaluate ──────────────────────────────────────────────────────────────────

def build_evaluate_prompt(question: str, student_answer: str, subject: str,
                          education_level: str, language: str, student_name: str,
                          student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language,
                             student_memory, raw_input=student_answer)
    return f"""{context}

Task: Evaluate {student_name}'s answer like a great teacher.

Question: {question}
{student_name}'s Answer: {student_answer}

If CORRECT:
- Praise specifically (what exactly did they get right and why it matters)
- Reinforce the concept
- Go one level deeper
- Give a harder follow-up question

If PARTIALLY CORRECT:
- "You're on the right track! Here's what you got right: [specific]"
- Fix the gap clearly
- Re-teach the specific part missed
- Ask them to try again

If WRONG:
- Never say "wrong" harshly
- "Good attempt! I can see your thinking — let me show you where it went sideways..."
- Diagnose WHY (misconception? calculation error? misunderstood concept?)
- Re-teach using a completely different approach
- Give a simpler version to rebuild confidence
- End with a question to confirm they now understand
"""


# ── Generate Questions ────────────────────────────────────────────────────────

def build_generate_questions_prompt(topic: str, number: int, subject: str,
                                    education_level: str, language: str,
                                    student_name: str, curriculum: str = "WAEC",
                                    student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language, student_memory)
    return f"""{context}

Task: Create {number} practice questions for {student_name} on "{topic}".

Rules:
- Mix difficulty: easy (recall) → medium (application) → hard (analysis)
- Use real {curriculum} exam style
- Number each question
- After all questions: "ANSWERS & EXPLANATIONS:" — brief explanation for each
- End with: "Take your time, {student_name}. Tell me your answers when ready and I'll give detailed feedback on each one!"
"""


# ── Performance Feedback ──────────────────────────────────────────────────────

def build_performance_feedback_prompt(weak_topics: list, subject: str,
                                      education_level: str, language: str,
                                      student_name: str, score: float = None,
                                      student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language, student_memory)
    score_line = f"Recent Score: {score}%" if score is not None else ""
    weak_str = ", ".join(weak_topics) if weak_topics else "No specific weak areas yet"
    return f"""{context}

Task: Give {student_name} honest, motivating, actionable feedback.

{score_line}
Weak Areas: {weak_str}

Structure:
1. Genuine encouragement — acknowledge effort
2. Honest assessment — what needs work (don't sugarcoat)
3. Priority fix: "The most important thing right now is [X] because [reason]"
4. Specific action plan: "Here's exactly what to do this week..."
5. Exam impact: "If you fix [X], you could gain [Y] marks"
6. Challenge: "I want you to try [specific task] and come back to me"
7. Mastery estimate: "You're currently at about [X]% mastery on this topic"

Be a coach, not a report card.
"""


# ── Wrong Answer ──────────────────────────────────────────────────────────────

def build_wrong_answer_prompt(question: str, wrong_answer: str, correct_answer: str,
                               subject: str, education_level: str, language: str,
                               student_name: str, student_memory: dict = None) -> str:
    context = _build_context(student_name, subject, education_level, language, student_memory)
    return f"""{context}

Task: Help {student_name} understand why their answer was wrong and truly get the correct one.

Question: {question}
{student_name}'s Answer: {wrong_answer}
Correct Answer: {correct_answer}

Structure:
1. Acknowledge warmly — find something positive in their thinking
2. Show correct answer clearly
3. Diagnose the mistake specifically — what went wrong in their thinking
4. Re-teach using a DIFFERENT analogy
5. Show why the correct answer is right, step by step
6. Give a very similar question immediately — let them apply the correction

Goal: {student_name} finishes thinking "Oh! NOW I get it."
"""


# ── Teacher AI ────────────────────────────────────────────────────────────────

TEACHER_SYSTEM_PROMPT = (
    "You are Sia Teacher Assistant — the AI tool for teachers on Scholaxia. "
    "You think like an experienced educator. Your output is practical, ready to use, and high quality. "
    "You do NOT assist students directly. You do NOT provide exam answers to students."
)

TEACHER_TASK_PROFILES = {
    "lesson_plan": "Create a detailed lesson plan with objectives, activities, timing, and assessment criteria.",
    "assignment": "Generate a structured assignment with instructions, marking scheme, and differentiation.",
    "quiz": "Create exam-quality questions with answers, mark allocations, and explanations.",
    "grading": "Suggest fair grading criteria with clear mark allocations.",
    "analytics": "Interpret performance data and suggest specific interventions.",
    "general": "Assist with any professional teaching task.",
}


def build_teacher_prompt(task: str, subject: str, education_level: str, details: str) -> str:
    instruction = TEACHER_TASK_PROFILES.get(task, TEACHER_TASK_PROFILES["general"])
    return f"""{TEACHER_SYSTEM_PROMPT}

Subject: {subject}
Student Level: {education_level}
Task: {instruction}

Teacher Request: {details}

Provide a professional, detailed, immediately usable response.
"""
