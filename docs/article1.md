# Article 1 · resultats de la v0.14 (resposta a la revisió externa del 24/10/2026)

Notebook: `notebooks/resposta_calor_bcn_v14.ipynb` (15 seccions). Arxius anteriors: v0.13 (versió depurada) i v0.12 (exploratòria).
**Executat a Colab el 25/10/2026** (Open Data BCN · Datadis fins al 30/11/2025, ERA5, estacions del Meteocat). Idèntic a l'execució local del 24/10, més les proves d'humitat i de preu.
**Escala:** tota l'anàlisi és a escala de ciutat (suma dels 42 CP). El títol no pot dir «postcode-level».

## Què ha canviat respecte de la v0.13 (i per què canvien les xifres)

1. **Regla de qualitat per any:** un estiu entra si ≥ 90 % dels seus CDD cauen en dies útils. El 2021-2024 hi entra (0,99-1,00) i el 2025 no (0,79): la separació és clara. La regla és *post hoc* (escrita després de veure la χ de la v0.13), però només fa servir mètriques de dades, s'aplica a tots els anys i queda congelada per al 2026. **Per això totes les xifres principals són ara del 2021-2024.** Els χ⁰ per any canvien una mica (4,32 → 4,66 el 2021) perquè els efectes fixos de setmana ja no s'estimen amb el 2025.
2. **Una sola mètrica de creixement:** Q = χ⁰₂₀₂₄/χ⁰₂₀₂₁, amb *bootstrap* per setmanes que refà la tria de $T_c$.
3. **R4 amb el test de la diferència**, fotovoltaica, tarifa 2.0TD, graella de llindars i regla de qualitat a les franges.
4. **Temperatura de les estacions del Meteocat** com a prova de robustesa (IDW de X4, X8 i WU al centre dels CP).
5. **Predicció registrada de l'estiu 2026** (`docs/prediccio_2026.md`).

## Afirmacions de l'article (estat a la v0.14)

| # | Afirmació | Estat |
|---|---|---|
| R1 | La ciutat respon amb χ⁰ = 6,4 %/K [5,6-7,1], amb memòria d'1-2 dies (57 % el mateix dia) | **Sòlid.** Els dies d'onada són fora de l'ajust: residu +2,0 % en 8 dies (dispersió ±3,9 %), sense saturació. La comprovació per correlacions (6,52) és només numèrica. Els χ(k) individuals no s'interpreten |
| R2 | **La resposta del 2024 és més gran que la del 2021:** Q = **1,61 [1,34-1,87]** (χ⁰ 4,66 → 7,48 %/K) | **Sòlid per al signe; la magnitud, amb l'interval.** 17 de 18 proves amb z > 2, incloses les estacions del Meteocat (+3,26 ± 0,32 amb el seu $T_c$ = 22 °C), el 2022→2024 (+2,02 ± 0,29) i amb el 2025 (+2,88). Només juny + setembre no creix. **No es pot dir «creix a un ritme»:** amb quatre estius no es distingeix una tendència d'un salt |
| R3 | Les corbes són **compatibles amb** la mateixa forma × un factor (λ₂₀₂₄ = 1,76 [1,46-2,29]) | Compatible: test pre-especificat p = 0,05 (< 24 °C) i 0,06 (≥ 24 °C); tota la corba p = 0,16. Amb el 2025, la part < 24 °C falla (p = 0,00). **Fragilitat:** cada corba s'ancora en només 9-14 dies ≤ 20 °C per estiu (a 20 de 400 rèpliques del *bootstrap*, un estiu se'n queda sense). No demostra que el llindar de confort no s'hagi mogut |
| R4 | A 0-6 h, la resposta a la calor de nit creix més que la de dia | **Feble i condicionat.** D = Δnit − Δdia = +4,05 ± 1,47 (z = 2,8). Aguanta la radiació (z = 2,2), els laborables (z = 2,6) i els caps de setmana (z = 2,6), i 18 de 25 llindars. **Però:** (a) només 1 de 4 franges té D amb z > 2 (el «4 de 4» de la v0.13 era un recompte de significacions); (b) **del 2021 al 2023 no hi ha cap diferència** (D = −0,27 ± 1,53): tot ve del 2024, que **no passa la regla de qualitat a les franges** (80 % dels CDD en dies del règim A; 65 dies útils, contra 109-116 els altres anys) |
| R5 | Nivell de la resposta elèctrica al fred: χ_h = 3,69 ± 0,21 %/K per sota de 15,5 °C | Sòlid el nivell. **Ni el canvi de χ_h ni la pèrdua de simetria són robustos:** amb la finestra pre-especificada R = 0,60 ± 0,08 (2021) → 0,57 ± 0,05 (2024). La caiguda de la v0.13 venia dels χ_c amb el 2025 i de les finestres *post hoc* |
| R6 | No hi ha histèresi estreta | Sòlid: γ = −0,003 ± 0,123, màx |z| = 0,3 |
| — | Component elèctric de Q_F: ∂Q_F,el/∂T = 0,23 → 0,40 W m⁻² K⁻¹ (2021 → 2024) | Mesurat; només electricitat (sense gas, trànsit ni metabolisme). G no verificat |

