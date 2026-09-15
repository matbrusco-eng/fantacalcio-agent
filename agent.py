from datetime import datetime
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup

GIOCATORI_DA_MONITORARE = [
    "SANCHEZ RO.", "BUTEZ", "VIGORITO", "MANGAS", "OBERT", 
    "HAPS", "OSTIGARD", "EBOSSE", "KOLASINAC", "MARUSIC", 
    "ZIELINSKI", "DE BRUYNE", "MILLA", "FRENDRUP", "KARLSTROM", 
    "PELLEGRINI LO.", "CALHANOGLU", "MEICHTRY", "PASALIC", "SUCIC P.", 
    "ZAMBO ANGUISSA", "MALEN", "VARELA G.", "COLOMBO", "SANTOS A."
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
    msg['Subject'] = "📊 Report Probabili Formazioni Serie A - Strutturato"
    
    corpo_html = f"""
    <p>Ecco l'aggiornamento strutturato delle probabili formazioni:</p>
    <pre style="font-family: monospace; background-color: #f4f4f4; padding: 10px; border-radius: 5px; font-size: 12px;">
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

def pulisci_testo_infortunio(testo, giocatore):
    """Estrae solo la frase relativa all'infortunio del giocatore specifico."""
    # Rimuove il nome del giocatore all'inizio se presente
    idx = testo.upper().find(giocatore)
    if idx != -1:
        testo = testo[idx + len(giocatore):]
    
    # Pulisce spazi e due punti iniziali
    testo = testo.strip(" :.-")
    
    # Tronca al primo punto o alla presenza di un altro giocatore/sezione
    for separatore in [".", ";", "\n"]:
        if separatore in testo:
            testo = testo.split(separatore)[0] + "."
            break
            
    return testo.strip()

def main():
    print("Avvio scraping analitico di fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Mappa dei risultati per giocatore: {giocatore: {"squadra": ..., "stato": ...}}
        risultati = {}

        # 1. Trova tutte le schede partita della giornata
        # Fantacalcio usa blocchi card/match per ogni partita
        schede_partite = soup.find_all(['div', 'article', 'section'], class_=lambda c: c and ('card' in c or 'match' in c or 'ingaggio' in c or 'formazione' in c))
        if not schede_partite:
            schede_partite = soup.find_all('div') # fallback

        # Processiamo la pagina cercando prima i blocchi squadra specifici
        for giocatore in GIOCATORI_DA_MONITORARE:
            # Troviamo tutti gli elementi di testo che contengono esattamente il nome del giocatore
            elementi_trovati = soup.find_all(text=re.compile(re.escape(giocatore), re.IGNORECASE))
            
            for el in elementi_trovati:
                parent = el.parent
                # Risaliamo fino al blocco contenitore della squadra / partita
                blocco_squadra = parent
                for _ in range(5):
                    if blocco_squadra.parent:
                        blocco_squadra = blocco_squadra.parent
                
                testo_blocco = " ".join(blocco_squadra.get_text(separator=" ").split())
                testo_blocco_up = testo_blocco.upper()
                
                # Cerca di rilevare la squadra nel blocco esteso
                squadre_serie_a = [
                    "ATALANTA", "BOLOGNA", "CAGLIARI", "COMO", "EMPOLI", 
                    "FIORENTINA", "GENOA", "INTER", "JUVENTUS", "LAZIO", 
                    "LECCE", "MILAN", "MONZA", "NAPOLI", "PARMA", 
                    "ROMA", "TORINO", "UDINESE", "VENEZIA", "VERONA"
                ]
                squadra_rilevata = "N.D."
                for sq in squadre_serie_a:
                    if sq in testo_blocco_up:
                        squadra_rilevata = sq
                        break

                # A. VERIFICA INFORTUNATI / SQUALIFICATI / INDISPONIBILI
                if any(kw in testo_blocco_up for kw in ["INFORTUNAT", "SQUALIFICAT", "INDISPONIBIL", "NOIE FISICHE", "PROBLEMA", "LESIONE", "RISENTIMENTO"]):
                    # Se il giocatore è chiaramente dentro una frase di infortunio
                    dettaglio = pulisci_testo_infortunio(testo_blocco, giocatore)
                    if len(dettaglio) > 5:
                        risultati[giocatore] = {
                            "squadra": squadra_rilevata,
                            "stato": f"INFORTUNATO/DUBBIO: {dettaglio}"
                        }
                        break

                # B. VERIFICA PERCENTUALE DI TITOLARITÀ / PANCHINA
                # Troviamo la percentuale vicina al nome
                match_perc = re.search(r'(\d{1,2}%|\d{1,2}\s*%)', testo_blocco)
                perc_str = match_perc.group(0).replace(" ", "") if match_perc else ""

                if perc_str:
                    # Determina se si trova nella sezione Panchina/Ballottaggio
                    if "PANCHINA" in testo_blocco_up or "BALLOTTAGGIO" in testo_blocco_up or "PAN." in testo_blocco_up:
                        stato_str = f"PANCHINA ({perc_str})"
                    else:
                        stato_str = f"TITOLARE ({perc_str})"

                    risultati[giocatore] = {
                        "squadra": squadra_rilevata,
                        "stato": stato_str
                    }
                    break

        # Costruzione della tabella finale per l'email
        righe_tabella = []
        for giocatore in GIOCATORI_DA_MONITORARE:
            if giocatore in risultati:
                sq = risultati[giocatore]["squadra"]
                st = risultati[giocatore]["stato"]
            else:
                sq = "N.D."
                st = "Non rilevato nella pagina"
            
            righe_tabella.append(f"{giocatore:<16} | {sq:<12} | {st}")

        tabella_finale = "\n".join(righe_tabella)
        print(tabella_finale)
        invia_email(tabella_finale)
                
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    main()
