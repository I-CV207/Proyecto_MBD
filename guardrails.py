import re, fasttext, pathlib

ALLOWED_TOPICS = {...}
MODEL_PATH = pathlib.Path("Modelos/topic_classifier.ftz")
clf = fasttext.load_model(str(MODEL_PATH))

REFUSAL = "Lo siento, solo puedo ayudar con temas financieros y bancarios. I’m sorry, I can only help with financial & banking topics."

def is_allowed_semantically(text: str) -> bool:
    label, prob = clf.predict(text.replace("\n", " "), k=1)
    return label[0] == "__label__finance" and prob[0] > 0.6

def contains_forbidden_keywords(text: str) -> bool:
    return bool(re.search(r"\b(sexo|política|religión|violencia|terrorismo)\b", text, re.I))

def validate_prompt(user_prompt: str):
    if contains_forbidden_keywords(user_prompt):
        return False, REFUSAL
    if not is_allowed_semantically(user_prompt):
        return False, REFUSAL
    return True, ""