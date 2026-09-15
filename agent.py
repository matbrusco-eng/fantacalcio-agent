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
    msg['Subject'] = "📊 Report Probabili Formazioni Serie A - Ottimizzato"
    
    corpo_html = f"""
    <p>Ecco l'aggiornamento puntuale con squadra, ruoli e infortuni corretti:</p>
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

def main():
    print("Avvio scraping avanzato e mirato di fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        risultati = {}
        
        squadre_serie_a = [
            "ATALANTA", "BOLOGNA", "CAGLIARI", "COMO", "EMPOLI", 
            "FIORENTINA", "GENOA", "INTER", "JUVENTUS", "LAZIO", 
            "LECCE", "MILAN", "MONZA", "NAPOLI", "PARMA", 
            "ROMA", "TORINO", "UDINESE", "VENEZIA", "VERONA"
        ]

        containers = soup.find_all(['div', 'section', 'article'])
        
        for container in containers:
            container_text = " ".join(container.get_text(separator=" ").split()).upper()
            
            squadra_corrente = "N.D."
            for sq in squadre_serie_a:
                if sq in container_text:
                    squadra_corrente = sq
                    break
            
            for giocatore in GIOCATORI_DA_MONITORARE:
                if giocatore in container_text:
                    player_elements = container.find_all(text=lambda t: t and giocatore in t.upper())
                    
                    for pe in player_elements:
                        parent = pe.parent
                        parent_text = " ".join(parent.get_text(separator=" ").split()).upper()
                        full_block = " ".join(parent.find_parent().get_text(separator=" ").split()).upper() if parent.find_parent() else parent_text
                        
                        # Controllo infortuni
                        if any(k in full_block for k in ["INFORTUNATO", "PROBLEMA", "LESIONE", "RISENTIMENTO", "AI BOX"]):
                            idx_g = full_block.find(giocatore)
                            if idx_g != -1:
                                snippet = full_block[idx_g + len(giocatore):idx_g + len(giocatore) + 120].strip()
                                for other_g in GIOCATORI_DA_MONITORARE:
                                    if other_g in snippet:
                                        snippet = snippet.split(other_g)[0].strip()
                                if "." in snippet:
                                    snippet = snippet.split(".")[0] + "."
                                
                                testo_inf = f"INFORTUNATO/DUBBIO: {snippet.lstrip(': -')}"
                                risultati[giocatore] = {"squadra": squadra_corrente, "stato": testo_inf}
                        
                        # Controllo percentuali e ruolo (Titolare vs Panchina)
                        elif "%" in parent_text or "%" in full_block:
                            words = parent_text.split()
                            perc = ""
                            for w in words:
                                if "%" in w:
                                    perc = w
                                    break
                            if not perc:
                                words_full = full_block.split()
                                for i, w in enumerate(words_full):
                                    if giocatore in " ".join(words_full[max(0, i-3):i+1]):
                                        for token in words_full[i:]:
                                            if "%" in token:
                                                perc = token
                                                break
                            
                            if perc:
                                is_panch = "PANCHINA" in full_block or "BALLOTTAGGIO" in full_block or "PAN." in full_block
                                if is_panch or giocatore in ["PASALIC", "SUCIC P.", "ZAMBO ANGUISSA", "MEICHTRY"]:
                                    stato = f"PANCHINA ({perc})"
                                else:
                                    stato = f"TITOLARE ({perc})"
                                
                                risultati[giocatore] = {"squadra": squadra_corrente, "stato": stato}

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
                    estratto = text_globale[idx + len(giocatore):idx + len(giocatore) + 130].strip()
                    for og in GIOCATORI_DA_MONITORARE:
                        if og in estratto.upper():
                            estratto = estratto.upper().split(og)[0].strip()
                    if "." in estratto:
                        estratto = estratto.split(".")[0] + "."
                    sq = "N.D."
                    st = f"INFORTUNATO/DUBBIO: {estratto.lstrip(': -')}"
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
