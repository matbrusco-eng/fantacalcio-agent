from datetime import datetime
os = __import__('os')
smtplib = __import__('smtplib')
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
requests = __import__('requests')
from bs4 import BeautifulSoup

def invia_email(testo_debug):
    mittente = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    
    if not mittente or not password:
        print("Credenziali Gmail non configurate nei Secret.")
        return

    destinatario = mittente
    msg = MIMEMultipart()
    msg['From'] = mittente
    msg['To'] = destinatario
    msg['Subject'] = "🛠️ DEBUG - Dump Testo Pagina Fantacalcio"
    
    corpo_html = f"""
    <p>Ecco il dump testuale grezzo estratto dalla pagina:</p>
    <pre style="font-family: monospace; background-color: #f4f4f4; padding: 10px; border-radius: 5px; font-size: 10px; white-space: pre-wrap;">
{testo_debug[:15000]}  <!-- Limitiamo per sicurezza la dimensione dell'email -->
    </pre>
    """
    msg.attach(MIMEText(corpo_html, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.comms.net', 587) # o smtp.gmail.com
        server = smplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(mittente, password)
        server.sendmail(mittente, destinatario, msg.as_string())
        server.quit()
        print("Email di debug inviata con successo!")
    except Exception as e:
        print(f"Errore invio email debug: {e}")

def main():
    print("Avvio scaricamento pagina per debug...")
    url = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore di connessione: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Puliamo i tag inutili come script e style per alleggerire il testo
        for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
            script_or_style.decompose()

        # Estraiamo tutto il testo mantenendo una minima formattazione a righe
        testo_grezzo = soup.get_text(separator="\n")
        
        # Puliamo le linee vuote di troppo
        linee_pulite = [line.strip() for line in testo_grezzo.splitlines() if line.strip()]
        testo_finale = "\n".join(linee_pulite)
        
        print(f"Testo totale estratto: {len(testo_finale)} caratteri.")
        print(testo_finale[:2000]) # Stampiamo un'anteprima nella console di GitHub Actions
        
        invia_email(testo_finale)
                
    except Exception as e:
        print(f"Errore durante il debug: {e}")

if __name__ == "__main__":
    main()
