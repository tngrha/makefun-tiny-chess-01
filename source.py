# tiny-chess-01: 0x88 alpha-beta engine (material + piece-square tables + bishop
# pair + endgame king, transposition table, killers, MVV-LVA, quiescence, fixed nodes).
import json, os, random, sys, urllib.error, urllib.request
ENV = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")
BUDGET = 220000
MATE = 100000
VAL = (0, 100, 320, 330, 500, 900, 0)
PST = (
    "++++++++55555555--/11/--,,-00-,,+++//+++,*)++)*,,--''--,++++++++",
    "!#%%%%#!#'++++'#%+-..-+%%,.//.,%%+.//.+%%,-..-,%#'+,,+'#!#%%%%#!",
    "'))))))')++++++))+,--,+)),,--,,))+----+))------)),++++,)'))))))'",
    "++++++++,------,*++++++**++++++**++++++**++++++**++++++*+++,,+++",
    "'))**))')++++++))+,,,,+)*+,,,,+*++,,,,+*),,,,,+))+,++++)'))**))'",
    "%##!!##%%##!!##%%##!!##%%##!!##%'%%##%%')'''''')//++++///1-++-1/",
)
SQ64 = [r * 16 + f for r in range(8) for f in range(8)]
ND = (-33, -31, -18, -14, 14, 18, 31, 33)
KD = (-17, -16, -15, -1, 1, 15, 16, 17)
BD = (-17, -15, 15, 17)
RD = (-16, -1, 1, 16)
_R = random.Random(7)
ZB = [_R.getrandbits(64) for _ in range(1664)]
ZS = _R.getrandbits(64)
b = [0] * 128
s = 1
c = 0
e = -1
ev = 0
mat = 0
nb = [0, 0]
nq = 0
K = [4, 116]
z = 0
N = 0
TT = {}
KL = [[0, 0] for _ in range(256)]
H = set()
P = set()
def pst(p, sq, white):
    i = (sq >> 4) * 8 + (sq & 7)
    return (ord(PST[p - 1][63 - i if white else i]) - 33) * 5 - 50
def pv(p, sq, white):
    return VAL[p] + (pst(p, sq, white) if p != 6 else 0)
def pos(fen):
    global b, s, c, e, ev, mat, nb, nq, K, z
    parts = fen.split()
    b = [0] * 128
    for r, row in enumerate(parts[0].split("/")):
        f = 0
        for ch in row:
            if ch.isdigit():
                f += int(ch)
            else:
                sq = (7 - r) * 16 + f
                code = "PNBRQK".index(ch.upper()) + 1
                b[sq] = code if ch.isupper() else -code
                f += 1
    s = 1 if parts[1] == "w" else -1
    c = 0
    if len(parts) > 2:
        for i, ch in enumerate("KQkq"):
            if ch in parts[2]:
                c |= 1 << i
    e = -1
    if len(parts) > 3 and parts[3] != "-":
        e = (ord(parts[3][0]) - 97) + (int(parts[3][1]) - 1) * 16
    ev = 0
    mat = 0
    nb = [0, 0]
    nq = 0
    K = [4, 116]
    z = 0
    for sq in SQ64:
        p = b[sq]
        if not p:
            continue
        ap = abs(p)
        white = p > 0
        ev += (1 if white else -1) * pv(ap, sq, white)
        if ap != 6:
            mat += VAL[ap]
        if ap == 3:
            nb[0 if white else 1] += 1
        if ap == 5:
            nq += 1
        if ap == 6:
            K[0 if white else 1] = sq
        z ^= ZB[(p + 6) * 128 + sq]
    if s == -1:
        z ^= ZS
def atk(t, w):
    for o in (-15, -17) if w == 1 else (15, 17):
        u = t + o
        if not u & 0x88 and b[u] == w:
            return 1
    for o in ND:
        u = t + o
        if not u & 0x88 and b[u] == 2 * w:
            return 1
    for o in KD:
        u = t + o
        if not u & 0x88 and b[u] == 6 * w:
            return 1
    for o in BD:
        u = t + o
        while not u & 0x88:
            q = b[u]
            if q:
                if q == 3 * w or q == 5 * w:
                    return 1
                break
            u += o
    for o in RD:
        u = t + o
        while not u & 0x88:
            q = b[u]
            if q:
                if q == 4 * w or q == 5 * w:
                    return 1
                break
            u += o
    return 0
