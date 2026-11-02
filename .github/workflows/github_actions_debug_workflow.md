name: Test Manuale Debug Formazione

on:
  workflow_dispatch:

jobs:
  run-debug:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests openpyxl beautifulsoup4

      - name: Run debug script
        env:
          FANTACALCIO_USER: ${{ secrets.FANTACALCIO_USER }}
          FANTACALCIO_PASS: ${{ secrets.FANTACALCIO_PASS }}
          FANTA_USER: ${{ secrets.FANTA_USER }}
          FANTA_PASS: ${{ secrets.FANTA_PASS }}
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          EMAIL_TO: ${{ secrets.EMAIL_TO }}
        run: |
          python test_debug.py