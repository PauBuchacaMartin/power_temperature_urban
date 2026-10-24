# Predicció registrada: resposta a la calor de l'estiu 2026

**Data del registre:** 24/10/2026, abans de descarregar cap dada de consum del 2026.
**Canonada:** commit `4b3189d`, paquet `consum_temperatura` 0.4.0, notebook `resposta_calor_bcn_v14.ipynb`, secció 14.
**Per què:** amb quatre estius (2021-2024) no es pot distingir una tendència d'un salt. Una predicció fixada abans de tenir les dades és la millor prova fora de mostra que tenim (revisió externa del 24/10/2026, punt G4).

## Què es prediu

$\chi^0_{2026}$: semielasticitat estàtica del consum elèctric residencial de Barcelona (suma de la ciutat) als graus-dia de refrigeració, en % per K. Model principal de l'article 1 (retards 0-3, efectes fixos d'any, setmana ISO, dia de la setmana i festiu; errors per clústers de setmana).

| Hipòtesi | Què diu | $\chi^0_{2026}$ (%/K) | Interval del 95 % |
|---|---|---|---|
| **H1** · continuació lineal | La recta dels estius 2021-2024 continua | **9,09** | 6,79 – 11,38 (predicció, amb la dispersió entre anys) |
| **H0** · salt i replà | La resposta es queda al nivell del 2024 | **7,48** | 6,44 – 8,21 (*bootstrap* per setmanes del 2024) |

Secundari: λ₂₀₂₆ (amplitud de la corba, 2021 = 1) amb continuació lineal = **2,26** (sense interval: λ és fràgil, vegeu la secció 9 del notebook).

Valors de partida: $\chi^0$ = 4,66 / 5,46 / 6,05 / 7,48 %/K (2021-2024), $T_c$ = 20 °C.

## Condicions fixades ara

1. Es fa servir $T_c$ = **20 °C**, sense tornar-lo a triar.
2. Mateixes exclusions: dies incomplets, anomalies (detector amb k = 6, blocs negatius < −12 % durant ≥ 7 dies) i dies d'onada, amb el **llindar P95 dels estius 2021-2025**.
3. L'estiu 2026 ha de passar la **regla de qualitat**: ≥ 90 % dels seus CDD en dies útils. Si no la passa, la predicció no s'avalua i es diu.
4. El 2026 s'estima conjuntament amb els estius 2021-2024 (el 2025 queda fora, com a la v0.14).

## Com es llegirà

- Dins de H1 i fora de H0: compatible amb una tendència; el replà queda descartat.
- Dins de H0 i fora de H1: compatible amb un salt; la continuació lineal queda descartada.
- Dins de tots dos (de 6,79 a 8,21): **no discrimina**. Ho declarem ara perquè els intervals se superposen.
- Fora de tots dos: cap de les dues hipòtesis descriu el 2026.

*Aquest fitxer no es pot modificar després de la data del registre. Qualsevol canvi va a un fitxer nou amb data nova.*