def mk(f, t, p):
    return f | (t << 7) | (p << 14)
def gen(caps_only=False):
    ms = []
    for sq in SQ64:
        p = b[sq]
        if p * s <= 0:
            continue
        ap = p if p > 0 else -p
        if ap == 1:
            d = 16 * s
            lr = 7 if s == 1 else 0
            t = sq + d
            if not t & 0x88 and b[t] == 0:
                last = (t >> 4) == lr
                if last:
                    for pr in (5, 4, 3, 2):
                        ms.append(mk(sq, t, pr))
                elif not caps_only:
                    ms.append(mk(sq, t, 0))
                    if (sq >> 4) == (1 if s == 1 else 6) and b[sq + 2 * d] == 0:
                        ms.append(mk(sq, sq + 2 * d, 0))
            for t in (sq + d - 1, sq + d + 1):
                if t & 0x88:
                    continue
                if (b[t] * s < 0 and abs(b[t]) != 6) or t == e:
                    last = (t >> 4) == lr
                    if last:
                        for pr in (5, 4, 3, 2):
                            ms.append(mk(sq, t, pr))
                    else:
                        ms.append(mk(sq, t, 0))
        elif ap == 2 or ap == 6:
            for o in ND if ap == 2 else KD:
                t = sq + o
                if not t & 0x88 and b[t] * s <= 0 and abs(b[t]) != 6 and (not caps_only or b[t] * s < 0):
                    ms.append(mk(sq, t, 0))
            if ap == 6 and not caps_only:
                o = 0 if s == 1 else 112
                sh = 0 if s == 1 else 2
                for bit, emp, at, t, rf, rt in ((1 << sh, (5, 6), (4, 5, 6), 6, 7, 5), (2 << sh, (1, 2, 3), (4, 3, 2), 2, 0, 3)):
                    if c & bit and b[o + rf] == 4 * s and all(b[o + i] == 0 for i in emp) and all(not atk(o + i, -s) for i in at):
                        ms.append(mk(o + 4, o + t, 0))
        else:
            ds = BD if ap == 3 else RD if ap == 4 else BD + RD
            for o in ds:
                t = sq + o
                while not t & 0x88:
                    q = b[t]
                    if q:
                        if q * s < 0 and abs(q) != 6:
                            ms.append(mk(sq, t, 0))
                        break
                    if not caps_only:
                        ms.append(mk(sq, t, 0))
                    t += o
    return ms
def make(m):
    global s, c, e, ev, mat, nq, z
    f = m & 127
    t = (m >> 7) & 127
    pr = m >> 14
    p = b[f]
    ap = p if p > 0 else -p
    col = 1 if p > 0 else -1
    cap = b[t]
    csq = t
    if ap == 1 and t == e and cap == 0:
        csq = t - 16 * s
        cap = b[csq]
    np = pr if pr else ap
    dev = 0
    dz = ZB[(p + 6) * 128 + f] ^ ZS
    dev -= col * pv(ap, f, col > 0)
    dev += col * pv(np, t, col > 0)
    if cap:
        ac = cap if cap > 0 else -cap
        dev += col * pv(ac, csq, cap > 0)
    rf = rt = -1
    if ap == 6 and abs(t - f) == 2:
        if t > f:
            rf, rt = t + 1, t - 1
        else:
            rf, rt = t - 2, t + 1
        dev += col * (pst(4, rt, col > 0) - pst(4, rf, col > 0))
        dz ^= ZB[(4 * col + 6) * 128 + rf] ^ ZB[(4 * col + 6) * 128 + rt]
        b[rt] = b[rf]
        b[rf] = 0
    b[t] = col * np
    b[f] = 0
    if csq != t:
        b[csq] = 0
    if ap == 6:
        K[0 if col == 1 else 1] = t
    if cap:
        ac = cap if cap > 0 else -cap
        mat -= VAL[ac]
        if ac == 3:
            nb[0 if cap > 0 else 1] -= 1
        if ac == 5:
            nq -= 1
    if pr:
        mat += VAL[pr] - VAL[1]
        if pr == 3:
            nb[0 if col == 1 else 1] += 1
        if pr == 5:
            nq += 1
    oc = c
    if ap == 6:
        c &= ~(3 if col == 1 else 12)
    if f == 0 or csq == 0:
        c &= ~2
    if f == 7 or csq == 7:
        c &= ~1
    if f == 112 or csq == 112:
        c &= ~8
    if f == 119 or csq == 119:
        c &= ~4
    oe = e
    e = f + 16 * s if ap == 1 and abs(t - f) == 32 else -1
    dz ^= ZB[(col * np + 6) * 128 + t]
    if cap:
        dz ^= ZB[(cap + 6) * 128 + csq]
    z ^= dz
    ev += dev
    s = -s
    return (m, cap, csq, oc, oe, dev, dz)
