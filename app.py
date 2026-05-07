import streamlit as st
import pandas as pd
import plotly.express as px
import re
import urllib.parse

st.set_page_config(
    page_title="Ludność miast Polski",
    page_icon="🏙️",
    layout="wide"
)

SHEET_ID = "1ODLdLJTUXReay6xfE_UTGO9XoP-iijXwMGa7tqtnm_E"
SHEET_NAME = "Liczby do aktualizacji"
_sheet_enc = urllib.parse.quote(SHEET_NAME)
CSV_URLS = [
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={_sheet_enc}",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv",
]

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
    "Wejherowo": (54.607, 18.235),
    "Pruszków": (52.169, 20.798),
    "Legionowo": (52.406, 20.929),
    "Otwock": (52.108, 21.263),
    "Piaseczno": (52.082, 21.022),
    "Żyrardów": (52.049, 20.447),
    "Mińsk Mazowiecki": (52.181, 21.564),
    "Wołomin": (52.345, 21.238),
    "Ząbki": (52.294, 21.118),
    "Tczew": (53.778, 18.780),
    "Pruszcz Gdański": (54.259, 18.634),
    "Jastrzębie Zdrój": (49.955, 18.582),
    "Jaworzno": (50.205, 19.274),
    "Mysłowice": (50.243, 19.138),
    "Siemianowice Śląskie": (50.327, 19.015),
    "Piekary Śląskie": (50.388, 18.954),
    "Świętochłowice": (50.295, 18.917),
    "Żory": (50.046, 18.698),
    "Piotrków Trybunalski": (51.405, 19.703),
    "Nowy Targ": (49.477, 20.033),
    "Skierniewice": (51.955, 20.158),
    "Płock": (52.546, 19.706),
    "Włocławek": (52.648, 19.065),
}

AGGREGATE_CITIES = {
    "Konurbacja Trójmiasta (od Wejherowa do Pruszcza)",
    "Stare Trójmiasto",
    "Małe Trójmiasto",
}

# Wiersze-przypisy — rozpoznajemy po tym że zawierają długi tekst opisowy
# (nazwy miast są krótkie, przypisy mają spacje i słowa kluczowe)
PRZYPIS_KEYWORDS = (
    "Korzysta", "Ilustrowany przewodnik", "jego dzieje", "Wolfram Alfa",
    "Włodzimierz Obraniak", "LUDNOŚĆ ŁODZI", "Sopot i okolice",
    "Franciszek Mamuszka", "Małkowski", "Świat w liczbach",
    "Wikipedia Warszawa", "Marian Kukiel", "Rozwój miast w Polsce",
    "Ludność i powierzchnia", "ministerstwa rozwoju",
)

def parse_year(col):
    col = str(col).strip()
    m = re.search(r'\b(1\d{3}|20\d{2})\b', col)
    if m:
        return int(m.group(1))
    col_lower = col.lower()
    century_map = [
        ('xviii w', 1750), ('xvii w', 1650), ('xvi w', 1550),
        ('xv w',  1450),  ('xiv w',  1325), ('xiii w', 1250),
        ('xii w', 1150),  ('xi w',   1050), ('x w',    975),
    ]
    for pattern, base_year in century_map:
        if pattern in col_lower:
            if 'ii poł' in col_lower or 'ii pol' in col_lower:
                return base_year + 25
            if 'i poł' in col_lower or 'pocz' in col_lower:
                return base_year - 25
            return base_year
    return None

@st.cache_data(ttl=3600)
def load_raw():
    """Zwraca surowy DataFrame z Google Sheets."""
    last_err = None
    for url in CSV_URLS:
        try:
            df = pd.read_csv(url, header=0)
            return df, url
        except Exception as e:
            last_err = e
    raise Exception(f"Nie udało się pobrać danych: {last_err}")

