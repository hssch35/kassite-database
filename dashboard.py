"""
dashboard.py — Kassitische Onomastik · Interactive Linguistic Dashboard

Run:
    streamlit run dashboard.py

Auto-reload: whenever main.py writes an updated enriched JSON, the dashboard
detects the new file-mtime and recomputes on next interaction (no restart needed).
"""

from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from collections import Counter

from src.db_analytics import compute_all_from_db

# ── Config ─────────────────────────────────────────────────────────────────────
DB_PATH = "ancient_names.db"

PRIMARY = "#8B6914"   # golden brown  (cuneiform tablet)
BLUE    = "#2E6B8B"   # lapis lazuli
TERRA   = "#C65D2A"   # terracotta
GREEN   = "#4A7C59"   # malachite

SECTIONS = [
    "Überblick",
    "Phonem-Inventar",
    "Namens-Struktur",
    "Vokal-Muster",
    "Morphologie",
    "Phonotaktik",
    "Theophore Analyse",
    "Varianten & Minimale Paare",
    "Kognaten & Sprachvergleich",
    "Namens-Browser",
]

st.set_page_config(
    page_title="Kassitisch — Linguistic Dashboard",
    page_icon="𒀭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      section[data-testid="stSidebar"] { background: #2C1F0E; }
      section[data-testid="stSidebar"] * { color: #F5E6C8 !important; }
      .block-container { padding-top: 1.5rem; }
      h1 { color: #5C3D0A; }
      h2, h3 { color: #7A5015; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Data loading ───────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Analysiere Datenbank …")
def load_data(db_path: str, mtime: float) -> dict:          # mtime in key → auto-invalidate
    return compute_all_from_db(db_path)


def get_data() -> dict:
    if not os.path.exists(DB_PATH):
        st.error(
            f"Datenbank **{DB_PATH}** nicht gefunden.  \n"
            "Bitte erst `python main.py` ausführen."
        )
        st.stop()
    return load_data(DB_PATH, os.path.getmtime(DB_PATH))


# ── Helpers ────────────────────────────────────────────────────────────────────

def cdf(c: Counter, key: str = "Kategorie", val: str = "Anzahl",
        top: int | None = None) -> pd.DataFrame:
    items = c.most_common(top) if top else sorted(c.items(), key=lambda x: -x[1])
    return pd.DataFrame(items, columns=[key, val])


def hbar(df: pd.DataFrame, x: str, y: str, title: str,
         color_col: str | None = None, palette: str = "YlOrBr") -> go.Figure:
    kwargs: dict = dict(orientation="h", title=title, height=400,
                        color_continuous_scale=palette)
    if color_col:
        kwargs["color"] = color_col
    else:
        kwargs["color_discrete_sequence"] = [PRIMARY]
    fig = px.bar(df, x=x, y=y, **kwargs)
    fig.update_layout(yaxis={"autorange": "reversed"},
                      margin=dict(t=40, b=0, l=0, r=0))
    return fig


def vbar(df: pd.DataFrame, x: str, y: str, title: str,
         color_col: str | None = None, palette: str = "YlOrBr",
         color: str | None = None) -> go.Figure:
    kwargs: dict = dict(title=title, height=380)
    if color_col:
        kwargs["color"] = color_col
        kwargs["color_continuous_scale"] = palette
    else:
        kwargs["color_discrete_sequence"] = [color or PRIMARY]
    fig = px.bar(df, x=x, y=y, **kwargs)
    fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    return fig


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 𒀭 Kassitisch")
    st.caption("Linguistisches Dashboard")
    st.divider()

    section = st.radio("", SECTIONS, label_visibility="collapsed")

    st.divider()
    if st.button("🔄  Daten neu laden", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    mtime_raw = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else 0
    import datetime
    st.caption(
        f"DB: `{DB_PATH}` (SQLite)  \n"
        f"Stand: {datetime.datetime.fromtimestamp(mtime_raw):%Y-%m-%d %H:%M}"
    )

# ── Load ───────────────────────────────────────────────────────────────────────

D  = get_data()
db = D["db"]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: Überblick
# ══════════════════════════════════════════════════════════════════════════════

if section == "Überblick":
    st.title("Kassitische Onomastik — Überblick")
    st.caption(
        "Das Dashboard lädt automatisch die aktuelle Datenbank. "
        "Nach jedem `python main.py`-Lauf reicht eine neue Interaktion zum Aktualisieren."
    )
    st.divider()

    # ── Metric row ────────────────────────────────────────────────────────────
    morpheme_cov = sum(1 for e in db if e.get("morpheme_root") and e.get("morpheme_suffix"))
    theophoric_n = sum(1 for e in db if e.get("detected_gods"))
    with_meaning = sum(1 for e in db if e.get("meaning"))
    llm_n        = sum(1 for e in db if e.get("llm_analysis"))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Gesamtnamen",       D["total"])
    c2.metric("Theophore Namen",   theophoric_n,
              f"{theophoric_n / D['total'] * 100:.0f} %")
    c3.metric("Morphem-Abdeckung", f"{morpheme_cov / D['total'] * 100:.1f} %")
    c4.metric("Mit Bedeutung",     with_meaning)
    c5.metric("LLM-angereichert",  llm_n)

    st.divider()

    # ── Field coverage ────────────────────────────────────────────────────────
    cov = D["field_coverage"]
    cov_df = pd.DataFrame(
        [(k, v, round(v / D["total"] * 100, 1))
         for k, v in sorted(cov.items(), key=lambda x: -x[1])],
        columns=["Feld", "Einträge", "Abdeckung %"],
    )
    col_a, col_b = st.columns([3, 1])
    with col_a:
        fig = px.bar(
            cov_df, x="Feld", y="Abdeckung %",
            color="Abdeckung %", color_continuous_scale="YlOrBr",
            title="Datenbankfelder — Abdeckung (%)", height=360,
        )
        fig.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.dataframe(cov_df, use_container_width=True, hide_index=True)

    st.divider()

    # ── Quick highlights ──────────────────────────────────────────────────────
    st.subheader("Highlights")
    h1, h2, h3, h4 = st.columns(4)
    with h1:
        st.markdown("**Top 3 Suffixe**")
        for s, c in D["morpheme_suffixes"].most_common(3):
            st.markdown(f"- `-{s}` · {c}×")
    with h2:
        st.markdown("**Top 3 Anlaute**")
        for ch, c in D["initial_consonants"].most_common(3):
            st.markdown(f"- `{ch}` · {c}×")
    with h3:
        st.markdown("**Top 3 Auslaute**")
        for ch, c in D["final_consonants"].most_common(3):
            st.markdown(f"- `{ch}` · {c}×")
    with h4:
        st.markdown("**Top 3 Götter**")
        for g, c in D["theophoric_counts"].most_common(3):
            st.markdown(f"- {g} · {c}×")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: Phonem-Inventar
# ══════════════════════════════════════════════════════════════════════════════

elif section == "Phonem-Inventar":
    st.title("Phonem-Inventar")
    st.caption(
        "Rekonstruiertes Inventar aus allen Transkriptionen des Korpus. "
        "Zeigt, welche Laute im Kassitischen belegt sind und wie häufig sie auftreten."
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        df_c = cdf(D["consonants"], "Phonem", "Häufigkeit")
        fig = px.bar(df_c, x="Phonem", y="Häufigkeit",
                     color="Häufigkeit", color_continuous_scale="YlOrBr",
                     title="Konsonanten-Inventar (rekonstruiert)", height=380)
        fig.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        df_v = cdf(D["vowels"], "Vokal", "Häufigkeit")
        fig2 = px.pie(df_v, names="Vokal", values="Häufigkeit",
                      title="Vokalverteilung",
                      color_discrete_sequence=px.colors.sequential.Oranges_r,
                      height=380)
        fig2.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Bigramm-Analyse (Phonotaktik)")
    st.caption(
        "Welche Zeichenpaare treten am häufigsten auf? "
        "Zeigt bevorzugte Lautfolgen und phonotaktische Einschränkungen."
    )

    tab_heat, tab_bar = st.tabs(["Heatmap", "Top-Bigramme"])

    with tab_heat:
        top_n = st.slider("Zeichen für Matrix", 8, 22, 14, key="hm_n")
        all_ph = D["consonants"] + D["vowels"]
        top_chars = [ch for ch, _ in all_ph.most_common(top_n)]
        matrix = [
            [D["bigrams"].get(a + b, 0) for b in top_chars]
            for a in top_chars
        ]
        fig_hm = go.Figure(go.Heatmap(
            z=matrix, x=top_chars, y=top_chars,
            colorscale="YlOrBr",
            hovertemplate="Bigramm: %{y}%{x}<br>Häufigkeit: %{z}<extra></extra>",
        ))
        fig_hm.update_layout(
            title="Bigramm-Frequenz-Matrix",
            height=520,
            xaxis_title="Folgezeichen",
            yaxis_title="Ausgangszeichen",
            margin=dict(t=40, b=0),
        )
        st.plotly_chart(fig_hm, use_container_width=True)

    with tab_bar:
        n_bg = st.slider("Top N Bigramme", 10, 40, 20, key="bg_n")
        df_bg = cdf(D["bigrams"], "Bigramm", "Häufigkeit", top=n_bg)
        fig_b = px.bar(df_bg, x="Bigramm", y="Häufigkeit",
                       color="Häufigkeit", color_continuous_scale="Blues",
                       title=f"Top {n_bg} Bigramme", height=380)
        fig_b.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_b, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: Namens-Struktur
# ══════════════════════════════════════════════════════════════════════════════

elif section == "Namens-Struktur":
    st.title("Namens-Struktur")

    col1, col2 = st.columns(2)
    with col1:
        df_len = cdf(D["name_lengths"], "Zeichen", "Anzahl")
        df_len = df_len.sort_values("Zeichen")
        fig_l = px.bar(df_len, x="Zeichen", y="Anzahl",
                       title="Namenslängen-Verteilung",
                       color_discrete_sequence=[PRIMARY], height=360)
        fig_l.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_l, use_container_width=True)
    with col2:
        df_syl = cdf(D["syllable_dist"], "Silben", "Anzahl")
        df_syl = df_syl.sort_values("Silben")
        fig_s = px.bar(df_syl, x="Silben", y="Anzahl",
                       title="Silbenanzahl-Verteilung",
                       color_discrete_sequence=[BLUE], height=360)
        fig_s.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_s, use_container_width=True)

    st.divider()

    col3, col4 = st.columns(2)
    with col3:
        n_cv = st.slider("Top CV-Muster", 10, 30, 15, key="cv_n")
        df_cv = cdf(D["cv_structures"], "CV-Muster", "Anzahl", top=n_cv)
        total_cv = df_cv["Anzahl"].sum()
        df_cv["Anteil %"] = (df_cv["Anzahl"] / total_cv * 100).round(1)
        fig_cv = px.bar(df_cv, x="Anzahl", y="CV-Muster",
                        orientation="h",
                        color="Anzahl", color_continuous_scale="YlOrBr",
                        title=f"Top {n_cv} Silbenstrukturen (CV-Muster)",
                        hover_data=["Anteil %"], height=420)
        fig_cv.update_layout(yaxis={"autorange": "reversed"},
                             margin=dict(t=40, b=0))
        st.plotly_chart(fig_cv, use_container_width=True)
    with col4:
        df_ph = cdf(D["phonetic_classes"], "Lautklasse", "Häufigkeit")
        fig_ph = px.pie(df_ph, names="Lautklasse", values="Häufigkeit",
                        title="Lautklassen-Verteilung",
                        color_discrete_sequence=px.colors.qualitative.Set2,
                        height=420)
        fig_ph.update_traces(textinfo="label+percent")
        fig_ph.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_ph, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: Vokal-Muster
# ══════════════════════════════════════════════════════════════════════════════

elif section == "Vokal-Muster":
    st.title("Vokal-Muster")
    st.caption(
        "Vokal-Inventar nach Wortposition sowie Korrelation "
        "zwischen Wurzel- und Suffixvokalen (potenzielle Vokalharmonie)."
    )

    # Position grouped bar
    vowels_all = sorted(
        set(list(D["vowel_initial"]) + list(D["vowel_medial"]) + list(D["vowel_final"]))
    )
    pos_data = []
    for v in vowels_all:
        pos_data.append({"Vokal": v, "Position": "Anlaut",  "n": D["vowel_initial"].get(v, 0)})
        pos_data.append({"Vokal": v, "Position": "Medial",  "n": D["vowel_medial"].get(v, 0)})
        pos_data.append({"Vokal": v, "Position": "Auslaut", "n": D["vowel_final"].get(v, 0)})
    df_pos = pd.DataFrame(pos_data)

    fig_pos = px.bar(
        df_pos, x="Vokal", y="n", color="Position", barmode="group",
        title="Vokalverteilung nach Wortposition",
        color_discrete_map={"Anlaut": PRIMARY, "Medial": BLUE, "Auslaut": TERRA},
        height=380,
    )
    fig_pos.update_layout(margin=dict(t=40, b=0), yaxis_title="Häufigkeit")
    st.plotly_chart(fig_pos, use_container_width=True)

    st.info(
        "**Beobachtung:** `u` dominiert im Anlaut, `a` im Medial. "
        "Das deutet auf mögliche positionelle Vokalrestriktionen hin."
    )

    st.divider()

    # Vowel correlation
    st.subheader("Vokal-Korrelation: Wurzelvokal → Suffix")
    st.caption(
        "Welcher Wurzelvokal kombiniert bevorzugt mit welchem Suffixvokal? "
        "Auffällige Muster können auf Vokalharmonie hinweisen."
    )
    df_vc = cdf(D["vowel_correlation"], "Muster", "Häufigkeit")
    fig_vc = px.bar(df_vc, x="Muster", y="Häufigkeit",
                    color="Häufigkeit", color_continuous_scale="RdYlBu_r",
                    title="Wurzelvokal → Suffix-Korrelation", height=360)
    fig_vc.update_layout(margin=dict(t=40, b=0))
    st.plotly_chart(fig_vc, use_container_width=True)

    # Raw table
    with st.expander("Rohdaten anzeigen"):
        total_vc = sum(D["vowel_correlation"].values())
        vc_rows = [
            {"Muster": k, "Häufigkeit": v, "Anteil %": round(v / total_vc * 100, 1)}
            for k, v in D["vowel_correlation"].most_common()
        ]
        st.dataframe(pd.DataFrame(vc_rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: Morphologie
# ══════════════════════════════════════════════════════════════════════════════

elif section == "Morphologie":
    st.title("Morphologie")

    col1, col2 = st.columns(2)
    with col1:
        n_suf = st.slider("Top Suffixe", 10, 30, 20, key="suf_n")
        df_suf = cdf(D["morpheme_suffixes"], "Suffix", "Häufigkeit", top=n_suf)
        fig_suf = px.bar(df_suf, x="Suffix", y="Häufigkeit",
                         color="Häufigkeit", color_continuous_scale="YlOrBr",
                         title=f"Top {n_suf} Suffixe", height=380)
        fig_suf.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_suf, use_container_width=True)
    with col2:
        n_root = st.slider("Top Morphem-Wurzeln", 10, 30, 20, key="root_n")
        df_root = cdf(D["morpheme_roots"], "Wurzel", "Häufigkeit", top=n_root)
        fig_root = px.bar(df_root, x="Wurzel", y="Häufigkeit",
                          color_discrete_sequence=[BLUE],
                          title=f"Top {n_root} Morphem-Wurzeln", height=380)
        fig_root.update_xaxes(tickangle=45)
        fig_root.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_root, use_container_width=True)

    st.divider()
    st.subheader("Wurzel-Produktivität")
    st.caption("Wie viele einzigartige Suffixe kombiniert eine Wurzel? "
               "Hohe Produktivität = morphologisch aktive Wurzel.")

    n_prod = st.slider("Top Wurzeln anzeigen", 10, 50, 30, key="prod_n")
    prod_df = pd.DataFrame(
        sorted(D["root_productivity"].items(), key=lambda x: -x[1])[:n_prod],
        columns=["Wurzel", "Einzigartige Suffixe"],
    )
    fig_prod = px.scatter(
        prod_df, x="Wurzel", y="Einzigartige Suffixe",
        size="Einzigartige Suffixe", color="Einzigartige Suffixe",
        color_continuous_scale="YlOrBr",
        title=f"Top {n_prod} produktivste Wurzeln",
        height=400,
    )
    fig_prod.update_xaxes(tickangle=45)
    fig_prod.update_layout(margin=dict(t=40, b=0))
    st.plotly_chart(fig_prod, use_container_width=True)

    st.divider()
    st.subheader("Suffix → Wurzel-Kollokationen")

    sorted_suffixes = sorted(
        D["suffix_to_roots"].keys(),
        key=lambda s: -len(D["suffix_to_roots"][s]),
    )
    sel_suf = st.selectbox("Suffix auswählen:", sorted_suffixes, key="suf_sel")
    if sel_suf:
        roots = sorted(D["suffix_to_roots"].get(sel_suf, []))
        st.markdown(
            f"**`-{sel_suf}`** kombiniert mit **{len(roots)}** "
            f"einzigartigen Wurzeln:"
        )
        # Show as tags
        st.write("  ".join(f"`{r}`" for r in roots))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: Phonotaktik
# ══════════════════════════════════════════════════════════════════════════════

elif section == "Phonotaktik":
    st.title("Phonotaktik")

    col1, col2 = st.columns(2)
    with col1:
        df_ic = cdf(D["initial_consonants"], "Konsonant", "Häufigkeit")
        fig_ic = px.bar(df_ic, x="Konsonant", y="Häufigkeit",
                        color="Häufigkeit", color_continuous_scale="YlOrBr",
                        title="Bevorzugte Anlaute (Wurzelbeginn)", height=360)
        fig_ic.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_ic, use_container_width=True)
    with col2:
        df_fc = cdf(D["final_consonants"], "Konsonant", "Häufigkeit")
        fig_fc = px.bar(df_fc, x="Konsonant", y="Häufigkeit",
                        color_discrete_sequence=[TERRA],
                        title="Bevorzugte Auslaute (Wurzelende)", height=360)
        fig_fc.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_fc, use_container_width=True)

    st.divider()

    col3, col4 = st.columns(2)
    with col3:
        n_cl = st.slider("Top Cluster", 10, 25, 15, key="cl_n")
        df_cl = cdf(D["consonant_clusters"], "Cluster", "Häufigkeit", top=n_cl)
        fig_cl = px.bar(df_cl, x="Cluster", y="Häufigkeit",
                        color_discrete_sequence=[BLUE],
                        title=f"Top {n_cl} Konsonanten-Cluster", height=360)
        fig_cl.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_cl, use_container_width=True)
    with col4:
        df_ct = cdf(D["cluster_types"], "Typ", "Häufigkeit")
        fig_ct = hbar(df_ct, "Häufigkeit", "Typ",
                      "Cluster-Typen (Lautklassen-Paare)",
                      color_col="Häufigkeit", palette="Blues")
        st.plotly_chart(fig_ct, use_container_width=True)

    st.divider()

    col5, col6 = st.columns([1, 2])
    with col5:
        df_son = cdf(D["sonority_stats"], "Tendenz", "Häufigkeit")
        fig_son = px.pie(df_son, names="Tendenz", values="Häufigkeit",
                         title="Sonoritätsprofil der Cluster",
                         color_discrete_sequence=[PRIMARY, BLUE, TERRA],
                         height=320)
        fig_son.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_son, use_container_width=True)
    with col6:
        st.markdown("#### Sonoritätshierarchie — Erklärung")
        st.markdown(
            """
            Die **Sonoritätskurve** beschreibt, wie sich die Schallstärke innerhalb
            eines Konsonantenclusters verändert:

            | Tendenz | Bedeutung | Typisch für |
            |---|---|---|
            | **Aufsteigend** | weniger sonor → sonorer | Silbenanlaute (Onset) |
            | **Absteigend** | sonorer → weniger sonor | Silbenauslaute (Coda) |
            | **Plateau** | gleiche Sonorität | selten; Geminaten |

            Im Kassitischen überwiegen **absteigende** Cluster → viele Namen enden
            auf Sonoranten gefolgt von Obstruenten (`rb`, `nd`, `kt`).
            """
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: Theophore Analyse
# ══════════════════════════════════════════════════════════════════════════════

elif section == "Theophore Analyse":
    st.title("Theophore Analyse — Götternamen")
    st.caption(
        "Theophore Namen enthalten einen Götternamen als Bestandteil. "
        "Die Produktivität gibt an, mit wie vielen einzigartigen Personalstämmen "
        "ein Gott Namen bildet."
    )

    col1, col2 = st.columns(2)
    with col1:
        df_god = cdf(D["theophoric_counts"], "Gottheit", "Häufigkeit")
        fig_god = px.bar(df_god, x="Gottheit", y="Häufigkeit",
                         color="Häufigkeit", color_continuous_scale="YlOrBr",
                         title="Götternamen-Häufigkeit", height=380)
        fig_god.update_xaxes(tickangle=30)
        fig_god.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_god, use_container_width=True)
    with col2:
        gp_df = pd.DataFrame(
            sorted(D["god_productivity"].items(), key=lambda x: -x[1]),
            columns=["Gottheit", "Einzigartige Stämme"],
        )
        fig_gp = px.bar(gp_df, x="Gottheit", y="Einzigartige Stämme",
                        color_discrete_sequence=[BLUE],
                        title="Theophore Produktivität (einzigartige Personalstämme)",
                        height=380)
        fig_gp.update_xaxes(tickangle=30)
        fig_gp.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_gp, use_container_width=True)

    st.divider()

    col3, col4 = st.columns([1, 2])
    with col3:
        df_gpos = cdf(D["god_position_counts"], "Position", "Häufigkeit")
        fig_gpos = px.pie(df_gpos, names="Position", values="Häufigkeit",
                          title="Position des Götternamens",
                          color_discrete_sequence=[PRIMARY, TERRA],
                          height=320)
        fig_gpos.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_gpos, use_container_width=True)

    with col4:
        st.subheader("Namen je Gottheit")
        deity_opts = sorted(
            D["theophoric_counts"].keys(),
            key=lambda x: -D["theophoric_counts"][x],
        )
        deity_sel = st.selectbox("Gottheit wählen:", deity_opts, key="deity_sel")
        if deity_sel:
            deity_names = sorted(
                e["transcription"]
                for e in db
                if deity_sel in (e.get("detected_gods") or [])
            )
            st.markdown(
                f"**{len(deity_names)} Namen** mit *{deity_sel}* "
                f"(Produktivität: {D['god_productivity'].get(deity_sel, '–')} Stämme):"
            )
            cols = st.columns(3)
            for i, n in enumerate(deity_names):
                cols[i % 3].markdown(f"- `{n}`")

    # LLM semantic fields (if available)
    if D["llm_semantic_fields"]:
        st.divider()
        st.subheader("Semantische Felder (LLM-Analyse)")
        df_sem = cdf(D["llm_semantic_fields"], "Feld", "Häufigkeit")
        fig_sem = px.bar(df_sem, x="Feld", y="Häufigkeit",
                         color_discrete_sequence=[GREEN],
                         title="Semantische Felder der Personennamen", height=360)
        fig_sem.update_xaxes(tickangle=30)
        fig_sem.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_sem, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: Varianten & Minimale Paare
