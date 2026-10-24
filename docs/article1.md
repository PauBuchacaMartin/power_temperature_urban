# Article 1 · resultats de la versió depurada (notebook v0.13, executat a Colab el 24/10/2026)

Notebook: `notebooks/resposta_calor_bcn_v13.ipynb` (13 seccions, només el que és publicable).
Arxiu complet amb totes les anàlisis exploratòries: `notebooks/resposta_calor_bcn_v12.ipynb`.
Executat a Colab amb les dades d'Open Data BCN · Datadis fins al 30/11/2025 i ERA5; reproduït exactament en local. Escala de ciutat (42 CP).

## Afirmacions de l'article

| # | Afirmació | Estat |
|---|---|---|
| R1 | La ciutat respon a la calor amb ~6 % de consum residencial per grau, amb memòria d'1-2 dies; la resposta lineal prediu les onades | Sòlid (regressió = correlacions). Residu d'onada +3 % amb 11 dies: sense saturació; possible amplificació petita, no concloent |
| R2 | La resposta creix de 4,3 a 7,2 %/K entre el 2021 i el 2024 | Sòlid: 13 de 14 proves amb z > 2 (a Colab, amb humitat ≈ +2,5 i preu ≈ +2,9 %/K, valors llegits de la figura 2; els exactes surten a `r2_robustesa.csv` des de la v0.13.1); també amb tots els sectors sumats (composició) i en absolut (535 → 931 MWh/dia per K, tots els sectors). Només juny + setembre no creix: el creixement és als mesos calents |
| R3 | El creixement és un canvi d'amplitud amb la mateixa forma de corba (model de llindars), λ = 1,00 / 1,27 / 1,54 / 1,84 / 1,83 | Test de tota la corba p = 0,18 (*post hoc*). El test pre-especificat falla a la part < 24 °C (p = 0,00, per culpa del 2025) i passa a la part ≥ 24 °C (p = 0,07) |
| R4 | La resposta que creix és la de la calor de nit, a les quatre franges horàries; la de la calor de dia no creix a cap | Sòlid amb només dies del règim A (alerta 2): 0-6 h nit +4,3 ± 0,9 vs dia +0,3 ± 0,8 %/K |
| R5 | Fred: resposta estable (3,7 ± 0,2 %/K per sota de 15,5 °C); la V es fa menys simètrica (R = χ_h/χ_c de ~0,7 a ~0,45-0,6) | El canvi de χ_h no és robust (+1,4 / +0,1 / −0,3 segons la versió); la caiguda de R sí que es veu a les tres versions |
| R6 | No hi ha histèresi estreta (test de fronts) | Sòlid: |z| < 0,8 a totes les versions |
| — | Sensibilitat de la calor antropogènica de tota la ciutat: ∂Q_F/∂T = 0,22 → 0,38 W m⁻² K⁻¹ (2021 → 2024) | Mesurat (àrea dels CP reconstruïda); G = 0,008-0,04 només com a ordre de magnitud (h_eff no verificat) |

## Taula de resultats (sortida automàtica de la secció 13)

| resultat   | magnitud                                                         | valor                       | nota                                            |
|:-----------|:-----------------------------------------------------------------|:----------------------------|:------------------------------------------------|
| R1         | Tc (°C)                                                          | 20.0                        | nan                                             |
| R1         | χ⁰ tots els estius (%/K)                                         | 6.32 ± 0.29                 | χ⁰ per correlacions 6.37                        |
| R1         | Residu d'onada, χ de cada estiu (%)                              | +3.0                        | 11 dies; dispersió normal ±4.1 %; poca potència |
| R2         | χ⁰ 2021 → 2024 (%/K)                                             | 4.32 → 7.20                 | nan                                             |
| R2         | Creixement 2021→2024 (%/K)                                       | +2.88 ± 0.35                | z = 8.2                                         |
| R2         | Creixement, tots els sectors (%/K)                               | +2.29 ± 0.41                | prova de composició                             |
| R2         | Resposta absoluta total 2021 → 2024 (MWh/dia/K)                  | 535 → 931                   | nan                                             |
| R2         | Proves de robustesa amb z > 2                                    | 11 de 12                    | juny + setembre: no s'espera                    |
| R3         | Pre-especificat: iguals < 24 °C (p) / forma × factor ≥ 24 °C (p) | 0.00 / 0.07                 | la part < 24 °C falla (2025)                    |
| R3         | Forma × factor a tota la corba 21-28 °C (p)                      | 0.18                        | post hoc · λ2024 = 1.84 ± 0.04                  |
| R4         | 0-6 h: resposta a la calor de nit / de dia (%/K)                 | 5.22 / 1.96                 | règim A                                         |
| R4         | 0-6 h: canvi de la resposta a la nit / al dia                    | +4.31 ± 0.88 / +0.27 ± 0.82 | nan                                             |
| R4         | Franges amb canvi a la nit z > 2 / al dia z > 2                  | 4 / 0 de 4                  | règim A                                         |
| R5         | χ_h nivell (%/K), Th                                             | 3.69 ± 0.21, 15.5 °C        | nan                                             |
| R5         | Canvi de χ_h (3 versions)                                        | +1.43 / +0.06 / -0.29       | robust només si les tres coincideixen           |
| R6         | γ histèresi (base)                                               | -0.076 ± 0.133              | màx |z| = 0.8                                   |
| —          | ∂Q_F/∂T total 2024 (W m⁻² K⁻¹)                                   | 0.38                        | G no verificat                                  |

