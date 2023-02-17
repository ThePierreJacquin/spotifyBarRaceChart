import pandas as pd
import os
from datetime import datetime
import streamlit as st
df = pd.DataFrame()
for file in os.listdir('./data/'):
    json = pd.read_json("./data/" + file)
    df = pd.concat([df,json])
df = df[~df["master_metadata_track_name"].isna()].reset_index()


serie = df["ts"].apply(lambda x : x.split("T")[0][:7])
timeSerie = serie.apply(lambda x: datetime(int(x.split("-")[0]),int(x.split("-")[1]),day=1))
df["ts"]=timeSerie
df = df[["ts","master_metadata_track_name","master_metadata_album_artist_name"]]
df =df.rename(columns={"ts":"date",
                   "master_metadata_track_name":"song",
                   "master_metadata_album_artist_name":"artist"})

top20 = df["artist"].value_counts()[:30].index
df_top = df[df["artist"].isin(set(top20))]
df_top = df_top[["date","artist"]]

dates = [ t[0] for t in df_top.value_counts().index]
artists = [ t[1] for t in df_top.value_counts().index]
nombres = df_top.value_counts().values

df_listens = pd.DataFrame([dates,artists,nombres]).transpose()

import matplotlib.pyplot as plt

# plt.figure(figsize=(25, 14), dpi=80)
# for artist in set(top20):
#     df_temp = df_listens[df_listens[1]==artist].sort_values(by=0)
#     plt.plot(df_temp[0],df_temp[2].cumsum(),label=artist)

# plt.legend()
# plt.show()

df_BRC = df_listens.pivot(index=0,columns=1).fillna(0)
import bar_chart_race as bcr

bcr.bar_chart_race(
    df=df_BRC,
    filename=None,
    orientation='h',
    sort='desc',
    n_bars=10)  

plt.show()

