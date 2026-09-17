import os
import requests
import io
import openpyxl
import json
import smtplib
import re
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

URL_LOGIN = "https://www.fantacalcio.it/api/v1/User/login"
URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"
URL_PROBABILI_FORMAZIONI = "https://www.fantacalcio.it/probabili-formazioni-serie-a"

RUOLI_ORDINE = {'P': 1, 'D': 2, 'C': 3, 'A': 4}

def calcola_score(fm, presenze, giornate_totali):
    if giornate_totali == 0:
        return 0.0
    c_pres = presenze / giornate_totali
    return round(fm * c_pres, 2)

def carica_json(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def recupera_stato_infermeria_live(session):
    giocatori_trovati_live = {}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = session.get(URL_PROBABILI_FORMAZIONI, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            for starter_list in soup.find_all('ul', class_='starters'):
                for li in starter_list.find_all('li', class_='player-item'):
                    a_tag = li.find('a', class_='player-link')
                    if a_tag and a_tag.get('href'):
                        id_match = re.search(r'/(\d+)$', a_tag['href'])
                        if id_match:
                            pid = id_match.group(1)
                            perc_div = li.find('div', class_='progress-value')
                            perc_str = perc_div.get_text(strip=True) if perc_div else "80%"
                            giocatori_trovati_live[pid] = {
                                "stato": "TITOLARE",
                                "perc": perc_str,
                                "note": "Disponibile"
                            }

            for reserve_list in soup.find_all('ul', class_=['reserves', 'ballot-list']):
                for li in reserve_list.find_all('li'):
                    a_tag = li.find('a', class_='player-link')
                    if a_tag and a_tag.get('href'):
                        id_match = re.search(r'/(\d+)$', a_tag['href'])
                        if id_match:
                            pid = id_match.group(1)
                            if pid not in giocatori_trovati_live:
                                perc_el = li.find('strong', class_='percentage') or li.find('div', class_='progress-value')
                                perc_str = perc_el.get_text(strip=True) if perc_el else "50%"
                                giocatori_trovati_live[pid] = {
                                    "stato": "PANCHINA",
                                    "perc": perc_str,
                                    "note": "Disponibile"
                                }

            for injured_list in soup.find_all('ul', class_='injured-list'):
                for li in injured_list.find_all('li'):
                    a_tag = li.find('a', class_='player-link')
                    if a_tag and a_tag.get('href'):
                        id_match = re.search(r'/(\d+)$', a_tag['href'])
                        if id_match:
                            pid = id_match.group(1)
                            desc_p = li.find('p', class_='description')
                            desc_str = desc_p.get_text(strip=True) if desc_p else "Infortunato"
                            giocatori_trovati_live[pid] = {
                                "stato": "INFORTUNATO",
                                "perc": "0%",
                                "note": desc_str
                            }

            for susp_list in soup.find_all('ul', class_='suspendeds-list'):
                for li in susp_list.find_all('li'):
                    a_tag = li.find('a', class_='player-link')
                    if a_tag and a_tag.get('href'):
                        id_match = re.search(r'/(\d+)$', a_tag['href'])
                        if id_match:
                            pid = id_match.group(1)
                            desc_p = li.find('p', class_='description')
                            desc_str = desc_p.get_text(strip=True) if desc_p else "Squalificato"
                            giocatori_trovati_live[pid] = {
                                "stato": "SQUALIFICATO",
                                "perc": "0%",
                                "note": desc_str
                            }
    except Exception as e:
        print(f"⚠️ Errore durante lo scraping dell'infermeria: {e}")

    return giocatori_trovati_live

def invia_email_report(titolari, panchina, dati_rosa, giornate_totali):
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

    # 1. Tabella Titolari con Squadra
    titolari_ordinati = sorted(titolari, key=lambda x: (RUOLI_ORDINE.get(x['ruolo'], 99), -x['score']))
    html_titolari = ""
    for i, g in enumerate(titolari_ordinati, 1):
        bordo = "border-bottom: 2px solid #555;" if i < len(titolari_ordinati) and g['ruolo'] != titolari_ordinati[i]['ruolo'] else "border-bottom: 1px solid #e0e0e0;"
        html_titolari += f"""
        <tr style="{bordo}">
            <td style="padding: 3px 6px; text-align: center;">{i}</td>
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 6px;"><b>{g['nome']}</b></td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #555;">{g['squadra']}</td>
            <td style="padding: 3px 6px; text-align: center; color: #2e7d32; font-weight: bold;">{g['score']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['fm']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['gol']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['assist']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['presenze']}/{giornate_totali}</td>
        </tr>
        """

    # 2. Tabella Panchina con Squadra
    html_panchina = ""
    for i, g in enumerate(panchina, 1):
        bordo = "border-bottom: 2px solid #555;" if i < len(panchina) and g['ruolo'] != panchina[i]['ruolo'] else "border-bottom: 1px solid #e0e0e0;"
        html_panchina += f"""
        <tr style="{bordo}">
            <td style="padding: 3px 6px; text-align: center;">{i}</td>
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 6px;">{g['nome']}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #555;">{g['squadra']}</td>
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['score']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['fm']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['gol']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['assist']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['presenze']}/{giornate_totali}</td>
        </tr>
        """

    # 3. Tabella Stato Rosa Completa con Squadra
    rosa_ordinata_stato = sorted(dati_rosa, key=lambda x: (RUOLI_ORDINE.get(x['ruolo'], 99), -x['score']))
    html_stato_rosa = ""
    for i, g in enumerate(rosa_ordinata_stato):
        bordo = "border-bottom: 2px solid #555;" if i < len(rosa_ordinata_stato) - 1 and g['ruolo'] != rosa_ordinata_stato[i+1]['ruolo'] else "border-bottom: 1px solid #eee;"
        colore_stato = "#2e7d32" if g['stato'] == "TITOLARE" else ("#e65100" if g['stato'] == "PANCHINA" else "#c62828")
        html_stato_rosa += f"""
        <tr style="{bordo}">
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 6px;"><b>{g['nome']}</b></td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #555;">{g['squadra']}</td>
            <td style="padding: 3px 6px; text-align: center; color: {colore_stato}; font-weight: bold;">{g['stato']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['perc_voto']}</td>
            <td style="padding: 3px 6px; font-size: 11px;">{g['note']}</td>
        </tr>
        """

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.2; font-size: 13px;">
        <h3 style="color: #1a237e; margin: 0 0 8px 0;">⚽ Report Formazione Fantacalcio - Giornata {giornate_totali}</h3>
        
        <b style="color: #2e7d32; font-size: 14px;">🔥 TITOLARI CONSIGLIATI</b>
        <table style="width: 100%; max-width: 620px; border-collapse: collapse; background: #f9f9f9; margin: 4px 0 12px 0;">
            <thead>
                <tr style="background-color: #2e7d32; color: white;">
                    <th style="padding: 4px 6px;">#</th>
                    <th style="padding: 4px 6px;">R</th>
                    <th style="padding: 4px 6px; text-align: left;">Nome</th>
                    <th style="padding: 4px 6px;">Squadra</th>
                    <th style="padding: 4px 6px;">Score</th>
                    <th style="padding: 4px 6px;">FM</th>
                    <th style="padding: 4px 6px;">G</th>
                    <th style="padding: 4px 6px;">A</th>
                    <th style="padding: 4px 6px;">Pres.</th>
                </tr>
            </thead>
            <tbody>
                {html_titolari}
            </tbody>
        </table>

        <b style="color: #e65100; font-size: 14px;">🪑 PANCHINA PER NUMERAZIONE (P -> A -> C -> D)</b>
        <table style="width: 100%; max-width: 620px; border-collapse: collapse; background: #f9f9f9; margin: 4px 0 16px 0;">
            <thead>
                <tr style="background-color: #e65100; color: white;">
                    <th style="padding: 4px 6px;">#</th>
                    <th style="padding: 4px 6px;">R</th>
                    <th style="padding: 4px 6px; text-align: left;">Nome</th>
                    <th style="padding: 4px 6px;">Squadra</th>
                    <th style="padding: 4px 6px;">Score</th>
                    <th style="padding: 4px 6px;">FM</th>
                    <th style="padding: 4px 6px;">G</th>
                    <th style="padding: 4px 6px;">A</th>
                    <th style="padding: 4px 6px;">Pres.</th>
                </tr>
            </thead>
            <tbody>
                {html_panchina}
            </tbody>
        </table>

        <hr style="border: 0; border-top: 1px solid #ccc; margin: 12px 0;">

        <b style="color: #37474f; font-size: 14px;">📊 STATO E DISPONIBILITÀ ROSA (AGENT.PY v10.0)</b>
        <table style="width: 100%; max-width: 620px; border-collapse: collapse; font-size: 12px; margin-top: 4px;">
            <thead>
                <tr style="background-color: #37474f; color: white;">
                    <th style="padding: 4px 6px;">R</th>
                    <th style="padding: 4px 6px; text-align: left;">Nome</th>
                    <th style="padding: 4px 6px;">Squadra</th>
                    <th style="padding: 4px 6px;">Stato</th>
                    <th style="padding: 4px 6px;">% Voto</th>
                    <th style="padding: 4px 6px; text-align: left;">Note / Infortuni</th>
                </tr>
            </thead>
            <tbody>
                {html_stato_rosa}
            </tbody>
        </table>
        <p style="font-size: 11px; color: #777; margin-top: 10px;"><i>Report generato automaticamente dall'algoritmo del Mostro v10.0.</i></p>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, email_to, msg.as_string())
        server.quit()
        print("📧 Email inviata con successo!")
    except Exception as e:
        print(f"❌ Errore durante l'invio dell'email: {e}")

def genera_formazione():
    username = os.environ.get("FANTACALCIO_USER")
    password = os.environ.get("FANTACALCIO_PASS")
    
    rosa = carica_json('rosa.json')
    ids_mia_rosa = {str(g['id']): g for g in rosa}
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
    
    dati_probabili = recupera_stato_infermeria_live(session)
    
    presenze_totali = [riga[5] for riga in rows[2:] if isinstance(riga[5], (int, float))]
    giornate_totali = max(presenze_totali) if presenze_totali else 1
    
    dati_rosa = []
    
    for riga in rows[2:]:
        id_excel = str(riga[0])
        if id_excel in ids_mia_rosa:
            giocatore_info = ids_mia_rosa[id_excel]
            ruolo = riga[1]
            
            # Lettura squadra dalla Colonna 5 (indice 4)
            squadra = str(riga[4]).upper() if len(riga) > 4 and riga[4] else "N/D"
            
            presenze = riga[5] or 0
            fm = riga[7] or 0.0
            
            gol = riga[8] if len(riga) > 8 and isinstance(riga[8], (int, float)) else 0
            assist = riga[14] if len(riga) > 14 and isinstance(riga[14], (int, float)) else 0
            
            score = calcola_score(fm, presenze, giornate_totali)
            
            info_live = dati_probabili.get(id_excel, {})
            
            stato = info_live.get('stato', "TITOLARE" if presenze > 0 else "PANCHINA")
            perc_voto = info_live.get('perc', f"{min(100, int((presenze/giornate_totali)*100))}%")
            note = info_live.get('note', "Disponibile")

            dati_rosa.append({
                'id': id_excel,
                'nome': giocatore_info['nome'],
                'ruolo': ruolo,
                'squadra': squadra,
                'fm': fm,
                'gol': int(gol),
                'assist': int(assist),
                'presenze': presenze,
                'score': score,
                'stato': stato,
                'perc_voto': perc_voto,
                'note': note
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

    # 2. Panchina per Numerazione (P -> A -> C -> D)
    ids_titolari = {g['id'] for g in titolari}
    panchina_grezza = [g for g in dati_rosa if g['id'] not in ids_titolari]
    
    p_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'P'], key=lambda x: x['score'], reverse=True)
    a_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'A'], key=lambda x: x['score'], reverse=True)
    c_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'C'], key=lambda x: x['score'], reverse=True)
    d_panchina = sorted([g for g in panchina_grezza if g['ruolo'] == 'D'], key=lambda x: x['score'], reverse=True)
    
    panchina = p_panchina + a_panchina + c_panchina + d_panchina

    invia_email_report(titolari, panchina, dati_rosa, giornate_totali)

    return titolari, panchina

if __name__ == "__main__":
    genera_formazione()