@st.cache_data(ttl=3600)
def load_data():
    df_raw, _ = load_raw()

    # Struktura arkusza:
    #   wiersz 0 (header): "Data", "Unnamed:1", "Unnamed:2", ...  <- nagłówki pandas (bezużyteczne)
    #   wiersz 0 danych  : "Gdańsk", daty tekstowe ("II poł X w.", "1427", ...)
    #   wiersz 1+ danych : kolejne miasta + liczby
    #
    # Dlatego: wiersz 0 danych = wiersz nagłówków dat, reszta = miasta+liczby

    # Wyciągnij wiersz z datami (pierwszy wiersz danych)
    date_row = df_raw.iloc[0]  # "Gdańsk", "II poł X w.", "XI wiek", ...
    # Właściwe dane miast zaczynają się od wiersza 1
    df_cities = df_raw.iloc[1:].copy()
    df_cities.columns = df_raw.columns  # zachowaj oryginalne kolumny pandas

    # Zbuduj mapę: kolumna_pandas -> rok (int)
    year_map = {}
    skipped = []
    for col in df_raw.columns:
        val = str(date_row[col]).strip()
        yr = parse_year(val)
        if yr is not None:
            if yr not in year_map.values():
                year_map[col] = yr
        else:
            if col != df_raw.columns[0]:  # kolumna miast pomijamy celowo
                skipped.append(val)

    # Kolumna miast = pierwsza kolumna
    city_col = df_raw.columns[0]
    df_cities = df_cities.rename(columns={city_col: "Miasto"})
    df_cities = df_cities.rename(columns=year_map)

    # Zostaw tylko kolumny które mamy w year_map + Miasto
    keep = ["Miasto"] + [year_map[c] for c in year_map]
    # year_map wartości mogą się powtarzać jeśli dwie kolumny dały ten sam rok
    # bezpieczniej przez oryginalne klucze:
    keep_orig = ["Miasto"] + list(year_map.keys())
    df_cities = df_cities[[c for c in keep_orig if c in df_cities.columns]].copy()
    # Rename po raz drugi (year_map klucze -> wartości)
    df_cities = df_cities.rename(columns=year_map)
    # Deduplikacja kolumn (ten sam rok z dwóch kolumn)
    df_cities = df_cities.loc[:, ~df_cities.columns.duplicated(keep="first")]

    # Usuń puste wiersze i przypisy
    df_cities = df_cities[df_cities["Miasto"].notna()].copy()
    df_cities = df_cities[df_cities["Miasto"].astype(str).str.strip() != ""].copy()
    mask_przypis = df_cities["Miasto"].astype(str).str.contains(
        "|".join(re.escape(k) for k in PRZYPIS_KEYWORDS), na=False, case=False
    )
    df_cities = df_cities[~mask_przypis].copy()
    df_cities = df_cities[~df_cities["Miasto"].isin(AGGREGATE_CITIES)].copy()

    # Konwersja wartości liczbowych
    for col in df_cities.columns[1:]:
        df_cities[col] = (
            df_cities[col]
            .astype(str)
            .str.replace(r'\s+', '', regex=True)
            .str.replace(',', '.')
            .replace('nan', pd.NA)
            .replace('', pd.NA)
        )
        df_cities[col] = pd.to_numeric(df_cities[col], errors='coerce')

    # Melt do formatu długiego
    df_long = df_cities.melt(id_vars="Miasto", var_name="Rok", value_name="Ludność")
    df_long = df_long.dropna(subset=["Ludność"])
    df_long["Rok"] = pd.to_numeric(df_long["Rok"], errors="coerce")
    df_long = df_long.dropna(subset=["Rok"])
    df_long["Rok"] = df_long["Rok"].astype(int)
    df_long["Ludność"] = df_long["Ludność"].astype(int)
    df_long = df_long.drop_duplicates(subset=["Miasto", "Rok"], keep="first")

    return df_long, skipped

# === UI ===
st.title("🏙️ Ludność miast Polski na przestrzeni wieków")

with st.spinner("Ładowanie danych..."):
    try:
        df_raw_debug, used_url = load_raw()
        df, skipped_cols = load_data()
    except Exception as e:
        st.error(f"Błąd: {e}")
        st.stop()

# ── DEBUG (można usunąć po weryfikacji) ───────────────────────────────────
with st.expander("🔧 DEBUG — kliknij żeby sprawdzić co zostało wczytane"):
    st.write(f"**URL użyty do pobrania:** `{used_url}`")
    st.write(f"**Liczba kolumn w surowym arkuszu:** {len(df_raw_debug.columns)}")
    st.write(f"**Liczba wierszy surowych:** {len(df_raw_debug)}")
    st.write("**Pierwsze 10 nagłówków kolumn:**")
    st.write(list(df_raw_debug.columns[:10]))
    st.write("**Ostatnie 10 nagłówków kolumn:**")
    st.write(list(df_raw_debug.columns[-10:]))
    st.write(f"**Nagłówki które NIE zostały rozpoznane jako lata ({len(skipped_cols)}):**")
    st.write(skipped_cols[:30])
    st.write(f"**Liczba miast po filtrowaniu:** {df['Miasto'].nunique()}")
    st.write(f"**Zakres lat:** {df['Rok'].min()} – {df['Rok'].max()}")
    st.write(f"**Lista miast:**")
    st.write(sorted(df['Miasto'].unique()))
