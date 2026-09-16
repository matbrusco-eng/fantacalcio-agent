import requests
import io
import openpyxl

URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"

def test_estrazione_fantamedia():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    print("📡 Scaricamento file Excel da Fantacalcio.it...")
    resp = requests.get(URL_EXCEL_STATS, headers=headers)
    
    if resp.status_code != 200:
        print(f"❌ Errore durante il download. Status Code: {resp.status_code}")
        return

    print(f"✅ Download completato ({len(resp.content)} bytes). Lettura file Excel...")
    
    try:
        excel_data = io.BytesIO(resp.content)
        wb = openpyxl.load_workbook(excel_data, data_only=True)
        sheet = wb.active
        
        # Stampi le prime 5 righe per capire l'intestazione
        rows = list(sheet.iter_rows(values_only=True))
        print(f"📊 Righe totali nel file: {len(rows)}")
        
        print("\n🔍 Prima riga (Intestazioni):")
        print(rows[0])
        print("\n🔍 Seconda riga (Intestazioni/Dati):")
        print(rows[1])
        print("\n🔍 Esempio giocatore (Riga 3):")
        print(rows[2] if len(rows) > 2 else "N/A")
        
    except Exception as e:
        print(f"❌ Errore nella lettura dell'Excel: {e}")

if __name__ == "__main__":
    test_estrazione_fantamedia()