### Què responen les proves de R4 a les dues explicacions alternatives del revisor

- **Autoconsum fotovoltaic:** si les plaques retallessin la resposta de dia, el control de radiació (i radiació × any) l'hauria de fer créixer i reduir D. D passa de 4,05 a 3,63 (z = 2,2): **no l'explica**, però el control és indirecte (no tenim l'autoconsum per CP).
- **Tarifa 2.0TD** (des de l'1 de juny de 2021; laborables amb vall de 0 a 8 h, caps de setmana i festius nacionals tot vall): si el creixement nocturn fos un desplaçament per preu, hauria de ser als laborables. Als caps de setmana D és igual o més gran (+9,2 ± 3,5). **No ho sembla**, amb poca potència. *Nota:* els festius de la prova inclouen els de Catalunya, no només els nacionals.

## Taula de resultats (sortida automàtica de la secció 15, Colab 25/10)

| resultat | magnitud | valor | nota |
|:--|:--|:--|:--|
| Q | Regla de qualitat: estius que entren | [2021, 2022, 2023, 2024] | fora: [2025]; franges: [2021, 2022, 2023] |
| R1 | Tc (°C) | 20.0 | bootstrap: 19.0–21.0 |
| R1 | χ⁰ tots els estius (%/K) | 6.41 [5.55–7.06] | IC bootstrap amb Tc a dins |
| R1 | Residu dels dies d'onada (fora de l'ajust) (%) | +2.0 | 8 dies; dispersió normal ±3.9 % |
| R2 | MÈTRICA PRINCIPAL Q = χ⁰2024/χ⁰2021 | 1.61 [1.34–1.87] | bootstrap per setmanes, Tc a dins |
| R2 | χ⁰ 2021 → 2024 (%/K) | 4.66 → 7.48 | diferència +2.82 [+1.72–+3.53] |
| R2 | χ⁰ 2025 (fora de la regla) | 7.14 ± 0.40 | l'únic número del 2025 |
| R2 | Canvi, tots els sectors (%/K) | +2.36 ± 0.39 | prova de composició |
| R2 | Proves de robustesa amb z > 2 | 17 de 18 | juny + setembre: no s'espera |
| R2 | Resposta absoluta total 2021 → 2024 (MWh/dia/K) | 565 → 972 | |
| R3 | Pre-especificat: < 24 °C iguals (p) / forma × factor ≥ 24 °C (p) | 0.05 / 0.06 | amb 2025: 0.00 / 0.07 |
| R3 | Forma × factor a tota la corba 21-28 °C (p) | 0.16 | post hoc · λ2024 = 1.76 [1.46–2.29] |
| R4 | 0-6 h: resposta a la calor de nit / de dia (%/K) | 5.22 / 1.96 | règim A, 2021-2024 |
| R4 | 0-6 h: D = Δnit − Δdia 2021→2024 (%/K) | +4.05 ± 1.47 (z = 2.8) | covariància completa |
| R4 | 0-6 h: D fins al 2023 (anys que passen la regla) | −0.27 ± 1.53 (z = −0.2) | sense el 2024 |
| R4 | 0-6 h: D amb radiació (FV) | +3.63 ± 1.63 (z = 2.2) | |
| R4 | 0-6 h: D laborables / caps de setmana | +4.05 (z = 2.6) / +9.21 (z = 2.6) | tarifa 2.0TD |
| R4 | Graella de llindars: combinacions amb z > 2 | 18 de 25 | |
| R4 | Franges amb D z > 2 | 1 de 4 | règim A |
| R5 | χ_h nivell (%/K), Th | 3.69 ± 0.21, 15.5 °C | nov.-març |
| R5 | Canvi de χ_h (pre-especificat; annex) | +1.43 / +0.06 / −0.29 | no robust |
| R6 | γ histèresi (base) | −0.003 ± 0.123 | màx \|z\| = 0.3 |
| — | ∂Q_F,el/∂T total 2024 (W m⁻² K⁻¹) | 0.40 | només elèctric; G no verificat |
| P | Predicció 2026 registrada: H1 / H0 (χ⁰, %/K) | 9.09 / 7.48 | docs/prediccio_2026.md |

Robustesa de R2 (canvi de χ⁰ 2021→2024, %/K): base +2,82 ± 0,33 · 2022→2024 +2,02 ± 0,29 · pendent × 3 +2,72 ± 0,29 · tots els sectors +2,36 ± 0,39 · $T_c$ 18/19/21/22/23 °C: +2,20 / +2,33 / +3,59 / +4,51 / +5,75 · estacions +3,26 ± 0,32 ($T_c$ 22, triat) i +2,56 ± 0,37 ($T_c$ 20) · amb onades +2,80 · quadràtic +2,92 · amb el 2025 +2,88 · juny i setembre −0,06 ± 0,52 · juliol i agost +2,59 ± 0,92. Punt de rosada +2,52 ± 0,29 · preu PVPC +2,85 ± 0,35 (Colab).

## Respostes a la revisió (G1-G4, I1-I7)

| Punt | Què s'ha fet | On |
|---|---|---|
| G1a test de la diferència | D amb la covariància completa (funció `day_night_difference`) | secció 10 |
| G1b FV i tarifa | Radiació i radiació × any; laborables contra caps de setmana i festius | secció 10 |
| G1c règim A i retards | Dies del règim A per estiu i definició dels retards al text | secció 10 |
| G2 magnitud | Q amb *bootstrap* per setmanes i $T_c$ a dins; λ amb el seu *bootstrap* | secció 8 |
| G2 «+67 % vs +84 %» | Una sola xifra: **+61 % [34-87 %]** (Q). λ (+76 %) és coherent dins dels intervals i només fa de prova de forma | secció 8 |
| G3 2025 | Regla escrita per any, el mateix període per a tots els resultats, el 2025 a les figures amb un altre estil, un sol número (7,14) | seccions 5 i 8 |
| G4 tendència | Redacció «2024 > 2021»; predicció registrada | secció 14, `docs/prediccio_2026.md` |
| I1 | Onades fora de l'ajust; correlacions com a comprovació numèrica; no interpretar χ(k) | secció 7 |
| I2 | Marge extensiu fora de l'article 1 (proposta: P2) | — |
| I3 | Novetat: dins d'una ciutat, any a any, amb consum mesurat, separació dia/nit (Colelli et al. 2023; Auffhammer i Mansur 2014; Davis i Gertler 2015) | per al redactor |
| I4 | «Escala de ciutat» al notebook; títol sense «postcode-level» | capçalera |
| I5 | «Component elèctric de Q_F» | secció 13 |
| I6 | Totes les taules en CSV a `dades_per_claude_v14.zip` | secció 15 |
| I7 | «Compatible amb» el model de llindars | secció 9 |
| Colors | Rampa de blaus amb més contrast de lluminositat (0,78 / 0,58 / 0,28 / 0,16 per al 2021-2024) | `figstyle.py` |

## Decisions post hoc (declarades)

- **Regla de qualitat per any (24/10/2026):** escrita després de veure la χ de la v0.13; només fa servir mètriques de dades i queda congelada per al 2026.
- **Q com a mètrica principal en lloc de λ:** proposta del tècnic (24/10, λ és fràgil al *bootstrap*), **decidida per Pau el 25/10**.
- Hivern desembre-febrer i model de llindars a tota la corba: com a la v0.13 (annex o *post hoc*).

## Figures (`docs/figures_v14/`)

| Fitxer | Contingut |
|---|---|
| `fig1_response_function.png` | a) χ(k); b) dies d'onada (fora de l'ajust) |
| `fig2_growth_bootstrap_robustness.png` | a) χ⁰ per estiu, amb el 2025 a part; b) distribució *bootstrap* de Q; c) robustesa |
| `fig3_curves_threshold_model.png` | a) corbes sense forma imposada (2025 a part); b) λ amb l'error de l'ajust i el *bootstrap* |
| `fig4_day_night.png` | a) resposta de cada franja; b) canvis i diferència nit − dia; c) graella de llindars (z de D) |
| `fig5_cold_symmetry.png` | a) χ_h per hivern (nov.-març); b) R |
| `auditoria_sectors.png`, `tria_tc.png` | auditoria de la font; tria de $T_c$ |

