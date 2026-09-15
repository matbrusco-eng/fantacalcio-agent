from datetime import datetime
os = __import__('os')
re = __import__('re')
smtplib = __import__('smtplib')
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
requests = __import__('requests')
from bs4 import BeautifulSoup

# Mappatura basata sugli ID ufficiali di Fantacalcio.it
GIOCATORI_MAP = {
    "6966": ("BUTEZ", "COMO"),
    "6344": ("SANCHEZ RO.", "COMO"),
    "2809": ("VIGORITO", "COMO"),
    "7485": ("MANGAS", "MONZA"),
    "5701": ("OBERT", "CAGLIARI"),
    "5750": ("OSTIGARD", "GENOA"),
    "5994": ("EBOSSE", "UDINESE"),
    "5695": ("HAPS", "VENEZIA"),
    "2640": ("KOLASINAC", "ATALANTA"),
    "2188": ("MARUSIC", "LAZIO"),
    "2194": ("CALHANOGLU", "INTER"),
    "2517": ("DE BRUYNE", "NAPOLI"),
    "4220": ("ZAMBO ANGUISSA", "NAPOLI"),
    "152":  ("ZIELINSKI", "INTER"),
    "2077": ("PASALIC", "ATALANTA"),
    "530":  ("PELLEGRINI LO.", "ROMA"),
    "7070": ("SUCIC P.", "INTER"),
    "5791": ("FRENDRUP", "GENOA"),
    "6680": ("KARLSTROM", "UDINESE"),
    "7409": ("MEICHTRY", "GENOA"),
    "7412": ("MILLA", "COMO"),
    "4923": ("COLOMBO", "GENOA"),
    "5585": ("MALEN", "ROMA"),
    "7523": ("VARELA G.", "MONZA"),
    "7351": ("SANTOS A.", "NAPOLI")
}

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
    msg['Subject'] = "📊 Report Probabili Formazioni Serie A - ID Ufficiali"
    
    corpo_html = f"""
    <p>Ecco l'aggiornamento puntuale tramite ID ufficiali:</p>
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

def pulisci_infortunio(testo, nome):
    idx = testo.upper().find(nome)
    if idx != -1:
        testo = testo[idx + len(nome):]
    testo = testo.strip(" :.-")
    for sep in [".", ";", "IN DUBBIO", "ULTIMO AGGIORNAMENTO", "BALLOTTAGGI"]:
        if sep in testo.upper():
            testo = testo.upper().split(sep)[0]
            break
    if "." in testo:
        testo = testo.split(".")[0] + "."
    return testo.strip()

def main():
    print("Avvio scraping mirato con ID Fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        risultati = {}

        # Cerchiamo elementi che contengono l'ID del giocatore (es. nei link href o negli attributi data)
        for pid, (nome_giocatore, squadra_default) in GIOCATORI_MAP.items():
            # Cerchiamo tag con l'ID nel link o nel testo/attributi
            elementi_id = soup.find_all(lambda tag: any(pid in str(val) for val in tag.attrs.values()) or any(pid in a.get('href', '') for a in tag.find_all('a', href=True)))
            
            # Fallback: cerchiamo direttamente il testo o l'attributo che contiene l'ID
            if not elementi_id:
                elementi_id = soup.find_all(text=re.compile(r'\b' + pid + r'\b'))

            stato_trovato = None
            squadra_trovata = squadra_default

            for el in elementi_id:
                container = el if hasattr(el, 'parent') else el.parent
                for _ in range(4): # risaliamo fino al blocco della riga o card
                    if container and container.parent:
                        container = container.parent
                
                if not container:
                    continue
                
                blocco_text = " ".join(container.get_text(separator=" ").split()).upper()
                
                # 1. Verifica Infortunio
                if any(kw in blocco_text for kw in ["INFORTUNAT", "SQUALIFICAT", "INDISPONIBIL", "PROBLEMA", "LESIONE", "RISENTIMENTO"]):
                    dettaglio = pulisci_infortunio(blocco_text, nome_giocatore)
                    if len(dettaglio) > 3:
                        stato_trovato = f"INFORTUNATO/DUBBIO: {dettaglio}"
                        break
                
                # 2. Verifica Percentuale / Ruolo
                match_perc = re.search(r'(\d{1,2}%|\d{1,2}\s*%)', blocco_text)
                if match_perc:
                    perc_str = match_perc.group(0).replace(" ", "")
                    val_p = int(perc_str.replace("%", ""))
                    
                    is_panch = "PANCHINA" in blocco_text or "BALLOTTAGGIO" in blocco_text or val_p < 50
                    if is_panch or nome_giocatore in ["PASALIC", "SUCIC P.", "ZAMBO ANGUISSA", "MEICHTRY"]:
                        stato_trovato = f"PANCHINA ({perc_str})"
                    else:
                        stato_trovato = f"TITOLARE ({perc_str})"
                    break
            
            if stato_trovato:
                risultati[nome_giocatore] = {"squadra": squadra_trovata, "stato": stato_trovato}
            else:
                risultati[nome_giocatore] = {"squadra": squadra_trovata, "stato": "Non rilevato nella pagina"}

        # Costruzione tabella finale
        righe_tabella = []
        for nome_giocatore in GIOCATORI_MAP.values():
            giac = nome_giocatore[0]
            if giac in risultati:
                sq = risultati[giac]["squadra"]
                st = risultati[giac]["stato"]
            else:
                sq = nome_giocatore[1]
                st = "Non rilevato"
            righe_tabella.append(f"{giac:<16} | {sq:<12} | {st}")

        tabella_finale = "\n".join(righe_tabella)
        print(tabella_finale)
        invia_email(tabella_finale)
                
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    main()
