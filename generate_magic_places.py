from datetime import datetime

def get_magic_places(birth_date: str, birth_time: str, birth_place: str):
    """
    Liefert die Top-Orte für Liebe, Karriere, Gesundheit.
    TODO: Hier deine echte Logik einbauen (aktuell Dummy).
    """
    return {
        "love": ["Berlin – 💕 Venus-Linie: Partnerschaft & Schönheit"],
        "career": ["New York – 💼 Sonne-MC: Strahlkraft & Berufung"],
        "health": ["Bali – 🧘 Mond-IC: Rückzug & emotionale Tiefe"]
    }

# -------------------------------------------
# Optional: Standalone Modus für Tests
# -------------------------------------------
if __name__ == "__main__":
    name = "Anna Mustermann"
    geburtstag = "04.07.1983"
    orte_liebe = ["Berlin – 💕 Venus-Linie: Partnerschaft & Schönheit"]
    orte_karriere = ["New York – 💼 Sonne-MC: Strahlkraft & Berufung"]
    orte_heilung = ["Bali – 🧘 Mond-IC: Rückzug & emotionale Tiefe"]

    print("🌟 Testauswertung")
    print("Liebe:", orte_liebe)
    print("Karriere:", orte_karriere)
    print("Heilung:", orte_heilung)
