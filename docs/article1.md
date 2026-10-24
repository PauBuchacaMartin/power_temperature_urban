# Article 1: la resposta energètica de Barcelona

*Estat a 23/10/2026. Font: `10_estat_actual_i_decisions.md` del projecte de tesi i notebook v0.11.*

## Pregunta

Com respon el consum elèctric de Barcelona a la calor, per què aquesta resposta creix cada any
i sobretot de nit, i quina part del creixement ve de tenir més aparells d'aire condicionat
(marge extensiu) i quina d'usar-los més (marge intensiu)?

## Dades

- Consum elèctric diari i per franges de 6 h, per codi postal i sector (Datadis via Open Data BCN), 2021–2025.
- Temperatura ERA5 (Open-Meteo), diària i horària, amb l'alçada de la capa límit; estacions del Meteocat.
- Certificats energètics de la Generalitat (registre `j6ii-t3w2` i instal·lacions `cmnw-duhh`) per als equips de fred.

## Resultats que aguanten (v0.11)

| Resultat | Valor | Notes |
|---|---|---|
| Creixement de χ⁰ de la ciutat, 2021→2024 | +2,78 ± 0,35 %/K | Errors per clústers de setmana |
| Factor de resposta λ (2021 = 1) | 1,00 · 1,25 · 1,56 · 1,83 · 1,76 (2021–2025) | Model de llindars: forma comuna per sobre de 24 °C (p = 0,17) |
| Creixement de la resposta a la calor nocturna (franja 0–6 h) | +5,7 ± 0,8 | En unitats del model del v0.11 |
| Creixement de la resposta a la calor diürna | +0,4 ± 1,1 | No significatiu |
| Creixement per franja, només règim A | vespre 4,2 · nit 3,2 · tarda 2,6 · matí 2,0 | Control del canvi de règim de franges |
| Capa límit (mediana ERA5, estius) | ~117 m de nit, ~696 m de dia | La calor nocturna es concentra en una capa ~6 vegades més prima |
| Pisos anteriors a 1980 amb fred declarat | 45,6 → 49,9 % (def. A); 28,8 → 35,2 % (def. B), 2021→2024 | Pilot de certificats |
| Part del creixement de λ explicada per més aparells | 13–42 % (escala log) | Model mínim χ ∝ aparells × ús |
| Validació creuada de la def. B | 31,0 % (certificats, 2020) vs 30,8 % (anuncis de Habitaclia, març 2020) | Rojas-Quiroz i Marmolejo 2026, *Urban Science* |

Proves superades (secció 20h del v0.11): la tendència no l'expliquen l'autoconsum fotovoltaic,
el vehicle elèctric, el preu ni l'any de la COVID. Només falla la prova amb juny i setembre sols.

## Alertes de dades

1. **Recodificació de codis postals (juliol 2025):** ~17 % del consum residencial i ~19 % del de serveis
   canvien de codi postal; suma zero a escala de ciutat (08037 multiplica per 15). Per això la sèrie
   de ciutat inclou tots els codis i les anàlisis per codi postal fan servir 2021–2024.
2. **Canvi de règim de les franges horàries (des del 2024):** la fracció de consum de 18–24 h cau
   respecte de la climatologia 2021–2023. Es controla amb `alerts.band_regime` (llindar −2,5 punts).
3. 08007, 08009 i 08011 desapareixen de les dades a partir del juny 2025: pendent d'investigar.

## Retirat o no utilitzable

- La correlació de 23f amb la calor antropogènica (ρ = 0,53) era un artefacte de les dades del 2025 (ρ = −0,11 amb 2023–24).
- El desplaçament de l'hora punta de 23d (18 min/K) era sobretot un artefacte del canvi de règim; amb control, 11 min/K, sense explicar.

## Pendent per tancar l'article

- [x] Branca de fred (graus-dia de calefacció) per hivern i simetria de la V: `seasonal.py`, notebook v0.12 secció 24 (pendent d'executar amb dades reals).
- [ ] Preu estimat conjuntament amb la calor i el fred.
- [x] Test d'histèresi (test de fronts amb memòria flexible): `seasonal.py`, notebook v0.12 secció 25 (pendent d'executar amb dades reals).
- [ ] Intervals de confiança per bootstrap per a la part extensiva.
- [ ] Contrast de l'equipament amb una enquesta independent de llars.
- [ ] Proposar l'estructura a l'AiEM (coautors).

## Referències de context (al radar de la tesi)

Auffhammer i Mansur 2014; Davis i Gertler 2015; Wenz, Levermann i Auffhammer 2017;
Moral-Carcedo i Vicéns-Otero 2005; Salvati, Coch i Cecere 2017; De Cian, Falchetta et al. 2025 (*JEEM*).

## v0.12 (24/10/2026): fred i histèresi

**Branca de fred.** Model d'hivern (novembre-març) amb graus-dia de calefacció i efectes fixos d'hivern,
setmana ISO (absorbeix el cicle de la llum), dia, festiu i Nadal. $\chi^0_h$ per hivern (2021-22 a 2024-25),
quocient $R=\chi_h/\chi_c$ i set proves de robustesa (llindar, Nadal, desembre-febrer, efectes hivern × mes,
memòria de 6 dies, CP sense salts). Lectura: si $\chi_h$ creix, electrificació de la calefacció; si no,
la tendència d'estiu és específica de la refrigeració.

**Test de fronts (histèresi).** $\gamma$ = resposta extra els dies que la temperatura baixa, amb una
memòria additiva flexible (frontisses per retard). Calibratge sintètic (40 simulacions): falsos positius
0 % (memòria lineal) i 3 % (resposta corbada); potència 100 % (histèresi d'1 K), 62 % (2 K), 10 % (3 K).
La versió amb memòria lineal dona falsos positius si la resposta és corbada: no s'ha de fer servir.
