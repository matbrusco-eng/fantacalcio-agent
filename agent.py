from datetime import datetime
os = __import__('os')
re = __import__('re')
smtplib = __import__('smtplib')
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
requests = __import__('requests')
from bs4 import BeautifulSoup

# Dizionario di mappatura dai nomi scelti alle varianti probabili su Gazzetta (basato sul cognome/chiave)
GIOCATORI_DA_MONITORARE = {
    "SANCHEZ RO.": "SANCHEZ",
    "BUTEZ": "BUTEZ",
    "VIGORITO": "VIGORITO",
    "MANGAS": "MANGAS",
    "OBERT": "OBERT",
    "HAPS": "HAPS",
    "OSTIGARD": "OSTIGARD",
    "EBOSSE": "EBOSSE",
    "KOLASINAC": "KOLASINAC",
    "MARUSIC": "MARUSIC",
    "ZIELINSKI": "ZIELINSKI",
    "DE BRUYNE": "DE BRUYNE",
    "MILLA": "MILLA",
    "FRENDRUP": "FRENDRUP",
    "KARLSTROM": "KARLSTROM",
    "PELLEGRINI LO.": "PELLEGRINI",
    "CALHANOGLU": "CALHANOGLU",
    "MEICHTRY": "MEICHTRY",
    "PASALIC": "PASALIC",
    "SUCIC P.": "SUCIC",
    "ZAMBO ANGUISSA": "ANGUISSA",
    "MALEN": "MALEN",
    "VARELA G.": "VARELA",
    "COLOMBO": "COLOMBO",
    "SANTOS A.": "SANTOS"
}

SQUADRE_SERIE_A = [
    "ATALANTA", "BOLOGNA", "CAGLIARI", "COMO", "EMPOLI", 
    "FIORENTINA", "GENOA", "INTER", "JUVENTUS", "LAZIO", 
    "LECCE", "MILAN", "MONZA", "NAPOLI", "PARMA", 
    "ROMA", "TORINO", "UDINESE", "VENEZIA", "VERONA"
]

def invia_email(testo_tabella):
    mittente = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    
    if not mittente or not password:
        print("Credenziali Gmail non configurate nei Secret.")
        return

    destinatario = mittente
    msg = MIMEMultipart()
    msg['From'] = mittente
    msg['To'] = destinatario
    msg['Subject'] = "📊 Report Gazzetta - Probabili Formazioni Serie A"
    
    corpo_html = f"""
    <p>Ecco l'estrazione effettuata da Gazzetta dello Sport:</p>
    <pre style="font-family: monospace; background-color: #f4f4f4; padding: 10px; border-radius: 5px; font-size: 11px;">
{testo_tabella}
    </pre>
    """
    msg.attach(MIMEText(corpo_html, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(mittente, password)
        server.sendmail(mittente, destinatario, msg.as_string())
        server.quit()
        print("Email inviata con successo!")
    except Exception as e:
        print(f"Errore invio email: {e}")

def main():
    print("Avvio scraping su gazzetta.it/Calcio/prob_form/ ...")
    url = "https://www.gazzetta.it/Calcio/prob_form/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Estraiamo tutto il testo della pagina pulito
        testo_pagina = " ".join(soup.get_text(separator=" ").split())
        testo_pagina_up = testo_pagina.upper()

        risultati = {}
        
        # Analizziamo i blocchi testuali o paragrafi della pagina di Gazzetta
        blocchi = soup.find_all(['p', 'div', 'li', 'span', 'tr'])
        
        for blocco in blocchi:
            testo_blocco = " ".join(blocco.get_text(separator=" ").split()).upper()
            
            # Individuiamo la squadra associata al blocco
            squadra_corrente = "N.D."
            for sq in SQUADRE_SERIE_A:
                if sq in testo_blocco:
                    squadra_corrente = sq
                    break
            
            for nome_originale, chiave in GIOCATORI_DA_MONITORARE.items():
                if chiave in testo_blocco and nome_originale not in risultati:
                    # Determiniamo lo stato in base alle parole chiave nel blocco di Gazzetta
                    if any(kw in testo_blocco for kw in ['INFORTUN', 'SQUALIFIC', 'INDISPONIBIL', 'OUT', 'KO']):
                        stato = f"INFORTUNATO/DUBBIO"
                    elif any(kw in testo_blocco for kw in ['PANCA', 'RISERVA', 'BALLOTTAGGIO']):
                        stato = f"PANCHINA"
                    else:
                        stato = f"TITOLARE"
                        
                    risultati[nome_originale] = {
                        "squadra": squadra_corrente,
                        "stato": stato
                    }

        # Composizione della tabella finale
        righe_tabella = []
        for nome_originale in GIOCATORI_DA_MONITORARE.keys():
            if nome_originale in risultati:
                sq = risultati[nome_originale]["squadra"]
                st = risultati[nome_originale]["stato"]
            else:
                sq = "N.D."
                st = "Non rilevato"
            righe_tabella.append(f"{nome_originale:<16} | {sq:<12} | {st}")

        tabella_finale = "\n".join(righe_tabella)
        print(tabella_finale)
        invia_email(tabella_finale)
                
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    main()
