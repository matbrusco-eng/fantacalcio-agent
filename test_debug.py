import os
import requests
import io
import openpyxl
import json
import smtplib
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

URL_LOGIN_EXCEL = "https://www.fantacalcio.it/api/v1/User/login"
URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"
URL_PROBABILI_FORMAZIONI = "https://www.fantacalcio.it/probabili-formazioni-serie-a"

RUOLI_ORDINE = {'P': 1, 'D': 2, 'C': 3, 'A': 4}
RUOLI_NUMERICI = {'P': '0', 'D': '1', 'C': '2', 'A': '3'}
STATI_PANCHINA = ["1", "2", "3", "4", "5", "6", "A", "B", "C", "D", "E", "F", "G", "H"]

def calcola_ranking_squadre_dinamico(rows):
    stats_squadre = {}
    for riga in rows[2:]:
        if len(riga) > 9 and riga[4]:
            sq = str(riga[4]).upper()
            ruolo = riga[1]
            
            gol_fatti = riga[8] if isinstance(riga[8], (int, float)) else 0
            gol_subiti = riga[9] if isinstance(riga[9], (int, float)) else 0
            
            if sq not in stats_squadre:
                stats_squadre[sq] = {'gol_fatti': 0, 'gol_subiti': 0}
            
            if ruolo == 'P':
                stats_squadre[sq]['gol_subiti'] += gol_subiti
            else:
                stats_squadre[sq]['gol_fatti'] += gol_fatti

    squadre_ordinate_difesa = sorted(stats_squadre.keys(), key=lambda x: stats_squadre[x]['gol_subiti'])
    squadre_ordinate_attacco = sorted(stats_squadre.keys(), key=lambda x: stats_squadre[x]['gol_fatti'], reverse=True)
    
    tier_difesa = {}
    tier_attacco = {}
    total = len(squadre_ordinate_difesa) or 1
    
    for idx, sq in enumerate(squadre_ordinate_difesa):
        percentile = idx / total
        tier_difesa[sq] = 1 if percentile < 0.25 else (2 if percentile < 0.50 else (3 if percentile < 0.75 else 4))
        
    for idx, sq in enumerate(squadre_ordinate_attacco):
        percentile = idx / total
        tier_attacco[sq] = 1 if percentile < 0.25 else (2 if percentile < 0.50 else (3 if percentile < 0.75 else 4))

    return tier_difesa, tier_attacco, stats_squadre

def calcola_dettagli_k_match(squadra_giocatore, partita_info, ruolo, tier_difesa, tier_attacco):
    if not partita_info:
        return 1.0, 1.0, 1.0, "N/D"

    is_casa = (partita_info['casa'] == squadra_giocatore)
    avversario = partita_info['trasferta'] if is_casa else partita_info['casa']
    
    if is_casa:
        match_str = f"vs {avversario}"
    else:
        match_str = f"vs <b>{avversario}</b>"

    if ruolo == 'P':
        return 1.0, 1.0, 1.0, match_str

    k_casa = 1.05 if is_casa else 0.95
    
    if ruolo == 'D':
        fascia_avv = tier_attacco.get(avversario, 2)
    else:
        fascia_avv = tier_difesa.get(avversario, 2)
        
    k_diff_map = {1: 0.88, 2: 0.96, 3: 1.04, 4: 1.12}
    k_diff = k_diff_map.get(fascia_avv, 1.0)
    
    k_totale = round(k_casa * k_diff, 2)
    
    return k_totale, k_casa, k_diff, match_str

def recupera_partita_giornata(squadra, giornata_attuale):
    try:
        with open('calendario.json', 'r', encoding='utf-8') as f:
            calendario = json.load(f)
        for g in calendario:
            if g['giornata'] == giornata_attuale:
                for p in g['partite']:
                    if p['casa'] == squadra or p['trasferta'] == squadra:
                        return p
    except Exception as e:
        print(f"⚠️ Errore lettura calendario: {e}")
    return None

def calcola_score(fm, presenze, giornate_totali, k_match=1.0):
    if giornate_totali == 0:
        return 0.0, 0.0
    c_pres = presenze / giornate_totali
    score_base = fm * c_pres
    
    # Attenuazione del k_match del 50% per dare molta più importanza alla FantaMedia pura
    k_match_attenuato = 1.0 + (k_match - 1.0) * 0.5
    
    score_finale = round(score_base * k_match_attenuato, 2)
    delta = round(score_finale - fm, 2)
    return score_finale, delta

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

def formatta_valore_html(val):
    if val > 0.05:
        return f'<b style="color: #2e7d32;">+{val:.2f}</b>'
    elif val < -0.05:
        return f'<b style="color: #c62828;">{val:.2f}</b>'
    else:
        sign = "+" if val > 0 else ""
        return f'<span style="color: #333;">{sign}{val:.2f}</span>'

def invia_email_report(titolari, panchina, dati_rosa, giornate_totali, tier_difesa, tier_attacco, stats_squadre):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")
    email_to = os.environ.get("EMAIL_TO", gmail_user)

    if not gmail_user or not gmail_pass:
        print("⚠️ Secret GMAIL_USER o GMAIL_APP_PASSWORD non trovati. Email non inviata.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"⚽ [DEBUG MODIFICATORI] Fantacalcio - Formazione Consigliata (G{giornate_totali})"
    msg["From"] = gmail_user
    msg["To"] = email_to

    # 1. Tabella Titolari
    titolari_ordinati = sorted(titolari, key=lambda x: (RUOLI_ORDINE.get(x['ruolo'], 99), -x['score']))
    html_titolari = ""
    for i, g in enumerate(titolari_ordinati, 1):
        bordo = "border-bottom: 2px solid #555;" if i < len(titolari_ordinati) and g['ruolo'] != titolari_ordinati[i]['ruolo'] else "border-bottom: 1px solid #e0e0e0;"
        squadra_html = f"<b>{g['squadra']}</b>" if "<b>" not in g['match_info'] and g['match_info'] != "N/D" else g['squadra']
        
        html_titolari += f"""
        <tr style="{bordo}">
            <td style="padding: 3px 6px; text-align: center;">{i}</td>
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 6px;"><b>{g['nome']}</b></td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #555;">{squadra_html}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #555;">{g['match_info']}</td>
            <td style="padding: 3px 6px; text-align: center; color: #2e7d32; font-weight: bold;">{g['score']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['fm']}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px;">{g['k_casa']:.2f}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px;">{g['k_diff']:.2f}</td>
            <td style="padding: 3px 6px; text-align: center;">{formatta_valore_html(g['delta'])}</td>
        </tr>
        """

    # 2. Tabella Panchina
    html_panchina = ""
    for i, g in enumerate(panchina, 1):
        bordo = "border-bottom: 2px solid #555;" if i < len(panchina) and g['ruolo'] != panchina[i]['ruolo'] else "border-bottom: 1px solid #e0e0e0;"
        squadra_html = f"<b>{g['squadra']}</b>" if "<b>" not in g['match_info'] and g['match_info'] != "N/D" else g['squadra']
        
        is_indisponibile = g['stato'] in ["INFORTUNATO", "SQUALIFICATO"] or g['perc_voto'] == "0%"
        nome_html = f'<b style="color: #c62828;">{g["nome"]}</b>' if is_indisponibile else g["nome"]
        score_html = f'<b style="color: #c62828;">{g["score"]}</b>'
