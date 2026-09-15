from datetime import datetime
import os
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
    msg['Subject'] = "📊 Report HTML Probabili Formazioni Serie A"
    
    corpo_html = f"""
    <p>Ecco l'estrazione strutturata dai blocchi HTML:</p>
    <pre style="font-family: monospace; background-color: #f4f4f4; padding: 10px; border-radius: 5px; font-size: 13px;">
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
    print("Avvio scraping strutturato di fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cerchiamo tutti i possibili blocchi o righe che contengono i dati dei giocatori nelle tabelle/formazioni
        # Solitamente i calciatori sono all'interno di elementi specifici delle liste squadra
        elementi_giocatori = soup.find_all(['div', 'tr', 'li', 'span'])
        
        # Dizionario per memorizzare i risultati trovati associati
        risultati_trovati = {}
        
        for el in elementi_giocatori:
            testo_elemento = el.get_text(separator=" ").strip().upper()
            for giocatore in GIOCATORI_DA_MONITORARE:
                # Se l'elemento contiene esattamente il nome del giocatore e non è troppo lungo (per evitare interi paragrafi)
                if giocatore in testo_elemento and len(testo_elemento) < 100:
                    # Se troviamo una percentuale o uno stato all'interno dello stesso blocco HTML, salviamolo
                    if "%" in testo_elemento or "PANCHINA" in testo_elemento or "BALLOTTAGGIO" in testo_elemento or "INFORTUNATO" in testo_elemento:
                        risultati_trovati[giocatore] = testo_elemento

        righe_tabella = []
        for giocatore in GIOCATORI_DA_MONITORARE:
            if giocatore in risultati_trovati:
                dettaglio = risultati_trovati[giocatore]
                righe_tabella.append(f"{giocatore:<16} | Trovato HTML: {dettaglio}")
            else:
                righe_tabella.append(f"{giocatore:<16} | Non rilevato nei blocchi")
                
        tabella_finale = "\n".join(righe_tabella)
        print(tabella_finale)
        invia_email(tabella_finale)
                
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    main()
