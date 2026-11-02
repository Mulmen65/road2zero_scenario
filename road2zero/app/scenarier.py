"""Tre scenarier i samma session för road2zero-scenario.

Indataflikarna från Road2Zero arbetar på ss.scen och widgetnycklar med ss.v. Här pekar ss.scen på det scenario som ändras,
och varje scenario har ett eget nummerområde för ss.v, så att fälten alltid läser om värdena när man byter scenario.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from road2zero import __version__
from road2zero.scenario import fran_json, till_json, tomt

from .common import LOGO, fb, ss

NAMN = ["A", "B", "C"]
FARG = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a"}   # de tre första kategorifärgerna; validerade för alla par
STEG = 1_000_000                                          # nummerområde per scenario för widgetnycklarna
FALL = Path(__file__).resolve().parents[1] / "fall"
SETTYP = "road2zero-scenarier"


def _nytt(n: str) -> dict:
    s = tomt(fb())
    s["projekt"]["namn"] = f"Scenario {n}"
    return s


def init():
    ss["_senare"] = []
    if "scenarier" not in ss:
        ss.scenarier = {n: _nytt(n) for n in NAMN}
        ss.versioner = {n: (i + 1) * STEG for i, n in enumerate(NAMN)}
        ss.aktiv = "A"
    ss.scen = ss.scenarier[ss.aktiv]
    ss.v = ss.versioner[ss.aktiv]


def spara_aktiv():
    """Efter indataflikarna: behåll det ändrade scenariot och dess nyckelversion."""
    ss.scenarier[ss.aktiv] = ss.scen
    ss.versioner[ss.aktiv] = ss.v


def _ny_version(n: str):
    ss.versioner[n] += 1
    for nyckel in [x for x in ss.keys() if str(x).startswith("bas_")]:
        del ss[nyckel]


def _byt():
    ss.aktiv = ss["scenario_val"]
    _ny_version(ss.aktiv)


def satt(n: str, s: dict):
    """Ersätt ett scenario (öppnad fil, kopia eller tomt) och läs om alla fält."""
    ss.scenarier[n] = s
    _ny_version(n)
    if n == ss.aktiv:
        ss.scen = s
        ss.v = ss.versioner[n]


def etikett(n: str) -> str:
    return f"{n} · {ss.scenarier[n]['projekt']['namn']}"


def medtagna() -> list[str]:
    """Scenarier med byggnader; tomma scenarier jämförs inte."""
    return [n for n in NAMN if ss.scenarier[n]["byggnader"]]


def valjare():
    """Väljer vilket scenario som ändras i indataflikarna."""
    st.radio("Scenario som ändras", NAMN, index=NAMN.index(ss.aktiv), horizontal=True, key="scenario_val", on_change=_byt,
             format_func=etikett, help="Indata, emissionsfaktorer och parametrar gäller det valda scenariot. Jämförelseflikarna visar alla tre.")


def markering(n: str, text: str = "") -> str:
    return (f"<span style='display:inline-block;width:12px;height:12px;border-radius:3px;background:{FARG[n]};"
            f"margin-right:8px;vertical-align:-1px'></span><b>{etikett(n)}</b>{text}")


def fardiga_fall() -> dict[str, Path]:
    ut = {}
    for f in sorted(FALL.glob("*.json")):
        try:
            ut[json.loads(f.read_text(encoding="utf-8"))["projekt"]["namn"]] = f
        except Exception:  # noqa: BLE001
            continue
    return ut


def sidopanel(resultat: dict):
    sb = st.sidebar
    sb.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">'
        f'<div style="width:46px;height:46px">{LOGO}</div>'
        f'<div><div style="font-size:20px;font-weight:700;line-height:1.1">Road2Zero scenario</div>'
        f'<div style="font-size:12px;color:#56635E">version {__version__}</div></div></div>', unsafe_allow_html=True)
    sb.caption("Tre scenarier med alla indata, beräknade med Road2Zero och jämförda med varandra.")
    sb.markdown("##### Nettoutsläpp, nivå 1 / 2 / 3")
    for n in NAMN:
        r = resultat.get(n)
        txt = (" · " + " / ".join(f"{r.netto(L)/1000:,.0f}".replace(",", " ") for L in (1, 2, 3)) + " kt") if r else " · inga byggnader"
        sb.markdown(f"<div style='font-size:13px;margin-bottom:4px'>{markering(n, txt)}</div>", unsafe_allow_html=True)

    a = ss.aktiv
    sb.divider()
    sb.markdown(f"##### Scenario {a}")
    p = ss.scenarier[a]["projekt"]
    sb.download_button(f"Spara scenario {a} (JSON)", data=till_json(ss.scenarier[a]).encode("utf-8"),
                       file_name=f"road2zero_{a}_{p['namn']}.json".replace(" ", "_"), mime="application/json", width="stretch")
    fil = sb.file_uploader(f"Öppna indata till scenario {a}", type=["json"], key=f"upp_{a}_{ss.versioner[a]}",
                           help="En sparad fil från Road2Zero eller road2zero-scenario.")
    if fil is not None:
        try:
            satt(a, fran_json(fil.getvalue().decode("utf-8"), fb()))
            st.rerun()
        except Exception as e:  # noqa: BLE001
            sb.error(f"Filen kunde inte läsas: {e}")
    fall = fardiga_fall()
    if fall:
        val = sb.selectbox("Färdigt fall", ["Välj …"] + list(fall), key="fall_val")
        if sb.button(f"Hämta till scenario {a}", width="stretch", disabled=val == "Välj …"):
            satt(a, fran_json(fall[val].read_text(encoding="utf-8"), fb())); st.rerun()
    andra = [n for n in NAMN if n != a]
    fran = sb.selectbox("Kopiera från", andra, key="kopiera_fran", format_func=etikett)
    if sb.button(f"Kopiera till scenario {a}", width="stretch", help=f"Ersätter scenario {a} med en kopia av det valda scenariot"):
        kopia = fran_json(till_json(ss.scenarier[fran]), fb())
        kopia["projekt"]["namn"] = f"{kopia['projekt']['namn']} (kopia)"
        satt(a, kopia); st.rerun()
    if sb.button(f"Töm scenario {a}", width="stretch"):
        satt(a, _nytt(a)); st.rerun()

    sb.divider()
    sb.markdown("##### Alla tre scenarier")
    paket = {"typ": SETTYP, "modellversion": __version__, "aktiv": a, "scenarier": ss.scenarier}
    sb.download_button("Spara alla tre (JSON)", data=json.dumps(paket, ensure_ascii=False, indent=2).encode("utf-8"),
                       file_name="road2zero_scenarier.json", mime="application/json", width="stretch")
    fil = sb.file_uploader("Öppna sparade scenarier", type=["json"], key=f"upp_alla_{sum(ss.versioner.values())}")
    if fil is not None:
        try:
            d = json.loads(fil.getvalue().decode("utf-8"))
            if d.get("typ") != SETTYP:
                raise ValueError("filen innehåller inte tre scenarier; öppna den som indata till ett scenario i stället")
            for n in NAMN:
                if n in d["scenarier"]:
                    satt(n, fran_json(json.dumps(d["scenarier"][n]), fb()))
            st.rerun()
        except Exception as e:  # noqa: BLE001
            sb.error(f"Filen kunde inte läsas: {e}")