# ══════════════════════════════════════════════════════════════════════════════

elif section == "Varianten & Minimale Paare":
    st.title("Varianten & Minimale Paare")

    tab1, tab2 = st.tabs(
        [f"Konsonantenskelett-Varianten  ({len(D['skeleton_variants'])})",
         f"Minimale Paare  ({len(D['minimal_pairs'])})"]
    )

    with tab1:
        st.caption(
            "Namen mit identischem Konsonantenskelett (alle Vokale entfernt) "
            "sind wahrscheinlich Schreibvarianten derselben Person oder "
            "morphologische Alternationen."
        )
        skel_rows = [
            {"Skelett": k, "Varianten": ", ".join(v), "Anzahl": len(v)}
            for k, v in sorted(
                D["skeleton_variants"].items(), key=lambda x: -len(x[1])
            )
        ]
        df_skel = pd.DataFrame(skel_rows)

        min_count = st.slider("Min. Varianten pro Gruppe", 2, 5, 2, key="skel_min")
        df_skel_f = df_skel[df_skel["Anzahl"] >= min_count]
        st.caption(f"{len(df_skel_f)} Gruppen angezeigt")
        st.dataframe(
            df_skel_f,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Anzahl": st.column_config.NumberColumn(width="small"),
                "Skelett": st.column_config.TextColumn(width="small"),
            },
            height=500,
        )

    with tab2:
        st.caption(
            "Namenpaare mit Hamming-Distanz 1 (gleiche Länge, genau 1 Zeichen "
            "verschieden). Besonders wertvoll für die phonemische Analyse: "
            "kontrastierende Paare belegen distinktive Merkmale."
        )
        pair_rows = []
        for a, b in D["minimal_pairs"]:
            diff_pos = next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)
            pair_rows.append({
                "Name A":    a,
                "Name B":    b,
                "Position":  diff_pos + 1,
                "Kontrast":  f"{a[diff_pos]} ↔ {b[diff_pos]}",
            })
        df_pairs = pd.DataFrame(pair_rows).sort_values("Kontrast")

        filter_contrast = st.text_input(
            "Kontrast filtern (z.B. 'š', 't'):", "", key="pair_filter"
        )
        if filter_contrast:
            df_pairs = df_pairs[
                df_pairs["Kontrast"].str.contains(filter_contrast, case=False)
            ]

        st.caption(f"{len(df_pairs)} Paare angezeigt")
        st.dataframe(
            df_pairs,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Position": st.column_config.NumberColumn(width="small"),
            },
            height=500,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: Kognaten & Sprachvergleich
