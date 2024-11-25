import ccxt


print("All exchanges", ccxt.exchanges)

print("Binance")
binance = ccxt.binance()
print(binance.id, binance.load_markets())
