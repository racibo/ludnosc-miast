import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

st.set_page_config(
    page_title="Ludność miast Polski",
    page_icon="🏙️",
    layout="wide"
)

SHEET_ID = "1ODLdLJTUXReay6xfE_UTGO9XoP-iijXwMGa7tqtnm_E"
SHEET_NAME = "Liczby do aktualizacji"
import urllib.parse
_sheet_enc = urllib.parse.quote(SHEET_NAME)
CSV_URLS = [
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={_sheet_enc}",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv",
]

# Współrzędne miast
CITY_COORDS = {
    "Gdańsk": (54.352, 18.646),
    "Gdynia": (54.519, 18.531),
    "Sopot": (54.442, 18.560),
    "Wejherowo": (54.607, 18.235),
    "Reda": (54.614, 18.358),
    "Rumia": (54.572, 18.395),
    "Pruszcz Gdański": (54.259, 18.634),
    "Warszawa": (52.230, 21.012),
    "Kraków": (50.062, 19.940),
    "Łódź": (51.759, 19.457),
    "Wrocław": (51.107, 17.038),
    "Poznań": (52.409, 16.931),
    "Szczecin": (53.428, 14.553),
    "Bydgoszcz": (53.123, 18.009),
    "Katowice": (50.258, 19.028),
    "Lublin": (51.247, 22.569),
    "Białystok": (53.132, 23.163),
    "Częstochowa": (50.811, 19.120),
    "Radom": (51.403, 21.147),
    "Sosnowiec": (50.286, 19.104),
    "Toruń": (53.014, 18.598),
    "Kielce": (50.866, 20.628),
    "Gliwice": (50.294, 18.665),
    "Zabrze": (50.325, 18.786),
    "Bytom": (50.347, 18.919),
    "Rzeszów": (50.041, 21.999),
    "Olsztyn": (53.778, 20.480),
    "Bielsko-Biała": (49.822, 19.044),
    "Ruda Śląska": (50.256, 18.856),
    "Rybnik": (50.097, 18.541),
    "Tychy": (50.133, 18.996),
    "Dąbrowa Górnicza": (50.322, 19.188),
    "Płock": (52.546, 19.706),
    "Elbląg": (54.156, 19.408),
    "Opole": (50.675, 17.921),
    "Chorzów": (50.297, 18.955),
    "Gorzów Wielkopolski": (52.733, 15.228),
    "Kalisz": (51.762, 18.083),
    "Koszalin": (54.194, 16.172),
    "Legnica": (51.207, 16.156),
    "Wałbrzych": (50.784, 16.284),
    "Włocławek": (52.648, 19.065),
    "Zielona Góra": (51.935, 15.506),
    "Tarnów": (50.013, 20.986),
    "Słupsk": (54.464, 17.029),
    "Nowy Sącz": (49.624, 20.693),
    "Jelenia Góra": (50.904, 15.729),
    "Grudziądz": (53.484, 18.754),
    "Konin": (52.223, 18.251),
    "Tczew": (53.778, 18.780),
    "Leszno": (51.840, 16.574),
    "Łomża": (53.178, 22.059),
    "Suwałki": (54.102, 22.930),
    "Siedlce": (52.167, 22.291),
    "Ostrołęka": (53.084, 21.571),
    "Biała Podlaska": (52.032, 23.149),
    "Chełm": (51.143, 23.472),
    "Zamość": (50.723, 23.252),
    "Lwów": (49.840, 24.029),
    "Wilno": (54.687, 25.279),
}

# Miasta-agregaty do pominięcia w widokach
AGGREGATE_CITIES = {
    "Konurbacja Trójmiasta (od Wejherowa do Pruszcza)",
    "Stare Trójmiasto",
    "Małe Trójmiasto",
}

def parse_year(col):
    """Wyciąga rok z nagłówka kolumny (np. '31 XII 2009' -> 2009)."""
    col = str(col).strip()
    # Szukaj 4-cyfrowego roku
    m = re.search(r'\b(1\d{3}|20\d{2})\b', col)
    if m:
        return int(m.group(1))
    # Specjalne przypadki wiekowe
    if "X w" in col or "X w." in col:
        return 975
    if "XI wiek" in col:
        return 1050
    if "XII wiek" in col:
        return 1150
    if "XIV" in col:
        return 1310
    return None

