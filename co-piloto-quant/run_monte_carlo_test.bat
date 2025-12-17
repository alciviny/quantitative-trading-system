@echo off
cd /d "c:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO\co-piloto-quant"
python scripts/stress_test_monte_carlo.py --input-file momentum_all_regimes_results.csv --simulations 5000
pause
