import pandas as pd
from datetime import datetime
import streamlit as st
import bar_chart_race as bcr
import base64
import zipfile
import ffmpeg
from streamlit_extras.colored_header import colored_header
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.mandatory_date_range import date_range_picker
import hydralit_components as hc

st.set_page_config(
    page_title="Spotify Bar Race Chart",
    page_icon="spotifyIcon.ico",
)

# Custom CSS styles
def set_theme():
    st.markdown(
        """
        <style>
        body {
            color: #FFFFFF;                   /* Text color: white */
            background-color: #191414;        /* Background color: black */
        }
        div.stButton > button:first-child {
            background-color: #1DB954;        /* Button color: Spotify green */
            color: #FFFFFF;                   /* Button text color: white */
        }
        div.stButton > button:hover {
        border-color: #FFFFFF;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# Call the custom theme function
set_theme()  

#Parse data from the spotify export
@st.cache_data(ttl=600)
def openZipFile()->pd.DataFrame:
    df = pd.DataFrame()
    with zipfile.ZipFile(st.session_state.file,"r") as z:
        for file in z.namelist():
            if file.startswith("MyData/endsong"):
                json = pd.read_json(z.open(file))
                df = pd.concat([df,json])
    df = df[~df["master_metadata_track_name"].isna()].reset_index()
    return df

#Pre Process the data
@st.cache_data(ttl=600)
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

#Run the bar race chart with adequate parameters
st.cache_data()
def barRaceChart(df:pd.DataFrame,obj:str,bars:int,cmap:str)->str:
    
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

#Load basic stats on the sidebar
def loadSidebar(df:pd.DataFrame):
    with st.sidebar:
        colored_header("All-Time Statistics","general statistics about your account","green-70")

        left,right = st.columns([1,1])
        left.metric("Number of plays",len(df))
        right.metric("Period (days)",(df["date"].max()-df["date"].min()).days)

        left.metric("Differents artists",len(df["artists"].unique()))
        right.metric("Differents songs",len(df["songs"].unique()))

        style_metric_cards(border_left_color="#1DB954",background_color="#222222")

        left,right = st.columns([1,1])
        with left:
            colored_header("Top 10 artists","Your Top 10 most listened artists","green-70")
            artist10 = df["artists"].value_counts()[:10].to_frame().rename(columns={"artists":"Plays"})
            st.table(artist10)
        with right:
            colored_header("Top 10 songs","Your Top 10 most listened songs","green-70")
            songs10 = df["songs"].value_counts()[:10].to_frame().rename(columns={0:"Plays"})
            st.table(songs10)
    return None

#Landing page
if "file" not in st.session_state:
    desc = "You can ask for this file on your Spotify privacy page"
else:
    desc = "Well done !"
colored_header("Upload your 'My_Spotify_Data.zip'",desc,"green-70")
st.session_state.file = st.file_uploader("Upload your 'My_Spotify_Data.zip' file",type="zip",label_visibility="collapsed")
if st.session_state.file is None:
    st.warning("You want to upload your extended streaming history, not your account data")
    st.image("tutorial.png")
    st.info("To download those, you must first request them on your Spotify account, under the privacy tab.  It may takes up to a week to be available")

#Main function, ask for parameters then run the bar race chart and display it
else:
    data = openZipFile()
    df = process(data)
    loadSidebar(df)

    with st.form("Settings"):
        colored_header("Video parameters","Select the timeframe and choose the appearance of your chart","green-70")
        _,center,_ = st.columns([1,1,1])
        with center:
            obj = hc.option_bar([{"icon":"fa fa-users","label":"Artists"},{"icon":"fa fa-music","label":"Songs"}],"",horizontal_orientation=True,
                                override_theme={"menu_background":"#1DB954"},)
        left,center,right = st.columns(3)
        bars = left.number_input("Number of bars to display :",5,15,10)
        cmap = center.selectbox("Color Palette :",['spring', 'summer', 'autumn', 'winter'])
        with right:
            timeframe_start,timeframe_end = date_range_picker("What timeframe should I look at",df["date"].min(),df["date"].max())
        timeframe_start = datetime.combine(timeframe_start,datetime.min.time())
        timeframe_end = datetime.combine(timeframe_end,datetime.max.time())
        df = df[(df['date'] >= timeframe_start) & (df['date'] <= timeframe_end)]
        
        left,right = st.columns([1,1])
        if st.form_submit_button("Load Video"):
            st.session_state.video = barRaceChart(df,obj.lower(),bars,cmap)
            
    if "video" in st.session_state:
        st.video(st.session_state.video)
        left,_,center,_,right = st.columns([1,1,1,1,1])
        center.download_button("Download",st.session_state.video,file_name="SpotifyBRC.m4v")
    



