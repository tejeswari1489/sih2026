from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import chromadb
from gtts import gTTS
from playsound import playsound
import tempfile

load_dotenv()

# --- Phase 6: Text-to-speech function ---
def speak(text, lang_code):
    tts = gTTS(text=text, lang=lang_code)
    tts.save("reply.mp3")
    playsound(os.path.abspath("reply.mp3"))
    os.remove("reply.mp3")

# --- Phase 4: Language selection + patient identification ---
print("Select your language:")
print("1. English")
print("2. Hindi")
print("3. Telugu")
lang_choice = input("Enter number: ")

languages = {"1": "English", "2": "Hindi", "3": "Telugu"}
selected_language = languages.get(lang_choice, "English")

lang_codes = {"English": "en", "Hindi": "hi", "Telugu": "te"}
tts_lang = lang_codes.get(selected_language, "en")

patient_id = input("Enter your name or ABHA ID (or type 'new' if first visit): ")

print(f"\nWelcome. Language set to {selected_language}.\n")

# --- Gemini client ---
gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# --- Phase 3: Knowledge base ---
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="symptom_questions")

collection.add(
    documents=[
        "chest pain: onset, character (sharp/dull/heavy), radiation to arm or jaw, associated symptoms like breathlessness or sweating, severity",
        "headache: onset, character (throbbing/dull/sharp), location (forehead/one side/whole head), associated symptoms like nausea or light sensitivity, severity",
        "stomach pain: onset, character (cramping/burning/sharp), location (upper/lower/whole abdomen), associated symptoms like vomiting or bloating, severity",
        "mouth ulcer: onset, associated symptoms like fever or swollen gums, severity",
        "fever: onset, pattern (continuous/comes and goes), associated symptoms like chills or body ache, severity",
        "cough: onset, character (dry/wet with phlegm), associated symptoms like fever or chest tightness, severity",
        "back pain: onset, character (dull ache/sharp/stiff), location (upper/lower back), associated symptoms like leg numbness or tingling, severity",
        "joint pain: onset, which joint(s), associated symptoms like swelling or redness, severity",
        "skin rash: onset, appearance (red/itchy/raised/flat), location on body, associated symptoms like fever or swelling, severity",
        "diarrhea: onset, frequency, associated symptoms like fever, blood, or dehydration signs, severity",
        "sore throat: onset, character (scratchy/painful swallowing), associated symptoms like fever or swollen glands, severity",
        "shortness of breath: onset, triggers (exertion/rest/lying down), associated symptoms like chest pain or wheezing, severity",
        "dizziness: onset, character (spinning/lightheaded), triggers (standing up/movement), associated symptoms like fainting or blurred vision, severity",
        "ear pain: onset, character (sharp/dull/throbbing), associated symptoms like hearing loss, discharge, or fever, severity",
        "eye redness/irritation: onset, associated symptoms like discharge, itching, or vision changes, severity"
    ],
    ids=["chest_pain", "headache", "stomach_pain", "mouth_ulcer", "fever", "cough",
         "back_pain", "joint_pain", "skin_rash", "diarrhea", "sore_throat",
         "shortness_of_breath", "dizziness", "ear_pain", "eye_irritation"]
)

# --- First complaint drives retrieval ---
first_complaint = input("You: ")
results = collection.query(query_texts=[first_complaint], n_results=1)
retrieved_questions = results["documents"][0][0]

system_prompt = f"""You are a clinical intake assistant collecting a patient's 
medical history before they see a doctor. Ask ONE short follow-up question 
at a time. Base your questions specifically on this retrieved question set 
for their symptom: {retrieved_questions}

Do not give medical advice, diagnoses, or treatment suggestions - if asked, 
say the doctor will address that. Once you've covered everything in the 
retrieved question set, STOP and reply with a summary formatted like:

Chief Complaint: ...
Onset: ...
Character: ... (only if relevant)
Location/Radiation: ... (only if relevant)
Associated Symptoms: ...
Severity: ...
"""

chat = gemini_client.chats.create(
    model="gemini-3.6-flash",
    config=types.GenerateContentConfig(system_instruction=system_prompt)
)

response = chat.send_message(first_complaint)
print("Assistant:", response.text)
speak(response.text, tts_lang)

while True:
    user_input = input("You: ")
    if user_input.lower() in ["quit", "exit"]:
        break
    response = chat.send_message(user_input)
    print("Assistant:", response.text)
    speak(response.text, tts_lang)
    if "Chief Complaint:" in response.text:
        break