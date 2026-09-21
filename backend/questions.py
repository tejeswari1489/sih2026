import chromadb

client = chromadb.Client()
collection = client.create_collection(name="symptom_questions")

collection.add(
    documents=[
        "chest pain: onset, character (sharp/dull/heavy), radiation to arm or jaw, associated symptoms like breathlessness or sweating, severity",
        "headache: onset, character (throbbing/dull/sharp), location (forehead/one side/whole head), associated symptoms like nausea or light sensitivity, severity",
        "stomach pain: onset, character (cramping/burning/sharp), location (upper/lower/whole abdomen), associated symptoms like vomiting or bloating, severity",
        "mouth ulcer: onset, associated symptoms like fever or swollen gums, severity"
    ],
    ids=["chest_pain", "headache", "stomach_pain", "mouth_ulcer"]
)

symptom = input("Enter a symptom: ")

results = collection.query(
    query_texts=[symptom],
    n_results=1
)

print("Closest match:", results["documents"][0][0])