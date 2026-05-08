import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

FOREIGN_MARKERS = ["(UA)", "(LIT)", "(BIA)", "(RUS)", "(DE)", "(CZ)", "(SK)"]

CITY_GROUPS = {
    "Trójmiasto": ["Gdańsk", "Sopot", "Gdynia"],
    "Małe Trójmiasto": ["Wejherowo", "Reda", "Rumia"],
    "Aglomeracja Warszawy": [],
    "GOP (Górny Śląsk)": [
        "Katowice", "Sosnowiec", "Gliwice", "Zabrze", "Bytom",
        "Ruda Śląska", "Tychy", "Dąbrowa Górnicza", "Chorzów", "Jaworzno",
        "Mysłowice", "Siemianowice Śląskie", "Tarnowskie Góry",
        "Piekary Śląskie", "Będzin", "Świętochłowice", "Knurów",
        "Mikołów", "Czeladź",
    ],
    "Aglomeracja Łódzka": [
        "Łódź", "Pabianice", "Zgierz", "Aleksandrów Łódzki",
        "Konstantynów Łódzki", "Ozorków", "Głowno", "Koluszki",
        "Brzeziny", "Tuszyn", "Rzgów", "Stryków", "Lutomiersk",
    ],
}

WARSAW_SHEET = "Aglomeracja Warszawy"
_enc_w = urllib.parse.quote(WARSAW_SHEET)
WARSAW_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={_enc_w}"


def is_foreign_city(name):
    return any(marker in str(name) for marker in FOREIGN_MARKERS)


def parse_year(text):
    if pd.isna(text) or str(text).strip() == '':
        return None, False
    orig = str(text).replace('\xa0', ' ').strip()

    # Wykryj "ok.", "około", "ok" (poprawione wyrażenie regularne, żeby łapać kropkę przed spacją)
    is_approx = bool(re.search(r'(?i)\bokoło\b|\bok\b|\bok\.', orig))

    # Wyciągnij rok z formatu DD.MM.YYYY
    dm = re.search(r'\b(\d{1,2})\.(\d{1,2})\.(\d{3,4})\b', orig)
    if dm:
        yr = int(dm.group(3))
        if 800 <= yr <= 2100:
            return yr, is_approx

    t = re.sub(r'[^\w\s]', ' ', orig).strip().upper()

    # Szukaj 3- lub 4-cyfrowego roku (np. 966, 1500)
    m = re.findall(r'\b(\d{3,4})\b', t)
    if m:
        valid_years = [int(x) for x in m if 800 <= int(x) <= 2100]
        if valid_years:
            return valid_years[-1], is_approx

    # Opisy stuleci cyframi rzymskimi (I–XX)
    romans = {
        'XX': 20, 'XIX': 19, 'XVIII': 18, 'XVII': 17, 'XVI': 16,
        'XV': 15, 'XIV': 14, 'XIII': 13, 'XII': 12, 'XI': 11,
        'X': 10, 'IX': 9, 'VIII': 8, 'VII': 7, 'VI': 6,
        'V': 5, 'IV': 4, 'III': 3, 'II': 2, 'I': 1,
    }
    t_lower = t.lower()
    for rom, cent in romans.items():
        if re.search(rf'\b{rom.lower()}\b\s*(w\.|w\b|wiek)', t_lower):
            base = (cent - 1) * 100 + 50
            if 'ii poł' in t_lower or '2 poł' in t_lower: return base + 25, True
            if 'pocz' in t_lower or 'i poł' in t_lower or '1 poł' in t_lower: return base - 25, True
            if 'koniec' in t_lower: return base + 40, True
            return base, True
    return None, False


def is_przypis(name):
    return any(f in str(name) for f in PRZYPIS_FRAGMENTS)


@st.cache_data(ttl=3600)
def load_warsaw_cities():
    try:
        dfw = pd.read_csv(WARSAW_CSV_URL, header=None, dtype=str)
        return [str(v).strip() for v in dfw.iloc[:, 0].tolist() if str(v).strip() not in ('', 'nan')]
    except Exception:
        return []


@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(CSV_URL, header=None, dtype=str)
    date_row = df.iloc[0].tolist()
    col_to_year, col_to_approx = {}, {}
    for i, val in enumerate(date_row):
        if i == 0: continue
        yr, approx = parse_year(val)
        if yr is not None:
            col_to_year[i] = yr
            col_to_approx[i] = approx

    records = []
    for row_idx in range(1, len(df)):
        row = df.iloc[row_idx].tolist()
        city = str(row[0]).strip()
        if not city or city == 'nan': continue
        if city in AGGREGATE_CITIES: continue
        if is_przypis(city): continue
        for col_idx, year in col_to_year.items():
            if col_idx >= len(row): continue
            raw = str(row[col_idx]).strip()
            if raw in ('', 'nan'): continue
            raw = re.sub(r'\s+', '', raw).replace(',', '.')
            try:
                val = int(float(re.sub(r'\[.*\]', '', raw)))
                records.append({
                    "Miasto": city, "Rok": year,
                    "Approx": col_to_approx[col_idx],
                    "Ludność": val,
                    "Zagraniczne": is_foreign_city(city),
                })
            except ValueError:
                pass

    df_long = pd.DataFrame(records)
    if df_long.empty:
        return df_long, date_row
    df_long["Rok_Label"] = df_long.apply(
        lambda r: f"~{r['Rok']}" if r["Approx"] else str(r["Rok"]), axis=1
    )
    return df_long.sort_values(["Miasto", "Rok"]), date_row