def unmake(u):
    global s, c, e, ev, mat, nq, z
    m, cap, csq, oc, oe, dev, dz = u
    f = m & 127
    t = (m >> 7) & 127
    pr = m >> 14
    p = b[t]
    ap = p if p > 0 else -p
    col = 1 if p > 0 else -1
    b[f] = col * (1 if pr else ap)
    b[t] = cap if csq == t else 0
    if csq != t:
        b[csq] = cap
    if cap:
        ac = cap if cap > 0 else -cap
        mat += VAL[ac]
        if ac == 3:
            nb[0 if cap > 0 else 1] += 1
        if ac == 5:
            nq += 1
    if pr:
        mat -= VAL[pr] - VAL[1]
        if pr == 3:
            nb[0 if col == 1 else 1] -= 1
        if pr == 5:
            nq -= 1
    if ap == 6:
        K[0 if col == 1 else 1] = f
        if abs(t - f) == 2:
            if t > f:
                rf, rt = t + 1, t - 1
            else:
                rf, rt = t - 2, t + 1
            b[rf] = b[rt]
            b[rt] = 0
    c = oc
    e = oe
    ev -= dev
    z ^= dz
    s = -s
def evl():
    v = ev
    if nq:
        v += pst(6, K[0], 1) - pst(6, K[1], 0)
    else:
        for k, col in ((K[0], 1), (K[1], -1)):
            v += col * (7 - abs((k & 7) - 3.5) - abs((k >> 4) - 3.5)) * 5
    v += 30 * (nb[0] == 2) - 30 * (nb[1] == 2)
    return v * s
class TO(Exception):
    pass
def order(ms, ply, tt_move):
    def sc(m):
        if m == tt_move:
            return 1 << 20
        f = m & 127
        t = (m >> 7) & 127
        cap = b[t]
        if cap == 0 and t == e and abs(b[f]) == 1:
            cap = -s
        if cap:
            return (1 << 16) + 10 * VAL[abs(cap)] - VAL[abs(b[f])] // 16
        if m == KL[ply][0]:
            return 1 << 15
        if m == KL[ply][1]:
            return 1 << 14
        return 0
    ms.sort(key=sc, reverse=True)
def qs(a, be, ply):
    global N
    N += 1
    if N > BUDGET:
        raise TO
    stand = evl()
    if stand >= be:
        return be
    if stand > a:
        a = stand
    in_check = atk(K[0] if s == 1 else K[1], -s)
    ms = gen(False) if in_check else gen(True)
    order(ms, ply, 0)
    for m in ms:
        u = make(m)
        if atk(K[0] if s == -1 else K[1], s):
            unmake(u)
            continue
        P.add(z)
        try:
            sc = -qs(-be, -a, ply + 1)
        except TO:
            P.discard(z)
            unmake(u)
            raise
        P.discard(z)
        unmake(u)
        if sc >= be:
            return be
        if sc > a:
            a = sc
    return a
