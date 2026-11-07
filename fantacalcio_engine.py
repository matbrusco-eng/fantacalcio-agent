import json
import pandas as pd
import os

def load_data():
    # 1. Legge la rosa attuale (aggiornata da te)
    if os.path.exists('rosa.json'):
        with open('rosa.json', 'r', encoding='utf-8') as f:
            rosa = json.load(f)
    else:
        raise FileNotFoundError("Il file rosa.json non è stato trovato nel repository.")
        
    # 2. Legge il file delle statistiche e dello storico
    if os.path.exists('statistiche_mostro.json'):
        with open('statistiche_mostro.json', 'r', encoding='utf-8') as f:
            statistiche = json.load(f)
    else:
        statistiche = {}
        
    return rosa, statistiche

def calculate_player_metrics(rosa, statistiche):
    evaluations = []
    
    for p in rosa:
        pid = str(p['id'])
        nome = p['nome']
        ruolo = p['ruolo']
        
        # Se il giocatore è presente nel file delle statistiche/storico
        if pid in statistiche:
            p_data = statistiche[pid]
            pv = float(p_data.get('Pv', 0))
            fm_tot = float(p_data.get('Fm_Tot', 6.0))
            gf = float(p_data.get('Gol', 0))
            ass = float(p_data.get('Assist', 0))
            squadra = p_data.get('squadra', 'N/D')
            voti = p_data.get('voti_settimanali', [])
        else:
            # 💡 GESTIONE DINAMICA NUOVO ACQUISTO:
            # Se hai appena aggiunto un giocatore in rosa.json che non c'era prima,
            # lo script lo inizializza automaticamente senza generare errori!
            pv = 0
            fm_tot = 6.0
            gf = 0.0
            ass = 0.0
            squadra = 'Nuovo'
            voti = []
            
        # Calcolo della FantaMedia recente sulle ultime 3 partite (o totale se < 3)
        if len(voti) > 0:
            ultime_3 = voti[-3:]
            fm_recent = sum(ultime_3) / len(ultime_3)
        else:
            fm_recent = fm_tot
            
        # Delta Forma & Trend
        delta_forma = round(fm_recent - fm_tot, 2)
        if pv == 0:
            trend = "⚪ Nuovo / N.D."
        elif delta_forma >= 0.3:
            trend = "📈 In Crescita"
        elif delta_forma <= -0.3:
            trend = "📉 In Calo"
        else:
            trend = "➡️ Stabile"
            
        # Score potenziale ponderato (60% totale, 40% recente + bonus)
        score_potenziale = round((fm_tot * 0.6) + (fm_recent * 0.4) + ((gf * 3 + ass * 1) / max(1, pv) * 0.5), 2)
        
        evaluations.append({
            "id": pid,
            "nome": nome,
            "ruolo": ruolo,
            "squadra": squadra,
            "Pv": int(pv),
            "Fm_Tot": round(fm_tot, 2),
            "Fm_Recente": round(fm_recent, 2),
            "Delta_Forma": delta_forma,
            "Trend": trend,
            "Score_Potenziale": score_potenziale,
            "Gol": int(gf),
            "Assist": int(ass)
        })
        
    return evaluations

if __name__ == "__main__":
    rosa, statistiche = load_data()
    evals = calculate_player_metrics(rosa, statistiche)
    df_evals = pd.DataFrame(evals)
    print("=== VALUTAZIONE DINAMICA ROSA (IL MOSTRO) ===")
    print(df_evals.sort_values(by="Score_Potenziale", ascending=False).to_string(index=False))