# ── Wczytanie danych ──────────────────────────────────────────────────────
st.title("🏙️ Ludność miast Polski na przestrzeni wieków")

with st.spinner("Ładowanie danych..."):
    try:
        df, _date_row = load_data()
        warsaw_cities = load_warsaw_cities()
        if warsaw_cities:
            CITY_GROUPS["Aglomeracja Warszawy"] = warsaw_cities
    except Exception as e:
        st.error(f"Błąd ładowania: {e}")
        st.stop()

if df.empty:
    st.error("Nie udało się wczytać danych.")
    st.stop()

df_pl = df[~df["Zagraniczne"]].copy()
all_cities_pl = sorted(df_pl["Miasto"].unique())
all_years = sorted(df["Rok"].unique())
all_cities_set = set(df["Miasto"].unique())

# Grupy przefiltrowane do miast faktycznie obecnych w danych
CITY_GROUPS_AVAIL = {
    name: [c for c in cities if c in all_cities_set]
    for name, cities in CITY_GROUPS.items()
    if any(c in all_cities_set for c in cities)
}


# ── Globalny panel wyboru (Dla wszystkich zakładek) ───────────────────────
st.markdown("### Wskaż miasta do analizy")

show_foreign = st.checkbox("Uwzględnij miasta za granicami Polski", key="show_foreign")
cities_pool = sorted(df["Miasto"].unique()) if show_foreign else all_cities_pl

# Startowe miasta to pusta lista (0 wybranych na start)
if "global_cities" not in st.session_state:
    st.session_state["global_cities"] = []

# Callback wymieniający zaznaczone miasta na grupę
def apply_global_group():
    group_name = st.session_state.get("global_group", "— brak —")
    if group_name == "— brak —":
        return
    group_cities = [c for c in CITY_GROUPS_AVAIL.get(group_name, []) if c in set(cities_pool)]
    # Zastępuje dotychczasowy wybór
    st.session_state["global_cities"] = group_cities
    # Resetuje pole wyboru grupy z powrotem na 'brak'
    st.session_state["global_group"] = "— brak —"

group_options = ["— brak —"] + [
    name for name, cities in CITY_GROUPS_AVAIL.items()
    if any(c in set(cities_pool) for c in cities)
]

# Utrzymaj w pamięci tylko dostępne miasta (np. po odznaczeniu "zagranicznych")
valid_cities = [c for c in st.session_state["global_cities"] if c in set(cities_pool)]
st.session_state["global_cities"] = valid_cities

c_sel1, c_sel2 = st.columns([3, 1])
with c_sel1:
    selected = st.multiselect("Wybierz miasta:", cities_pool, key="global_cities")
with c_sel2:
    st.selectbox("Zastąp wybór grupą:", group_options, key="global_group", on_change=apply_global_group)

st.divider()

# Wybór bazowej ramki w zależności od checkboxa "zagranicznego"
df_src = df if show_foreign else df_pl

tab1, tab2, tab3 = st.tabs(["📈 Wykres liniowy", "📊 Zmiana rankingu", "🏆 Ranking (Słupkowy)"])


