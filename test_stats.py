import os
import requests
import io
import openpyxl

URL_LOGIN = "https://www.fantacalcio.it/api/v1/User/login"
URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"

def test_login_and_download():
    username = os.environ.get("FANTACALCIO_USER")
    password = os.environ.get("FANTACALCIO_PASS")
    
    if not username or not password:
        print("❌ Errore: FANTACALCIO_USER o FANTACALCIO_PASS non impostati nei Secrets.")
        return

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.fantacalcio.it/',
        'Origin': 'https://www.fantacalcio.it'
    })

    print("🔑 Autenticazione in corso su Fantacalcio.it...")
    login_payload = {
        "username": username,
        "password": password
    }
    
    res_login = session.post(URL_LOGIN, json=login_payload)
    print(f"📡 Status Code Login: {res_login.status_code}")
    
    if res_login.status_code == 200 and res_login.json().get("success"):
        print("✅ Autenticazione riuscita! Download del file statistiche...")
        
        res_excel = session.get(URL_EXCEL_STATS)
        print(f"📡 Status Code Excel: {res_excel.status_code}")
        
        if res_excel.status_code == 200:
            print(f"🎉 Download completato! Dimensione file: {len(res_excel.content)} bytes.")
            
            wb = openpyxl.load_workbook(io.BytesIO(res_excel.content), data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            
            print(f"📊 Totale righe nell'Excel: {len(rows)}")
            print("\n🔍 Esempio riga dati (Giocatore 1):")
            print(rows[2] if len(rows) > 2 else rows[0])
        else:
            print(f"❌ Impossibile scaricare l'Excel: {res_excel.status_code}")
    else:
        print(f"❌ Fallimento login: {res_login.text}")

if __name__ == "__main__":
    test_login_and_download()
