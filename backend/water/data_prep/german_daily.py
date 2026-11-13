import sys, os, json, pandas as pd, numpy as np
root = sys.argv[1]; out = sys.argv[2]
rows = []
for hh in sorted(os.listdir(root)):
    p = os.path.join(root, hh, "smartmeter.csv")
    info = open(os.path.join(root, hh, "info.txt")).read()
    res = int(info.split("number of residents:")[1].split()[0])
    df = pd.read_csv(p, usecols=["time", "total_m3"])
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert("Europe/Berlin")
    df = df.sort_values("time")
    df["date"] = df["time"].dt.date
    g = df.groupby("date")["total_m3"].agg(["first", "last", "count"])
    g["max"] = df.groupby("date")["total_m3"].max()
    # consumption of day d = first reading of d+1 - first reading of d (only consecutive days with data)
    g = g.reset_index()
    g["date"] = pd.to_datetime(g["date"])
    g["next_date"] = g["date"].shift(-1); g["next_first"] = g["first"].shift(-1)
    ok = (g["next_date"] - g["date"]).dt.days == 1
    d = g[ok].copy()
    d["m3"] = d["next_first"] - d["first"]
    d = d[(d["m3"] >= 0) & (d["m3"] < 5) & (d["count"] >= 100)]   # drop resets, faults and days with few readings
    d["household"] = hh; d["residents"] = res
    rows.append(d[["household", "residents", "date", "m3", "count"]])
    print(hh, res, len(df), "rows ->", len(d), "days", d["date"].min().date(), d["date"].max().date(),
          f"{d['m3'].mean()*1000/res:.0f} L/person/day")
pd.concat(rows).to_csv(out, index=False)
