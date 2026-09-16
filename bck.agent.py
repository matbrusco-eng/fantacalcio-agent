from datetime import datetime
os = __import__('os')
re = __import__('re')
unicodedata = __import__('unicodedata')
smtplib = __import__('smtplib')
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
requests = __import__('requests')
from bs4 import BeautifulSoup

# ==========================================
# TRACCIAMENTO VERSIONE (Anti-regressione)
# ==========================================
SCRIPT_VERSION = "v10.0-DOM-Extra-Mile-Infermeria"

# Mappatura basata sugli ID ufficiali estratti dagli URL del DOM
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

def normalizza(testo):
    if not testo:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', testo)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).upper()

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
    msg['Subject'] = f"📊 Report Formazioni [{SCRIPT_VERSION}] - Serie A"
    
    corpo_html = f"""
    <p>Report generato con la versione: <b>{SCRIPT_VERSION}</b> (Parsing DOM avanzato con estrazione descrizioni infortuni)</p>
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
        print(f"Email [{SCRIPT_VERSION}] inviata con successo!")
    except Exception as e:
        print(f"Errore invio email: {e}")

def main():
    print(f"Avvio script {SCRIPT_VERSION} su Fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        giocatori_trovati_live = {}

        # 1. TITOLARI (.starters)
        for starter_list in soup.find_all('ul', class_='starters'):
            for li in starter_list.find_all('li', class_='player-item'):
                a_tag = li.find('a', class_='player-link')
                if a_tag and a_tag.get('href'):
                    id_match = re.search(r'/(\d+)$', a_tag['href'])
                    if id_match:
                        pid = id_match.group(1)
                        perc_div = li.find('div', class_='progress-value')
                        perc_str = perc_div.get_text(strip=True) if perc_div else ""
                        giocatori_trovati_live[pid] = f"TITOLARE ({perc_str})" if perc_str else "TITOLARE"

        # 2. RISERVE / BALLOTTAGGI (.reserves o .ballot-list)
        for reserve_list in soup.find_all('ul', class_=['reserves', 'ballot-list']):
            for li in reserve_list.find_all('li'):
                a_tag = li.find('a', class_='player-link')
                if a_tag and a_tag.get('href'):
                    id_match = re.search(r'/(\d+)$', a_tag['href'])
                    if id_match:
                        pid = id_match.group(1)
                        perc_el = li.find('strong', class_='percentage') or li.find('div', class_='progress-value')
                        perc_str = perc_el.get_text(strip=True) if perc_el else ""
                        giocatori_trovati_live[pid] = f"PANCHINA ({perc_str})" if perc_str else "PANCHINA"

        # 3. INFORTUNATI (.injured-list) CON ESTRAZIONE DESCRIZIONE
        for injured_list in soup.find_all('ul', class_='injured-list'):
            for li in injured_list.find_all('li'):
                a_tag = li.find('a', class_='player-link')
                if a_tag and a_tag.get('href'):
                    id_match = re.search(r'/(\d+)$', a_tag['href'])
                    if id_match:
                        pid = id_match.group(1)
                        desc_p = li.find('p', class_='description')
                        desc_str = desc_p.get_text(strip=True) if desc_p else ""
                        if desc_str:
                            giocatori_trovati_live[pid] = f"INFORTUNATO: {desc_str}"
                        else:
                            giocatori_trovati_live[pid] = "INFORTUNATO"

        # 4. SQUALIFICATI (.suspendeds-list)
        for susp_list in soup.find_all('ul', class_='suspendeds-list'):
            for li in susp_list.find_all('li'):
                a_tag = li.find('a', class_='player-link')
                if a_tag and a_tag.get('href'):
                    id_match = re.search(r'/(\d+)$', a_tag['href'])
                    if id_match:
                        giocatori_trovati_live[id_match.group(1)] = "SQUALIFICATO"

        # Assegnazione finale basata sugli ID mappati
        risultati = {}
        for pid, (nome_giocatore, squadra_default) in GIOCATORI_MAP.items():
            stato_finale = giocatori_trovati_live.get(pid, "Non rilevato")
            risultati[nome_giocatore] = {
                "squadra": squadra_default,
                "stato": stato_finale
            }

        # Costruzione tabella finale con tracciamento versione
        righe_tabella = []
        righe_tabella.append(f"VERSIONE SCRIPT: {SCRIPT_VERSION}")
        righe_tabella.append(f"{'GIOCATORE':<16} | {'SQUADRA':<12} | {'STATO / RUOLO'}")
        righe_tabella.append("-" * 70)
        
        for item in GIOCATORI_MAP.values():
            giac = item[0]
            sq = risultati.get(giac, {}).get("squadra", item[1])
            st = risultati.get(giac, {}).get("stato", "Non rilevato")
            righe_tabella.append(f"{giac:<16} | {sq:<12} | {st}")

        tabella_finale = "\n".join(righe_tabella)
        print(tabella_finale)
        invia_email(tabella_finale)
                
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    main()
