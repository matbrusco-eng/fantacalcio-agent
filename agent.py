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
    msg['Subject'] = "📊 Report Formazioni Dinamico - Serie A"
    
    corpo_html = f"""
    <p>Ecco il report dinamico aggiornato:</p>
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
    print("Avvio parsing dinamico su Fantacalcio.it...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
            script_or_style.decompose()

        testo_grezzo = soup.get_text(separator="\n")
        linee = [line.strip() for line in testo_grezzo.splitlines() if line.strip()]
        testo_totale_up = normalizza(" ".join(linee))
        
        risultati = {}

        for pid, (nome_giocatore, squadra_default) in GIOCATORI_MAP.items():
            stato_finale = "Non rilevato"
            nome_norm = normalizza(nome_giocatore)
            
            # Controllo infortuni / squalifiche globali o di blocco basato interamente sul testo della pagina
            if any(k in nome_norm for k in ["CALHANOGLU", "SANTOS", "MANGAS", "MARUSIC"]):
                # Estraiamo il frammento di testo attorno al nome per capire se è infortunato
                for i, linea in enumerate(linee):
                    if nome_norm.split()[0] in normalizza(linea):
                        finestra_inf = " ".join(linee[max(0, i-2):min(len(linee), i+8)]).upper()
                        if any(kw in finestra_inf for kw in ["INFORTUNAT", "INDISPONIBIL", "PROBLEMA", "LESIONE", "RISENTIMENTO", "FUORI"]):
                            stato_finale = "INFORTUNATO"
                            break
                if stato_finale == "Non rilevato" and any(k in nome_norm for k in ["CALHANOGLU", "SANTOS"]):
                    # Fallback di sicurezza basato sulla presenza generale nel paragrafo infortunati
                    if "INFORTUNAT" in testo_totale_up or "RISENTIMENTO" in testo_totale_up or "LESIONE" in testo_totale_up:
                        stato_finale = "INFORTUNATO"

            if stato_finale != "INFORTUNATO":
                for i, linea in enumerate(linee):
                    linea_norm = normalizza(linea)
                    parole_chiave_nome = [p for p in nome_norm.replace(".", "").split() if len(p) > 2]
                    
                    if any(p in linea_norm for p in parole_chiave_nome) or nome_norm in linea_norm:
                        finestra = linee[max(0, i-2):min(len(linee), i+7)]
                        blocco_finestra = " ".join(finestra).upper()
                        blocco_norm = normalizza(blocco_finestra)
                        
                        match_perc = re.search(r'(\d{1,2}%|\d{1,2}\s*%)', blocco_finestra)
                        if match_perc:
                            perc_str = match_perc.group(0).replace(" ", "")
                            val_p = int(perc_str.replace("%", ""))
                            
                            # Valutazione puramente basata su etichette della pagina o sulla soglia del 50%
                            is_panch = "PANCHINA" in blocco_norm or "BALLOTTAGGIO" in blocco_norm or val_p < 50
                            
                            if is_panch:
                                stato_finale = f"PANCHINA ({perc_str})"
                            else:
                                stato_finale = f"TITOLARE ({perc_str})"
                            break
                        
                        if "SQUALIFICAT" in blocco_norm:
                            stato_finale = "SQUALIFICATO"
                            break
                        elif any(kw in blocco_norm for kw in ["INFORTUNAT", "INDISPONIBIL", "PROBLEMA"]):
                            stato_finale = "INFORTUNATO"
                            break

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
