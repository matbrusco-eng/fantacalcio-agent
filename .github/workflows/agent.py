Python
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def get_calendario_serie_a():
    # Mappa di esempio delle date della prima partita per ogni giornata della Serie A 2026/27
    return {
        1: datetime(2026, 8, 22).date(),
        2: datetime(2026, 8, 28).date(),
        3: datetime(2026, 9, 4).date(),
        4: datetime(2026, 9, 11).date(),
        5: datetime(2026, 9, 18).date(), # 5ª giornata (venerdì 18 settembre 2026)
        6: datetime(2026, 10, 10).date(),
        # Aggiungeremo progressivamente le altre se necessario
    }

def main():
    oggi = datetime.now().date()
    calendario = get_calendario_serie_a()

    giornata_attiva = None
    for giornata, data_partita in calendario.items():
        if data_partita == oggi:
            giornata_attiva = giornata
            break

    if not giornata_attiva:
        print(f"Oggi ({oggi}) non è la data della prima partita di nessuna giornata monitorata. L'agent si ferma.")
        return

    print(f"Oggi è il giorno della prima partita per la {giornata_attiva}ª Giornata! Avvio scraping di fantacalcio.it...")

    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("Pagina scaricata con successo! Qui elaboreremo la tua lista di giocatori.")
        # Qui inseriremo la logica di parsing della tabella che abbiamo visto insieme
    else:
        print(f"Errore di connessione al sito: {response.status_code}")

if __name__ == "__main__":
    main()
