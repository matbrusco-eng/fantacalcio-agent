import json
import os
from datetime import datetime, timedelta

def formatta_cron(data_target, ora=12, minuto=0):
    """Genera la stringa cron: Minuto Ora Giorno Mese *"""
    return f"{minuto} {ora} {data_target.day} {data_target.month} *"

def aggiorna_file_workflow(cron_expr):
    """Aggiorna la riga del cron senza usare regex per evitare errori di escape."""
    path_yml = ".github/workflows/run_algorithm.yml"
    
    if not os.path.exists(path_yml):
        print(f"❌ File non trovato: {path_yml}")
        return

    with open(path_yml, 'r', encoding='utf-8') as f:
        righe = f.readlines()

    nuove_righe = []
    aggiornato = False

    for riga in righe:
        if '- cron:' in riga:
            indentazione = riga[:riga.find('-')]
            nuove_righe.append(f"{indentazione}- cron: '{cron_expr}'\n")
            aggiornato = True
        else:
            nuove_righe.append(riga)

    if aggiornato:
        with open(path_yml, 'w', encoding='utf-8') as f:
            f.writelines(nuove_righe)
        print(f"✅ Workflow aggiornato con successo -> cron: '{cron_expr}'")
    else:
        print("⚠️ Nessuna riga '- cron:' trovata nel file YAML.")

def calcola_prossima_schedulazione():
    if not os.path.exists('calendario.json'):
        print("❌ File calendario.json non trovato.")
        return

    with open('calendario.json', 'r', encoding='utf-8') as f:
        calendario = json.load(f)

    oggi = datetime.now()
    prossima_giornata = None
    data_giornata = None

    for g in calendario:
        dt_str = g.get('data_inizio')
        if dt_str:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
            if dt.date() >= oggi.date():
                prossima_giornata = g['giornata']
                data_giornata = dt
                break

    if not data_giornata:
        print("⚠️ Nessuna giornata futura trovata nel calendario.")
        return

    # Logica di calcolo giorni di anticipo:
    # 0 = Lunedì, 1 = Martedì, 2 = Mercoledì, 3 = Giovedì, 4 = Venerdì, 5 = Sabato, 6 = Domenica
    giorno_settimana = data_giornata.weekday()

    if giorno_settimana == 6:    # DOMENICA -> 2 giorni prima (VENERDÌ)
        giorni_anticipo = 2
    elif giorno_settimana == 2:  # MERCOLEDÌ -> 1 giorno prima (MARTEDÌ)
        giorni_anticipo = 1
    else:
        giorni_anticipo = 1

    data_esecuzione = data_giornata - timedelta(days=giorni_anticipo)
    cron_expr = formatta_cron(data_esecuzione, ora=12, minuto=0)

    print(f"📌 Prossima Giornata: G{prossima_giornata} ({data_giornata.strftime('%d/%m/%Y')})")
    print(f"⏰ Esecuzione schedulata per: {data_esecuzione.strftime('%A %d/%m/%Y')} alle 12:00 UTC")
    
    aggiorna_file_workflow(cron_expr)

if __name__ == "__main__":
    calcola_prossima_schedulazione()
