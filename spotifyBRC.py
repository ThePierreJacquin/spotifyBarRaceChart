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

st.markdown("""
            <style>
            .css-1xarl3l {
                font-size: 0.75rem;
                padding-bottom: 0.25rem;}
            .css-jcmizx {
                font-size: 0.25rem;}
            </style>
            """,
            unsafe_allow_html=True)

#Parse data from the spotify export
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
def barRaceChart(df:pd.DataFrame,obj:str,bars:int,cmap:str)->str:
    
    with st.spinner("Generating video ..."):
        top100 = df[obj].value_counts()[:100].index
        df_top = df[df[obj].isin(set(top100))]
        df_top = df_top[["date",obj]]
        dates = [ t[0] for t in df_top.value_counts().index]
        objs = [ t[1] for t in df_top.value_counts().index]
        number = df_top.value_counts().values

        df_listens = pd.DataFrame([dates,objs,number]).transpose().rename({0:"date",1:"name",2:"values"},axis=1)
        df_BRC = pd.pivot(df_listens,values="values",index="date",columns="name").fillna(0).cumsum()
        
        html_str = bcr.bar_chart_race(  df=df_BRC,
                                        filename=None,
                                        orientation='h',
                                        sort='desc',
                                        n_bars=bars,
                                        cmap=cmap,
                                        period_label={'x': .98, 'y': .1, 'ha': 'right', 'va': 'center',"size":18}, 
                                        period_fmt='%B %Y', 
                                        period_summary_func=lambda v, r: {'x': .98, 'y': .14, 
                                          's': f'Total listens: {v.sum():,.0f}', 
                                          'ha': 'right', 'size': 10}, 
                                        steps_per_period=20,
                                        filter_column_colors=True,
                                        bar_kwargs={'alpha': .7},
                                        figsize=(5, 5),
                                        dpi=144,
                                        title="My Spotify Bar Race Chart",
                                        title_size="smaller",
                                        shared_fontdict={'family': 'Impact', 'weight': 'bold',
                                                        'color': 'black'})
        start = html_str.find('base64,')+len('base64,')
        end = html_str.find('">')

        video = base64.b64decode(html_str[start:end])
    return (video)

def format_number_with_space(number):
    # Convert the number to a string
    number_str = str(number)

    # Insert spaces between every three digits from the right
    formatted_number = ""
    for i, digit in enumerate(reversed(number_str)):
        if i > 0 and i % 3 == 0:
            formatted_number = " " + formatted_number
        formatted_number = digit + formatted_number

    return formatted_number

#Load basic stats on the sidebar
def loadSidebar(df:pd.DataFrame):
    with st.sidebar:
        colored_header("All-Time Statistics","General statistics about your account","green-70")
        style_metric_cards(border_left_color="#1DB954",background_color="#191414")
        with st.expander("All-around stats",True):
            left,right = st.columns([1,1])
            left.metric("Number of plays",format_number_with_space(len(df)))
            right.metric("Period (days)",format_number_with_space((df["date"].max()-df["date"].min()).days))

            left.metric("Differents artists",format_number_with_space(len(df["artists"].unique())))
            right.metric("Differents songs",format_number_with_space(len(df["songs"].unique())))
            

        left,right = st.columns([1,1])
        with left,st.form(key="left"):
            colored_header("Top 10 artists","Your Top 10 most listened artists","green-70")
            artist10 = df["artists"].value_counts().reset_index()
            for rank,row in artist10[:10].iterrows():
                st.metric(str(rank+1)+ "# - " +str(row[0]),str(format_number_with_space(row[1])) +" listens")
            if st.form_submit_button("Show full rankings"):
                artist10.rename({"index":"Artists","artists":"listens"},inplace=True,axis=1)
                st.dataframe(artist10,use_container_width=True)

        with right,st.form(key="right"):
            colored_header("Top 10 songs","Your Top 10 most listened songs","green-70")
            songs10 = df["songs"].value_counts().reset_index()
            for rank,row in songs10[:10].iterrows():
                st.metric(str(rank+1)+ "# - " +str(row[0]),str(format_number_with_space(row[1])) +" listens")
            if st.form_submit_button("Show full rankings"):
                songs10.rename({"index":"Songs","songs":"listens"},inplace=True,axis=1)
                st.dataframe(songs10,use_container_width=True)
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
    if "df" not in st.session_state:
        data = openZipFile()
        df = st.session_state.df = process(data)
    else:
        df = st.session_state.df
        
    loadSidebar(df)

    with st.form("Settings"):
        colored_header("Video parameters","Select the timeframe and choose the appearance of your chart","green-70")
        _,center,_ = st.columns([1,1,1])
        with center:
            obj = hc.option_bar([{"icon":"fa fa-users","label":"Artists"},{"icon":"fa fa-music","label":"Songs"}],"",horizontal_orientation=True,
                                override_theme={"menu_background":"#1DB954"},)
        left,center,right = st.columns(3)
        bars = left.number_input("Number of bars to display :",5,15,10)
        cmap = center.selectbox("Color Palette :",['Dark24', 'Light24'],format_func=lambda x:x[:-2])
        with right:
            timeframe_start,timeframe_end = date_range_picker("What timeframe should I look at",df["date"].min(),df["date"].max())
        timeframe_start = datetime.combine(timeframe_start,datetime.min.time())
        timeframe_end = datetime.combine(timeframe_end,datetime.max.time())
        df = df[(df['date'] >= timeframe_start) & (df['date'] <= timeframe_end)]
        
        left,right = st.columns([5,1])
        if right.form_submit_button("Load Video"):
            st.session_state.video = barRaceChart(df,obj.lower(),bars,cmap)
            
    if "video" in st.session_state:
        st.video(st.session_state.video)
        left,_,center,_,right = st.columns([1,1,1,1,1])
        center.download_button("Download",st.session_state.video,file_name="SpotifyBRC.m4v")
    