# ── TAB 1: WYKRES LINIOWY ──────────────────────────────────────────────────
with tab1:
    st.subheader("Porównanie miast w czasie")
    
    yr_range = st.slider("Zakres lat (wykres liniowy):", int(min(all_years)), int(max(all_years)),
                         value=(int(min(all_years)), int(max(all_years))))

    if selected:
        sub = df_src[df_src["Miasto"].isin(selected) & df_src["Rok"].between(*yr_range)].sort_values("Rok")
        if not sub.empty:
            ordered = sub.groupby("Miasto")["Ludność"].max().sort_values(ascending=False).index.tolist()
            fig = px.line(sub, x="Rok", y="Ludność", color="Miasto", markers=True,
                          category_orders={"Miasto": ordered},
                          labels={"Ludność": "Liczba mieszkańców"},
                          custom_data=["Rok_Label"])
            fig.update_xaxes(type='linear', title="Rok")
            fig.update_layout(hovermode="x unified", height=550,
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig.update_traces(hovertemplate="%{fullData.name}: <b>%{y:,}</b> (%{customdata[0]})<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak danych w wybranym przedziale lat dla podanych miast.")
    else:
        st.info("Wybierz co najmniej jedno miasto w panelu powyżej.")


# ── TAB 2: ZMIANA RANKINGU ──────────────────────────────────────────────────
with tab2:
    st.subheader("Zmiana pozycji w rankingu na przestrzeni lat")

    c2_1, c2_2 = st.columns(2)
    with c2_1:
        yr_range_rank = st.slider("Zakres lat (ranking):", int(min(all_years)), int(max(all_years)),
                                  value=(int(min(all_years)), int(max(all_years))), key="rank_years")
    with c2_2:
        tolerance_rank = st.slider("Tolerancja (lata, przybliżenia roczników):", 0, 50, 15, key="rank_tol")

    if selected:
        years_in_range = [y for y in all_years if yr_range_rank[0] <= y <= yr_range_rank[1]]
        rank_records = []
        for y in years_in_range:
            diffs = (df_src["Rok"] - y).abs()
            temp = df_src[diffs <= tolerance_rank].copy()
            if not temp.empty:
                temp["Diff"] = diffs
                temp = temp.sort_values(["Miasto", "Diff"])
                closest = temp.drop_duplicates(subset=["Miasto"], keep="first").copy()
                closest["Pozycja"] = closest["Ludność"].rank(ascending=False, method="min")
                closest["Rok_Wykresu"] = y
                rank_records.append(closest)

        if rank_records:
            df_all_ranks = pd.concat(rank_records)
            df_plot_ranks = df_all_ranks[df_all_ranks["Miasto"].isin(selected)].sort_values("Rok_Wykresu")

            if not df_plot_ranks.empty:
                ordered_rank = df_plot_ranks.groupby("Miasto")["Pozycja"].min().sort_values().index.tolist()
                fig_r = go.Figure()
                colors = px.colors.qualitative.Plotly
                for i, city in enumerate(ordered_rank):
                    city_data = df_plot_ranks[df_plot_ranks["Miasto"] == city].sort_values("Rok_Wykresu")
                    color = colors[i % len(colors)]
                    custom = list(zip(city_data["Pozycja"].astype(int),
                                     city_data["Ludność"], city_data["Rok_Label"]))
                    fig_r.add_trace(go.Scatter(
                        x=city_data["Rok_Wykresu"], y=city_data["Pozycja"],
                        mode="lines+markers", name=city,
                        line=dict(color=color), marker=dict(color=color),
                        customdata=custom,
                        hovertemplate=(
                            "<b>%{fullData.name}</b><br>"
                            "Pozycja: %{customdata[0]}<br>"
                            "Ludność: %{customdata[1]:,}<br>"
                            "Rok danych: %{customdata[2]}<extra></extra>"
                        ),
                    ))
                fig_r.update_layout(
                    yaxis=dict(autorange="reversed", title="Pozycja w rankingu (wśród wszystkich miast)"),
                    xaxis=dict(title="Rok"),
                    hovermode="closest",
                    height=600,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig_r, use_container_width=True)
            else:
                 st.info("Brak danych spełniających kryteria tolerancji.")
        else:
            st.info("Brak danych.")
    else:
        st.info("Wybierz co najmniej jedno miasto w panelu powyżej.")


# ── TAB 3: RANKING SŁUPKOWY ────────────────────────────────────────────────
with tab3:
    st.subheader("Ranking miast (zawężony do wybranych na górze ekranu)")
    
    col_r1, col_r2, col_r3 = st.columns([2, 2, 3])
    with col_r1:
        rank_year = st.selectbox("Rok bazowy:", sorted(all_years, reverse=True))
    with col_r2:
        top_n = st.slider("Liczba miast na wykresie:", 5, 60, 20)
    with col_r3:
        tolerance = st.slider("Tolerancja (lata, przybliżenia roczników):", 0, 50, 15, key="bar_tol")

    if selected:
        # Pokaż wykres tylko dla miast wybranych w panelu głównym
        df_rank = df_src[df_src["Miasto"].isin(selected)].copy()
        
        df_rank["Roznica"] = (df_rank["Rok"] - rank_year).abs()
        df_rank = df_rank[df_rank["Roznica"] <= tolerance]
        df_rank = df_rank.sort_values(["Miasto", "Roznica"])
        closest_records = df_rank.drop_duplicates(subset=["Miasto"], keep="first").copy()

        if closest_records.empty:
            st.info("Brak danych dla wybranych miast w pobliżu wskazanego roku.")
        else:
            closest_records = closest_records.sort_values("Ludność", ascending=False).reset_index(drop=True)
            closest_records["Pozycja_Nr"] = closest_records.index + 1

            def format_label(r):
                base = f"{int(r['Pozycja_Nr'])}. {r['Miasto']}"
                if r["Rok"] == rank_year and not r["Approx"]:
                    return base
                return f"{base} ({r['Rok_Label']})"

            closest_records["Etykieta"] = closest_records.apply(format_label, axis=1)
            dr = closest_records.head(top_n)
            
            fig_b = px.bar(dr, x="Ludność", y="Etykieta", orientation="h",
                           color="Ludność", text="Ludność")
            fig_b.update_layout(yaxis=dict(autorange="reversed", title=""),
                                coloraxis_showscale=False, height=max(400, len(dr) * 35))
            st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.info("Wybierz co najmniej jedno miasto w panelu powyżej.")