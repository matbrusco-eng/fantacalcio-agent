from datetime import datetime
os = __import__('os')
re = __import__('re')
unicodedata = __import__('unicodedata')
smtplib = __import__('smtplib')
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
requests = __import__('requests')
from bs4 import BeautifulSoup

# Mappatura basata sugli ID e cognomi ufficiali
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
    """Rimuove accenti e uniforma il testo per facilitare i riscontri"""
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
    msg['Subject'] = "📊 Report Formazioni DOM Mirato - Serie A"
    
    corpo_html = f"""
    <p>Ecco il report basato su parsing HTML mirato:</p>
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

def main():
    print("Avvio parsing strutturato via DOM su Fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Pulizia elementi inutili ma mantenendo i contenitori di squadra/giocatori
        for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
            script_or_style.decompose()

        risultati = {}

        # Cerchiamo blocchi che contengono le squadre o le sezioni di match
        # Su Fantacalcio i box delle singole partite o squadre raggruppano i dati
        blocchi_pagina = soup.find_all(['div', 'section', 'article'])
        
        # Testo globale della pagina per fallback infortuni/squalifiche espliciti
        testo_pagina_norm = normalizza(soup.get_text())

        for pid, (nome_giocatore, squadra_default) in GIOCATORI_MAP.items():
            stato_finale = "Non rilevato"
            nome_norm = normalizza(nome_giocatore)
            cognome_chiave = nome_norm.replace(".", "").split()[0]
            
            # Cerchiamo un blocco HTML circoscritto che menzioni il giocatore
            blocco_trovato = None
            for blocco in blocchi_pagina:
                testo_blocco = normalizza(blocco.get_text())
                if cognome_chiave in testo_blocco:
                    # Scegliamo il blocco più specifico possibile (il testo più corto che contiene il nome)
                    if not blocco_trovato or len(testo_blocco) < len(blocco_trovato):
                        blocco_trovato = blocco

            if blocco_trovato:
                testo_b = normalizza(blocco_trovato.get_text())
                
                # 1. Controllo infortuni / squalifiche specifici nel suo sotto-blocco
                if "SQUALIFICAT" in testo_b:
                    stato_finale = "SQUALIFICATO"
                elif any(kw in testo_b for kw in ["INFORTUNAT", "INDISPONIBIL", "PROBLEMA", "LESIONE", "RISENTIMENTO", "FUORI"]):
                    stato_finale = "INFORTUNATO"
                else:
                    # 2. Cerchiamo la percentuale all'interno del suo blocco
                    match_perc = re.search(r'(\d{1,2}%|\d{1,2}\s*%)', blocco_trovato.get_text())
                    perc_str = match_perc.group(0).replace(" ", "") if match_perc else ""
                    
                    # 3. Verifichiamo se nel suo specifico blocco HTML compare la parola Panchina o Ballottaggio vicino al suo nome
                    # Cerchiamo tag specifici di panchina se presenti nel blocco
                    is_panchina = "PANCHINA" in testo_b or "BALLOTTAGGIO" in testo_b
                    
                    if is_panchina:
                        stato_finale = f"PANCHINA ({perc_str})" if perc_str else "PANCHINA"
                    else:
                        stato_finale = f"TITOLARE ({perc_str})" if perc_str else "TITOLARE"
            else:
                stato_finale = "Non rilevato"

            risultati[nome_giocatore] = {
                "squadra": squadra_default,
                "stato": stato_finale
            }

        # Costruzione tabella finale allineata
        righe_tabella = []
        righe_tabella.append(f"{'GIOCATORE':<16} | {'SQUADRA':<12} | {'STATO / RUOLO'}")
        righe_tabella.append("-" * 50)
        
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
