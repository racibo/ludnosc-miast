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

tab1, tab2, tab3 = st.tabs(["📈 Wykres liniowy", "📊 Zmiana rankingu", "🏆 Ranking (Słupkowy)"])

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
        
        # Sortowanie miast, aby dymek (hover) i legenda były uporządkowane od największej populacji do najmniejszej
        # Plotly użyje tej kolejności globalnie dla danego wykresu
        city_max_pop = sub.groupby("Miasto")["Ludność"].max().sort_values(ascending=False)
        ordered_cities = city_max_pop.index.tolist()

        fig = px.line(sub, x="Rok", y="Ludność", color="Miasto", markers=True,
                      category_orders={"Miasto": ordered_cities},
                      labels={"Ludność": "Liczba mieszkańców"})
        
        # Wymuszenie fizycznej proporcjonalności osi X (widoczne luki czasowe do interpolacji)
        fig.update_xaxes(type='linear', title="Rok")
        
        fig.update_layout(hovermode="x unified", height=550,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig.update_traces(hovertemplate="%{fullData.name}: <b>%{y:,}</b><extra></extra>")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Wybierz co najmniej jedno miasto.")

# ── TAB 2: ZMIANA RANKINGU ──────────────────────────────────────────────────
with tab2:
    st.subheader("Zmiana pozycji w rankingu na przestrzeni lat")
    
    c2_1, c2_2, c2_3 = st.columns([2, 1, 1])
    with c2_1:
        default_rank = [c for c in ["Gdańsk","Warszawa","Kraków","Łódź","Wrocław", "Poznań"] if c in all_cities]
        selected_rank = st.multiselect("Wybierz miasta do śledzenia rankingu:", all_cities, default=default_rank, key="rank_cities")
    with c2_2:
        yr_range_rank = st.slider("Zakres lat (ranking):", int(min(all_years)), int(max(all_years)),
                             value=(1800, int(max(all_years))), key="rank_years")
    with c2_3:
        tolerance_rank = st.slider("Tolerancja (lata):", 0, 50, 15, key="rank_tol",
            help="Jeśli miasto nie ma danych w badanym roku, system uwzględni najbliższy punkt z zachowaniem tej tolerancji.")

    if selected_rank:
        with st.spinner("Obliczanie historycznych rankingów..."):
            # Filtrujemy tylko te lata, które mieszczą się w wybranym przedziale (do osi X)
            years_in_range = [y for y in all_years if yr_range_rank[0] <= y <= yr_range_rank[1]]
            
            rank_records = []
            for y in years_in_range:
                # Szukanie najbliższych danych dla WSZYSTKICH miast (by poprawnie wyliczyć ranking)
                diffs = (df["Rok"] - y).abs()
                mask = diffs <= tolerance_rank
                temp = df[mask].copy()
                
                if not temp.empty:
                    temp["Diff"] = diffs[mask]
                    temp = temp.sort_values(["Miasto", "Diff"])
                    closest = temp.drop_duplicates(subset=["Miasto"], keep="first").copy()
                    
                    # Obliczanie pozycji (metoda 'min' - np. dwa ex aequo 1 miejsca)
                    closest["Pozycja"] = closest["Ludność"].rank(ascending=False, method="min")
                    closest["Rok_Wykresu"] = y
                    rank_records.append(closest)
            
            if rank_records:
                df_all_ranks = pd.concat(rank_records)
                
                # Filtrujemy tylko wybrane miasta, aby je narysować
                df_plot_ranks = df_all_ranks[df_all_ranks["Miasto"].isin(selected_rank)].sort_values("Rok_Wykresu")
                
                if df_plot_ranks.empty:
                    st.warning("Brak danych spełniających kryteria tolerancji dla wybranych miast w tym okresie.")
                else:
                    # Sortowanie legendy od najwyższego rankingu (najniższej wartości)
                    city_best_rank = df_plot_ranks.groupby("Miasto")["Pozycja"].min().sort_values()
                    ordered_rank_cities = city_best_rank.index.tolist()

                    fig_r = px.line(df_plot_ranks, x="Rok_Wykresu", y="Pozycja", color="Miasto", markers=True,
                                    category_orders={"Miasto": ordered_rank_cities},
                                    labels={"Pozycja": "Miejsce w rankingu", "Rok_Wykresu": "Rok"})
                    
                    fig_r.update_xaxes(type='linear', title="Rok")
                    # autorange="reversed" upewnia się, że miejsce 1. jest na górze
                    fig_r.update_layout(yaxis=dict(autorange="reversed", title="Pozycja w rankingu"),
                                        hovermode="x unified", height=600,
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    fig_r.update_traces(hovertemplate="%{fullData.name}: <b>%{y} miejsce</b><extra></extra>")
                    st.plotly_chart(fig_r, use_container_width=True)
            else:
                st.info("Brak punktów danych do obliczenia rankingów w tym okresie.")
    else:
        st.info("Wybierz co najmniej jedno miasto do wykresu rankingowego.")

# ── TAB 3: RANKING SŁUPKOWY ────────────────────────────────────────────────────────
with tab3:
    st.subheader("Ranking miast z systemem uzupełniania danych")
    
    col_r1, col_r2, col_r3 = st.columns([2, 2, 3])
    with col_r1:
        rank_year = st.selectbox("Rok bazowy:", sorted(all_years, reverse=True))
    with col_r2:
        top_n = st.slider("Liczba miast:", 5, 60, 20)
    with col_r3:
        tolerance = st.slider("Tolerancja braku danych (lata):", 0, 50, 15,
            help="Jeśli miasto nie ma danych w wybranym roku, system poszuka najbliższych danych z tolerancją +/- tylu lat.", key="bar_tol")

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