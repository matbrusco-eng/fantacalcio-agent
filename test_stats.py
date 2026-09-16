import requests

URL_EXCEL_STATS = "https://www.fantacalcio.it/api/v1/Excel/stats/21/5"

def test_download_with_headers():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/octet-stream, */*',
        'Referer': 'https://www.fantacalcio.it/statistiche-serie-a',
        'Origin': 'https://www.fantacalcio.it'
    }
    
    print("📡 Scaricamento file Excel con Referer...")
    resp = requests.get(URL_EXCEL_STATS, headers=headers)
    
    print(f"📡 Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print(f"✅ Download sbloccato! Dimensione: {len(resp.content)} bytes")
    else:
        print("⚠️ Richiesto token di autorizzazione o cookie di sessione.")

if __name__ == "__main__":
    test_download_with_headers()
