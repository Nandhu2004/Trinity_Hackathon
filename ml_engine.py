def analyze_symptoms(text):
    text = text.lower()

    if "chest pain" in text:
        return {
            "risk": "HIGH",
            "recommendation": "Consult Cardiologist",
            "explanation": "Chest pain detected → cardiac risk rule triggered"
        }
    elif "fever" in text:
        return {
            "risk": "MEDIUM",
            "recommendation": "General Physician",
            "explanation": "Fever indicates possible infection"
        }
    else:
        return {
            "risk": "LOW",
            "recommendation": "Self care / GP",
            "explanation": "No high-risk symptoms found"
        }

def summarize_consultation(text):
    return f"Patient reported: {text}. AI summary generated for clinical assistance."
# ml_engine.py

def chatbot_reply(user_input, state):
    """
    Professional telemedicine chatbot that collects structured patient info.
    State-aware:
    - symptom
    - location
    - severity
    - duration
    - additional questions
    """

    user_input = user_input.strip().lower()
    stage = state.get("stage", "start")

    if stage == "start":
        state["stage"] = "symptom"
        return "Hello, I’m your AI Health Assistant. What main symptom are you experiencing?"

    if stage == "symptom":
        state["symptom"] = user_input
        state["stage"] = "location"
        return "Can you tell me where the symptom is located? (e.g., chest, head, stomach)"

    if stage == "location":
        state["location"] = user_input
        state["stage"] = "severity"
        return "On a scale of 1 to 10, how severe is the symptom?"

    if stage == "severity":
        state["severity"] = user_input
        state["stage"] = "duration"
        return "How long have you been experiencing this symptom? (hours, days, weeks)"

    if stage == "duration":
        state["duration"] = user_input
        state["stage"] = "additional"
        return "Do you have any other symptoms or information to share?"

    if stage == "additional":
        # Collect additional notes if any
        state["additional"] = user_input
        state["stage"] = "done"
        return "Thank you. I have collected your information. You can now proceed to consultation."

    if stage == "done":
        return "You may now proceed to consultation."

    return "Please provide more information."