import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from difflib import get_close_matches
import plotly.express as px

# ===========================
# 1️⃣ Konfigurasi Halaman
# ===========================
st.set_page_config(
    page_title="Dashboard Ketahanan Pangan Sumatera",
    layout="wide",
    page_icon="🌾"
)

# ---- CUSTOM CSS ----
st.markdown("""
<style>
.main-title {text-align:center; font-size:40px; color:#2d6a4f; font-weight:bold;}
.sub-header {text-align:center; font-size:18px; color:#40916c; margin-bottom:20px;}
[data-testid="stSidebar"] {background-color: #f1faee;}
.dataframe th {background-color:#40916c; color:white; text-align:center;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>📊 Dashboard Ketahanan Pangan Pulau Sumatera</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Analisis klasterisasi ketahanan pangan kabupaten/kota se-Sumatera</p>", unsafe_allow_html=True)

# ===========================
# 2️⃣ Load Data
# ===========================
@st.cache_data
def load_data():
    gdf = gpd.read_file(r"D:\semester 7\Project Sains Data\Sumatera.shp")
    df_cluster = pd.read_excel(r"D:\semester 7\Project Sains Data\hasil_cluster_som.xlsx")

    def clean_name(x):
        if pd.isna(x): return ""
        x = x.upper().replace("KABUPATEN","").replace("KOTA","").strip()
        return " ".join(x.split())

    gdf['NAME_CLEAN'] = gdf['NAME_2'].apply(clean_name)
    df_cluster['Kab_CLEAN'] = df_cluster['Kabupaten/Kota'].apply(clean_name)

    merged = gdf.merge(df_cluster, left_on='NAME_CLEAN', right_on='Kab_CLEAN', how='left')

    # fuzzy matching
    unmatched = merged[merged['Cluster'].isna()]
    for i, row in unmatched.iterrows():
        match = get_close_matches(row['NAME_CLEAN'], df_cluster['Kab_CLEAN'], n=1, cutoff=0.80)
        if match:
            data_row = df_cluster[df_cluster['Kab_CLEAN']==match[0]].iloc[0]
            for col in df_cluster.columns:
                merged.loc[i, col] = data_row[col]

    kategori_dict = {0:"Rentan",1:"Agak Tahan",2:"Sangat Tahan",3:"Sangat Rentan",4:"Tahan",5:"Sangat Tahan"}
    if "Kategori_Ketahanan_Pangan" not in merged.columns:
        merged["Kategori_Ketahanan_Pangan"] = merged["Cluster"].map(kategori_dict)

    return merged

sumatera = load_data()

# ===========================
# 3️⃣ Sidebar
# ===========================
st.sidebar.header("🔍 Filter dan Informasi")
provinsi_list = sorted(sumatera["NAME_1"].unique())
selected_provinsi = st.sidebar.selectbox("Pilih Provinsi", provinsi_list)
filtered_data = sumatera[sumatera["NAME_1"]==selected_provinsi]

st.sidebar.markdown("---")
st.sidebar.write("**Indikator Utama**")
st.sidebar.markdown("""
- 🟢 IKP – Indeks Ketahanan Pangan  
- 🌾 Produktivitas Padi & Produksi Beras  
- 💰 PDRB – ekonomi daerah  
- 👥 RLS, UHH, TPAK, P0, PPK
""")
st.sidebar.markdown("---")

# ===========================
# 4️⃣ Warna Per Cluster
# ===========================
color_dict = {0:"#f4a261",1:"#52b69a",2:"#2d6a4f",3:"#d62828",4:"#f4d35e",5:"#264653"}

# ===========================
# 5️⃣ Ringkasan Cluster + Metrics + Pie Chart
# ===========================
st.subheader(f"📈 Ringkasan Cluster {selected_provinsi}")

# Metrics indikator utama
col_metrics = st.columns(4)
col_metrics[0].metric("IKP Rata-rata", f"{filtered_data['IKP'].mean():.2f}")
col_metrics[1].metric("Produktivitas Padi", f"{filtered_data['Produktivitas_Padi'].mean():.2f} ku/ha")
col_metrics[2].metric("Produksi Beras", f"{filtered_data['Produksi_Beras'].sum():,.0f} ton")
col_metrics[3].metric("PDRB", f"{filtered_data['PDRB'].sum():,.0f}")

# Ringkasan cluster
cluster_summary = (
    filtered_data.groupby("Cluster")
    .agg(
        Jumlah_Kabupaten=("NAME_2","count"),
        IKP_Rata2=("IKP","mean"),
        Produktivitas_Rata2=("Produktivitas_Padi","mean"),
        Produksi_Beras_Rata2=("Produksi_Beras","mean"),
        PDRB_Rata2=("PDRB","mean")
    ).reset_index()
)
cluster_labels = {0:"Rentan",1:"Agak Tahan",2:"Sangat Tahan",3:"Sangat Rentan",4:"Tahan",5:"Sangat Tahan"}
cluster_summary["Kategori"] = cluster_summary["Cluster"].map(cluster_labels)

# Layout Tabel + Pie Chart
col1, col2 = st.columns([2,1])

with col1:
    st.markdown("#### Tabel Ringkasan Cluster")
    # Highlight warna kategori
    def highlight_cat(val):
        color_map = {"Sangat Rentan":"#d62828","Rentan":"#f4a261","Agak Tahan":"#52b69a",
                     "Tahan":"#f4d35e","Sangat Tahan":"#264653"}
        return f"background-color: {color_map.get(val,'#ffffff')}; color:white; font-weight:bold;"
    st.dataframe(cluster_summary.style.applymap(highlight_cat, subset=["Kategori"]), height=400)

with col2:
    st.markdown("#### Distribusi Cluster")
    pie_df = cluster_summary[["Kategori","Jumlah_Kabupaten"]]
    fig = px.pie(pie_df, values="Jumlah_Kabupaten", names="Kategori",
                 color="Kategori", color_discrete_map=color_dict,
                 title="Distribusi Cluster")
    fig.update_traces(textinfo="percent+label", pull=[0.03]*len(pie_df))
    st.plotly_chart(fig, use_container_width=True)

# ===========================
# 6️⃣ Peta Klaster
# ===========================
st.subheader(f"🗺️ Peta Ketahanan Pangan Provinsi {selected_provinsi}")
center = filtered_data.geometry.centroid.unary_union.centroid
m = folium.Map(location=[center.y, center.x], zoom_start=7, tiles="CartoDB positron")
folium.GeoJson(filtered_data,
               style_function=lambda feature: {"fillColor": color_dict.get(feature["properties"]["Cluster"], "#cccccc"),
                                               "color":"black","weight":0.8,"fillOpacity":0.75},
               tooltip=folium.GeoJsonTooltip(fields=["NAME_2","Cluster","Kategori_Ketahanan_Pangan"],
                                             aliases=["Daerah","Cluster","Kategori"], localize=True)
              ).add_to(m)
st_folium(m, width=980, height=600)

# ===========================
# 7️⃣ Tabel Data Kabupaten/Kota
# ===========================
with st.expander("📋 Lihat Data Kabupaten/Kota"):
    st.dataframe(filtered_data[["NAME_1","NAME_2","Cluster","Kategori_Ketahanan_Pangan","IKP","Produksi_Beras","PDRB"]],
                 use_container_width=True, height=400)
    