def sr(a, be, d, ply):
    global N
    N += 1
    if N > BUDGET:
        raise TO
    e = TT.get(z)
    tt_move = 0
    if e and e[0] >= d:
        sc, fl, tt_move = e[1], e[2], e[3]
        if fl == 0:
            return sc
        if fl == 1 and sc >= be:
            return sc
        if fl == 2 and sc <= a:
            return sc
    if d <= 0:
        return qs(a, be, ply)
    in_check = atk(K[0] if s == 1 else K[1], -s)
    if in_check:
        d += 1
    ms = gen(False)
    order(ms, ply, tt_move)
    best = -MATE
    bm = 0
    fl = 2
    a0 = a
    legal = 0
    for m in ms:
        u = make(m)
        if atk(K[0] if s == -1 else K[1], s):
            unmake(u)
            continue
        legal += 1
        if z in H or z in P:
            sc = 0
        else:
            P.add(z)
            try:
                sc = -sr(-be, -a, d - 1, ply + 1)
            except TO:
                P.discard(z)
                unmake(u)
                raise
            P.discard(z)
        unmake(u)
        if sc > best:
            best, bm = sc, m
        if sc > a:
            a = sc
            if a >= be:
                fl = 1
                if not b[(m >> 7) & 127]:
                    KL[ply][1] = KL[ply][0]
                    KL[ply][0] = m
                break
    if legal == 0:
        return -MATE + ply if in_check else 0
    if fl != 1:
        fl = 0 if best > a0 else 2
    TT[z] = (d, fl, best, bm)
    return best
def rt(d, root_best):
    global N
    ms = gen(False)
    order(ms, 0, root_best)
    a = -MATE
    best = 0
    for m in ms:
        u = make(m)
        if atk(K[0] if s == -1 else K[1], s):
            unmake(u)
            continue
        if z in H or z in P:
            sc = 0
        else:
            P.add(z)
            try:
                sc = -sr(-MATE, -a, d - 1, 1)
            except TO:
                P.discard(z)
                unmake(u)
                raise
            P.discard(z)
        unmake(u)
        if sc > a:
            a, best = sc, m
    return a, best
def root():
    global N
    ms = gen(False)
    legal = [m for m in ms if _legal(m)]
    if not legal:
        return ms[0] if ms else 0
    if len(legal) == 1:
        return legal[0]
    best = legal[0]
    for d in range(1, 99):
        try:
            sc, m = rt(d, best)
        except TO:
            break
        if m:
            best = m
        if sc > MATE - 1000:
            break
    return best
def _legal(m):
    u = make(m)
    ok = not atk(K[0] if s == -1 else K[1], s)
    unmake(u)
    return ok
def sn(sq):
    return chr(97 + (sq & 7)) + str((sq >> 4) + 1)
def uci(m):
    f = m & 127
    t = (m >> 7) & 127
    pr = m >> 14
    return sn(f) + sn(t) + ("", "x", "n", "b", "r", "q")[pr]
def pu(u):
    f = (ord(u[0]) - 97) + (int(u[1]) - 1) * 16
    t = (ord(u[2]) - 97) + (int(u[3]) - 1) * 16
    pr = {"n": 2, "b": 3, "r": 4, "q": 5}.get(u[4], 0) if len(u) > 4 else 0
    return mk(f, t, pr)
def choose(game):
    global H, N, TT
    pos(game["start_fen"])
    H = {z}
    for u in game["moves"]:
        make(pu(u))
        H.add(z)
    pos(game["fen"])
    N = 0
    TT = {}
    for i in range(256):
        KL[i][0] = KL[i][1] = 0
    m = root()
    ans = uci(m)
    if ans not in game["legal_moves"]:
        return game["legal_moves"][0]
    return ans
def post(path, body):
    req = urllib.request.Request(ENV + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as ex:
        sys.exit(f"{path}: HTTP {ex.code} {ex.read().decode(errors='replace')}")
    except urllib.error.URLError:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
def main():
    while True:
        g = post("/game", {})
        if g["status"] == "done":
            break
        while g["status"] == "your_move":
            g = post("/move", {"game": g["game"], "move": choose(g)})
    print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)
if __name__ == "__main__":
    main()