## Pendent

- [x] v0.14 executada a Colab (25/10): coincideix amb l'execució local.
- [x] Decisió de Pau (25/10): **Q** com a mètrica principal; λ només com a prova de forma.
- [x] Decisió de Pau (25/10): R4 es presenta com a **indici**.
- [x] Decisió de Pau (25/10): «la V es torna menys simètrica» **surt de l'article**.
- [ ] Validació externa del total anual (Ajuntament / ICAEN) i correu a Open Data BCN.
- [ ] Dades d'autoconsum per CP (prova directa de la FV).

## Nota sobre les corbes del 2021

A l'estiu 2021 (ERA5) cap dia té una mitjana dels 3 últims dies ≥ 28 °C (màxim 27,2 °C), i només 2 dies tenen la mitjana diària > 27 °C (19 i 22/7/2021, no consecutius). Per això el 2021 no té punt a la classe ≥ 28 °C de la figura 3. És una propietat de les dades, no un error: el 2021 va ser l'estiu més fresc de la sèrie segons ERA5 (mitjana de juny a setembre de 23,4 °C). El model de llindars hi dona pes zero a la casella buida. ERA5 és una mitjana en una cel·la d'uns 25 km i a l'estiu surt ~1,3 °C per sota de les estacions urbanes (X4 Raval).
