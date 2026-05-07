import streamlit as st
import pandas as pd
import plotly.express as px
import re
import urllib.parse

st.set_page_config(page_title="Ludność miast Polski", page_icon="🏙️", layout="wide")

SHEET_ID = "1ODLdLJTUXReay6xfE_UTGO9XoP-iijXwMGa7tqtnm_E"
SHEET_NAME = "Liczby do aktualizacji"
_enc = urllib.parse.quote(SHEET_NAME)
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={_enc}"

CITY_COORDS = {
    "Gdańsk": (54.352, 18.646), "Gdynia": (54.519, 18.531), "Sopot": (54.442, 18.560),
    "Wejherowo": (54.607, 18.235), "Reda": (54.614, 18.358), "Rumia": (54.572, 18.395),
    "Pruszcz Gdański": (54.259, 18.634), "Warszawa": (52.230, 21.012),
    "Kraków": (50.062, 19.940), "Łódź": (51.759, 19.457), "Wrocław": (51.107, 17.038),
    "Poznań": (52.409, 16.931), "Szczecin": (53.428, 14.553), "Bydgoszcz": (53.123, 18.009),
    "Katowice": (50.258, 19.028), "Lublin": (51.247, 22.569), "Białystok": (53.132, 23.163),
    "Częstochowa": (50.811, 19.120), "Radom": (51.403, 21.147), "Sosnowiec": (50.286, 19.104),
    "Toruń": (53.014, 18.598), "Kielce": (50.866, 20.628), "Gliwice": (50.294, 18.665),
    "Zabrze": (50.325, 18.786), "Bytom": (50.347, 18.919), "Rzeszów": (50.041, 21.999),
    "Olsztyn": (53.778, 20.480), "Bielsko-Biała": (49.822, 19.044),
    "Ruda Śląska": (50.256, 18.856), "Rybnik": (50.097, 18.541), "Tychy": (50.133, 18.996),
    "Dąbrowa Górnicza": (50.322, 19.188), "Płock": (52.546, 19.706),
    "Elbląg": (54.156, 19.408), "Opole": (50.675, 17.921), "Chorzów": (50.297, 18.955),
    "Gorzów Wielkopolski": (52.733, 15.228), "Kalisz": (51.762, 18.083),
    "Koszalin": (54.194, 16.172), "Legnica": (51.207, 16.156), "Wałbrzych": (50.784, 16.284),
    "Włocławek": (52.648, 19.065), "Zielona Góra": (51.935, 15.506),
    "Tarnów": (50.013, 20.986), "Słupsk": (54.464, 17.029), "Nowy Sącz": (49.624, 20.693),
    "Jelenia Góra": (50.904, 15.729), "Grudziądz": (53.484, 18.754),
    "Konin": (52.223, 18.251), "Tczew": (53.778, 18.780), "Leszno": (51.840, 16.574),
    "Łomża": (53.178, 22.059), "Suwałki": (54.102, 22.930), "Siedlce": (52.167, 22.291),
    "Ostrołęka": (53.084, 21.571), "Biała Podlaska": (52.032, 23.149),
    "Chełm": (51.143, 23.472), "Zamość": (50.723, 23.252),
    "Lwów": (49.840, 24.029), "Wilno": (54.687, 25.279),
    "Jastrzębie Zdrój": (49.955, 18.582), "Jaworzno": (50.205, 19.274),
    "Mysłowice": (50.243, 19.138), "Siemianowice Śląskie": (50.327, 19.015),
    "Piekary Śląskie": (50.388, 18.954), "Świętochłowice": (50.295, 18.917),
    "Żory": (50.046, 18.698), "Piotrków Trybunalski": (51.405, 19.703),
    "Nowy Targ": (49.477, 20.033), "Skierniewice": (51.955, 20.158),
    "Pruszków": (52.169, 20.798), "Legionowo": (52.406, 20.929),
    "Otwock": (52.108, 21.263), "Piaseczno": (52.082, 21.022),
    "Żyrardów": (52.049, 20.447), "Mińsk Mazowiecki": (52.181, 21.564),
    "Wołomin": (52.345, 21.238),
}

AGGREGATE_CITIES = {
    "Konurbacja Trójmiasta (od Wejherowa do Pruszcza)",
    "Stare Trójmiasto", "Małe Trójmiasto",
}

PRZYPIS_FRAGMENTS = [
    "Korzystałem", "Ilustrowany przewodnik", "jego dzieje", "Wolfram Alfa",
    "Włodzimierz Obraniak", "LUDNOŚĆ ŁODZI", "Sopot i okolice",
    "Franciszek Mamuszka", "Małkowski", "Świat w liczbach",
    "Wikipedia Warszawa", "Marian Kukiel", "Rozwój miast w Polsce",
    "Ludność i powierzchnia", "ministerstwa rozwoju",
]

