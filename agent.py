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
    msg['Subject'] = "📊 Report Pulito Probabili Formazioni Serie A"
    
    corpo_html = f"""
    <p>Ecco l'estrazione pulita e strutturata dei tuoi giocatori:</p>
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
    print("Avvio scraping e pulizia dati di fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Raccolta dai blocchi strutturati (percentuali)
        elementi_giocatori = soup.find_all(['div', 'tr', 'li', 'span'])
        risultati_trovati = {}
        
        for el in elementi_giocatori:
            testo_elemento = " ".join(el.get_text(separator=" ").split()).upper()
            for giocatore in GIOCATORI_DA_MONITORARE:
                if giocatore in testo_elemento and len(testo_elemento) < 100:
                    if "%" in testo_elemento:
                        # Estraiamo la percentuale pulita dal blocco
                        parole = testo_elemento.split()
                        for i, p in enumerate(parole):
                            if giocatore in " ".join(parole[max(0, i-2):i+1]):
                                # Cerca un token percentuale vicino
                                for token in parole[i:]:
                                    if "%" in token:
                                        risultati_trovati[giocatore] = token
                                        break

        # 2. Testo completo per il fallback (infortuni / assenze)
        testo_completo = " ".join(soup.get_text(separator=" ").split()).upper()

        righe_tabella = []
        for giocatore in GIOCATORI_DA_MONITORARE:
            if giocatore in risultati_trovati:
                stato = f"Titolare/Ballottaggio ({risultati_trovati[giocatore]})"
            else:
                # Fallback: controlliamo se menzionato in contesti di infortunio o altro nel testo
                idx = testo_completo.find(giocatore)
                if idx != -1:
                    estratto = testo_completo[idx + len(giocatore):idx + len(giocatore) + 40].strip()
                    stato = f"Segnalato: {estratto[:30]}..."
                else:
                    stato = "Non rilevato"
                    
            righe_tabella.append(f"{giocatore:<16} | {stato}")
                
        tabella_finale = "\n".join(righe_tabella)
        print(tabella_finale)
        invia_email(tabella_finale)
                
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    main()
