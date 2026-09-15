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
    msg['Subject'] = "📊 Report Probabili Formazioni Serie A (Aggiornato)"
    
    corpo_html = f"""
    <p>Ecco l'analisi dettagliata per i tuoi giocatori:</p>
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
    print("Avvio scraping di https://www.fantacalcio.it/probabili-formazioni-serie-a ...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Pulizia del testo della pagina
        testo_pagina = soup.get_text(separator=" ")
        testo_pagina_maiusc = " ".join(testo_pagina.split()).upper()
        
        righe_tabella = []
        for giocatore in GIOCATORI_DA_MONITORARE:
            giocatore_upper = giocatore.upper()
            
            if giocatore_upper in testo_pagina_maiusc:
                # Troviamo la prima occorrenza rilevante e prendiamo i caratteri subito successivi
                idx = testo_pagina_maiusc.find(giocatore_upper)
                # Estraiamo un pezzo successivo per catturare la percentuale o lo stato (es. " 85% " o " PANCHINA ")
                fine = min(len(testo_pagina_maiusc), idx + len(giocatore_upper) + 25)
                contesto_successivo = testo_pagina_maiusc[idx + len(giocatore_upper):fine].strip()
                
                # Puliamo eventuali spazi multipli
                contesto_successivo = " ".join(contesto_successivo.split())
                
                righe_tabella.append(f"{giocatore:<16} | Info: {contesto_successivo}")
            else:
                righe_tabella.append(f"{giocatore:<16} | Non trovato")
                
        tabella_finale = "\n".join(righe_tabella)
        print(tabella_finale)
        invia_email(tabella_finale)
                
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    main()
