import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

RUOLI_ORDINE = {'P': 1, 'D': 2, 'C': 3, 'A': 4}

def load_data():
    if os.path.exists('rosa.json'):
        with open('rosa.json', 'r', encoding='utf-8') as f:
            rosa = json.load(f)
    else:
        rosa = []
        
    if os.path.exists('statistiche_mostro.json'):
        with open('statistiche_mostro.json', 'r', encoding='utf-8') as f:
            statistiche = json.load(f)
    else:
        statistiche = {}
        
    return rosa, statistiche

def calcola_metriche_giocatori(rosa, statistiche):
    evaluations = []
    
    for p in rosa:
        pid = str(p['id'])
        nome = p['nome']
        ruolo = p['ruolo']
        
        if pid in statistiche:
            p_data = statistiche[pid]
            pv = float(p_data.get('Pv', 0))
            fm_tot = float(p_data.get('Fm_Tot', 6.0))
            gf = float(p_data.get('Gol', 0))
            ass = float(p_data.get('Assist', 0))
            squadra = p_data.get('squadra', 'N/D')
            voti = p_data.get('voti_settimanali', [])
        else:
            pv = 0
            fm_tot = 6.0
            gf = 0.0
            ass = 0.0
            squadra = 'Nuovo'
            voti = []
            
        if len(voti) > 0:
            ultime_3 = voti[-3:]
            fm_recent = sum(ultime_3) / len(ultime_3)
        else:
            fm_recent = fm_tot
            
        delta_forma = round(fm_recent - fm_tot, 2)
        if pv == 0:
            trend = "⚪ Nuovo / N.D."
        elif delta_forma >= 0.3:
            trend = "📈 In Crescita"
        elif delta_forma <= -0.3:
            trend = "📉 In Calo"
        else:
            trend = "➡️ Stabile"
            
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

def formatta_valore_html(val):
    if val > 0.05:
        return f'<b style="color: #2e7d32;">+{val:.2f}</b>'
    elif val < -0.05:
        return f'<b style="color: #c62828;">{val:.2f}</b>'
    else:
        sign = "+" if val > 0 else ""
        return f'<span style="color: #333;">{sign}{val:.2f}</span>'

def invia_email_report(dati_rosa):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")
    email_to = os.environ.get("EMAIL_TO", gmail_user)

    if not gmail_user or not gmail_pass:
        print("⚠️ Secret GMAIL_USER o GMAIL_APP_PASSWORD non trovati. Email non inviata.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "⚽ [IL MOSTRO] Report Aggiornato Rosa con Trend di Forma e Score"
    msg["From"] = gmail_user
    msg["To"] = email_to

    rosa_ordinata = sorted(dati_rosa, key=lambda x: (RUOLI_ORDINE.get(x['ruolo'], 99), -x['Score_Potenziale']))
    
    html_righe = ""
    for i, g in enumerate(rosa_ordinata, 1):
        html_righe += f"""
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 4px 6px; text-align: center; font-weight: bold;">{g['ruolo']}</td>
            <td style="padding: 4px 6px;"><b>{g['nome']}</b></td>
            <td style="padding: 4px 6px; text-align: center; font-size: 11px; color: #555;">{g['squadra']}</td>
            <td style="padding: 4px 6px; text-align: center; color: #2e7d32; font-weight: bold;">{g['Score_Potenziale']}</td>
            <td style="padding: 4px 6px; text-align: center;">{g['Fm_Tot']}</td>
            <td style="padding: 4px 6px; text-align: center;">{g['Fm_Recente']}</td>
            <td style="padding: 4px 6px; text-align: center;">{formatta_valore_html(g['Delta_Forma'])}</td>
            <td style="padding: 4px 6px; text-align: center; font-size: 11px;">{g['Trend']}</td>
            <td style="padding: 4px 6px; text-align: center;">{g['Gol']}</td>
            <td style="padding: 4px 6px; text-align: center;">{g['Assist']}</td>
        </tr>
        """

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.3; font-size: 13px;">
        <div style="background-color: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; padding: 12px; margin-bottom: 15px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 14px;">
            🤖 Motore "Il Mostro" - Analisi Rosa e Trend di Forma Aggiornata (Senza Excel)
        </div>

        <h3 style="color: #1a237e; margin: 0 0 8px 0;">📊 Valutazione Giocatori & Momentum Recente</h3>
        <p style="font-size: 12px; margin: 0 0 10px 0; color: #555;"><b>Legenda:</b> <i>Fm Tot</i> (Media Stagionale), <i>Fm Rec</i> (Ultime 3), <i>Δ</i> (Delta Forma), <i>Score</i> (Punteggio Ponderato).</p>
        
        <table style="width: 100%; max-width: 760px; border-collapse: collapse; background: #f9f9f9; margin: 4px 0 12px 0;">
            <thead>
                <tr style="background-color: #1a237e; color: white; font-size: 12px;">
                    <th style="padding: 6px;">R</th>
                    <th style="padding: 6px; text-align: left;">Nome</th>
                    <th style="padding: 6px;">Squadra</th>
                    <th style="padding: 6px;">Score</th>
                    <th style="padding: 6px;">Fm Tot</th>
                    <th style="padding: 6px;">Fm Rec</th>
                    <th style="padding: 6px;">Δ</th>
                    <th style="padding: 6px;">Trend</th>
                    <th style="padding: 6px;">Gol</th>
                    <th style="padding: 6px;">Ass</th>
                </tr>
            </thead>
            <tbody>
                {html_righe}
            </tbody>
        </table>

        <p style="font-size: 11px; color: #777; margin-top: 15px;"><i>Generato automaticamente da GitHub Actions con architettura JSON dinamica.</i></p>
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
        print("📧 Email di report con metriche di trend formattata e inviata con successo!")
    except Exception as e:
        print(f"❌ Errore durante l'invio dell'email: {e}")

if __name__ == "__main__":
    print("🚀 Avvio script di test/debug aggiornato (Il Mostro).")
    rosa, statistiche = load_data()
    evals = calcola_metriche_giocatori(rosa, statistiche)
    invia_email_report(evals)
