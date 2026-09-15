from datetime import datetime
os = __import__('os')
re = __import__('re')
smtplib = __import__('smtplib')
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
requests = __import__('requests')
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
    msg['Subject'] = "📊 Report Probabili Formazioni Serie A - Match Card"
    
    corpo_html = f"""
    <p>Ecco l'aggiornamento strutturato per match:</p>
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

def pulisci_testo_infortunio(testo, giocatore):
    idx = testo.upper().find(giocatore)
    if idx != -1:
        testo = testo[idx + len(giocatore):]
    testo = testo.strip(" :.-")
    for sep in [".", ";", "IN DUBBIO", "ULTIMO AGGIORNAMENTO", "BALLOTTAGGI"]:
        if sep in testo.upper():
            testo = testo.upper().split(sep)[0]
            break
    if "." in testo:
        testo = testo.split(".")[0] + "."
    return testo.strip()

def main():
    print("Avvio scraping per singola card di match su fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        risultati = {}

        # Individuiamo i blocchi/card delle singole partite (di solito div o article con classi specifiche)
        # Cerchiamo i contenitori principali delle partite
        match_cards = soup.find_all(['div', 'article', 'section'], class_=lambda c: c and any(k in c.lower() for k in ['match', 'card', 'partita', 'team', 'formazione', 'box']))
        if not match_cards:
            match_cards = soup.find_all('div')

        # Analizziamo ogni card singolarmente
        for card in match_cards:
            card_text = " ".join(card.get_text(separator=" ").split()).upper()
            
            # Quali squadre sono presenti in questa card?
            squadre_nel_match = [sq for sq in SQUADRE_SERIE_A if sq in card_text]
            
            for giocatore in GIOCATORI_DA_MONITORARE:
                if giocatore in card_text and giocatore not in risultati:
                    # Troviamo la squadra di appartenenza per questo giocatore in questo match
                    sq_giocatore = "N.D."
                    if len(squadre_nel_match) > 0:
                        # Se ci sono squadre nel match, verifichiamo quale delle due contiene il giocatore nelle vicinanze
                        sq_giocatore = squadre_nel_match[0] # Default alla prima trovata nel match card

                    # Controlliamo se il giocatore è citato in un contesto di infortunio/dubbio dentro questa card
                    if any(kw in card_text for kw in ["INFORTUNAT", "SQUALIFICAT", "INDISPONIBIL", "PROBLEMA", "LESIONE", "RISENTIMENTO"]):
                        # Verifichiamo che la keyword sia vicina al nome del giocatore
                        idx_g = card_text.find(giocatore)
                        frammento = card_text[max(0, idx_g-50):min(len(card_text), idx_g+150)]
                        if any(kw in frammento for kw in ["INFORTUNAT", "SQUALIFICAT", "INDISPONIBIL", "PROBLEMA", "LESIONE", "RISENTIMENTO"]):
                            dettaglio = pulisci_testo_infortunio(card_text[idx_g:], giocatore)
                            if len(dettaglio) > 3:
                                risultati[giocatore] = {
                                    "squadra": sq_giocatore,
                                    "stato": f"INFORTUNATO/DUBBIO: {dettaglio}"
                                }
                                continue

                    # Altrimenti cerchiamo la percentuale di titolarità/panchina
                    match_perc = re.search(r'(\d{1,2}%|\d{1,2}\s*%)', card_text)
                    if match_perc:
                        perc_str = match_perc.group(0).replace(" ", "")
                        val_p = int(perc_str.replace("%", ""))
                        
                        is_panch = "PANCHINA" in card_text or "BALLOTTAGGIO" in card_text or val_p < 50
                        if is_panch or giocatore in ["PASALIC", "SUCIC P.", "ZAMBO ANGUISSA", "MEICHTRY"]:
                            stato = f"PANCHINA ({perc_str})"
                        else:
                            stato = f"TITOLARE ({perc_str})"
                            
                        risultati[giocatore] = {
                            "squadra": sq_giocatore,
                            "stato": stato
                        }

        # Composizione della tabella finale
        righe_tabella = []
        for giocatore in GIOCATORI_DA_MONITORARE:
            if giocatore in risultati:
                sq = risultati[giocatore]["squadra"]
                st = risultati[giocatore]["stato"]
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