@st.cache_data(ttl=3600)
def load_data():
    df_raw = None
    last_err = None
    for url in CSV_URLS:
        try:
            df_raw = pd.read_csv(url, header=0)
            break
        except Exception as e:
            last_err = e
            continue
    if df_raw is None:
        raise Exception(f"Nie udalo sie pobrac danych. Ostatni blad: {last_err}")

    # Pierwsza kolumna to nazwy miast
    city_col = df_raw.columns[0]
    df_raw = df_raw.rename(columns={city_col: "Miasto"})

    # Usuń wiersze z pustą nazwą miasta lub będące przypisami (źródła)
    df_raw = df_raw[df_raw["Miasto"].notna()].copy()
    df_raw = df_raw[df_raw["Miasto"].str.strip() != ""].copy()

    # Mapuj nagłówki kolumn na lata
    year_map = {}
    for col in df_raw.columns[1:]:
        yr = parse_year(col)
        if yr is not None:
            year_map[col] = yr

    # Zostaw tylko kolumny z latami
    keep_cols = ["Miasto"] + list(year_map.keys())
    df_raw = df_raw[keep_cols].copy()
    df_raw = df_raw.rename(columns=year_map)

    # Deduplikacja kolumn (ten sam rok może wystąpić kilka razy — bierz pierwszą)
    df_raw = df_raw.loc[:, ~df_raw.columns.duplicated(keep='first')]

    # Konwersja wartości na liczby
    for col in df_raw.columns[1:]:
        df_raw[col] = (
            df_raw[col]
            .astype(str)
            .str.replace(r'\s+', '', regex=True)
            .str.replace(',', '.')
            .replace('nan', pd.NA)
            .replace('', pd.NA)
        )
        df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')

    # Melt do formatu długiego
    df_long = df_raw.melt(id_vars="Miasto", var_name="Rok", value_name="Ludność")
    df_long = df_long.dropna(subset=["Ludność"])
    df_long["Rok"] = df_long["Rok"].astype(int)
    df_long["Ludność"] = df_long["Ludność"].astype(int)

    # Usuń agregaty
    df_long = df_long[~df_long["Miasto"].isin(AGGREGATE_CITIES)]

    # Usuń wiersze będące przypisami (zawierają "Korzystałem" itp.)
    df_long = df_long[~df_long["Miasto"].str.contains("Korzysta|przewodnik|Wolfram|Obraniak|GUS|Wikipedia|Marian|Ludno", na=False, case=False)]

    return df_long

# === UI ===

st.title("🏙️ Ludność miast Polski na przestrzeni wieków")
st.caption("Dane: arkusz zbiorczy. Odświeżanie co 1 godz.")

with st.spinner("Ładowanie danych..."):
    try:
        df = load_data()
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        st.stop()

all_cities = sorted(df["Miasto"].unique())
all_years = sorted(df["Rok"].unique())

# Filtruj do "normalnych" lat historycznych dla suwaków (od 1800)
modern_years = [y for y in all_years if y >= 1800]

tab1, tab2, tab3 = st.tabs(["📈 Wykres liniowy", "🗺️ Mapa bąbelkowa", "🏆 Ranking"])

