name: Bearish Horizon Test
on:
  workflow_dispatch:
permissions:
  contents: write
jobs:
  run:
    runs-on: ubuntu-latest
    timeout-minutes: 120
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pandas numpy requests yfinance
      - name: Run test
        env:
          ALPACA_API_KEY_ID: ${{ secrets.ALPACA_API_KEY_ID }}
          ALPACA_API_SECRET_KEY: ${{ secrets.ALPACA_API_SECRET_KEY }}
          APCA_API_KEY_ID: ${{ secrets.APCA_API_KEY_ID }}
          APCA_API_SECRET_KEY: ${{ secrets.APCA_API_SECRET_KEY }}
        run: python bearish_horizon_test.py
      - name: Save results
        if: always()
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add results/bearish_horizon || true
          git commit -m "Bearish horizon results" || true
          git pull --rebase || true
          git push || true