# ══════════════════════════════════════════════════════════════════════════════

elif section == "Kognaten & Sprachvergleich":
    st.title("Kognaten & Sprachvergleich")
    st.caption(
        "Phonetische Ähnlichkeitssuche und bekannte Etymologien zwischen dem "
        "Kassitischen, Hurritischen (Nuzi-Archiv) und Vedischem Sanskrit. "
        "Grundlage: Mayrhofer 1966, Balkan 1954, Cassin & Glassner 1977."
    )

    # ── Corpus overview ────────────────────────────────────────────────────────
    st.subheader("Verfügbare Korpora")
    corp_rows = []
    for c in D["all_corpora"]:
        start = f"{abs(c['start'])} BCE" if c["start"] < 0 else str(c["start"])
        end   = f"{abs(c['end'])} BCE"   if c["end"]   < 0 else str(c["end"])
        corp_rows.append({
            "Korpus":    c["name"],
            "Sprache":   c["lang"],
            "Periode":   f"{start} – {end}",
            "Region":    c["region"],
            "Namen":     c["count"],
        })
    st.dataframe(
        pd.DataFrame(corp_rows),
        use_container_width=True,
        hide_index=True,
        column_config={"Namen": st.column_config.NumberColumn(width="small")},
    )

    st.divider()

    # ── Known scholarly cognates ───────────────────────────────────────────────
    st.subheader("Bekannte Kognaten (Wissenschaftlicher Konsens)")
    st.caption(
        "Die Götternamen des kassitischen Pantheons zeigen starke Übereinstimmungen "
        "mit vedisch-indoarischen Gottheiten — ein zentrales Argument für den "
        "Kassite-Arya-Kontakt (Balkan 1954; Mayrhofer 1966)."
    )

    if D["known_cognates"]:
        conf_order = {"high": 0, "medium": 1, "low": 2}
        cog_df = pd.DataFrame(D["known_cognates"]).sort_values(
            "confidence", key=lambda s: s.map(conf_order)
        )
        conf_colors = {"high": "🟢", "medium": "🟡", "low": "🔴"}
        cog_df["Konfidenz"] = cog_df["confidence"].map(
            lambda c: f"{conf_colors.get(c, '⚪')} {c}"
        )
        cog_df = cog_df.rename(columns={
            "form":    "Kassitisch",
            "cognate": "Kognat",
            "lang":    "Sprache",
            "meaning": "Bedeutung",
            "ref":     "Quelle",
        })
        st.dataframe(
            cog_df[["Kassitisch", "Kognat", "Sprache", "Bedeutung", "Konfidenz", "Quelle"]],
            use_container_width=True,
            hide_index=True,
        )

        # Visualise cognate similarity scores
        from src.phonetic_analysis import phonetic_distance
        cog_vis = cog_df.drop_duplicates(subset=["Kassitisch", "Kognat"]).copy()
        cog_vis["Ähnlichkeit"] = cog_vis.apply(
            lambda r: round(1 - phonetic_distance(r["Kassitisch"], r["Kognat"]), 3), axis=1
        )
        cog_vis["Paar"] = cog_vis["Kassitisch"] + " ~ " + cog_vis["Kognat"]
        fig_cog = px.bar(
            cog_vis.sort_values("Ähnlichkeit", ascending=False),
            x="Ähnlichkeit", y="Paar", orientation="h",
            color="Sprache",
            color_discrete_map={
                "Vedisches Sanskrit": BLUE,
                "Sanskrit": GREEN,
                "Hurritisch": TERRA,
            },
            title="Phonetische Ähnlichkeit bekannter Kognaten",
            height=420,
        )
        fig_cog.update_layout(yaxis={"autorange": "reversed"}, margin=dict(t=40, b=0))
        fig_cog.add_vline(x=0.6, line_dash="dot", line_color="gray",
                          annotation_text="Schwelle 0.6")
        st.plotly_chart(fig_cog, use_container_width=True)
    else:
        st.info("Noch keine Kognaten in der Datenbank.")

    st.divider()

    # ── Live phonetic search ───────────────────────────────────────────────────
    st.subheader("Phonetische Ähnlichkeitssuche (live)")
    st.caption(
        "Wähle ein Kassitisches Wort und finde die phonetisch ähnlichsten Namen "
        "im Hurritischen und Vedischen Korpus. Basis: gewichtete Edit-Distanz "
        "auf phonologischer Ebene."
    )

    from src.phonetic_analysis import (
        load_corpus_names, find_cognate_candidates,
    )

    col_q1, col_q2 = st.columns([2, 1])
    with col_q1:
        query_name = st.text_input(
            "Kassitischer Name / Element:", "Indaš", key="cog_query"
        )
    with col_q2:
        cog_threshold = st.slider("Max. Distanz", 0.1, 0.8, 0.5, 0.05, key="cog_thresh")
        target_corpus = st.selectbox(
            "Vergleichskorpus:",
            ["Hurrian Personal Names (Nuzi)", "Vedic Sanskrit Personal Names", "Beide"],
            key="cog_target",
        )

    if query_name:
        target_corpora = (
            ["Hurrian Personal Names (Nuzi)", "Vedic Sanskrit Personal Names"]
            if target_corpus == "Beide"
            else [target_corpus]
        )

        all_candidates = []
        for corp in target_corpora:
            target_names = load_corpus_names(DB_PATH, corp)
            from src.phonetic_analysis import find_cognate_candidates as _fcc, phonetic_distance as _pd
            cands = []
            for (nb, lb) in target_names:
                d  = _pd(query_name, nb)
                sd = _pd(
                    "".join(c for c in query_name.lower() if c not in "aeiouāīūêâîûàèìò"),
                    "".join(c for c in nb.lower()    if c not in "aeiouāīūêâîûàèìò"),
                )
                sc = 0.6 * d + 0.4 * sd
                if sc <= cog_threshold:
                    cands.append({
                        "Korpus":       corp.split()[0],
                        "Name":         nb,
                        "Phonet. Dist.": round(d, 3),
                        "Skel. Dist.":  round(sd, 3),
                        "Ähnlichkeit":  round(1 - sc, 3),
                    })
            all_candidates.extend(cands)

        if all_candidates:
            res_df = pd.DataFrame(all_candidates).sort_values("Ähnlichkeit", ascending=False)
            st.caption(f"**{len(res_df)}** Kandidaten für `{query_name}` (Schwelle ≤ {cog_threshold})")

            col_r1, col_r2 = st.columns([2, 1])
            with col_r1:
                fig_res = px.bar(
                    res_df.head(20), x="Ähnlichkeit", y="Name", orientation="h",
                    color="Korpus",
                    color_discrete_map={"Hurrian": TERRA, "Vedic": BLUE},
                    title=f"Top Ähnlichkeiten zu »{query_name}«",
                    height=max(300, len(res_df.head(20)) * 28),
                )
                fig_res.update_layout(yaxis={"autorange": "reversed"}, margin=dict(t=40, b=0))
                st.plotly_chart(fig_res, use_container_width=True)
            with col_r2:
                st.dataframe(res_df.head(20), use_container_width=True, hide_index=True)
        else:
            st.info(f"Keine Kandidaten für `{query_name}` mit Distanz ≤ {cog_threshold}.")

    st.divider()

    # ── Batch scan: top cross-corpus pairs ─────────────────────────────────────
    st.subheader("Top Kassite-Hurrian Ähnlichkeiten (Batch-Scan)")
    st.caption("Die 30 ähnlichsten Namenspaare zwischen kassitischem und hurritischem Korpus.")

    @st.cache_data(show_spinner="Berechne Distanzen …")
    def _get_top_kh_pairs(db_path: str, _mtime: float, n: int = 30):
        from src.phonetic_analysis import load_corpus_names, find_cognate_candidates
        kas = load_corpus_names(db_path, "Kassite Personal Names")
        hur = load_corpus_names(db_path, "Hurrian Personal Names (Nuzi)")
        cands = find_cognate_candidates(kas, hur, threshold=0.5)
        return [
            {
                "Kassitisch": c.name_a,
                "Hurritisch": c.name_b,
                "Ähnlichkeit": round(c.similarity, 3),
                "Phonet. Dist.": round(c.phonetic_dist, 3),
                "Skel. Dist.": round(c.skeleton_dist, 3),
            }
            for c in cands[:n]
        ]

    import os as _os
    _mtime = _os.path.getmtime(DB_PATH)
    kh_df = pd.DataFrame(_get_top_kh_pairs(DB_PATH, _mtime))
    if not kh_df.empty:
        col_a, col_b = st.columns([3, 1])
        with col_a:
            fig_kh = px.scatter(
                kh_df, x="Phonet. Dist.", y="Skel. Dist.",
                text="Kassitisch",
                hover_data=["Hurritisch", "Ähnlichkeit"],
                color="Ähnlichkeit",
                color_continuous_scale="YlOrRd_r",
                title="Kassite ↔ Hurrian: Phonetische vs. Skelett-Distanz",
                height=420,
            )
            fig_kh.update_traces(textposition="top center", textfont_size=9)
            fig_kh.update_layout(margin=dict(t=40, b=0))
            st.plotly_chart(fig_kh, use_container_width=True)
        with col_b:
            st.dataframe(kh_df[["Kassitisch", "Hurritisch", "Ähnlichkeit"]],
                         use_container_width=True, hide_index=True, height=420)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: Namens-Browser
