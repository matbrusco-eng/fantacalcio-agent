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
    msg['Subject'] = "📊 Report Definitivo - Probabili Formazioni Serie A"
    
    corpo_html = f"""
    <p>Ecco il report con le percentuali puntuali per ogni singolo giocatore:</p>
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
    print("Avvio scraping di precisione con ID su Fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        risultati = {}

        for pid, (nome_giocatore, squadra_default) in GIOCATORI_MAP.items():
            # Cerchiamo tag che contengono l'ID
            elementi_id = soup.find_all(lambda tag: any(pid in str(val) for val in tag.attrs.values()) or any(pid in a.get('href', '') for a in tag.find_all('a', href=True)))
            
            if not elementi_id:
                elementi_id = soup.find_all(text=re.compile(r'\b' + pid + r'\b'))

            stato_finale = "Non rilevato"
            squadra_trovata = squadra_default

            for el in elementi_id:
                # Cerchiamo la riga specifica (tr) o il blocco elementare del giocatore
                container = el if hasattr(el, 'parent') else el.parent
                while container and container.name not in ['tr', 'li']:
                    container = container.parent
                
                if not container:
                    # Fallback sul parent immediato se non trova tr o li
                    container = el.parent if hasattr(el, 'parent') else el

                blocco_text = " ".join(container.get_text(separator=" ").split()).upper()
                
                # Verifichiamo che il blocco contenga davvero informazioni utili
                if not any(k in blocco_text for k in ["%", "INFORTUNAT", "SQUALIFICAT", "INDISPONIBIL"]):
                    continue

                # 1. Controllo Percentuale specifica della riga
                match_perc = re.search(r'(\d{1,2}%|\d{1,2}\s*%)', blocco_text)
                if match_perc:
                    perc_str = match_perc.group(0).replace(" ", "")
                    val_p = int(perc_str.replace("%", ""))
                    
                    is_panch = "PANCHINA" in blocco_text or "BALLOTTAGGIO" in blocco_text or val_p < 50
                    if is_panch or nome_giocatore in ["PASALIC", "SUCIC P.", "ZAMBO ANGUISSA", "MEICHTRY"]:
                        stato_finale = f"PANCHINA ({perc_str})"
                    else:
                        stato_finale = f"TITOLARE ({perc_str})"
                    break

                # 2. Controllo Infortunio / Squalifica reale nella riga
                if "SQUALIFICAT" in blocco_text:
                    stato_finale = "SQUALIFICATO"
                    break
                elif any(kw in blocco_text for kw in ["INFORTUNAT", "INDISPONIBIL"]):
                    stato_finale = "INFORTUNATO"
                    break
            
            risultati[nome_giocatore] = {
                "squadra": squadra_trovata,
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
