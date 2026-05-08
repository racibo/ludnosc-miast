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

# Znaczniki miast zagranicznych w nazwie
FOREIGN_MARKERS = ["(UA)", "(LIT)", "(BIA)", "(RUS)", "(DE)", "(CZ)", "(SK)"]

def is_foreign_city(name):
    name = str(name)
    return any(marker in name for marker in FOREIGN_MARKERS)

def parse_year(text):
    """
    Wyciąga rok z tekstu. Zwraca (int lub None, bool is_approx).
    Obsługuje formaty: 
    1. '2024'
    2. 'ok. 1600'  → is_approx=True
    3. 'II poł X w.', 'XI wiek'  → is_approx=True (daty opisowe)
    4. '31 XII 2017', 'VI 2012', '31 XII 2011'
    """
    if pd.isna(text) or text == '':
        return None, False

    orig = str(text).replace('\xa0', ' ').strip()
    is_approx = bool(re.search(r'\bok\.', orig, re.IGNORECASE))

    # Czyścimy tekst ze wszystkich nietypowych znaków
    t = re.sub(r'[^\w\s]', ' ', orig)
    t = t.strip().upper()

    # Próba 1: Szukamy 4 cyfr z rzędu (1000-2099) w dowolnym miejscu
    m = re.findall(r'\b(1\d{3}|20\d{2})\b', t)
    if m:
        return int(m[-1]), is_approx

    # 2. Mapowanie rzymskich na stulecia (dla dat opisowych typu wiek)
    romans = {
        'XVIII': 18, 'XVII': 17, 'XVI': 16, 'XV': 15, 'XIV': 14,
        'XIII': 13, 'XII': 12, 'XI': 11, 'X': 10, 'IX': 9
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
    name = str(name)
    return any(f in name for f in PRZYPIS_FRAGMENTS)

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(CSV_URL, header=None, dtype=str)
    date_row = df.iloc[0].tolist()

    col_to_year = {}      # col_idx → int year
    col_to_approx = {}    # col_idx → bool is_approx

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
                raw_clean = re.sub(r'\[.*\]', '', raw)
                val = int(float(raw_clean))
                records.append({
                    "Miasto": city,
                    "Rok": year,
                    "Approx": col_to_approx[col_idx],
                    "Ludność": val,
                    "Zagraniczne": is_foreign_city(city),
                })
            except ValueError:
                pass

    df_long = pd.DataFrame(records)
    if df_long.empty:
        return df_long, date_row

    # Kolumna z etykietą roku: ~1600 dla przybliżonych
    df_long["Rok_Label"] = df_long.apply(
        lambda r: f"~{r['Rok']}" if r["Approx"] else str(r["Rok"]), axis=1
    )

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
    st.error("Nie udało się wczytać danych. Sprawdź formatowanie nagłówków w arkuszu.")
    st.stop()

# Podział na polskie i zagraniczne
df_pl = df[~df["Zagraniczne"]].copy()
df_foreign = df[df["Zagraniczne"]].copy()

all_cities_pl = sorted(df_pl["Miasto"].unique())
all_cities_foreign = sorted(df_foreign["Miasto"].unique())
all_years = sorted(df["Rok"].unique())

tab1, tab2, tab3 = st.tabs(["📈 Wykres liniowy", "📊 Zmiana rankingu", "🏆 Ranking (Słupkowy)"])

# ── TAB 1: WYKRES LINIOWY ──────────────────────────────────────────────────
with tab1:
    st.subheader("Porównanie miast w czasie")
    c1, c2 = st.columns([3, 1])
    with c1:
        show_foreign_t1 = st.checkbox("Uwzględnij miasta za granicami Polski", key="foreign_t1")
        cities_pool_t1 = sorted(df["Miasto"].unique()) if show_foreign_t1 else all_cities_pl
        default = [c for c in ["Gdańsk", "Warszawa", "Kraków", "Łódź", "Wrocław"] if c in cities_pool_t1]
        selected = st.multiselect("Wybierz miasta:", cities_pool_t1, default=default)
    with c2:
        yr_range = st.slider("Zakres lat:", int(min(all_years)), int(max(all_years)),
                             value=(1800, int(max(all_years))))
    if selected:
        df_src = df if show_foreign_t1 else df_pl
        sub = df_src[df_src["Miasto"].isin(selected) & df_src["Rok"].between(*yr_range)].sort_values("Rok")

        ordered_cities = sub.groupby("Miasto")["Ludność"].max().sort_values(ascending=False).index.tolist()

        fig = px.line(sub, x="Rok", y="Ludność", color="Miasto", markers=True,
                      category_orders={"Miasto": ordered_cities},
                      labels={"Ludność": "Liczba mieszkańców"},
                      custom_data=["Rok_Label"])

        fig.update_xaxes(type='linear', title="Rok")
        fig.update_layout(
            hovermode="x unified",
            height=550,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        # Tylda w tooltipie dla przybliżonych dat
        fig.update_traces(hovertemplate="%{fullData.name}: <b>%{y:,}</b> (%{customdata[0]})<extra></extra>")

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Wybierz co najmniej jedno miasto.")

# ── TAB 2: ZMIANA RANKINGU ──────────────────────────────────────────────────
with tab2:
    st.subheader("Zmiana pozycji w rankingu na przestrzeni lat")

    c2_1, c2_2, c2_3 = st.columns([2, 1, 1])
    with c2_1:
        show_foreign_t2 = st.checkbox("Uwzględnij miasta za granicami Polski", key="foreign_t2")
        cities_pool_t2 = sorted(df["Miasto"].unique()) if show_foreign_t2 else all_cities_pl
        default_rank = [c for c in ["Gdańsk", "Warszawa", "Kraków", "Łódź", "Wrocław", "Poznań"] if c in cities_pool_t2]
        selected_rank = st.multiselect("Wybierz miasta do śledzenia rankingu:", cities_pool_t2,
                                       default=default_rank, key="rank_cities")
    with c2_2:
        yr_range_rank = st.slider("Zakres lat (ranking):", int(min(all_years)), int(max(all_years)),
                                  value=(1800, int(max(all_years))), key="rank_years")
    with c2_3:
        tolerance_rank = st.slider("Tolerancja (lata):", 0, 50, 15, key="rank_tol")

    if selected_rank:
        df_src2 = df if show_foreign_t2 else df_pl
        years_in_range = [y for y in all_years if yr_range_rank[0] <= y <= yr_range_rank[1]]
        rank_records = []
        for y in years_in_range:
            diffs = (df_src2["Rok"] - y).abs()
            temp = df_src2[diffs <= tolerance_rank].copy()
            if not temp.empty:
                temp["Diff"] = diffs
                temp = temp.sort_values(["Miasto", "Diff"])
                closest = temp.drop_duplicates(subset=["Miasto"], keep="first").copy()
                closest["Pozycja"] = closest["Ludność"].rank(ascending=False, method="min")
                closest["Rok_Wykresu"] = y
                rank_records.append(closest)

        if rank_records:
            df_all_ranks = pd.concat(rank_records)
            df_plot_ranks = df_all_ranks[df_all_ranks["Miasto"].isin(selected_rank)].sort_values("Rok_Wykresu")

            if not df_plot_ranks.empty:
                ordered_rank_cities = df_plot_ranks.groupby("Miasto")["Pozycja"].min().sort_values().index.tolist()

                # Budujemy wykres ręcznie przez go.Scatter, żeby mieć pełną kontrolę nad tooltipem.
                # Tooltip: przy każdym punkcie zapisujemy customdata z pozycją i ludnością,
                # a JS Plotly posortuje wpisy w "x unified" wg kolejności traces — dlatego
                # dla każdego punktu X dynamicznie sortujemy traces po pozycji (rosnąco = lepiej).
                # Rozwiązanie: używamy osobnego hover per trace z customdata zawierającym pozycję,
                # a hovermode="x unified" sortuje automatycznie wg wartości Y (przy reversed axis
                # najniższa pozycja = góra). Kluczowe: NIE stosujemy stałego category_orders —
                # zamiast tego sortujemy traces wg bieżącej pozycji w punkcie hover.
                # Plotly "x unified" wyświetla traces w kolejności ich definicji na fig,
                # więc sortujemy traces wg minimalnej pozycji (najlepszy wynik na pierwszym).

                fig_r = go.Figure()

                colors = px.colors.qualitative.Plotly
                for i, city in enumerate(ordered_rank_cities):
                    city_data = df_plot_ranks[df_plot_ranks["Miasto"] == city].sort_values("Rok_Wykresu")
                    color = colors[i % len(colors)]

                    # customdata: [pozycja (int), ludność, rok_label]
                    custom = list(zip(
                        city_data["Pozycja"].astype(int),
                        city_data["Ludność"],
                        city_data["Rok_Label"],
                    ))

                    fig_r.add_trace(go.Scatter(
                        x=city_data["Rok_Wykresu"],
                        y=city_data["Pozycja"],
                        mode="lines+markers",
                        name=city,
                        line=dict(color=color),
                        marker=dict(color=color),
                        customdata=custom,
                        hovertemplate=(
                            "<b>%{fullData.name}</b><br>"
                            "Pozycja: %{customdata[0]}<br>"
                            "Ludność: %{customdata[1]:,}<br>"
                            "Rok danych: %{customdata[2]}"
                            "<extra></extra>"
                        ),
                    ))

                fig_r.update_layout(
                    yaxis=dict(autorange="reversed", title="Pozycja w rankingu"),
                    xaxis=dict(title="Rok"),
                    hovermode="x unified",
                    height=600,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig_r, use_container_width=True)
        else:
            st.info("Brak danych.")

# ── TAB 3: RANKING SŁUPKOWY ────────────────────────────────────────────────────────
with tab3:
    st.subheader("Ranking miast")
    col_r1, col_r2, col_r3 = st.columns([2, 2, 3])
    with col_r1:
        rank_year = st.selectbox("Rok bazowy:", sorted(all_years, reverse=True))
    with col_r2:
        top_n = st.slider("Liczba miast:", 5, 60, 20)
    with col_r3:
        tolerance = st.slider("Tolerancja (lata):", 0, 50, 15, key="bar_tol")

    show_foreign_t3 = st.checkbox("Uwzględnij miasta za granicami Polski", key="foreign_t3")
    df_src3 = df if show_foreign_t3 else df_pl

    df_rank = df_src3.copy()
    df_rank["Roznica"] = (df_rank["Rok"] - rank_year).abs()
    df_rank = df_rank[df_rank["Roznica"] <= tolerance]
    df_rank = df_rank.sort_values(["Miasto", "Roznica"])
    closest_records = df_rank.drop_duplicates(subset=["Miasto"], keep="first").copy()

    if closest_records.empty:
        st.info("Brak danych.")
    else:
        closest_records = closest_records.sort_values("Ludność", ascending=False).reset_index(drop=True)
        closest_records["Pozycja_Nr"] = closest_records.index + 1

        def format_label(r):
            city_with_rank = f"{int(r['Pozycja_Nr'])}. {r['Miasto']}"
            rok_display = r["Rok_Label"]  # zawiera ~ jeśli przybliżony
            if r["Rok"] == rank_year and not r["Approx"]:
                return city_with_rank
            else:
                return f"{city_with_rank} ({rok_display})"

        closest_records["Etykieta"] = closest_records.apply(format_label, axis=1)
        dr = closest_records.head(top_n)

        fig_b = px.bar(dr, x="Ludność", y="Etykieta", orientation="h",
                       color="Ludność", text="Ludność")
        fig_b.update_layout(
            yaxis=dict(autorange="reversed", title=""),
            coloraxis_showscale=False,
            height=max(400, top_n * 25),
        )
        st.plotly_chart(fig_b, use_container_width=True)
