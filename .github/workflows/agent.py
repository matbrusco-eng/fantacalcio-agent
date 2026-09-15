from datetime import datetime
import requests
from bs4 import BeautifulSoup

# La tua lista fissa di giocatori da monitorare
GIOCATORI_DA_MONITORARE = [
    "SANCHEZ RO.", "BUTEZ", "VIGORITO", "MANGAS", "OBERT", 
    "HAPS", "OSTIGARD", "EBOSSE", "KOLASINAC", "MARUSIC", 
    "ZIELINSKI", "DE BRUYNE", "MILLA", "FRENDRUP", "KARLSTROM", 
    "PELLEGRINI LO.", "CALHANOGLU", "MEICHTRY", "PASALIC", "SUCIC P.", 
    "ZAMBO ANGUISSA", "MALEN", "VARELA G.", "COLOMBO", "SANTOS A."
]

def get_calendario_serie_a():
    # Calendario di riferimento per la stagione 2026/27 (prima partita di ogni giornata)
    return {
        1: datetime(2026, 8, 22).date(),
        2: datetime(2026, 8, 28).date(),
        3: datetime(2026, 9, 4).date(),
        4: datetime(2026, 9, 11).date(),
        5: datetime(2026, 9, 18).date(), # 5ª giornata (venerdì 18 settembre 2026)
        6: datetime(2026, 10, 10).date(),
        7: datetime(2026, 10, 16).date(),
        8: datetime(2026, 10, 23).date(),
        # Aggiungi qui le altre date se necessario per coprire tutto il campionato
    }

def main():
    oggi = datetime.now().date()
    calendario = get_calendario_serie_a()
    
    giornata_attiva = None
    for giornata, data_partita in calendario.items():
        if data_partita == oggi:
            giornata_attiva = giornata
            break
            
    # PER IL TEST DI OGGI (15 Settembre 2026): forziamo l'esecuzione per testare lo scraping
    # (Commenta o rimuovi la riga sotto quando il sistema andrà a regime con le date reali)
    giornata_attiva = 5 

    if not giornata_attiva:
        print(f"Oggi ({oggi}) non è la data della prima partita. L'agent si ferma.")
        return

    print(f"Avvio scraping di fantacalcio.it per la Giornata {giornata_attiva}...")
    
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        testo_pagina = soup.get_text().upper()
        
        print("\n--- RISULTATO ANALISI GIOCATORI ---")
        tabella_risultati = []
        
        for giocatore in GIOCATORI_DA_MONITORARE:
            # Ricerca euristica basilare all'interno del testo della pagina
            if giocatore in testo_pagina:
                stato = "Presente in elenco / Da verificare"
                tabella_risultati.append(f"| {giocatore:<18} | Rilevato nella pagina di giornata |")
            else:
                tabella_risultati.append(f"| {giocatore:<18} | Non rilevato / Turno differente |")
                
        for riga in tabella_risultati:
            print(riga)
            
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    main()