def parse_year(text):
    """
    Wyciąga rok z tekstu. Zwraca int lub None.
    Zoptymalizowane pod łapanie 'ok. 1600' oraz stuleci (np. 'II poł X w.', 'XI wiek').
    """
    t = str(text).strip().lower()
    
    # Szukaj 4-cyfrowego roku, ewentualnie z prefixem "ok."
    m = re.search(r'(?:ok\.?\s*)?([12]\d{3})', t)
    if m:
        return int(m.group(1))
    
    # Mapowanie rzymskich na stulecia
    romans = {
        'xviii': 18, 'xvii': 17, 'xvi': 16, 'xv': 15, 'xiv': 14,
        'xiii': 13, 'xii': 12, 'xi': 11, 'x': 10, 'ix': 9
    }
    
    for rom, cent in romans.items():
        # Szukamy liczby rzymskiej jako oddzielnego słowa, a po niej opcjonalnie 'w' lub 'wiek'
        if re.search(rf'\b{rom}\b\s*(w\.|w\b|wiek)', t):
            base = (cent - 1) * 100 + 50  # Domyślnie środek wieku
            
            # Przesunięcia czasowe
            if 'ii poł' in t or '2 poł' in t: return base + 25
            if 'pocz' in t or 'i poł' in t or '1 poł' in t: return base - 25
            if 'koniec' in t: return base + 40
            
            return base
            
    return None

def is_przypis(name):
    name = str(name)
    return any(f in name for f in PRZYPIS_FRAGMENTS)

@st.cache_data(ttl=3600)
def load_data():
    # Czytamy RAW bez żadnego parsowania przez pandas
    df = pd.read_csv(CSV_URL, header=None, dtype=str)

    # Wiersz 0: kolumna 0 = "Data", kolumny 1..N = daty tekstowe
    date_row = df.iloc[0].tolist()

    # Zbuduj słownik: indeks_kolumny -> rok
    col_to_year = {}
    seen_years = set()
    for i, val in enumerate(date_row):
        if i == 0:
            continue
        yr = parse_year(val)
        if yr is not None and yr not in seen_years:
            col_to_year[i] = yr
            seen_years.add(yr)

    # Dane miast: wiersze 1..koniec
    records = []
    for row_idx in range(1, len(df)):
        row = df.iloc[row_idx].tolist()
        city = str(row[0]).strip()

        if not city or city == 'nan': continue
        if city in AGGREGATE_CITIES: continue
        if is_przypis(city): continue

        for col_idx, year in col_to_year.items():
            if col_idx >= len(row):
                continue
            raw = str(row[col_idx]).strip()
            if raw in ('', 'nan'):
                continue
            # Usuń spacje w liczbach (np. "1 100" -> "1100")
            raw = re.sub(r'\s+', '', raw).replace(',', '.')
            try:
                val = int(float(raw))
                records.append({"Miasto": city, "Rok": year, "Ludność": val})
            except ValueError:
                pass

    df_long = pd.DataFrame(records)
    if df_long.empty:
        return df_long, date_row

    df_long = df_long.drop_duplicates(subset=["Miasto", "Rok"], keep="first")
    df_long = df_long.sort_values(["Miasto", "Rok"])
    
    # Obliczamy stały rozmiar punktów dla mapy bazujący na globalnym maksimum populacji.
    # Używamy pierwiastka, by ogromne miasta nie zasłaniały całkowicie mniejszych.
    max_pop = df_long["Ludność"].max()
    df_long["Rozmiar_mapa"] = (df_long["Ludność"] / max_pop) ** 0.5 * 50
    df_long["Rozmiar_mapa"] = df_long["Rozmiar_mapa"].clip(lower=4) # minimum 4px dla widoczności

    return df_long, date_row

# ── UI ────────────────────────────────────────────────────────────────────
st.title("🏙️ Ludność miast Polski na przestrzeni wieków")

with st.spinner("Ładowanie danych..."):
    try:
        df, _date_row = load_data()
    except Exception as e:
        st.error(f"Błąd ładowania: {e}")
        st.stop()

if df.empty:
    st.error("Nie udało się wczytać żadnych danych. Sprawdź czy arkusz jest publiczny.")
    st.stop()

all_cities = sorted(df["Miasto"].unique())
all_years  = sorted(df["Rok"].unique())

tab1, tab2, tab3 = st.tabs(["📈 Wykres liniowy", "🗺️ Mapa bąbelkowa", "🏆 Ranking"])

