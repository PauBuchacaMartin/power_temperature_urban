# Pilot · model físic mínim i problema invers (25/10/2026)

**Estat:** pilot. Correspon al pas 1 de l'estratègia en quatre passos, més una primera mirada a les dades reals. Pertany a la peça opcional «estat energètic real del parc», que **s'obre quan s'enviï l'article 1** (regla d'una peça en anàlisi). El que aquí serveix directament a l'article 1 està marcat amb ⟶ P1.

Codi: `src/consum_temperatura/forward.py` · proves: `tests/test_forward.py`.

## El model (cadena de Wiener)

1. **Envolupant 1R1C** amb constant de temps $\tau$ (dies). Cada habitatge sent una temperatura exterior filtrada:
   $x(d)=a\,x(d-1)+(1-a)\,T(d)$, amb $a=e^{-1/\tau}$.
2. **Llindars heterogenis**, $T^*\sim\mathcal N(\mu,\sigma)$. La suma sobre llars és
   $R(x)=\mathbb E[(x-T^*)_+]=\sigma[\varphi(z)+z\Phi(z)]$, amb $z=(x-\mu)/\sigma$, i per tant $R''(x)=P(T^*)$.
3. **Consum:** $E(d)=B(d)\,[1+A_y\,R(x(d))]$. Aquí $A_y=n_{AC}(y)\,u(y)/B$ és l'amplitud de l'estiu $y$ (aparells × ús per aparell, per unitat de base).
4. **Invers:** mínims quadrats no lineals per a $(\mu,\sigma,\tau,A_y)$ sobre $\ln E$, amb els mateixos efectes fixos que l'article 1 (any, setmana ISO, dia i festiu) projectats.

**Avís físic:** amb un termòstat sempre engegat, la massa de l'edifici no crea memòria en l'electricitat, perquè l'aire treu la càrrega instantània. La memòria apareix perquè l'ús és intermitent i la decisió d'engegar depèn de $x$, que sí que recorda. Per això $\tau$ és una **constant de temps efectiva, tèrmica i de comportament**, no una $RC$ pura.

## Pas 1 · Prova sintètica (fet)

Amb les temperatures reals d'ERA5 (2021–2024) i paràmetres coneguts ($\mu$ = 23, $\sigma$ = 2, $\tau$ = 1,2 dies, $Q$ = 1,6, soroll del 2 %), en 5 simulacions:

- **$\tau$ es recupera molt bé:** 1,15–1,25.
- **$Q$ es recupera bé:** 1,51–1,74.
- **$\mu$ i $\sigma$ es recuperen junts però estan correlacionats:** en una simulació surt 23,7 / 2,7 en lloc de 23 / 2.
- Les proves automàtiques ho comproven amb soroll baix (`test_inverse_recovers_parameters`).

## Artefacte del temps a la $Q$ lineal ⟶ P1

Si l'amplitud **no canvia** entre estius, quina $Q$ dona el codi de l'article 1? Ho he comprovat simulant amb les temperatures reals:

| $\mu$ / $\sigma$ / $\tau$ | $T_c$ triat | $Q$ lineal (hauria de ser 1) | % el mateix dia |
|---|---|---|---|
| 22 / 1,5 / 1,2 | 21,5 | 1,01 | 0,60 |
| 23 / 2 / 1,2 | 22,5 | 1,03 | 0,62 |
| 24 / 2 / 1,2 | 23,0 | 1,04 | 0,63 |
| 25 / 2,5 / 1,2 | 23,5 | 1,04 | 0,63 |
| 23 / 2 / 0,5 | 22,5 | 1,02 | 0,90 |
| 23 / 2 / 3 | 22,5 | **1,19** | 0,38 |

**Lectura:** amb la memòria que mesurem (57 % el mateix dia, que correspon a $\tau\approx$ 1,2–1,3 dies), el fet que el 2021 fos un estiu fresc i que la resposta sigui convexa infla $Q$ com a màxim un **1–4 %**. Ho he calculat amb un model que no s'ha ajustat a les dades. És una resposta quantitativa a «el creixement no és un efecte de la corba combinada amb estius diferents?».

## Primera mirada a les dades reals (residencial net, estius 2021–2024)

| Paràmetre | Valor | IC 95 % (*bootstrap* per setmanes, 150 rèpliques) |
|---|---|---|
| $\tau$ (dies) | **1,31** | 1,04 – 1,71 |
| $\mu$ (°C, llindar efectiu mitjà) | 22,6 | 21,9 – 26,1 |
| $\sigma$ (°C, amplada dels llindars) | 2,7 | 1,7 – 5,3 |
| $Q_\text{fís}=A_{2024}/A_{2021}$ | **1,86** | 1,47 – 2,26 |

- **$\mu$ i $\sigma$ no se separen bé:** al *bootstrap* tenen correlació 0,89. Les dades fixen la combinació, no cadascun per separat.
- **El model físic s'ajusta millor que el lineal de l'article 1** amb menys paràmetres: RSS 0,608 amb 7 paràmetres no lineals, contra 0,665 amb 16 coeficients de CDD.
- **Els dies d'onada,** fora de l'ajust, donen els mateixos paràmetres ($\tau$ = 1,29; $Q$ = 1,88).
- **$Q_\text{fís}$ = 1,86** és coherent amb $\lambda$ = 1,76 [1,46–2,29] i una mica per sobre de $Q$ = 1,61 [1,34–1,87]. Els intervals se superposen. Té sentit: $Q_\text{fís}$ i $\lambda$ mesuren l'amplitud a forma fixa; $Q$ lineal barreja amplitud i especificació.

## Què pot identificar i què no (abans de fer els passos 2–4)

| Es pot identificar amb dades diàries de ciutat | No es pot identificar |
|---|---|
| $\tau$ (bé) | $R$ i $C$ per separat, només el producte $\tau=RC$ |
| Una combinació de $\mu$ i $\sigma$ | El desplaçament per guanys interns respecte de $\mu$ |
| $A_y$ per estiu i el seu quocient | $n_{AC}$ i $u$ per separat (només el producte) |

**Conseqüència per al pas 3:** dels 5–6 paràmetres globals proposats (mitjana i amplada de $T^*$, penetració del 2021, fracció de finestres, potència), la fracció de finestres i la potència només entren a través de $\tau$ i de $A$. **Amb dades de ciutat queden 3 paràmetres de forma i 1 d'amplitud.** La resta s'ha de fixar des de fora (Cadastre, TABULA, certificats) o queda per a l'anàlisi de sensibilitat del pas 4.

## Pas 3 a l'engròs (només per orientar)

Si la penetració ve dels certificats (pisos anteriors al 1980 amb fred, 2021→2024: def. A 45,6 → 49,9 %, ×1,09; def. B 28,8 → 35,2 %, ×1,22), la $Q$ que s'espera només per aparells és **1,09–1,22**, molt per sota de $Q_\text{fís}$ = 1,86 [1,47–2,26].

- **Fracció extensiva:** $\ln Q_n/\ln Q_\text{fís}$ ≈ **14–32 %**. És coherent amb el 18–42 % del pilot, que es calculava sobre $Q$ = 1,61.
- **Cautela:** els certificats tenen biaix de flux (només els pisos que es venen o es lloguen), les dues definicions no estan resoltes, i el que queda inclou l'ús, la potència per aparell, l'ocupació i l'error de mesura.

## Passos següents (quan s'obri la peça)

1. **Pas 2, sense ajustar res:** cal fixar $A$ amb valors de fora: potència i COP dels equips, superfície i $UA$ per arquetip (TABULA/EPISCOPE [per verificar]), hores d'ús i consum base per llar. **Cap d'aquests valors està verificat encara.** No els he posat al codi.
2. **Pas 3:** ajustar la forma ($\mu,\sigma,\tau$) i $A_{2021}$ amb el 2021–22 i predir el 2023–24 amb $A_y\propto n_{AC}(y)$ dels certificats. Cal una sèrie anual de $n_{AC}$ (no només els extrems) i resoldre A/B.
3. **Arquetips:** mescla de $\tau_a$ amb pesos del Cadastre. Sense paràmetres lliures nous: el $\tau$ mesurat (1,3 dies) fa de prova fora de mostra dels $\tau_a$ de la literatura.
4. **Pas 4, Sobol:** sobre les incògnites que no s'identifiquen (guanys interns, fracció de finestres, potència, COP), per saber quines conclusions en depenen.
5. **Hivern fora:** la calefacció és sobretot de gas.
