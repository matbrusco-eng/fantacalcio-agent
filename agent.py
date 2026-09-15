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
    msg['Subject'] = "📊 Report Probabili Formazioni Serie A - Strutturale"
    
    corpo_html = f"""
    <p>Ecco l'aggiornamento puntuale basato sulle sezioni ufficiali:</p>
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
        
        # Testo completo per il recupero esteso degli infortuni
        testo_completo = " ".join(soup.get_text(separator=" ").split())
        testo_completo_maiusc = testo_completo.upper()

        # Analisi dei blocchi HTML per determinare se si trova in panchina o tra i titolari in base alla sezione
        elementi_giocatori = soup.find_all(['div', 'tr', 'li', 'ul', 'section'])
        risultati_trovati = {}
        
        for el in elementi_giocatori:
            testo_elemento = " ".join(el.get_text(separator=" ").split()).upper()
            for giocatore in GIOCATORI_DA_MONITORARE:
                if giocatore in testo_elemento and len(testo_elemento) < 300:
                    # Cerchiamo la percentuale associata se presente
                    parole = testo_elemento.split()
                    perc_trovata = ""
                    for i, p in enumerate(parole):
                        if giocatore in " ".join(parole[max(0, i-2):i+1]):
                            for token in parole[i:]:
                                if "%" in token:
                                    perc_trovata = token
                                    break
                    
                    # Verifichiamo la sezione di appartenenza all'interno dello stesso blocco HTML
                    is_panchina = "PANCHINA" in testo_elemento or "BALLOTTAGGIO" in testo_elemento
                    
                    # Se troviamo un'indicazione esplicita o la percentuale
                    if perc_trovata:
                        if is_panchina and "TITOLARE" not in testo_elemento:
                            stato_desc = f"PANCHINA ({perc_trovata})"
                        else:
                            # Se non è esplicitamente marcato panchina nel blocco, lo consideriamo titolare con percentuale
                            stato_desc = f"TITOLARE ({perc_trovata})"
                        
                        # Salviamo o sovrascriviamo se troviamo il match corretto
                        risultati_trovati[giocatore] = stato_desc

        righe_tabella = []
        for giocatore in GIOCATORI_DA_MONITORARE:
            squadra = "N.D."
            
            if giocatore in risultati_trovati:
                stato = risultati_trovati[giocatore]
            else:
                # Fallback per gli infortunati: estraiamo la descrizione completa senza tagli
                idx = testo_completo_maiusc.find(giocatore)
                if idx != -1:
                    estratto = testo_completo[idx + len(giocatore):idx + len(giocatore) + 140].strip()
                    parti = estratto.split(".")[0] if "." in estratto else estratto[:100]
                    stato = f"INFORTUNATO/DUBBIO: {parti}"
                else:
                    stato = "Non rilevato"
                    
            righe_tabella.append(f"{giocatore:<16} | {squadra:<12} | {stato}")
                
        tabella_finale = "\n".join(righe_tabella)
        print(tabella_finale)
        invia_email(tabella_finale)
                
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    main()
