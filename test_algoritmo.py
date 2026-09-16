import os
import requests
import io
import openpyxl
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

URL_LOGIN = "https://www.fantacalcio.it/api/v1/User/login"
URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"

def calcola_score(fm, presenze, giornate_totali):
    if giornate_totali == 0:
        return 0.0
    c_pres = presenze / giornate_totali
    return round(fm * c_pres, 2)

def carica_rosa():
    with open('rosa.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def invia_email_report(titolari, panchina, dati_rosa, giornate_totali):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")
    email_to = os.environ.get("EMAIL_TO", gmail_user)

    if not gmail_user or not gmail_pass:
        print("⚠️ Secret GMAIL_USER o GMAIL_APP_PASSWORD non trovati. Email non inviata.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"⚽ Fantacalcio - Formazione Consigliata e Stato Rosa (G{giornate_totali})"
    msg["From"] = gmail_user
    msg["To"] = email_to

    # Costruzione Tabella Titolari
    html_titolari = ""
    for g in titolari:
        html_titolari += f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 8px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 8px;"><b>{g['nome']}</b></td>
            <td style="padding: 8px; text-align: center; color: #2e7d32; font-weight: bold;">{g['score']}</td>
            <td style="padding: 8px; text-align: center;">{g['fm']}</td>
            <td style="padding: 8px; text-align: center;">{g['presenze']}/{giornate_totali}</td>
        </tr>
        """

    # Costruzione Tabella Panchina per Numerazione
    html_panchina = ""
    for i, g in enumerate(panchina, 1):
        html_panchina += f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 8px; text-align: center;">{i}</td>
            <td style="padding: 8px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 8px;">{g['nome']}</td>
            <td style="padding: 8px; text-align: center; font-weight: bold;">{g['score']}</td>
            <td style="padding: 8px; text-align: center;">{g['fm']}</td>
            <td style="padding: 8px; text-align: center;">{g['presenze']}/{giornate_totali}</td>
        </tr>
        """

    # Costruzione Tabella Stato Completo Rosa
    html_stato_rosa = ""
    for g in sorted(dati_rosa, key=lambda x: (x['ruolo'], -x['score'])):
        html_stato_rosa += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 6px; text-align: center;">{g['ruolo']}</td>
            <td style="padding: 6px;">{g['nome']}</td>
            <td style="padding: 6px; text-align: center;">{g['score']}</td>
            <td style="padding: 6px; text-align: center;">{g['fm']}</td>
            <td style="padding: 6px; text-align: center;">{g['presenze']}</td>
        </tr>
        """

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">
        <h2 style="color: #1a237e;">⚽ Report Formazione Fantacalcio - Giornata {giornate_totali}</h2>
        
        <h3 style="color: #2e7d32;">🔥 TITOLARI CONSIGLIATI</h3>
        <table style="width: 100%; max-width: 600px; border-collapse: collapse; background: #f9f9f9; margin-bottom: 20px;">
            <thead>
                <tr style="background-color: #2e7d32; color: white;">
                    <th style="padding: 8px;">R</th>
                    <th style="padding: 8px; text-align: left;">Nome</th>
                    <th style="padding: 8px;">Score</th>
                    <th style="padding: 8px;">FM</th>
                    <th style="padding: 8px;">Pres.</th>
                </tr>
            </thead>
            <tbody>
                {html_titolari}
            </tbody>
        </table>

        <h3 style="color: #e65100;">🪑 PANCHINA PER NUMERAZIONE (P -> A -> C -> D)</h3>
        <table style="width: 100%; max-width: 600px; border-collapse: collapse; background: #f9f9f9; margin-bottom: 25px;">
            <thead>
                <tr style="background-color: #e65100; color: white;">
                    <th style="padding: 8px;">#</th>
                    <th style="padding: 8px;">R</th>
                    <th style="padding: 8px; text-align: left;">Nome</th>
                    <th style="padding: 8px;">Score</th>
                    <th style="padding: 8px;">FM</th>
                    <th style="padding: 8px;">Pres.</th>
                </tr>
            </thead>
            <tbody>
                {html_panchina}
            </tbody>
        </table>

        <hr style="border: 0; border-top: 1px solid #ccc; margin: 30px 0;">

        <h3 style="color: #37474f;">📊 STATO E DETTAGLIO COMPLETO DELLA ROSA</h3>
        <table style="width: 100%; max-width: 600px; border-collapse: collapse; font-size: 13px;">
            <thead>
                <tr style="background-color: #37474f; color: white;">
                    <th style="padding: 6px;">Ruolo</th>
                    <th style="padding: 6px; text-align: left;">Nome</th>
                    <th style="padding: 6px;">Score</th>
                    <th style="padding: 6px;">FM</th>
                    <th style="padding: 6px;">Presenze</th>
                </tr>
            </thead>
            <tbody>
                {html_stato_rosa}
            </tbody>
        </table>
        <br>
        <p style="font-size: 12px; color: #777;"><i>Report generato automaticamente dall'algoritmo del Mostro.</i></p>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, email_to, msg.as_string())
        server.quit()
        print("📧 Email con il report inviata con successo!")
    except Exception as e:
        print(f"❌ Errore durante l'invio dell'email: {e}")

def genera_formazione():
    username = os.environ.get("FANTACALCIO_USER")
    password = os.environ.get("FANTACALCIO_PASS")
    
    rosa = carica_rosa()
    ids_mia_rosa = {g['id']: g for g in rosa}
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.fantacalcio.it/'
    })
    
    res_login = session.post(URL_LOGIN, json={"username": username, "password": password})
    if res_login.status_code != 200 or not res_login.json().get("success"):
        print("❌ Errore Login")
        return

    res_excel = session.get(URL_EXCEL_STATS)
    wb = openpyxl.load_workbook(io.BytesIO(res_excel.content), data_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    
    presenze_totali = [riga[5] for riga in rows[2:] if isinstance(riga[5], (int, float))]
    giornate_totali = max(presenze_totali) if presenze_totali else 1
    
    dati_rosa = []
    
    for riga in rows[2:]:
        id_excel = riga[0]
        if id_excel in ids_mia_rosa:
            giocatore_info = ids_mia_rosa[id_excel]
            ruolo = riga[1]
            presenze = riga[5] or 0
            fm = riga[7] or 0.0
            
            score = calcola_score(fm, presenze, giornate_totali)
            dati_rosa.append({
                'id': id_excel,
                'nome': giocatore_info['nome'],
                'ruolo': ruolo,
                'fm': fm,
                'presenze': presenze,
                'score': score
            })

    dati_rosa.sort(key=lambda x: x['score'], reverse=True)

    # 1. Selezione Titolari
    titolari = []
    portieri = [g for g in dati_rosa if g['ruolo'] == 'P']
    if portieri:
        titolari.append(portieri[0])
    
    difensori = [g for g in dati_rosa if g['ruolo'] == 'D']
    titolari.extend(difensori[:3])
    
    ids_scelti = {g['id'] for g in titolari}
    movimento_restante = [g for g in dati_rosa if g['ruolo'] != 'P' and g['id'] not in ids_scelti]
    titolari.extend(movimento_restante[:7])

    # 2. Ordinamento Panchina per Numerazione (P -> A -> C -> D)
    ids_titolari = {g['id'] for g in titolari}
    panchina_grezza = [g for g in dati_rosa if g['id'] not in ids_titolari]
    
    p_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'P'], key=lambda x: x['score'], reverse=True)
    a_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'A'], key=lambda x: x['score'], reverse=True)
    c_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'C'], key=lambda x: x['score'], reverse=True)
    d_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'D'], key=lambda x: x['score'], reverse=True)
    
    panchina = p_panchina + a_panchina + c_panchina + d_panchina

    # Output Console
    print("\n--- ⚽ TITOLARI CONSIGLIATI ---")
    for g in titolari:
        print(f"[{g['ruolo']}] (ID: {g['id']}) {g['nome']} - Score: {g['score']} (FM: {g['fm']}, Pres: {g['presenze']}/{giornate_totali})")
        
    print("\n--- 🪑 PANCHINA PER NUMERAZIONE (P -> A -> C -> D) ---")
    for i, g in enumerate(panchina, 1):
        print(f"{i}. [{g['ruolo']}] (ID: {g['id']}) {g['nome']} - Score: {g['score']} (FM: {g['fm']}, Pres: {g['presenze']}/{giornate_totali})")

    # Invio Email
    invia_email_report(titolari, panchina, dati_rosa, giornate_totali)

    return titolari, panchina

if __name__ == "__main__":
    genera_formazione()
