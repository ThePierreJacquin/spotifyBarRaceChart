import pandas as pd
from datetime import datetime
import streamlit as st
import bar_chart_race as bcr
import base64
import zipfile
import ffmpeg
st.set_page_config(
    page_title="Spotify Bar Race Chart",
    page_icon="spotifyIcon.ico",
)

@st.cache_data()
def openZipFile()->pd.DataFrame:
    df = pd.DataFrame()
    with zipfile.ZipFile(st.session_state.file,"r") as z:
        for file in z.namelist():
            if file.startswith("MyData/endsong"):
                json = pd.read_json(z.open(file))
                df = pd.concat([df,json])
    df = df[~df["master_metadata_track_name"].isna()].reset_index()
    return df

@st.cache_data()
def process(df:pd.DataFrame)->pd.DataFrame:
    serie = df["ts"].apply(lambda x : str(x).split("T")[0][:7])
    timeSerie = serie.apply(lambda x: datetime(int(x.split("-")[0]),int(x.split("-")[1]),day=1))
    df["ts"]=timeSerie
    df = df[["ts","master_metadata_track_name","master_metadata_album_artist_name"]]
    df =df.rename(columns={"ts":"date",
                    "master_metadata_track_name":"songs",
                    "master_metadata_album_artist_name":"artists"})
    df = df.replace('\\$', '',regex=True)
    df = df.sort_values("date")
    return df

st.cache_data()
def barRaceChart(df:pd.DataFrame,obj:str,bars:int,cmap:str):
    
    with st.spinner("Generating video ..."):
        top100 = df[obj].value_counts()[:100].index
        df_top = df[df[obj].isin(set(top100))]
        df_top = df_top[["date",obj]]
        dates = [ t[0] for t in df_top.value_counts().index]
        objs = [ t[1] for t in df_top.value_counts().index]
        number = df_top.value_counts().values

        df_listens = pd.DataFrame([dates,objs,number]).transpose()
        df_BRC = df_listens.pivot(index=0,columns=1).fillna(0).cumsum()
        html_str = bcr.bar_chart_race(  df=df_BRC,
                                        filename=None,
                                        orientation='h',
                                        sort='desc',
                                        n_bars=bars,
                                        cmap=cmap,
                                        filter_column_colors=True,
                                        title="My Spotify Bar Race Chart")
        start = html_str.find('base64,')+len('base64,')
        end = html_str.find('">')

        video = base64.b64decode(html_str[start:end])
    return (video)

def loadSidebar(df:pd.DataFrame):
    with st.sidebar:
        st.markdown("<h1 style='text-align: center; font-size:2.5em;'> Statistics </h1>",unsafe_allow_html=True)
        st.markdown("---")
        left,right = st.columns([1,1])
        left.metric("Number of plays",len(df))
        right.metric("Period (days)",(df["date"].max()-df["date"].min()).days)

        left.metric("Differents artists",len(df["artists"].unique()))
        right.metric("Differents songs",len(df["songs"].unique()))

        st.markdown("---")
        left,right = st.columns([1,1])

        artist10 = df["artists"].value_counts()[:10].to_frame().rename(columns={"artists":"Plays"})
        left.title("Top artists")
        left.table(artist10)

        songs10 = df["songs"].value_counts()[:10].to_frame().rename(columns={0:"Plays"})
        right.title("Top songs")
        right.table(songs10)
    return None

st.title("Upload your 'My_Spotify_Data.zip'")
st.session_state.file = st.file_uploader("Upload your 'My_Spotify_Data.zip' file",type="zip",label_visibility="collapsed")

if st.session_state.file is None:
    st.warning("You want to upload your extended streaming history, not your account data")
    st.image("tutorial.png")
    st.info("To download those, you must first request them on your Spotify account, under the privacy tab.  It may takes up to a week to be available")
else:
    data = openZipFile()
    df = process(data)
    loadSidebar(df)
    with st.form("Settings"):
        _,center,_ = st.columns([1,1,1])
        obj = center.radio("What do you want to track :",["artists","songs"],horizontal=True)
        bars = st.slider("Number of bars to display :",5,15,10)
        cmap = st.select_slider("Color Palette :",['spring', 'summer', 'autumn', 'winter'])
        
        timeframe_start,timeframe_end =  st.select_slider("What timeframe should I look at",df["date"],value=(df["date"].min(),df["date"].max()),format_func=lambda x: str(x)[:7].replace("-","/"))
        df = df[(df['date'] >= timeframe_start) & (df['date'] <= timeframe_end)]
        st.write("temps de chargement ~" , 5*bars*(df["date"].max()-df["date"].min()).days/365, " secondes")
        if st.form_submit_button("Load Video"):
            st.session_state.video = barRaceChart(df,obj,bars,cmap)
    if "video" in st.session_state:
        st.video(st.session_state.video)
        left,_,center,_,right = st.columns([1,1,1,1,1])
        center.download_button("Download",st.session_state.video,file_name="SpotifyBRC.m4v")
    