# ── koniec DEBUG ──────────────────────────────────────────────────────────

all_cities = sorted(df["Miasto"].unique())
all_years  = sorted(df["Rok"].unique())

tab1, tab2, tab3 = st.tabs(["📈 Wykres liniowy", "🗺️ Mapa bąbelkowa", "🏆 Ranking"])

# ── TAB 1 ─────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Porównanie miast w czasie")
    col1, col2 = st.columns([3, 1])
    with col1:
        default_cities = [c for c in ["Gdańsk","Warszawa","Kraków","Łódź","Wrocław"] if c in all_cities]
        selected_cities = st.multiselect("Wybierz miasta:", options=all_cities, default=default_cities)
    with col2:
        year_range = st.slider("Zakres lat:", min_value=min(all_years), max_value=max(all_years),
                               value=(1800, max(all_years)))

    if selected_cities:
        mask = df["Miasto"].isin(selected_cities) & df["Rok"].between(*year_range)
        fig = px.line(df[mask].sort_values("Rok"), x="Rok", y="Ludność", color="Miasto",
                      markers=True, labels={"Ludność":"Liczba mieszkańców"})
        fig.update_layout(hovermode="x unified", height=500,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig.update_traces(hovertemplate="%{fullData.name}: <b>%{y:,}</b><extra></extra>")
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Wybierz co najmniej jedno miasto.")

# ── TAB 2 ─────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Mapa bąbelkowa")
    mappable = df[df["Rok"] >= 1800]
    mappable = mappable[mappable["Miasto"].isin(CITY_COORDS)]
    available_map_years = sorted(mappable["Rok"].unique())

    if not available_map_years:
        st.warning("Brak danych mapowych.")
    else:
        selected_year = st.select_slider("Wybierz rok:", options=available_map_years,
                                         value=available_map_years[-1])
        df_map = mappable[mappable["Rok"] == selected_year].copy()
        df_map["lat"] = df_map["Miasto"].map(lambda c: CITY_COORDS[c][0])
        df_map["lon"] = df_map["Miasto"].map(lambda c: CITY_COORDS[c][1])
        fig_map = px.scatter_map(df_map, lat="lat", lon="lon", size="Ludność", color="Ludność",
                                 hover_name="Miasto",
                                 hover_data={"Ludność":":,","lat":False,"lon":False},
                                 color_continuous_scale="Viridis", size_max=60,
                                 zoom=5.5, center={"lat":52.0,"lon":19.5},
                                 map_style="carto-positron")
        fig_map.update_layout(height=580)
        st.plotly_chart(fig_map, width="stretch")
        st.caption(f"Miast na mapie: {len(df_map)}")

# ── TAB 3 ─────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Ranking miast")
    col1, col2 = st.columns([2,2])
    with col1:
        rank_year = st.selectbox("Rok:", options=sorted(all_years, reverse=True))
    with col2:
        top_n = st.slider("Liczba miast:", 5, 60, 20)

    df_rank = (df[df["Rok"] == rank_year]
               .sort_values("Ludność", ascending=False)
               .head(top_n).reset_index(drop=True))
    df_rank.index += 1

    if df_rank.empty:
        st.info("Brak danych dla wybranego roku.")
    else:
        fig_bar = px.bar(df_rank, x="Ludność", y="Miasto", orientation="h",
                         color="Ludność", color_continuous_scale="Blues", text="Ludność")
        fig_bar.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_bar.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False,
                              height=max(400, top_n*28))
        st.plotly_chart(fig_bar, width="stretch")
        with st.expander("📋 Tabela"):
            df_disp = df_rank[["Miasto","Ludność"]].copy()
            df_disp["Ludność"] = df_disp["Ludność"].map("{:,}".format)
            st.dataframe(df_disp, width="stretch")