## Registre d'alertes de la font (secció 4)

|   alerta | què                                                | abast                   | tractament                                                                                |
|---------:|:---------------------------------------------------|:------------------------|:------------------------------------------------------------------------------------------|
|        1 | Recodificació de CP (tardor 2023, juliol 2025)     | per CP; no a la ciutat  | tot a escala de ciutat; creixement 2021→2024; el 2025 només com a robustesa               |
|        2 | Canvi del repartiment entre franges (2024-25)      | 494 dies                | R4 només amb dies del règim A (principal) i amb variable de règim (secundari); sense 2025 |
|        3 | Forat de cobertura dels serveis (gen.-mar. 2023)   | 158 dies de serveis     | exclòs pel detector de blocs; també el del residencial de principis de gener              |
|        4 | Reclassificacions de sector (ago. 2023; set. 2025) | serveis i indústria     | prova de composició amb el total de tots els sectors                                      |
|        5 | Dies dolents i bloc d'agost del 2025               | 25 dies del residencial | detector condicionat a la temperatura; els dies extrems mai s'exclouen                    |
|        6 | Unitats: el portal diu MWh, són kWh                | —                       | comprovació de l'ordre de magnitud (secció 3)                                             |
|        7 | Sense validació externa del total                  | —                       | limitació declarada; demanar el total anual a l'Ajuntament o l'ICAEN                      |

## Figures (`docs/figures_v13/`)

| Fitxer | Contingut |
|---|---|
| `fig1_response_function.png` | a) Funció de resposta χ(k); b) dies d'onada predits per la resposta lineal |
| `fig2_trend_robustness.png` | a) χ⁰ per estiu (residencial i tots els sectors); b) creixement 2021→2024 a cada prova de robustesa |
| `fig3_curves_threshold_model.png` | a) Corba de resposta de cada estiu sense forma imposada; b) amplitud λ de cada estiu |
| `fig4_day_night.png` | a) Resposta de cada franja a la calor de dia i de nit; b) canvi 2021→2024 |
| `fig5_cold_symmetry.png` | a) Resposta al fred per hivern (tres versions); b) simetria de la V |
| `auditoria_sectors.png` | Consum diari de tota la ciutat per sector: forats i reclassificacions de la font |

## Decisions post hoc (declarades)

- Hivern desembre-febrer (24/10/2026), triat després de veure que novembre i març dominaven el canvi de χ_h.
- Model de llindars a tota la corba (24/10/2026), afegit després de veure que la part < 24 °C del test pre-especificat fallava.
- Comparacions per CP dins de cada any (14/10/2026): fora d'aquest notebook.

## Pendent per enviar l'article

- [ ] Validació externa del total anual de consum (Ajuntament / ICAEN) i correu a Open Data BCN amb les incidències.
- [x] v0.13 executada a Colab (24/10): resultats idèntics a l'execució local; humitat i preu no expliquen el creixement.
- [ ] Tornar a executar la v0.13.1 per tenir totes les taules en CSV (números exactes per a l'article).
- [ ] Penetració d'aire condicionat (sèrie temporal independent) per separar aparells i ús (pilot CEE: 13-42 %).
- [ ] Estructura de l'article amb l'AiEM (coautors).