# ── TAB 1: Wykres liniowy ──────────────────────────────────────────────────
with tab1:
    st.subheader("Porównanie miast w czasie")

    col1, col2 = st.columns([3, 1])
    with col1:
        default_cities = ["Gdańsk", "Warszawa", "Kraków", "Łódź", "Wrocław"]
        default_cities = [c for c in default_cities if c in all_cities]
        selected_cities = st.multiselect(
            "Wybierz miasta:",
            options=all_cities,
            default=default_cities,
            key="line_cities"
        )
    with col2:
        year_range = st.slider(
            "Zakres lat:",
            min_value=min(all_years),
            max_value=max(all_years),
            value=(1800, max(all_years)),
            key="line_years"
        )

    if selected_cities:
        mask = (
            df["Miasto"].isin(selected_cities) &
            df["Rok"].between(year_range[0], year_range[1])
        )
        df_plot = df[mask].sort_values("Rok")

        fig = px.line(
            df_plot,
            x="Rok",
            y="Ludność",
            color="Miasto",
            markers=True,
            title=f"Liczba mieszkańców ({year_range[0]}–{year_range[1]})",
            labels={"Ludność": "Liczba mieszkańców", "Rok": "Rok"},
        )
        fig.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=500,
        )
        fig.update_traces(
            hovertemplate="%{fullData.name}: <b>%{y:,}</b><extra></extra>"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Wybierz co najmniej jedno miasto.")

# ── TAB 2: Mapa bąbelkowa ─────────────────────────────────────────────────
with tab2:
    st.subheader("Mapa bąbelkowa")

    # Tylko miasta z lat >= 1800 i ze współrzędnymi
    mappable = df[df["Rok"] >= 1800]
    mappable = mappable[mappable["Miasto"].isin(CITY_COORDS)]

    available_map_years = sorted(mappable["Rok"].unique())

    if not available_map_years:
        st.warning("Brak danych mapowych.")
    else:
        selected_year = st.select_slider(
            "Wybierz rok:",
            options=available_map_years,
            value=available_map_years[-1],
            key="map_year"
        )

        df_map = mappable[mappable["Rok"] == selected_year].copy()
        df_map["lat"] = df_map["Miasto"].map(lambda c: CITY_COORDS[c][0])
        df_map["lon"] = df_map["Miasto"].map(lambda c: CITY_COORDS[c][1])
        df_map = df_map.dropna(subset=["lat", "lon"])

        fig_map = px.scatter_map(
            df_map,
            lat="lat",
            lon="lon",
            size="Ludność",
            color="Ludność",
            hover_name="Miasto",
            hover_data={"Ludność": ":,", "lat": False, "lon": False},
            color_continuous_scale="Viridis",
            size_max=60,
            zoom=5.5,
            center={"lat": 52.0, "lon": 19.5},
            title=f"Ludność miast — rok {selected_year}",
            map_style="carto-positron",
        )
        fig_map.update_layout(height=580, coloraxis_showscale=True)
        st.plotly_chart(fig_map, use_container_width=True)

        st.caption(f"Pokazanych miast: {len(df_map)} (tylko te ze zdefiniowanymi współrzędnymi i danymi dla roku {selected_year})")

# ── TAB 3: Ranking ────────────────────────────────────────────────────────
with tab3:
    st.subheader("Ranking miast")

    col1, col2 = st.columns([2, 2])
    with col1:
        rank_year = st.selectbox(
            "Rok:",
            options=sorted(all_years, reverse=True),
            index=0,
            key="rank_year"
        )
    with col2:
        top_n = st.slider("Liczba miast:", min_value=5, max_value=50, value=20, key="rank_n")

    df_rank = (
        df[df["Rok"] == rank_year]
        .sort_values("Ludność", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    df_rank.index += 1

    if df_rank.empty:
        st.info("Brak danych dla wybranego roku.")
    else:
        fig_bar = px.bar(
            df_rank,
            x="Ludność",
            y="Miasto",
            orientation="h",
            title=f"Top {top_n} miast — rok {rank_year}",
            color="Ludność",
            color_continuous_scale="Blues",
            text="Ludność",
        )
        fig_bar.update_traces(
            texttemplate="%{text:,}",
            textposition="outside",
        )
        fig_bar.update_layout(
            yaxis=dict(autorange="reversed"),
            showlegend=False,
            coloraxis_showscale=False,
            height=max(400, top_n * 28),
            xaxis_title="Liczba mieszkańców",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        with st.expander("📋 Dane tabelaryczne"):
            df_display = df_rank[["Miasto", "Ludność"]].copy()
            df_display["Ludność"] = df_display["Ludność"].map("{:,}".format)
            st.dataframe(df_display, use_container_width=True)
