def max_profit_given_risk(points, risk_percent, delta_percent, fee_percent=0.25):
    """
    Determine the maximum profit that could be obtained within the given points without going below risk
    """
    # TODO: Use OHLC in here

    fee_fraction = abs(fee_percent / 100.0)
    risk_fraction = abs(risk_percent / 100.0)
    delta_fraction = abs(delta_percent / 100.0)
    
    initial = points[0]
    sl = initial * (1.0 - risk_fraction)
    tp = initial * (1.0 + risk_fraction)
    risk_abs = initial * risk_fraction
    max_value = initial
    exit_value = initial
        
    for p in points:
        if p <= sl: # Hit stop loss
            exit_value = sl
            break
            
        if p > max_value: # Record new high
            max_value = p
            
        if (max_value >= tp) and p <= max_value * (1.0 - delta_fraction): # Close trade when price drops
            exit_value = p
            break
            
    fees = (initial + exit_value) * fee_fraction
    
    #print("Initial: {}, Stop Loss: {}, Take Profit: {}, Abs risk: {}".format(initial, sl, tp, risk_abs))
    #print("Gain: {}, Exit: {}, Max : {}, Fees: {}".format(exit_value - initial, exit_value, max_value, fees))
    
    return exit_value - initial, fees


def profit_series(df, window=256, risk=1.0, delta=0.1):
    num = len(df.Close[:-window])
    tick = range(num)
    tp = []

    for idx in tick:
        t = max_profit_given_risk(df.Close[idx:idx+window], risk_percent=risk, delta_percent=delta)
        tp.append(t)
    tp.extend([0]*window)
    df['Profit'] = tp
    return df