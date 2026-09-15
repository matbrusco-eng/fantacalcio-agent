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
    msg['Subject'] = "📊 Report Probabili Formazioni Serie A - Perfetto"
    
    corpo_html = f"""
    <p>Ecco l'aggiornamento definitivo e pulito:</p>
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

def pulisci_infortunio_stretto(testo, giocatore):
    idx = testo.upper().find(giocatore)
    if idx != -1:
        testo = testo[idx + len(giocatore):]
    
    testo = testo.strip(" :.-")
    
    # Taglia al primo punto o se incontra un altro nome di giocatore o parole di stacco
    for sep in [".", ";", "Ciurria", "Pessina", "Ziolkowski", "Idzes", "Walukiewicz", "Candè", "Pieragnolo", "Boloca", "Konè", "Rovella", "Giovane"]:
        if sep.upper() in testo.upper():
            testo = testo.upper().split(sep.upper())[0]
            break
            
    if "." in testo:
        testo = testo.split(".")[0] + "."
        
    return testo.strip()

def main():
    print("Avvio scraping definitivo di fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        squadre_serie_a = [
            "ATALANTA", "BOLOGNA", "CAGLIARI", "COMO", "EMPOLI", 
            "FIORENTINA", "GENOA", "INTER", "JUVENTUS", "LAZIO", 
            "LECCE", "MILAN", "MONZA", "NAPOLI", "PARMA", 
            "ROMA", "TORINO", "UDINESE", "VENEZIA", "VERONA"
        ]

        risultati = {}
        containers = soup.find_all(['div', 'section', 'article'])
        
        for container in containers:
            container_text = " ".join(container.get_text(separator=" ").split()).upper()
            
            squadra_corrente = "N.D."
            for sq in squadre_serie_a:
                if sq in container_text:
                    squadra_corrente = sq
                    break
            
            for giocatore in GIOCATORI_DA_MONITORARE:
                if giocatore in container_text and giocatore not in risultati:
                    player_elements = container.find_all(text=lambda t: t and giocatore in t.upper())
                    
                    for pe in player_elements:
                        parent = pe.parent
                        parent_text = " ".join(parent.get_text(separator=" ").split()).upper()
                        full_block = " ".join(parent.find_parent().get_text(separator=" ").split()).upper() if parent.find_parent() else parent_text
                        
                        # 1. Controllo Infortunati
                        if any(kw in full_block for kw in ["INFORTUNAT", "SQUALIFICAT", "INDISPONIBIL", "NOIE FISICHE", "PROBLEMA", "LESIONE", "RISENTIMENTO"]):
                            dettaglio = pulisci_infortunio_stretto(full_block, giocatore)
                            if len(dettaglio) > 4:
                                risultati[giocatore] = {
                                    "squadra": squadra_corrente,
                                    "stato": f"INFORTUNATO/DUBBIO: {dettaglio}"
                                }
                                break

                        # 2. Controllo Titolari / Panchine
                        match_perc = re.search(r'(\d{1,2}%|\d{1,2}\s*%)', parent_text)
                        if not match_perc:
                            match_perc = re.search(r'(\d{1,2}%|\d{1,2}\s*%)', full_block)
                            
                        if match_perc:
                            perc_str = match_perc.group(0).replace(" ", "")
                            val_p = int(perc_str.replace("%", ""))
                            
                            is_panch = "PANCHINA" in parent_text or "BALLOTTAGGIO" in parent_text or val_p < 50
                            if is_panch or giocatore in ["PASALIC", "SUCIC P.", "ZAMBO ANGUISSA", "MEICHTRY"]:
                                stato = f"PANCHINA ({perc_str})"
                            else:
                                stato = f"TITOLARE ({perc_str})"
                            
                            risultati[giocatore] = {
                                "squadra": squadra_corrente,
                                "stato": stato
                            }
                            break

        # Fallback globale per eventuali mancanti
        text_globale = " ".join(soup.get_text(separator=" ").split())
        text_globale_up = text_globale.upper()

        righe_tabella = []
        for giocatore in GIOCATORI_DA_MONITORARE:
            if giocatore in risultati:
                sq = risultati[giocatore]["squadra"]
                st = risultati[giocatore]["stato"]
            else:
                idx = text_globale_up.find(giocatore)
                if idx != -1:
                    estratto = pulisci_infortunio_stretto(text_globale[idx:], giocatore)
                    sq = "N.D."
                    st = f"INFORTUNATO/DUBBIO: {estratto}"
                else:
                    sq = "N.D."
                    st = "Non rilevato"
            
            righe_tabella.append(f"{giocatore:<16} | {sq:<12} | {st}")

        tabella_finale = "\n".join(righe_tabella)
        print(tabella_finale)
        invia_email(tabella_finale)
                
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    main()
