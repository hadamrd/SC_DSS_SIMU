def periodNervosity(Q_history, t):
    n = len(Q_history[0])
    res = 0
    print
    for k in range(n-1):
        y = t - k
        res += abs(Q_history[y][k] - Q_history[y-1][k+1])
    return res

def GI(Q_history):
    n = len(Q_history[0])
    res = sum([periodNervosity(Q_history, t) for t in range(n-1, 2*(n-1) + 1)]) / (n * (n-1))
    return res