# ══════════════════════════════════════════════════════════════════════════════

elif section == "Namens-Browser":
    st.title("Namens-Browser")

    df_all = pd.DataFrame(D["browser_rows"])

    # ── Filter bar ────────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        search = st.text_input("Name suchen:", "", key="nb_search")
    with fc2:
        only_theophoric = st.checkbox("Nur theophore Namen")
    with fc3:
        only_meaning = st.checkbox("Nur Namen mit Bedeutung")
    with fc4:
        struct_filter = st.text_input("CV-Struktur enthält:", "", key="nb_struct")

    df_f = df_all.copy()
    if search:
        df_f = df_f[df_f["Transkription"].str.contains(search, case=False, na=False)]
    if only_theophoric:
        df_f = df_f[df_f["Gottheiten"].str.len() > 0]
    if only_meaning:
        df_f = df_f[df_f["Bedeutung"].str.len() > 0]
    if struct_filter:
        df_f = df_f[df_f["Struktur"].str.contains(struct_filter, case=False, na=False)]

    st.caption(f"**{len(df_f)}** Namen angezeigt (von {D['total']} gesamt)")

    st.dataframe(
        df_f,
        use_container_width=True,
        hide_index=True,
        height=520,
        column_config={
            "Länge":  st.column_config.NumberColumn(width="small"),
            "Silben": st.column_config.NumberColumn(width="small"),
        },
    )

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        csv = df_f.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇  CSV herunterladen", csv, "kassite_names_filtered.csv", "text/csv"
        )
    with col_dl2:
        json_bytes = df_f.to_json(orient="records", force_ascii=False).encode("utf-8")
        st.download_button(
            "⬇  JSON herunterladen", json_bytes,
            "kassite_names_filtered.json", "application/json"
        )
