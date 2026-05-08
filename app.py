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
    
    # Oczyszczanie tekstu
    orig = str(text).replace('\xa0', ' ').strip()

    # Wykrywanie "około" / "ok." / "ok" (uproszczone bez \b, by łapać wszystko)
    is_approx = bool(re.search(r'(około|ok\.|ok)', orig, re.IGNORECASE))

    # 1. Próba znalezienia formatu DD.MM.YYYY
    dm = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{3,4})', orig)
    if dm:
        yr = int(dm.group(3))
        if 800 <= yr <= 2100:
            return yr, is_approx

    # 2. Szukanie dowolnej liczby 3 lub 4 cyfrowej (800-2100)
    # Wyciągamy wszystkie liczby z tekstu
    numbers = re.findall(r'\d{3,4}', orig)
    if numbers:
        for n in reversed(numbers): # Szukamy od końca, zazwyczaj rok jest ostatni
            yr = int(n)
            if 800 <= yr <= 2100:
                return yr, is_approx

    # 3. Obsługa wieków (rzymskie)
    romans = {
        'XX': 20, 'XIX': 19, 'XVIII': 18, 'XVII': 17, 'XVI': 16,
        'XV': 15, 'XIV': 14, 'XIII': 13, 'XII': 12, 'XI': 11,
        'X': 10, 'IX': 9, 'VIII': 8, 'VII': 7, 'VI': 6,
        'V': 5, 'IV': 4, 'III': 3, 'II': 2, 'I': 1,
    }
    t_lower = orig.lower()
    for rom, cent in romans.items():
        if re.search(rf'\b{rom.lower()}\b', t_lower):
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
        if not city or city == 'nan' or city in AGGREGATE_CITIES or is_przypis(city):
            continue
            
        for col_idx, year in col_to_year.items():
            if col_idx >= len(row): continue
            raw = str(row[col_idx]).strip()
            if raw in ('', 'nan'): continue
            
            # Czyszczenie wartości liczbowej (ludność)
            raw_clean = re.sub(r'\s+', '', raw).replace(',', '.')
            try:
                val = int(float(re.sub(r'\[.*\]', '', raw_clean)))
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


# --- STREAMLIT UI ---

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
    st.error("Brak danych do wyświetlenia.")
    st.stop()

df_pl = df[~df["Zagraniczne"]].copy()
all_years = sorted(df["Rok"].unique())
all_cities_set = set(df["Miasto"].unique())

# --- GLOBALNY PANEL ---
st.markdown("### Wskaż miasta do analizy")
show_foreign = st.checkbox("Uwzględnij miasta za granicami Polski", key="show_foreign")
cities_pool = sorted(df["Miasto"].unique()) if show_foreign else sorted(df_pl["Miasto"].unique())

if "global_cities" not in st.session_state:
    st.session_state["global_cities"] = []

def apply_global_group():
    group_name = st.session_state.get("global_group", "— brak —")
    if group_name != "— brak —":
        group_cities = [c for c in CITY_GROUPS.get(group_name, []) if c in set(cities_pool)]
        st.session_state["global_cities"] = group_cities
        st.session_state["global_group"] = "— brak —"

c_sel1, c_sel2 = st.columns([3, 1])
with c_sel1:
    selected = st.multiselect("Wybierz miasta:", cities_pool, key="global_cities")
with c_sel2:
    st.selectbox("Zastąp wybór grupą:", ["— brak —"] + list(CITY_GROUPS.keys()), key="global_group", on_change=apply_global_group)

st.divider()

df_src = df if show_foreign else df_pl
tab1, tab2, tab3 = st.tabs(["📈 Wykres liniowy", "📊 Zmiana rankingu", "🏆 Ranking (Słupkowy)"])

# --- TAB 1 ---
with tab1:
    st.subheader("Porównanie miast w czasie")
    min_y, max_y = int(min(all_years)), int(max(all_years))
    yr_range = st.slider("Zakres lat (wykres liniowy):", min_y, max_y, (min_y, max_y))

    if selected:
        sub = df_src[df_src["Miasto"].isin(selected) & df_src["Rok"].between(*yr_range)].sort_values("Rok")
        if not sub.empty:
            fig = px.line(sub, x="Rok", y="Ludność", color="Miasto", markers=True,
                          labels={"Ludność": "Liczba mieszkańców"},
                          custom_data=["Rok_Label"])
            fig.update_layout(hovermode="x unified", height=550)
            fig.update_traces(hovertemplate="%{fullData.name}: <b>%{y:,}</b> (%{customdata[0]})<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak danych dla wybranych miast w tym zakresie.")
    else:
        st.info("Wybierz miasta powyżej.")

# --- TAB 2 ---
with tab2:
    st.subheader("Zmiana pozycji w rankingu")
    yr_range_rank = st.slider("Zakres lat:", min_y, max_y, (min_y, max_y), key="rank_years")
    tolerance_rank = st.slider("Tolerancja (lata):", 0, 50, 15)

    if selected:
        years_in_range = [y for y in all_years if yr_range_rank[0] <= y <= yr_range_rank[1]]
        rank_records = []
        for y in years_in_range:
            temp = df_src[(df_src["Rok"] - y).abs() <= tolerance_rank].copy()
            if not temp.empty:
                temp["Diff"] = (temp["Rok"] - y).abs()
                temp = temp.sort_values(["Miasto", "Diff"]).drop_duplicates("Miasto")
                temp["Pozycja"] = temp["Ludność"].rank(ascending=False, method="min")
                temp["Rok_Wykresu"] = y
                rank_records.append(temp)
        
        if rank_records:
            df_plot_ranks = pd.concat(rank_records)
            df_plot_ranks = df_plot_ranks[df_plot_ranks["Miasto"].isin(selected)]
            fig_r = px.line(df_plot_ranks, x="Rok_Wykresu", y="Pozycja", color="Miasto", markers=True)
            fig_r.update_layout(yaxis=dict(autorange="reversed"), height=600)
            st.plotly_chart(fig_r, use_container_width=True)

# --- TAB 3 ---
with tab3:
    st.subheader("Ranking słupkowy (dla wybranych miast)")
    rank_year = st.selectbox("Rok bazowy:", sorted(all_years, reverse=True))
    tolerance = st.slider("Tolerancja (lata):", 0, 50, 15, key="bar_tol")

    if selected:
        df_rank = df_src[df_src["Miasto"].isin(selected)].copy()
        df_rank["Diff"] = (df_rank["Rok"] - rank_year).abs()
        df_rank = df_rank[df_rank["Diff"] <= tolerance].sort_values(["Miasto", "Diff"]).drop_duplicates("Miasto")
        
        if not df_rank.empty:
            df_rank = df_rank.sort_values("Ludność", ascending=False)
            fig_b = px.bar(df_rank, x="Ludność", y="Miasto", orientation="h", color="Ludność", text="Ludność")
            fig_b.update_layout(yaxis=dict(autorange="reversed"), height=max(400, len(df_rank)*30))
            st.plotly_chart(fig_b, use_container_width=True)
        else:
            st.info("Brak danych w wybranym przedziale.")