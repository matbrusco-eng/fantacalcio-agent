import os
import json
import requests
import io
import openpyxl
import smtplib
import re
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

URL_LOGIN_EXCEL = "https://www.fantacalcio.it/api/v1/User/login"
URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"
URL_PROBABILI_FORMAZIONI = "https://www.fantacalcio.it/probabili-formazioni-serie-a"

RUOLI_ORDINE = {'P': 1, 'D': 2, 'C': 3, 'A': 4}

def carica_parametri():
    """Carica i parametri di calcolo dal file esterno parametri.json con fallback di sicurezza."""
    default_params = {
        "peso_storico": 0.6,
        "peso_recent": 0.4,
        "attenuazione_match": 0.5,
        "malus_stato_panchina": 0.85,
        "soglia_percentuale_panchina": 0.6,
        "boost_massimo_bonus": 0.15,
        "sensibilita_bonus": 0.10
    }
    if os.path.exists('parametri.json'):
        try:
            with open('parametri.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for k in default_params:
                    if k in data:
                        default_params[k] = float(data[k])
                print("⚙️ Parametri caricati correttamente da 'parametri.json'.")
        except Exception as e:
            print(f"⚠️ Errore lettura parametri.json: {e}. Uso i valori di default.")
    return default_params

def aggiorna_statistiche_da_excel(rows, rosa, statistiche):
    if not rows or len(rows) < 3:
        print("⚠️ Impossibile aggiornare le statistiche: righe Excel non valide o vuote.")
        return statistiche

    presenze_list = [riga[5] for riga in rows[2:] if isinstance(riga[5], (int, float))]
    giornata_rilevata = int(max(presenze_list)) if presenze_list else 0

    if giornata_rilevata == 0:
        return statistiche

    rosa_ids = {str(p['id']) for p in rosa}
    voti_nuova_giornata = {}

    for riga in rows[2:]:
        cod_val = riga[0]
        if cod_val is None:
            continue
        try:
            pid = str(int(float(cod_val)))
        except:
            continue

        if pid in rosa_ids:
            try:
                voto_raw = str(riga[3])
                voto_clean = re.sub(r'[^0-9\.\-]', '', voto_raw.replace(',', '.'))
                voto = float(voto_clean)
            except:
                voto = None

            if voto is not None:
                def safe_val(idx):
                    try:
                        val = riga[idx]
                        return float(val) if val is not None else 0.0
                    except:
                        return 0.0

                gf = safe_val(4)   # Goal fatti (+3)
                gs = safe_val(5)   # Goal subiti (-1)
                rp = safe_val(6)   # Rigore parato (+3)
                rs = safe_val(7)   # Rigore sbagliato (-3)
                rf = safe_val(8)   # Rigore segnato (+3)
                au = safe_val(9)   # Autogol (-2)
                amm = safe_val(10) # Ammonito (-0.5)
                esp = safe_val(11) # Espulso (-1)
                ass = safe_val(12) # Assist (+1)

                bonus_malus = (gf * 3) + (gs * -1) + (rp * 3) + (rs * -3) + (rf * 3) + (au * -2) + (amm * -0.5) + (esp * -1) + (ass * 1)
                fantavoto = voto + bonus_malus
                fantavoto = round(fantavoto * 2) / 2
                voti_nuova_giornata[pid] = fantavoto

    file_modificato = False
    for pid in rosa_ids:
        if pid not in statistiche:
            p_info = next((p for p in rosa if str(p['id']) == pid), {})
            statistiche[pid] = {
                "nome": p_info.get('nome', ''),
                "ruolo": p_info.get('ruolo', ''),
                "squadra": "N/D",
                "Pv": 0,
                "Fm_Tot": 6.0,
                "Gol": 0,
                "Assist": 0,
                "voti_settimanali": []
            }

        p_stat = statistiche[pid]
        voti_list = p_stat.get("voti_settimanali", [])

        while len(voti_list) < giornata_rilevata:
            if len(voti_list) == giornata_rilevata - 1:
                voto_g = voti_nuova_giornata.get(pid, None)
                voti_list.append(voto_g)
                file_modificato = True
            else:
                voti_list.append(None)
                file_modificato = True

        p_stat["voti_settimanali"] = voti_list
        valid_voti = [v for v in voti_list if v is not None]
        p_stat["Pv"] = len(valid_voti)
        p_stat["Fm_Tot"] = round(sum(valid_voti) / len(valid_voti), 2) if valid_voti else 6.0

    if file_modificato:
        with open('statistiche_mostro.json', 'w', encoding='utf-8') as f:
            json.dump(statistiche, f, ensure_ascii=False, indent=4)
        print(f"💾 File 'statistiche_mostro.json' aggiornato automaticamente fino alla Giornata {giornata_rilevata}!")

    return statistiche

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

def recupera_partita_giornata(squadra, giornata_obiettivo):
    try:
        with open('calendario.json', 'r', encoding='utf-8') as f:
            calendario = json.load(f)
        for g in calendario:
            if g['giornata'] == giornata_obiettivo:
                for p in g['partite']:
                    if p['casa'] == squadra or p['trasferta'] == squadra:
                        return p
    except Exception as e:
        pass
    return None

def verifica_finestra_invio(giornata_obiettivo):
    try:
        with open('calendario.json', 'r', encoding='utf-8') as f:
            calendario = json.load(f)
            
        partite_giornata = []
        for g in calendario:
            if g['giornata'] == giornata_obiettivo:
                partite_giornata = g.get('partite', [])
                break
                
        if not partite_giornata:
            return False, giornata_obiettivo
            
        orari_match = []
        for p in partite_giornata:
            orario_str = p.get('orario') or p.get('data_ora')
            if orario_str:
                try:
                    if '/' in orario_str:
                        dt = datetime.strptime(orario_str, '%d/%m/%Y %H:%M')
                    else:
                        dt = datetime.fromisoformat(orario_str)
                    orari_match.append(dt)
                except Exception:
                    pass

        if not orari_match:
            return True, giornata_obiettivo

        tz_italia = pytz.timezone('Europe/Rome')
        adesso = datetime.now(tz_italia)
        prima_partita = min(orari_match)
        if prima_partita.tzinfo is None:
            prima_partita = tz_italia.localize(prima_partita)
            
        if adesso >= prima_partita:
            return False, giornata_obiettivo
        else:
            return True, giornata_obiettivo
    except Exception as e:
        return False, giornata_obiettivo

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
                            giocatori_trovati_live[pid] = {"stato": "TITOLARE", "sigla": "T", "perc": perc_str, "note": "Disponibile"}

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
                                giocatori_trovati_live[pid] = {"stato": "PANCHINA", "sigla": "P", "perc": perc_str, "note": "Disponibile"}

            for injured_list in soup.find_all('ul', class_='injured-list'):
                for li in injured_list.find_all('li'):
                    a_tag = li.find('a', class_='player-link')
                    if a_tag and a_tag.get('href'):
                        id_match = re.search(r'/(\d+)$', a_tag['href'])
                        if id_match:
                            pid = id_match.group(1)
                            desc_p = li.find('p', class_='description')
                            desc_str = desc_p.get_text(strip=True) if desc_p else "Infortunato"
                            giocatori_trovati_live[pid] = {"stato": "INFORTUNATO", "sigla": "I", "perc": "0%", "note": desc_str}

            for susp_list in soup.find_all('ul', class_='suspendeds-list'):
                for li in susp_list.find_all('li'):
                    a_tag = li.find('a', class_='player-link')
                    if a_tag and a_tag.get('href'):
                        id_match = re.search(r'/(\d+)$', a_tag['href'])
                        if id_match:
                            pid = id_match.group(1)
                            desc_p = li.find('p', class_='description')
                            desc_str = desc_p.get_text(strip=True) if desc_p else "Squalificato"
                            giocatori_trovati_live[pid] = {"stato": "SQUALIFICATO", "sigla": "S", "perc": "0%", "note": desc_str}
    except Exception as e:
        pass
    return giocatori_trovati_live

def load_json_data():
    with open('rosa.json', 'r', encoding='utf-8') as f:
        rosa = json.load(f)
    if os.path.exists('statistiche_mostro.json'):
        with open('statistiche_mostro.json', 'r', encoding='utf-8') as f:
            statistiche = json.load(f)
    else:
        statistiche = {}
    return rosa, statistiche

def formatta_valore_html(val):
    if val > 0.05:
        return f'<b style="color: #2e7d32;">+{val:.2f}</b>'
    elif val < -0.05:
        return f'<b style="color: #c62828;">{val:.2f}</b>'
    else:
        sign = "+" if val > 0 else ""
        return f'<span style="color: #333;">{sign}{val:.2f}</span>'

def get_tier_badge_style(tier):
    if tier == 1:
        return 'background-color: #ffebee; color: #c62828; font-weight: bold; border-radius: 3px; padding: 2px 6px; display: inline-block;'
    elif tier == 2:
        return 'background-color: #fff3e0; color: #e65100; font-weight: bold; border-radius: 3px; padding: 2px 6px; display: inline-block;'
    elif tier == 3:
        return 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold; border-radius: 3px; padding: 2px 6px; display: inline-block;'
    else:
        return 'background-color: #ede7f6; color: #4527a0; font-weight: bold; border-radius: 3px; padding: 2px 6px; display: inline-block;'

def get_sigla_badge_style(sigla):
    if sigla == 'T':
        return 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold; border-radius: 3px; padding: 2px 5px; display: inline-block;'
    elif sigla == 'P':
        return 'background-color: #fff3e0; color: #e65100; font-weight: bold; border-radius: 3px; padding: 2px 5px; display: inline-block;'
    elif sigla == 'I':
        return 'background-color: #ffebee; color: #c62828; font-weight: bold; border-radius: 3px; padding: 2px 5px; display: inline-block;'
    else: # S
        return 'background-color: #f3e5f5; color: #7b1fa2; font-weight: bold; border-radius: 3px; padding: 2px 5px; display: inline-block;'

def invia_email_report(titolari, panchina, dati_rosa, giornata_riferimento, tier_difesa, tier_attacco, stats_squadre, invio_consentito, statistiche):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")
    email_to = os.environ.get("EMAIL_TO", gmail_user)

    if not gmail_user or not gmail_pass:
        return

    msg = MIMEMultipart("alternative")
    stato_invio_str = "🚀 FORMAZIONE INVIATA AL SITO" if invio_consentito else "🛑 TURNO INIZIATO - SOLO REPORT (Invio Bloccato)"
    msg["Subject"] = f"⚽ [IL MOSTRO] {stato_invio_str} - Giornata {giornata_riferimento}"
    msg["From"] = gmail_user
    msg["To"] = email_to

    # 1. Titolari (con colonna P tra R e Nome)
    titolari_ordinati = sorted(titolari, key=lambda x: (RUOLI_ORDINE.get(x['ruolo'], 99), -x['score']))
    html_titolari = ""
    for i, g in enumerate(titolari_ordinati, 1):
        bordo = "border-bottom: 2px solid #555;" if i < len(titolari_ordinati) and g['ruolo'] != titolari_ordinati[i]['ruolo'] else "border-bottom: 1px solid #e0e0e0;"
        squadra_html = f"<b>{g['squadra']}</b>" if "<b>" not in g['match_info'] and g['match_info'] != "N/D" else g['squadra']
        sigla_badge = f'<span style="{get_sigla_badge_style(g["sigla"])}">{g["sigla"]}</span>'
        
        html_titolari += f"""
        <tr style="{bordo}">
            <td style="padding: 3px 6px; text-align: center;">{i}</td>
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 6px; text-align: center;">{sigla_badge}</td>
            <td style="padding: 3px 6px;"><b>{g['nome']}</b></td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #555;">{squadra_html}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #555;">{g['match_info']}</td>
            <td style="padding: 3px 6px; text-align: center; color: #2e7d32; font-weight: bold;">{g['score']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['fm']}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px;">{g['fm_recent']}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px;">{g['trend']}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #1a237e; font-weight: bold;">{g['k_bonus']}x</td>
            <td style="padding: 3px 6px; text-align: center;">{formatta_valore_html(g['delta_forma'])}</td>
        </tr>
        """

    # 2. Panchina (con colonna P tra R e Nome)
    html_panchina = ""
    for i, g in enumerate(panchina, 1):
        bordo = "border-bottom: 2px solid #555;" if i < len(panchina) and g['ruolo'] != panchina[i]['ruolo'] else "border-bottom: 1px solid #e0e0e0;"
        squadra_html = f"<b>{g['squadra']}</b>" if "<b>" not in g['match_info'] and g['match_info'] != "N/D" else g['squadra']
        
        is_indisponibile = g['stato'] in ["INFORTUNATO", "SQUALIFICATO"] or g['perc_voto'] == "0%"
        nome_html = f'<b style="color: #c62828;">{g["nome"]}</b>' if is_indisponibile else g["nome"]
        score_html = f'<b style="color: #c62828;">{g["score"]}</b>' if is_indisponibile else f'<b>{g["score"]}</b>'
        sigla_badge = f'<span style="{get_sigla_badge_style(g["sigla"])}">{g["sigla"]}</span>'

        html_panchina += f"""
        <tr style="{bordo}">
            <td style="padding: 3px 6px; text-align: center;">{i}</td>
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 6px; text-align: center;">{sigla_badge}</td>
            <td style="padding: 3px 6px;">{nome_html}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #555;">{squadra_html}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #555;">{g['match_info']}</td>
            <td style="padding: 3px 6px; text-align: center;">{score_html}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['fm']}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px;">{g['fm_recent']}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px;">{g['trend']}</td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #1a237e; font-weight: bold;">{g['k_bonus']}x</td>
            <td style="padding: 3px 6px; text-align: center;">{formatta_valore_html(g['delta_forma'])}</td>
        </tr>
        """

    # 3. Stato Rosa
    rosa_ordinata_stato = sorted(dati_rosa, key=lambda x: (RUOLI_ORDINE.get(x['ruolo'], 99), -x['score']))
    html_stato_rosa = ""
    for i, g in enumerate(rosa_ordinata_stato):
        bordo = "border-bottom: 2px solid #555;" if i < len(rosa_ordinata_stato) - 1 and g['ruolo'] != rosa_ordinata_stato[i+1]['ruolo'] else "border-bottom: 1px solid #eee;"
        colore_stato = "#2e7d32" if g['stato'] == "TITOLARE" else ("#e65100" if g['stato'] == "PANCHINA" else "#c62828")
        sigla_badge = f'<span style="{get_sigla_badge_style(g["sigla"])}">{g["sigla"]}</span>'
        html_stato_rosa += f"""
        <tr style="{bordo}">
            <td style="padding: 3px 6px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 3px 6px; text-align: center;">{sigla_badge}</td>
            <td style="padding: 3px 6px;"><b>{g['nome']}</b></td>
            <td style="padding: 3px 6px; text-align: center; font-size: 11px; color: #555;">{g['squadra']}</td>
            <td style="padding: 3px 6px; text-align: center; color: {colore_stato}; font-weight: bold;">{g['stato']}</td>
            <td style="padding: 3px 6px; text-align: center;">{g['perc_voto']}</td>
            <td style="padding: 3px 6px; font-size: 11px;">{g['note']}</td>
        </tr>
        """

    # 4. Squadre e Tier
    squadre_lista = []
    for sq in stats_squadre.keys():
        g_fatti = stats_squadre[sq]['gol_fatti']
        g_subiti = stats_squadre[sq]['gol_subiti']
        diff_reti = g_fatti - g_subiti
        t_def = tier_difesa.get(sq, 2)
        t_att = tier_attacco.get(sq, 2)
        squadre_lista.append({
            'sq': sq,
            'tier_difesa': t_def,
            'tier_attacco': t_att,
            'gol_fatti': g_fatti,
            'gol_subiti': g_subiti,
            'coeff_forza': round(diff_reti, 1)
        })
    squadre_lista.sort(key=lambda x: (x['coeff_forza'], x['gol_fatti']), reverse=True)

    html_squadre = ""
    for item in squadre_lista:
        t_def_style = get_tier_badge_style(item['tier_difesa'])
        t_att_style = get_tier_badge_style(item['tier_attacco'])
        html_squadre += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 4px 6px; font-weight: bold;">{item['sq']}</td>
            <td style="padding: 4px 6px; text-align: center; font-weight: bold; color: #1a237e;">{item['coeff_forza']}</td>
            <td style="padding: 4px 6px; text-align: center;"><span style="{t_def_style}">Tier {item['tier_difesa']}</span></td>
            <td style="padding: 4px 6px; text-align: center;"><span style="{t_att_style}">Tier {item['tier_attacco']}</span></td>
            <td style="padding: 4px 6px; text-align: center;">{item['gol_fatti']}</td>
            <td style="padding: 4px 6px; text-align: center;">{item['gol_subiti']}</td>
        </tr>
        """

    # 5. TABELLA MATRICE DI VERIFICA FANTAVOTI
    max_giornate = 0
    for p_id, p_info in statistiche.items():
        voti_list = p_info.get('voti_settimanali', [])
        if len(voti_list) > max_giornate:
            max_giornate = len(voti_list)

    th_giornate_html = "".join([f'<th style="padding: 3px 4px; text-align: center; font-size: 10px; width: 28px;">G{g}</th>' for g in range(1, max_giornate + 1)])

    html_matrice_righe = ""
    rosa_ordinata_verifica = sorted(dati_rosa, key=lambda x: (RUOLI_ORDINE.get(x['ruolo'], 99), x['nome']))
    for g in rosa_ordinata_verifica:
        pid = str(g['id'])
        p_stat = statistiche.get(pid, {})
        voti = p_stat.get('voti_settimanali', [])
        
        td_voti_html = ""
        for idx in range(max_giornate):
            if idx < len(voti):
                val = voti[idx]
                val_str = str(val) if val is not None else "-"
                td_voti_html += f'<td style="padding: 3px 4px; text-align: center; font-size: 10px;">{val_str}</td>'
            else:
                td_voti_html += f'<td style="padding: 3px 4px; text-align: center; font-size: 10px; color: #ccc;">-</td>'
                
        html_matrice_righe += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 3px 6px; font-weight: bold; white-space: nowrap; width: 1%; font-size: 11px;">{g['nome']} <span style="font-size: 9px; color: #666;">({g['ruolo']})</span></td>
            {td_voti_html}
            <td style="width: 99%;"></td>
        </tr>
        """

    avviso_banner = ""
    if not invio_consentito:
        avviso_banner = f"""
        <div style="background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; padding: 12px; margin-bottom: 15px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 14px;">
            ⚠️ ATTENZIONE: La Giornata {giornata_riferimento} è già iniziata. L'invio automatico della formazione al sito è stato BLOCCATO per sicurezza. Questo è solo il report di analisi/debug.
        </div>
        """
    else:
        avviso_banner = f"""
        <div style="background-color: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; padding: 12px; margin-bottom: 15px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 14px;">
            ✅ Finestra temporale valida per la Giornata {giornata_riferimento}: Formazione calcolata e inviata regolarmente al sito.
        </div>
        """

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.2; font-size: 13px;">
        {avviso_banner}

        <h3 style="color: #1a237e; margin: 0 0 8px 0;">⚽ Report "Il Mostro" - Giornata {giornata_riferimento}</h3>
        <p style="font-size: 12px; margin: 0 0 10px 0; color: #555;"><b>Legenda:</b> <i>P</i> (T=Titolare, P=Panchina, I=Infortunato, S=Squalificato), <i>Bonus</i> (K_Bonus Propensione).</p>
        
        <b style="color: #2e7d32; font-size: 14px;">🔥 TITOLARI CONSIGLIATI</b>
        <table style="width: 100%; max-width: 840px; border-collapse: collapse; background: #f9f9f9; margin: 4px 0 12px 0;">
            <thead>
                <tr style="background-color: #2e7d32; color: white; font-size: 12px;">
                    <th style="padding: 4px 6px;">#</th>
                    <th style="padding: 4px 6px;">R</th>
                    <th style="padding: 4px 6px;">P</th>
                    <th style="padding: 4px 6px; text-align: left;">Nome</th>
                    <th style="padding: 4px 6px;">Squadra</th>
                    <th style="padding: 4px 6px;">Match</th>
                    <th style="padding: 4px 6px;">Score</th>
                    <th style="padding: 4px 6px;">Fm Tot</th>
                    <th style="padding: 4px 6px;">Fm Rec</th>
                    <th style="padding: 4px 6px;">Trend</th>
                    <th style="padding: 4px 6px;">Bonus</th>
                    <th style="padding: 4px 6px;">Δ</th>
                </tr>
            </thead>
            <tbody>
                {html_titolari}
            </tbody>
        </table>

        <b style="color: #e65100; font-size: 14px;">🪑 PANCHINA PER NUMERAZIONE (P -> A -> C -> D)</b>
        <table style="width: 100%; max-width: 840px; border-collapse: collapse; background: #f9f9f9; margin: 4px 0 16px 0;">
            <thead>
                <tr style="background-color: #e65100; color: white; font-size: 12px;">
                    <th style="padding: 4px 6px;">#</th>
                    <th style="padding: 4px 6px;">R</th>
                    <th style="padding: 4px 6px;">P</th>
                    <th style="padding: 4px 6px; text-align: left;">Nome</th>
                    <th style="padding: 4px 6px;">Squadra</th>
                    <th style="padding: 4px 6px;">Match</th>
                    <th style="padding: 4px 6px;">Score</th>
                    <th style="padding: 4px 6px;">Fm Tot</th>
                    <th style="padding: 4px 6px;">Fm Rec</th>
                    <th style="padding: 4px 6px;">Trend</th>
                    <th style="padding: 4px 6px;">Bonus</th>
                    <th style="padding: 4px 6px;">Δ</th>
                </tr>
            </thead>
            <tbody>
                {html_panchina}
            </tbody>
        </table>

        <hr style="border: 0; border-top: 1px solid #ccc; margin: 12px 0;">

        <b style="color: #37474f; font-size: 14px;">📊 STATO E DISPONIBILITÀ ROSA</b>
        <table style="width: 100%; max-width: 780px; border-collapse: collapse; font-size: 12px; margin-top: 4px;">
            <thead>
                <tr style="background-color: #37474f; color: white;">
                    <th style="padding: 4px 6px;">R</th>
                    <th style="padding: 4px 6px;">P</th>
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

        <hr style="border: 0; border-top: 1px solid #ccc; margin: 12px 0;">

        <b style="color: #1a237e; font-size: 14px;">🛡️ RANKING E FORZA SQUADRE</b>
        <table style="width: 100%; max-width: 620px; border-collapse: collapse; font-size: 12px; margin-top: 4px; background: #fdfdfd;">
            <thead>
                <tr style="background-color: #1a237e; color: white;">
                    <th style="padding: 4px 6px; text-align: left;">Squadra</th>
                    <th style="padding: 4px 6px;">Coeff. Forza</th>
                    <th style="padding: 4px 6px;">Tier Difesa</th>
                    <th style="padding: 4px 6px;">Tier Attacco</th>
                    <th style="padding: 4px 6px;">Gol Fatti</th>
                    <th style="padding: 4px 6px;">Gol Subiti</th>
                </tr>
            </thead>
            <tbody>
                {html_squadre}
            </tbody>
        </table>

        <hr style="border: 0; border-top: 1px solid #ccc; margin: 16px 0;">

        <b style="color: #4527a0; font-size: 14px;">📈 VERIFICA FANTAVOTI DI GIORNATA (statistiche_mostro.json)</b>
        <div style="overflow-x: auto; margin-top: 6px;">
            <table style="width: 100%; border-collapse: collapse; background: #fff; font-size: 11px;">
                <thead>
                    <tr style="background-color: #4527a0; color: white;">
                        <th style="padding: 4px 6px; text-align: left; width: 1%;">Giocatore</th>
                        {th_giornate_html}
                        <th style="width: 99%;"></th>
                    </tr>
                </thead>
                <tbody>
                    {html_matrice_righe}
                </tbody>
            </table>
        </div>
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
        print("📧 Email di report unificato inviata con successo!")
    except Exception as e:
        print(f"❌ Errore invio email: {e}")

def invia_formazione_al_sito(session, titolari, panchina, invio_consentito):
    if not invio_consentito:
        print("🛑 BLOCCO ASSOLUTO: Turno iniziato. Nessun invio effettuato al sito.")
        return False
    try:
        titolari_ids = [g['id'] for g in titolari]
        panchina_ids = [g['id'] for g in panchina]
        from agent import imposta_formazione_fantagazzetta
        imposta_formazione_fantagazzetta(titolari_ids, panchina_ids)
        print("🚀 Formazione inviata con successo al sito di Fantacalcio!")
        return True
    except Exception as e:
        print(f"❌ Errore durante l'invio della formazione al sito: {e}")
        return False

def genera_formazione():
    # Caricamento parametri esterni
    params = carica_parametri()
    
    username_excel = os.environ.get("FANTACALCIO_USER", "").strip()
    password_excel = os.environ.get("FANTACALCIO_PASS", "").strip()
    
    rosa, statistiche = load_json_data()
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.fantacalcio.it/'
    })
    
    try:
        res_login = session.post(URL_LOGIN_EXCEL, json={"username": username_excel, "password": password_excel}, timeout=15)
        res_excel = session.get(URL_EXCEL_STATS, timeout=15)
        wb = openpyxl.load_workbook(io.BytesIO(res_excel.content), data_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        statistiche = aggiorna_statistiche_da_excel(rows, rosa, statistiche)
    except Exception as e:
        print(f"⚠️ Impossibile scaricare le statistiche Excel da fantacalcio.it: {e}")
        rows = []

    tier_difesa, tier_attacco, stats_squadre = calcola_ranking_squadre_dinamico(rows) if rows else ({}, {}, {})
    dati_probabili = recupera_stato_infermeria_live(session)
    
    presenze_totali = [riga[5] for riga in rows[2:] if isinstance(riga[5], (int, float))] if rows else [10]
    giornate_totali = max(presenze_totali) if presenze_totali else 1
    
    invio_consentito, giornata_riferimento = verifica_finestra_invio(giornate_totali)
    
    dati_rosa = []
    excel_map = {}
    if rows:
        for riga in rows[2:]:
            id_exc = str(riga[0])
            excel_map[id_exc] = riga

    for p in rosa:
        pid = str(p['id'])
        nome = p['nome']
        ruolo = p['ruolo']
        
        p_stat = statistiche.get(pid, {})
        fm_tot = float(p_stat.get('Fm_Tot', 6.0))
        voti = p_stat.get('voti_settimanali', [])
        
        valid_voti_storico = [v for v in voti if v is not None]
        if len(valid_voti_storico) > 0:
            ultime_3 = valid_voti_storico[-3:]
            fm_recent = round(sum(ultime_3) / len(ultime_3), 2)
        else:
            fm_recent = fm_tot
            
        delta_forma = round(fm_recent - fm_tot, 2)
        if len(valid_voti_storico) == 0:
            trend = "⚪ N.D."
        elif delta_forma >= 0.3:
            trend = "📈 Crescita"
        elif delta_forma <= -0.3:
            trend = "📉 Calo"
        else:
            trend = "➡️ Stabile"

        riga_ex = excel_map.get(pid)
        if riga_ex:
            squadra = str(riga_ex[4]).upper() if len(riga_ex) > 4 and riga_ex[4] else "N/D"
            presenze = riga_ex[5] or len(valid_voti_storico)
            fm = riga_ex[7] or fm_tot
            gol_stg = float(riga_ex[8] or 0) if len(riga_ex) > 8 else 0
            assist_stg = float(riga_ex[12] or 0) if len(riga_ex) > 12 else 0
        else:
            squadra = p_stat.get('squadra', 'N/D')
            presenze = len(valid_voti_storico)
            fm = fm_tot
            gol_stg = float(p_stat.get('Gol', 0))
            assist_stg = float(p_stat.get('Assist', 0))

        partita_info = recupera_partita_giornata(squadra, giornata_riferimento)
        k_totale, k_casa, k_diff, match_str = calcola_dettagli_k_match(squadra, partita_info, ruolo, tier_difesa, tier_attacco)
        
        score_base = fm * (presenze / max(1, giornata_riferimento))
        # Utilizzo del parametro esterno per l'attenuazione match
        k_attenuato = 1.0 + (k_totale - 1.0) * params["attenuazione_match"]
        
        # ⚡ CALCOLO K_BONUS USANDO I PARAMETRI ESTERNI
        pv_safe = max(1, presenze)
        freq_bonus = ((gol_stg * 3) + (assist_stg * 1)) / pv_safe
        if ruolo in ['C', 'A']:
            k_bonus = round(1.0 + min(params["boost_massimo_bonus"], freq_bonus * params["sensibilita_bonus"]), 2)
        else:
            k_bonus = 1.0

        # ⚡ K_STATUS USANDO I PARAMETRI ESTERNI
        info_live = dati_probabili.get(pid, {})
        stato = info_live.get('stato', "TITOLARE" if presenze > 0 else "PANCHINA")
        sigla = info_live.get('sigla', "T" if presenze > 0 else "P")
        perc_voto_str = info_live.get('perc', f"{min(100, int((presenze/max(1, giornata_riferimento))*100))}%")
        note = info_live.get('note', "Disponibile")
        
        try:
            perc_val = float(perc_voto_str.replace('%', '')) / 100.0
        except:
            perc_val = 0.5

        if stato == "PANCHINA" or perc_val <= params["soglia_percentuale_panchina"]:
            k_status = params["malus_stato_panchina"]
        else:
            k_status = 1.0

        # ⚡ SCORE FINALE CON PESI STORICO E RECENTE DA PARAMETRI
        score_grezzo = (score_base * k_attenuato * params["peso_storico"]) + (fm_recent * params["peso_recent"])
        score_finale = round((score_grezzo * k_status) * k_bonus, 2)
        delta_score = round(score_finale - fm, 2)

        dati_rosa.append({
            'id': pid,
            'nome': nome,
            'ruolo': ruolo,
            'sigla': sigla,
            'squadra': squadra,
            'match_info': match_str,
            'fm': fm,
            'fm_recent': fm_recent,
            'delta_forma': delta_forma,
            'trend': trend,
            'k_bonus': k_bonus,
            'score': score_finale,
            'delta': delta_score,
            'stato': stato,
            'perc_voto': perc_voto_str,
            'note': note
        })

    dati_rosa.sort(key=lambda x: x['score'], reverse=True)

    # Selezione Titolari flessibile
    arruolabili = [g for g in dati_rosa if g['stato'] not in ["INFORTUNATO", "SQUALIFICATO"] and g['perc_voto'] != "0%"]
    portieri_arr = sorted([g for g in arruolabili if g['ruolo'] == 'P'], key=lambda x: x['score'], reverse=True)
    difensori_arr = sorted([g for g in arruolabili if g['ruolo'] == 'D'], key=lambda x: x['score'], reverse=True)
    altri_arr = sorted([g for g in arruolabili if g['ruolo'] in ['C', 'A']], key=lambda x: x['score'], reverse=True)

    titolari = []
    if portieri_arr:
        titolari.append(portieri_arr[0])
    titolari.extend(difensori_arr[:3])
    
    pool_rimanenti = difensori_arr[3:] + altri_arr
    pool_rimanenti.sort(key=lambda x: x['score'], reverse=True)
    
    slot_mancanti = 11 - len(titolari)
    titolari.extend(pool_rimanenti[:slot_mancanti])
    
    attaccanti_scelti = [g for g in titolari if g['ruolo'] == 'A']
    if len(attaccanti_scelti) > 3:
        attaccanti_scelti.sort(key=lambda x: x['score'], reverse=True)
        attaccanti_da_tenere = set(id(g) for g in attaccanti_scelti[:3])
        
        nuovi_titolari = []
        attaccanti_rimossi_count = 0
        for g in titolari:
            if g['ruolo'] == 'A' and id(g) not in attaccanti_da_tenere:
                attaccanti_rimossi_count += 1
            else:
                nuovi_titolari.append(g)
        titolari = nuevos_titolari if 'nuevos_titolari' in locals() else nuovi_titolari
        
        esclusi_validi = [g for g in arruolabili if g not in titolari and g['ruolo'] != 'A']
        esclusi_validi.sort(key=lambda x: x['score'], reverse=True)
        titolari.extend(esclusi_validi[:attaccanti_rimossi_count])

    ids_titolari = {g['id'] for g in titolari}
    panchina_grezza = [g for g in dati_rosa if g['id'] not in ids_titolari]

    def sort_panchina(lista):
        arr_sub = [g for g in lista if g['stato'] not in ["INFORTUNATO", "SQUALIFICATO"] and g['perc_voto'] != "0%"]
        ind_sub = [g for g in lista if g not in arr_sub]
        arr_sub.sort(key=lambda x: x['score'], reverse=True)
        ind_sub.sort(key=lambda x: x['score'], reverse=True)
        return arr_sub + ind_sub

    panchina = sort_panchina([g for g in panchina_grezza if g['ruolo'] == 'P']) + \
               sort_panchina([g for g in panchina_grezza if g['ruolo'] == 'A']) + \
               sort_panchina([g for g in panchina_grezza if g['ruolo'] == 'C']) + \
               sort_panchina([g for g in panchina_grezza if g['ruolo'] == 'D'])

    invia_formazione_al_sito(session, titolari, panchina, invio_consentito)
    invia_email_report(titolari, panchina, dati_rosa, giornata_riferimento, tier_difesa, tier_attacco, stats_squadre, invio_consentito, statistiche)
    return titolari, panchina

if __name__ == "__main__":
    print("🚀 Avvio motore definitivo 'Il Mostro + Parametri Esterni & Colonna P'.")
    genera_formazione()