# ── TAB 1: WYKRES LINIOWY ──────────────────────────────────────────────────
with tab1:
    st.subheader("Porównanie miast w czasie")
    c1, c2 = st.columns([3, 1])
    with c1:
        default = [c for c in ["Gdańsk","Warszawa","Kraków","Łódź","Wrocław"] if c in all_cities]
        selected = st.multiselect("Wybierz miasta:", all_cities, default=default)
    with c2:
        yr_range = st.slider("Zakres lat:", int(min(all_years)), int(max(all_years)),
                             value=(1800, int(max(all_years))))
    if selected:
        sub = df[df["Miasto"].isin(selected) & df["Rok"].between(*yr_range)].sort_values("Rok")
        fig = px.line(sub, x="Rok", y="Ludność", color="Miasto", markers=True,
                      labels={"Ludność": "Liczba mieszkańców"})
        
        # Wymuszenie fizycznej proporcjonalności osi X (widoczne luki czasowe do interpolacji)
        fig.update_xaxes(type='linear', title="Rok")
        
        fig.update_layout(hovermode="x unified", height=550,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig.update_traces(hovertemplate="%{fullData.name}: <b>%{y:,}</b><extra></extra>")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Wybierz co najmniej jedno miasto.")

# ── TAB 2: MAPA BĄBELKOWA ──────────────────────────────────────────────────
with tab2:
    st.subheader("Mapa bąbelkowa")
    mappable = df[df["Rok"] >= 1400] # Zaczynamy od 1400 by ominąć puste wieki w animacji
    mappable = mappable[mappable["Miasto"].isin(CITY_COORDS)]
    map_years = sorted(mappable["Rok"].unique())

    if not map_years:
        st.warning("Brak danych mapowych.")
    else:
        sel_year = st.select_slider("Wybierz rok na mapie:", options=map_years, value=map_years[-1])
        dm = mappable[mappable["Rok"] == sel_year].copy()
        dm["lat"] = dm["Miasto"].map(lambda c: CITY_COORDS[c][0])
        dm["lon"] = dm["Miasto"].map(lambda c: CITY_COORDS[c][1])
        
        # Tworzymy mapę, ale pomijamy parametr size=... bo on normalizuje kółka do aktualnej klatki
        fig_m = px.scatter_map(dm, lat="lat", lon="lon", color="Ludność",
                               hover_name="Miasto",
                               hover_data={"Ludność":":,","lat":False,"lon":False},
                               color_continuous_scale="Viridis",
                               zoom=5.5, center={"lat":52.0,"lon":19.5},
                               map_style="carto-positron")
        
        # Narzucamy nasz globalnie wyliczony, absolutny rozmiar (nie będzie skakać między latami)
        fig_m.update_traces(marker=dict(size=dm["Rozmiar_mapa"]))
        fig_m.update_layout(height=600)
        st.plotly_chart(fig_m, use_container_width=True)
        st.caption(f"Miast widocznych na mapie w {sel_year} roku: **{len(dm)}**")

# ── TAB 3: RANKING ────────────────────────────────────────────────────────
with tab3:
    st.subheader("Ranking miast z systemem uzupełniania danych")
    
    col_r1, col_r2, col_r3 = st.columns([2, 2, 3])
    with col_r1:
        rank_year = st.selectbox("Rok bazowy:", sorted(all_years, reverse=True))
    with col_r2:
        top_n = st.slider("Liczba miast:", 5, 60, 20)
    with col_r3:
        tolerance = st.slider("Tolerancja braku danych (lata):", 0, 50, 15,
            help="Jeśli miasto nie ma danych w wybranym roku, system poszuka najbliższych danych z tolerancją +/- tylu lat.")

    # Szukanie najbliższych punktów danych dla każdego miasta
    df_rank = df.copy()
    df_rank["Roznica"] = (df_rank["Rok"] - rank_year).abs()
    # Odrzucamy dane wykraczające poza tolerancję
    df_rank = df_rank[df_rank["Roznica"] <= tolerance]
    
    # Sortujemy najpierw po mieście, potem po najmniejszej różnicy i bierzemy pierwszy rekord
    df_rank = df_rank.sort_values(["Miasto", "Roznica"])
    closest_records = df_rank.drop_duplicates(subset=["Miasto"], keep="first").copy()

    def create_label(row):
        """Tworzy etykietę z rokiem, jeśli dane są z innego roku niż wybrany."""
        if row["Rok"] == rank_year:
            return row["Miasto"]
        return f"{row['Miasto']} (z {row['Rok']} r.)"

    if closest_records.empty:
        st.info("Brak danych dla wybranego roku i podanej tolerancji.")
    else:
        closest_records["Miasto_Etykieta"] = closest_records.apply(create_label, axis=1)
        
        dr = closest_records.sort_values("Ludność", ascending=False).head(top_n).reset_index(drop=True)
        dr.index += 1

        fig_b = px.bar(dr, x="Ludność", y="Miasto_Etykieta", orientation="h",
                       color="Ludność", color_continuous_scale="Blues", text="Ludność")
        fig_b.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_b.update_layout(yaxis=dict(autorange="reversed", title="Miasto"), coloraxis_showscale=False,
                            height=max(400, top_n * 28))
        st.plotly_chart(fig_b, use_container_width=True)
        
        with st.expander("📋 Tabela szczegółowa"):
            disp = dr[["Miasto_Etykieta", "Ludność", "Rok"]].copy()
            disp["Ludność"] = disp["Ludność"].map("{:,}".format)
            disp.columns = ["Miasto", "Liczba mieszkańców", "Rok pochodzenia danych"]
            st.dataframe(disp, use_container_width=True)