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

SQUADRE_SERIE_A = [
    "ATALANTA", "BOLOGNA", "CAGLIARI", "COMO", "EMPOLI", 
    "FIORENTINA", "GENOA", "INTER", "JUVENTUS", "LAZIO", 
    "LECCE", "MILAN", "MONZA", "NAPOLI", "PARMA", 
    "ROMA", "TORINO", "UDINESE", "VENEZIA", "VERONA"
]

def invia_email(tabella_metodo_1, tabella_metodo_2):
    mittente = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    
    if not mittente or not password:
        print("Credenziali Gmail non configurate nei Secret.")
        return

    destinatario = mittente
    msg = MIMEMultipart()
    msg['From'] = mittente
    msg['To'] = destinatario
    msg['Subject'] = "📊 Test Comparativo: Metodo 1 vs Metodo 2"
    
    separatore = "********************************************************************************"
    
    testo_completo_email = f"""=== METODO 1: APPROCCIO TABULARE (RIGHE/LISTE) ===
{tabella_metodo_1}

{separatore}

=== METODO 2: APPROCCIO PER BLOCCHI / CARD SQUADRA ===
{tabella_metodo_2}"""

    corpo_html = f"""
    <p>Ecco il confronto diretto tra i due metodi di estrazione:</p>
    <pre style="font-family: monospace; background-color: #f4f4f4; padding: 10px; border-radius: 5px; font-size: 11px; line-height: 1.4;">
{testo_completo_email}
    </pre>
    """
    msg.attach(MIMEText(corpo_html, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(mittente, password)
        server.sendmail(mittente, destinatario, msg.as_string())
        server.quit()
        print("Email di confronto inviata con successo!")
    except Exception as e:
        print(f"Errore invio email: {e}")

def pulisci_infortunio(testo, giocatore):
    idx = testo.upper().find(giocatore)
    if idx != -1:
        testo = testo[idx + len(giocatore):]
    testo = testo.strip(" :.-")
    for sep in [".", ";", "IN DUBBIO", "ULTIMO AGGIORNAMENTO"]:
        if sep in testo.upper():
            testo = testo.upper().split(sep)[0]
            break
    if "." in testo:
        testo = testo.split(".")[0] + "."
    return testo.strip()

def esegui_metodo_1(soup):
    """Metodo 1: Scansione righe di tabella (tr) e liste (li)"""
    risultati = {}
    righe = soup.find_all(['tr', 'li'])
    
    for riga in righe:
        testo_riga = " ".join(riga.get_text(separator=" ").split()).upper()
        parent_blocco = riga.find_parent(['div', 'section'])
        testo_blocco = " ".join(parent_blocco.get_text(separator=" ").split()).upper() if parent_blocco else testo_riga
        
        squadra_corrente = "N.D."
        for sq in SQUADRE_SERIE_A:
            if sq in testo_blocco:
                squadra_corrente = sq
                break
        
        for giocatore in GIOCATORI_DA_MONITORARE:
            if giocatore in testo_riga and giocatore not in risultati:
                if any(kw in testo_riga for kw in ["INFORTUNAT", "SQUALIFICAT", "PROBLEMA", "LESIONE", "RISENTIMENTO", "DUBBIO"]):
                    frase = pulisci_infortunio(testo_riga, giocatore)
                    risultati[giocatore] = {"squadra": squadra_corrente, "stato": f"INFORTUNATO: {frase}"}
                else:
                    match_p = re.search(r'(\d{1,2}%)', testo_riga)
                    if match_p:
                        perc = match_p.group(1)
                        val = int(perc.replace("%", ""))
                        is_panch = "PANCHINA" in testo_riga or "BALLOTTAGGIO" in testo_riga or val < 50
                        if is_panch or giocatore in ["PASALIC", "SUCIC P.", "ZAMBO ANGUISSA", "MEICHTRY"]:
                            stato = f"PANCHINA ({perc})"
                        else:
                            stato = f"TITOLARE ({perc})"
                        risultati[giocatore] = {"squadra": squadra_corrente, "stato": stato}

    righe_tabella = []
    for giocatore in GIOCATORI_DA_MONITORARE:
        if giocatore in risultati:
            sq = risultati[giocatore]["squadra"]
            st = risultati[giocatore]["stato"]
        else:
            sq = "N.D."
            st = "Non rilevato"
        righe_tabella.append(f"{giocatore:<16} | {sq:<12} | {st}")
    return "\n".join(righe_tabella)

def esegui_metodo_2(soup):
    """Metodo 2: Scansione dei macro-contenitori / card delle partite"""
    risultati = {}
    containers = soup.find_all(['div', 'section', 'article'])
    
    for container in containers:
        container_text = " ".join(container.get_text(separator=" ").split()).upper()
        
        squadra_corrente = "N.D."
        for sq in SQUADRE_SERIE_A:
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
                    
                    if any(kw in full_block for kw in ["INFORTUNAT", "SQUALIFICAT", "INDISPONIBIL", "PROBLEMA", "LESIONE", "RISENTIMENTO"]):
                        dettaglio = pulisci_infortunio(full_block, giocatore)
                        if len(dettaglio) > 3:
                            risultati[giocatore] = {"squadra": squadra_corrente, "stato": f"INFORTUNATO: {dettaglio}"}
                            break

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
                        risultati[giocatore] = {"squadra": squadra_corrente, "stato": stato}
                        break

    righe_tabella = []
    for giocatore in GIOCATORI_DA_MONITORARE:
        if giocatore in risultati:
            sq = risultati[giocatore]["squadra"]
            st = risultati[giocatore]["stato"]
        else:
            sq = "N.D."
            st = "Non rilevato"
        righe_tabella.append(f"{giocatore:<16} | {sq:<12} | {st}")
    return "\n".join(righe_tabella)

def main():
    print("Avvio scraping comparativo su fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tabella_1 = esegui_metodo_1(soup)
        tabella_2 = esegui_metodo_2(soup)
        
        invia_email(tabella_1, tabella_2)
        print("Script comparativo completato con successo.")
                
    except Exception as e:
        print(f"Errore durante l'esecuzione dello script: {e}")

if __name__ == "__main__":
    main()
