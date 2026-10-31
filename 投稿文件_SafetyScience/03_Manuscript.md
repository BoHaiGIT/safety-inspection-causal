# Manuscript — Safety Science (Draft v2, real-data revision)

**Title:** How large is the deterrent effect of safety inspections? Within-establishment evidence from 59,621 U.S. construction establishments

**Article type:** Research Article

**Authors:** Bin Jiang (Jared)*

**Affiliation:** Qingdao Bohai Construction Group, Qingdao, China

**Corresponding author:** Bin Jiang (Jared), 13963901396@163.com

**ORCID:** https://orcid.org/0009-0008-3989-0924

**Data and code:** https://github.com/BoHaiGIT/safety-inspection-causal

---

## Abstract

Safety inspections are the main regulatory instrument for reducing harm in construction, yet credible estimates of their deterrent value are scarce because inspectors target the establishments they already suspect. Using the complete U.S. federal enforcement registry for construction (2010–2019) and a text-normalised establishment key that recovers longitudinal links absent from the public data, I assemble 142,354 inspection-to-inspection transitions across 59,621 establishments and compare three identification strategies on the same records. Pooled comparison of subsequent serious violations is strongly **positive** (+22.6%), the opposite of a deterrent effect, because programmed (targeted) inspections are assigned to establishments with persistently higher violation propensity. Regression adjustment on observables (value-added OLS, double machine learning) reverses the sign to **−4.5%** and **−3.7%** (both significant), but a doubly robust AIPW estimator is indistinguishable from zero (−1.9%), and a placebo that substitutes a *future* programmed inspection for the treatment remains strongly significant (+26.1%), indicating residual confounding by time-persistent establishment heterogeneity. Exploiting within-establishment variation in inspection type — 10,986 establishments observed under both programmed and unprogrammed protocols — yields a stable deterrent effect of **−3.5%** (95% CI −5.9% to −0.4%) on serious violations at the next inspection, and −4.8% in the switcher subsample, with concordant effects on the probability of any serious violation (−5.4%) and on total violation counts (−5.6%), but not on penalty dollars. The effect is concentrated in large establishments (−6.1%), unionised workplaces (−16.0%), and transitions longer than one year (−5.8%); it is absent among establishments already cited at the index inspection and after 2015. I conclude that the deterrent effect of programmed inspection in U.S. construction is real but modest — roughly one order of magnitude smaller than pooled comparisons imply in the opposite direction — and that between-establishment estimates of inspection effectiveness should not be interpreted causally without a within-establishment or placebo-based diagnostic.

**Keywords:** Safety inspection; Deterrence; Selection bias; Within-establishment identification; Construction safety; Placebo test; Enforcement data

---

## 1. Introduction

Construction accounts for a disproportionate share of fatal and serious occupational injuries (Bureau of Labor Statistics, 2023), and inspections are the principal lever regulators use to reduce them. Whether inspections work is therefore a first-order policy question, and it has been asked many times (Viscusi, 1979; Gray and Scholz, 1993; Gray and Mendeloff, 2005; Levine et al., 2012; Johnson, 2020). The answers, however, disagree — not only in magnitude but in sign.

The disagreement is not primarily about data availability. Enforcement records are public, large, and detailed. It is about identification. Inspectors do not visit establishments at random: programmed inspections are allocated to sectors, establishments, and periods already flagged as hazardous, and unprogrammed inspections are triggered by complaints, referrals, and accidents (OSHA, 2019). Both the treatment and the outcome are therefore driven by the same latent variable — the establishment's underlying hazard and compliance propensity. Pooled comparisons inherit that dependence, and the resulting bias is not a nuisance to be trimmed away; in these data it is large enough to reverse the sign of the estimated effect.

This paper asks a narrow question and answers it with an unusually direct design: **how much do programmed inspections reduce violations detected at the establishment's next inspection, once the establishment's own persistent propensity is differenced out?**

I study the universe of U.S. federal OSHA enforcement records for construction over 2010–2019. Three features of the setting make it informative. First, the registry records the *type* of every inspection, separating programmed (planned, sector- or establishment-targeted) inspections from unprogrammed ones (complaints, referrals, accidents, follow-ups). Second, establishments are inspected repeatedly, so the same establishment is observed under both protocols — the variation that within-establishment designs require. Third, the public records contain no establishment identifier, which has historically forced analysts into cross-sectional designs; I show that a text-normalised establishment key recovers longitudinal structure at a scale sufficient for fixed-effects estimation (59,621 establishments; 142,354 transitions).

The design compares three strategies on the same records and reports all of them:

1. **Pooled comparison** of violations at the next inspection, which I show is positively biased to the point of sign reversal (+22.6%).
2. **Between-establishment regression adjustment** — value-added OLS, double machine learning (DML), and doubly robust AIPW — which reverses the sign (−4.5%, −3.7%, −1.9%) but is shown to be fragile by a placebo test (+26.1%).
3. **Within-establishment fixed effects**, using the 10,986 establishments observed under both inspection protocols, which yields a stable **−3.5%** (switcher subsample −4.8%) and survives concordance checks across alternative outcomes.

The contribution is deliberately double-edged. Methodologically, I quantify how much of the "inspection effect" reported in registry-based studies can be produced by selection, and I show that a placebo constructed from *future* treatment assignment is a cheap and decisive diagnostic. Substantively, I provide what I believe is the first within-establishment estimate of programmed-inspection deterrence in U.S. construction, and I characterise where the effect lives: large establishments, unionised workplaces, and longer horizons — but not among establishments already cited, and not after 2015.

## 2. Background

### 2.1 Evidence on inspection effectiveness

The theoretical prior is unambiguous. If firms weigh the expected cost of detection against the cost of prevention, then a higher probability of inspection — or a higher conditional penalty — should reduce non-compliance (Becker, 1968; Stigler, 1970; Polinsky and Shavell, 2000). Applied to occupational safety, this predicts that inspections reduce injuries by raising the expected cost of an unsafe workplace (Viscusi, 1979; Mendeloff, 1979).

The empirical record is far less settled. The first generation of studies, working on manufacturing data from the 1970s and 1980s, generally found that inspections reduced lost-workday injuries, with the largest effects among inspections that carried a penalty (Smith, 1979; Viscusi, 1979, 1986), although the estimated direct effects were small and sensitive to specification (Bartel and Thomas, 1985). The second generation exploited the panel structure of state and federal enforcement records more explicitly and confirmed the direction while shrinking the magnitude (Scholz and Gray, 1990; Gray and Scholz, 1993). By the 1990s, however, the estimated effect had largely disappeared: Gray and Mendeloff (2005) find that the effect of an inspection carrying a penalty declined steadily across 1979–1985, 1987–1991 and 1992–1998, becoming statistically indistinguishable from zero in the last period, and they are unable to explain the decline. Haviland et al. (2012), using Pennsylvania workers' compensation records for 1998–2005, recover larger effects — 19–24% — but only for inspections that imposed a penalty, and only for establishments between roughly 20 and 250 employees. Haviland et al. (2010) further show that inspections reduce the kinds of injuries that standards address and leave others untouched, which suggests that the mechanism is specific abatement rather than a general improvement in safety management.

Two studies stand apart because they do not rely on observational contrast at all. Levine et al. (2012) exploit California's random assignment of programmed inspections and find a 9.4% reduction in injury claims with no detectable cost in employment, sales, or firm survival. Johnson (2020) exploits the penalty threshold that triggers an OSHA press release and finds that publicising violations improves compliance among *nearby* establishments, with an effect equivalent to that of 210 additional inspections. Both designs identify a clean local effect, and both are restricted — by construction — to a narrow margin: random assignment of programmed inspections in one state, or a disclosure rule affecting a small set of large-penalty cases.

For construction specifically, the evidence is thinner and less encouraging. Weil (2001) studies large national construction firms in 1987–1993 and finds that, despite a high probability of annual inspection, inspections have only a modest effect on compliance, and that the standards most frequently cited diverge from the injury events that actually cause harm in the sector. This is consistent with the wider assessment in the Cochrane review of enforcement tools, which finds the evidence base too weak and too heterogeneous to support strong conclusions (Mischke et al., 2013), and with the broader lesson from environmental enforcement that discretion in *whom* to inspect is itself a determinant of regulatory productivity (Duflo et al., 2018).

The construction-safety literature has largely taken a different route. Its central questions have been the causation of accidents (Hinze et al., 1998; Suraji et al., 2001), the measurement of safety climate and culture (Alruqi et al., 2018; Fang et al., 2020), and the technical efficiency of site-level inspection itself (Rey et al., 2021). That work explains why an inspection *finds* what it finds, but it is not designed to answer whether the inspection changes what the establishment does next, and the two literatures have remained largely separate (Jin et al., 2019). This paper sits at their intersection: it treats the regulatory inspection as the treatment and asks what happens at the establishment's next visit.

Read together, the literature supports three generalisations. Effects are modest where they are found at all, they are conditional on penalties rather than on inspection per se, and they appear to have weakened over time. What the literature does not supply is agreement on sign, and that is the gap this paper addresses.

### 2.2 Why enforcement registries are hard

The disagreement is largely an identification problem, and the enforcement registry itself explains why.

First, treatment is assigned by the regulator, not by the researcher. OSHA distinguishes *programmed* inspections — planned visits allocated to industries and establishments selected under emphasis programmes — from *unprogrammed* inspections arising from complaints, referrals, fatalities, and follow-ups (OSHA, 2019). Programmed inspections are therefore delivered to establishments that the agency already believes to be hazardous, which is precisely the population in which the outcome of interest is elevated. Unprogrammed inspections are triggered by an event that is itself a signal of poor safety performance. Neither group is a plausible counterfactual for the other.

Second, violation propensity is strongly persistent within an establishment. An establishment cited repeatedly in one period tends to be cited repeatedly in the next; this serial correlation is not a nuisance that averaging removes, because it is correlated with the assignment rule. Gray and Scholz (1993) addressed this by exploiting panel variation, and Weil (1996) showed that observed compliance is far higher than the observed inspection probability can explain — a pattern that only makes sense if establishments differ in unobserved propensity. Any design that does not difference out the establishment's own persistent level will attribute that level to the inspection.

Third, the public extracts have historically lacked an establishment identifier. This is not a technicality: without a longitudinal link, the analyst is forced into cross-sectional comparisons, which is exactly the design that cannot separate the inspection from the establishment. The consequence is a literature in which the same underlying records can support estimates of opposite sign depending on the comparison made.

The methodological literature supplies the diagnostic that this setting demands. A *negative control* outcome or exposure — one that cannot be causally affected by the treatment but shares its confounding structure — reveals whether an association is driven by the confounder rather than the treatment (Lipsitch et al., 2010). I apply that logic directly in Section 4.5, substituting a future inspection's type for the current one.

### 2.3 This study

This paper makes three contributions to that literature.

First, it recovers longitudinal structure from a registry that was not designed to supply it. Using a text-normalised establishment key — name normalisation plus state — I link 59,621 construction establishments across 142,354 consecutive inspection pairs in the complete federal enforcement extract for 2010–2019. Construction is the sector in which the policy stakes are highest and the evidence weakest (Weil, 2001; McVittie et al., 1997), and to my knowledge no within-establishment estimate of inspection deterrence exists for it on a national scale.

Second, it compares three identification strategies on exactly the same records and reports all three. This is deliberate. The literature's disagreement is not resolved by adding another estimate to the pile; it is resolved by showing what each design does to the same data. I report the pooled comparison (+22.6%), the regression-adjusted estimates (−1.9% to −4.5%), and the within-establishment estimate (−3.5%), and I show that the gap between the first and the last is roughly seven times the effect being estimated.

Third, it uses a future-treatment placebo as a selection diagnostic and reports the result even where it is unfavourable. The placebo fails decisively between establishments (+26.1%) and survives only partially within them (+10.4%). I treat the residual as a bound rather than dismiss it, and I argue in Section 5.5 that it makes the headline estimate conservative rather than invalid.

The substantive question is narrow on purpose: how much do programmed inspections reduce violations at the establishment's *next* inspection, once the establishment's own persistent propensity is differenced out? The answer I obtain — 3 to 5% — is small. But it is obtained from a design that can be wrong in only one direction, and it is set against a selection bias large enough to reverse its sign.

## 3. Data

### 3.1 Source

I use the complete U.S. Department of Labor OSHA enforcement extract for 1970–2020, obtained from the public data-catalog mirror of the enforcement registry (the `data.dol.gov` enforcement tables: inspection, violation, accident, and supporting dictionaries). The extract contains 4,783,331 inspections, 12,488,743 cited violations, and 134,948 accident records. No application programming interface key or restricted data is required; the analysis is fully reproducible from the public files.

I restrict to **construction** (NAICS 23, or SIC 15/16/17 where NAICS is unavailable) and to inspections opened between **2010 and 2019**, the period in which NAICS coding is complete and enforcement practice is stable. This yields 415,000+ construction inspections.

### 3.2 Recovering an establishment key

The public extract contains no establishment identifier, and the internal `host_est_key` field is unusable: 61% of construction records carry the literal sentinel value `HOST_EST_KEY_VALUE`. Establishment names are, however, reported consistently. I therefore construct a key by normalising the establishment name — upper-casing, stripping punctuation, removing corporate suffixes (INC, LLC, LTD, CO, CORP, COMPANY, INCORPORATED, LP, LLP, THE, DBA) and collapsing whitespace — and appending the two-letter site state. Establishments with a normalised name shorter than three characters are dropped as unlinkable.

This resolution rule is conservative: it will split a single legal entity that reports under different trade names, and it may merge distinct establishments that share a name within a state. Both errors are attenuated by the within-establishment design, which differences out anything constant within a key.

### 3.3 Outcome measure and a note on injury rates

The registry records cited violations, not injury counts. Establishment-level injury and illness counts (Form 300A) are collected separately by the Bureau of Labor Statistics and are not present in the public enforcement extract (Bureau of Labor Statistics, 2023). I therefore use **the number of serious violations cited at the establishment's next inspection** (violation types S = serious, W = willful, R = repeat) as the outcome. This is a compliance outcome, not an injury outcome, and I do not claim otherwise anywhere in the paper. It is the natural outcome for a deterrence question — deterrence operates on the probability and severity of detected non-compliance — but it is not a substitute for injury rates, and the two can move differently.

I also use total cited violations, total assessed penalty dollars, and the indicator for any serious violation as secondary outcomes.

### 3.4 Estimation samples

Two samples are used.

**Between-establishment sample.** One row per establishment: the first inspection (index) and the next inspection, requiring that the index inspection be classifiable as programmed or unprogrammed. N = 59,617 establishments. Treatment is index-inspection type; baseline (`pre`) is serious violations at the index inspection; outcome (`post`) is serious violations at the next inspection.

**Within-establishment (transition) sample.** One row per consecutive inspection pair *k → k+1* for every establishment with at least two inspections. N = 142,354 transitions across 59,621 establishments. Treatment is the type of inspection *k*; baseline is serious violations at *k*; outcome is serious violations at *k+1*. 10,986 establishments (18.4%) contribute transitions under both protocols and constitute the identifying subsample for the switcher design.

**Table 1. Descriptive statistics**

| | Between-establishment sample | Within-establishment transitions |
|---|---|---|
| Units | 59,617 establishments | 142,354 transitions / 59,621 establishments |
| Period | 2010–2019 index inspections | 2010–2019 |
| Programmed share | 70.6% | 70.6% |
| Serious violations at baseline, mean (SD) | 1.534 (2.256) | 1.100 (1.954) |
| … share with zero | — | 56.8% |
| Serious violations at next inspection, mean (SD) | 1.165 (1.903) | 0.919 (1.732) |
| … share with zero | — | 61.4% |
| Years between inspections, mean / median | — | 1.20 / 0.60 |
| Establishments with both protocols | — | 10,986 (18.4%) |
| Establishments ever observed only under programmed | — | 45,912 |

## 4. Empirical strategy

Let `Y` denote serious violations at the next inspection, `D` the type of the current inspection (`D = 1` programmed, `D = 0` unprogrammed), `X` a vector of establishment characteristics (baseline violations, log employment, a risk score, complaint history, union status), and `c` the establishment key.

### 4.1 Pooled comparison and its bias

The naive estimand is `E[Y | D = 1] − E[Y | D = 0]`. Because programmed inspections are targeted at high-propensity establishments, this difference reflects selection and not deterrence. I report it precisely in order to show its magnitude and sign.

### 4.2 Between-establishment regression adjustment

I estimate

`Y_i = α + β·D_i + γ·pre_i + X_i'δ + λ_region + λ_year + λ_naics + ε_i`   (1)

by OLS ("value-added" specification), and additionally by **double machine learning** (Chernozhukov et al., 2018; `econml.LinearDML`, 5-fold cross-fitting, gradient-boosted nuisances) and by **AIPW** (cross-fitted gradient boosting for both the propensity and the two outcome surfaces), which is consistent if either nuisance is correctly specified. I report all three because they answer slightly different questions: OLS leans on the linearity of the baseline control, DML relaxes it partially, and AIPW relaxes it on both margins.

### 4.3 Within-establishment fixed effects

Differencing out `c`:

`Y_{c,t+1} = α_c + β·D_{c,t} + γ·pre_{c,t} + δ·gap_{c,t} + λ_year + u_{c,t}`   (2)

estimated by OLS after within-establishment demeaning, with **CR1 cluster-robust standard errors at the establishment level** (Bertrand et al., 2004; Cameron and Miller, 2015; Abadie et al., 2023). Identification comes from establishments whose inspection type varies over time — the switcher (change-in-change) design. Establishments inspected only under one protocol contribute nothing to `β` and are effectively absorbed by α_c.

The switcher design absorbs any fixed establishment characteristic, observed or not, including the persistent violation propensity that generates the pooled bias in Section 4.1. It does **not** absorb time-varying targeting, for example a decision to programme an establishment precisely because violations spiked at the previous inspection; that concern is addressed by the placebo in Section 4.5.

### 4.4 Alternative outcomes and heterogeneity

Equation (2) is re-estimated with total violation counts, penalty dollars, and the indicator for any serious violation. Heterogeneity is examined by splitting the transition sample rather than by interacting (the latter is equivalent here but less transparent) on establishment size, baseline violation status, union status, gap length, two-digit industry, and period. I report subgroup estimates rather than a causal forest (Wager and Athey, 2018; Athey and Wager, 2019). A forest's honest-split inference rests on the number of clusters at each leaf, and with a coarse binary treatment and 59,621 establishment-level clusters the subgroup cut is both more transparent and, for a policy reader, more directly interpretable; the two approaches answer the same question.

### 4.5 Placebo tests

If `β` were driven by persistent establishment heterogeneity rather than by the inspection protocol itself, then a *future* inspection's type — which cannot causally affect an outcome that precedes it — should nonetheless predict the outcome. I therefore re-estimate (1) and (2) substituting `D̃`, the type of the *next* inspection, for `D`. A well-identified design should return zero. This is a stringent test, and in these data it is the diagnostic that separates the strategies. It is the exposure-side analogue of the negative-control logic used in epidemiology (Lipsitch et al., 2010): the placebo shares the confounding structure of the treatment while severing its causal path.

### 4.6 Sensitivity to unmeasured confounding

I report E-values (VanderWeele & Ding) — the minimum strength of association that an unmeasured confounder would need with both treatment and outcome, on the risk-ratio scale, to explain away the estimate.

## 5. Results

### 5.1 The sign reverses when selection is removed

Pooled comparison of serious violations at the next inspection gives a **positive** difference: establishments whose index inspection was programmed have **+0.044 more** serious violations at their next inspection (table 2, row 1). Establishments with a programmed index inspection also have higher baseline violations (1.549 vs 1.498). This is the signature of targeting, and it means a cross-sectional reading of the registry would conclude that inspections *increase* violations.

When the same records are analysed as within-establishment transitions, the pooled coefficient grows to **+22.6%** (table 3, row 1). Adding establishment fixed effects reverses it to **−3.5%** (95% CI −5.9% to −0.4%). The change in sign is not a marginal adjustment; it is the removal of the identifying obstacle.

**Table 2. Between-establishment estimates (outcome: serious violations at next inspection, N = 59,617)**

| Specification | Estimate | 95% CI | Relative |
|---|---|---|---|
| Naive difference (pooled) | +0.0436 | — | +3.7% |
| Raw difference-in-differences | −0.0079 | — | — |
| Value-added OLS (baseline + covariates + FE) | **−0.0524** | [−0.0861, −0.0190] | **−4.5%** |
| Value-added OLS, common-support trimmed (pre ≤ P90) | −0.0535 | [−0.0910, −0.0209] | −4.9% |
| Raw DiD, common-support trimmed | −0.0627 | — | −5.4% |
| Value-added OLS + state × year FE | −0.1013 | [−0.1366, −0.0674] | −8.7% |
| Double machine learning (LinearDML, 5-fold) | −0.0426 | [−0.0805, −0.0046] | −3.7% |
| AIPW, cross-fitted gradient boosting | −0.0227 | [−0.0684, +0.0215] | −1.9% (n.s.) |
| **Placebo: future programmed inspection** | **+0.3044** | **[+0.2747, +0.3392]** | **+26.1%** |

Two features of table 2 deserve emphasis. First, the near-zero raw DiD (−0.008) is an artefact of the tails: in the full sample the treated group contains disproportionately many establishments with extreme baseline counts, and restricting to the common support (`pre ≤ 4`, discarding 4,860 establishments) moves the DiD to −0.063, in line with the regression estimates. Second, the three regression-adjusted estimators agree in sign but not in precision, and the doubly robust one cannot reject zero. Both facts point to the same conclusion: **adjustment on observables is doing real work, but it is not enough.**

### 5.2 The placebo fails between establishments

Row 8 of table 2 is the diagnostic that matters. Substituting the type of the *next* inspection for the current one — an event that occurs after the outcome and therefore cannot affect it — raises the estimated coefficient to **+0.304** serious violations (95% CI [+0.275, +0.339]), some six to seven times the size of any estimated treatment effect, in the opposite direction.

The mechanism is transparent: OSHA programmes inspections at establishments that keep generating violations. Time-persistent establishment propensity is therefore correlated with `D`, and any estimator that does not difference it out will mis-state the effect. Note that this placebo does not merely show that selection exists — it shows that the selection is *stronger* than the effect being estimated, which is why I do not report the regression-adjusted estimates as the main result.

### 5.3 Within-establishment estimates

Table 3 reports the fixed-effects estimates.

**Table 3. Within-establishment estimates (CR1 standard errors clustered on establishment)**

| Specification | Estimate | SE | 95% CI | Relative | N (firms) |
|---|---|---|---|---|---|
| Pooled OLS, all transitions | +0.2076 | 0.0093 | [+0.1894, +0.2258] | +22.6% | 142,354 (59,621) |
| Pooled OLS, switcher subsample | +0.0659 | 0.0128 | [+0.0407, +0.0910] | +9.4% | 60,056 (10,986) |
| **Firm FE, all transitions** | **−0.0318** | 0.0140 | **[−0.0591, −0.0044]** | **−3.5%** | 142,354 (59,621) |
| **Firm FE, switcher subsample** | **−0.0335** | 0.0139 | **[−0.0607, −0.0062]** | **−4.8%** | 60,056 (10,986) |
| Firm FE, total violation count | −0.0579 | 0.0167 | [−0.0906, −0.0253] | −5.6% | 60,056 (10,986) |
| Firm FE, P(any serious violation) | −0.0163 | 0.0038 | [−0.0238, −0.0088] | −5.4% | 60,056 (10,986) |
| Firm FE, total penalty dollars | +48.18 | 86.11 | [−120.6, +217.0] | +1.9% (n.s.) | 60,056 (10,986) |
| Firm FE, placebo: future programmed inspection | +0.0819 | 0.0190 | [+0.0447, +0.1191] | +10.4% | 82,733 (26,000) |

Within establishment, a programmed inspection is followed by **0.032 fewer serious violations** at the next inspection (−3.5%, 95% CI −5.9% to −0.4%). The switcher subsample, where identification is cleanest, gives −4.8%. The effect is concordant across the extensive and intensive margins — the probability of any serious violation falls by 5.4 percentage points of its base rate, and the total violation count falls by 5.6% — which is what a deterrence mechanism should look like. Penalty dollars, however, are unchanged. This is plausible: penalties are driven by a small number of high-gravity cases, and a 3–5% reduction in citation counts need not move total assessed dollars. It also marks a substantive difference from Haviland et al. (2012), for whom effects appear only where a penalty was imposed. In these data the deterrent margin operates on the *count* of serious citations rather than on the financial sanction, which is consistent with a mechanism driven by the prospect of scrutiny rather than by the size of the bill.

### 5.4 Heterogeneity

**Table 4. Within-establishment effects by subgroup (outcome: serious violations at next inspection)**

| Subgroup | Estimate | 95% CI | Relative | N |
|---|---|---|---|---|
| Establishment size ≤ median | −0.0228 | [−0.0689, +0.0232] | −2.3% (n.s.) | 79,354 |
| Establishment size > median | **−0.0511** | **[−0.0906, −0.0117]** | **−6.1%** | 63,000 |
| Clean record at index inspection (pre = 0) | **−0.0249** | **[−0.0496, −0.0002]** | **−5.1%** | 80,856 |
| Violations found at index inspection (pre > 0) | +0.0482 | [−0.0229, +0.1192] | +3.3% (n.s.) | 61,498 |
| Unionised | **−0.0823** | **[−0.1507, −0.0139]** | **−16.0%** | 21,514 |
| Non-unionised | −0.0267 | [−0.0572, +0.0039] | −2.7% (n.s.) | 120,840 |
| Gap ≤ 1 year | +0.0192 | [−0.0137, +0.0522] | +2.3% (n.s.) | 89,842 |
| Gap > 1 year | **−0.0612** | **[−0.1211, −0.0014]** | **−5.8%** | 52,512 |
| 2010–2014 | −0.0279 | [−0.0643, +0.0085] | −3.1% (n.s.) | 98,386 |
| 2015–2019 | +0.0240 | [−0.0253, +0.0733] | +2.5% (n.s.) | 43,968 |

Three patterns stand out.

*Size.* The effect is concentrated in larger establishments (−6.1%) and is not distinguishable from zero among smaller ones (−2.3%). Larger establishments have formal safety functions that can respond to a citation; smaller ones may simply lack the capacity to convert an inspection into changed practice (Hasle and Limborg, 2006; McVittie et al., 1997). The comparison with Haviland et al. (2012) is instructive and not entirely comfortable: they find effects only for establishments between roughly 20 and 250 employees and none above 250, whereas the median split places the estimated effect in the upper half of a size distribution dominated by small firms. The two results need not conflict — the margins compared are different, and "large" in a construction registry means something different from "large" in manufacturing — but together they suggest that the size gradient is not monotone, and that a single "small versus large" contrast is too coarse to carry a policy recommendation.

*Baseline compliance.* Deterrence appears among establishments with a **clean** record at the index inspection (−5.1%) and not among those already cited (+3.3%, n.s.). This is the opposite of a remediation story and consistent with a prevention story: the inspection signals scrutiny to establishments for which being cited is a new and salient event, whereas establishments already in the enforcement system are, in effect, already deterred — or already habituated to scrutiny (Weil, 1996).

*Union presence.* The effect is an order of magnitude larger in unionised workplaces (−16.0%, n = 21,514) than in non-unionised ones (−2.7%, n.s.). Unions provide the worker-side channel — a safety committee, a grievance procedure, someone whose job is to keep the citation on the agenda — through which an inspection becomes durable practice (Weil, 1991; Walters and Nichols, 2007). This is consistent with the wider evidence that worker representation is what converts a regulatory signal into a lasting change in safety climate and practice (Clarke, 2006; Zohar, 2010), and it is, in my view, the most policy-relevant heterogeneity in the paper. It is also the estimate most exposed to time confounding: union density in U.S. construction fell over the study window, so union status is correlated with period, and the coefficient should not be read as a stable structural parameter.

The effect also requires time: transitions of more than one year show −5.8%, shorter ones show nothing. And it does not appear in the later period: the 2015–2019 subsample point estimate is positive and insignificant. I return to this in Section 6.3.

### 5.5 The within-establishment placebo, and what remains

Row 8 of table 3 repeats the placebo inside the fixed-effects design: substituting the *next* inspection's type gives **+0.082** serious violations (95% CI [+0.045, +0.119]), a relative effect of +10.4%. Fixed effects remove most — but not all — of the placebo signal that the between-establishment design showed (+26.1% → +10.4%). The residual is interpretable: a decision to programme the *next* inspection is partly a response to what was found at the current one, so the placebo remains informative about time-varying targeting that α_c cannot absorb.

I do not treat this as a refutation. Three considerations bound the damage. First, the residual placebo operates in the same direction as selection, so if anything it implies that the true deterrent effect is **larger** in absolute value than −3.5%, not smaller. Second, the placebo's magnitude (+10.4%) is substantially smaller than the between-establishment placebo (+26.1%), confirming that fixed effects are doing their job. Third, the substantive results are internally consistent: the outcomes that should move under deterrence (violation counts, extensive margin) do move, and the one that should not respond mechanically (penalty dollars) does not.

### 5.6 Sensitivity to unmeasured confounding

The E-value for the within-establishment estimate is **1.28** (RR = 0.952): an unmeasured confounder would need to be associated with both inspection type and subsequent violations by a risk ratio of about 1.28 to explain the estimate away. This is a modest threshold — comparable to associations routinely observed between, say, establishment size and citation counts — and it is the main reason I describe the effect as modest and fragile rather than established.

## 6. Discussion

### 6.1 What the registry can and cannot tell us

The most robust finding in this paper is not the size of the effect but the size of the bias. On the same records, pooled comparison says inspections increase violations by 22.6%; within-establishment comparison says they reduce them by 3.5%. Both numbers are computed from the same 142,354 transitions. The gap between them — a swing of roughly 26 percentage points, or about seven times the effect itself — is the price of ignoring targeting.

This has an immediate implication for the literature: any registry-based estimate of inspection effectiveness that does not difference out establishment propensity, or at minimum report a placebo of the kind in Section 4.5, should be read as an upper bound on harm rather than an estimate of benefit. It also reconciles two otherwise puzzling features of the published record — the wide dispersion of estimates, from the imprecise 1% of Gray and Mendeloff (2005) to the 19–24% of Haviland et al. (2012) and the 9.4% of Levine et al. (2012), and the fact that some estimates are positive. Dispersion is what one expects when the magnitude of selection bias varies across samples; a positive estimate is what one expects when it is large.

### 6.2 Substantive reading

I read the within-establishment estimates as evidence of a **real but modest deterrent effect**, on the order of 3–5% fewer serious violations at the next inspection. The mechanism the heterogeneity suggests is not remediation of bad establishments but reinforcement of scrutiny among ordinary ones, especially where a union provides an implementation channel and where the establishment is large enough to have someone tasked with responding. This has a direct allocation implication: if the marginal return is concentrated among currently-clean, larger, unionised establishments with inspection horizons beyond a year, then a programme aimed exclusively at the worst performers — the intuitive targeting rule — may be operating where the marginal effect is smallest. This is the occupational-safety counterpart of the finding that discretion in targeting is itself a determinant of regulatory productivity (Duflo et al., 2018), and it sits uneasily with an evaluation practice organised around high-penalty cases (Johnson, 2020).

I state this cautiously. The 2015–2019 subsample shows no effect, which could indicate that the effect has weakened, that enforcement practice changed (for example toward higher-frequency, lower-depth inspections), or simply that the later period has less within-establishment variation after conditioning. I am not the first to observe a weakening: Gray and Mendeloff (2005) documented a decline across three decades of manufacturing enforcement and were equally unable to explain it. Whether the pattern I observe is the same phenomenon or an artefact of reduced identifying variation late in the window, I cannot distinguish, and I flag it as the single most important open question.

### 6.3 Limitations

1. **Compliance outcome, not injury outcome.** Establishment injury counts are not in the public enforcement registry. The outcome is cited serious violations. Deterrence on compliance need not translate one-for-one into injury reduction.
2. **No establishment identifier.** Links are recovered by name normalisation plus state. Split and merge errors are unavoidable; a validated identifier (as exists in some state-plan data) would materially improve precision.
3. **Residual time-varying selection.** The within-firm placebo remains significant at +10.4%. The switcher design absorbs fixed heterogeneity only.
4. **Modest statistical strength.** The main estimate is −3.5% with a confidence interval reaching −0.4%, and the E-value is 1.28 (VanderWeele and Ding, 2017). These are not large margins.
5. **No effect after 2015** and no effect on penalty dollars; both are reported rather than explained.
6. **Federal-plan coverage.** The extract covers federal OSHA enforcement; state-plan states (which include several large construction markets) report through separate channels and are unevenly represented, so external validity to state-plan jurisdictions is limited.
7. **Single country, single sector.** Construction in the United States, 2010–2019. Generalisation to other sectors and to other enforcement regimes is untested.

## 7. Conclusion

Programmed safety inspections in U.S. construction reduce serious violations detected at the establishment's next inspection by roughly 3–5%, once the establishment's own persistent violation propensity is differenced out. The same records, analysed cross-sectionally, imply the opposite and seven times larger: a 22.6% increase. The deterrent effect is therefore real but modest, concentrated among large, unionised, and currently-clean establishments, absent among establishments already cited and after 2015, and sensitive to unmeasured confounding at an E-value of 1.28.

For evaluation practice, the lesson is that the placebo — substituting a future treatment for the current one — is a cheap and unusually informative diagnostic, and that estimates of inspection effectiveness which fail it should not be read causally.

---

## Declaration of competing interest
The authors declare no competing interests.

## Acknowledgements
The author thanks the U.S. Department of Labor for maintaining the public enforcement registry on which this study relies, and colleagues in the construction safety practice for comments on an earlier draft. This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.

## Data and code availability
All data are public: the OSHA enforcement extract is available from the U.S. Department of Labor data catalog. Analysis code, the establishment-resolution routine, and scripts reproducing every table in this paper are archived at https://github.com/BoHaiGIT/safety-inspection-causal. Estimation uses EconML (Battocchi et al., 2019), scikit-learn (Pedregosa et al., 2011), and NumPy (Harris et al., 2020).

## References
Abadie, A., Athey, S., Imbens, G.W., Wooldridge, J.M., 2023. When should you adjust standard errors for clustering? Q. J. Econ. 138, 1–35.

Alruqi, W.M., Hallowell, M.R., Techera, U., 2018. Safety climate dimensions and their relationship to construction safety performance: A meta-analytic review. Saf. Sci. 109, 165–173.

Athey, S., Wager, S., 2019. Estimating treatment effects with causal forests: An application. Obs. Stud. 5, 37–51.

Bartel, A.P., Thomas, L.G., 1985. Direct and indirect effects of regulation: A new look at OSHA's impact. J. Law Econ. 28, 1–25.

Battocchi, K., Dillon, E., Hei, M., Lewis, G., Oka, P., Oprescu, M., Syrgkanis, V., 2019. EconML: A Python package for ML-based heterogeneous treatment effects estimation. https://github.com/py-why/EconML

Becker, G.S., 1968. Crime and punishment: An economic approach. J. Polit. Econ. 76, 169–217.

Bertrand, M., Duflo, E., Mullainathan, S., 2004. How much should we trust differences-in-differences estimates? Q. J. Econ. 119, 249–275.

Bureau of Labor Statistics, 2023. Census of Fatal Occupational Injuries (CFOI). U.S. Department of Labor, Washington, DC.

Cameron, A.C., Miller, D.L., 2015. A practitioner's guide to cluster-robust inference. J. Hum. Resour. 50, 317–372.

Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W., Robins, J., 2018. Double/debiased machine learning for treatment and structural parameters. Econom. J. 21, C1–C68.

Clarke, S., 2006. The relationship between safety climate and safety performance: A meta-analytic review. J. Occup. Health Psychol. 11, 315–327.

Duflo, E., Greenstone, M., Pande, R., Ryan, N., 2018. The value of regulatory discretion: Estimates from environmental inspections in India. Econometrica 86, 2123–2160.

Fang, D., Huang, Y., Guo, H., Lim, H.W., 2020. LCB approach for construction safety. Saf. Sci. 128, 104761.

Gray, W.B., Mendeloff, J.M., 2005. The declining effects of OSHA inspections on manufacturing injuries, 1979–1998. Ind. Labor Relat. Rev. 58, 571–587.

Gray, W.B., Scholz, J.T., 1993. Does regulatory enforcement work? A panel analysis of OSHA enforcement. Law Soc. Rev. 27, 177–213.

Harris, C.R., Millman, K.J., van der Walt, S.J., Gommers, R., Virtanen, P., Cournapeau, D., Wieser, E., Taylor, J., Berg, S., Smith, N.J., et al., 2020. Array programming with NumPy. Nature 585, 357–362.

Hasle, P., Limborg, H.J., 2006. A review of the literature on preventive occupational health and safety activities in small enterprises. Ind. Health 44, 6–12.

Haviland, A.M., Burns, R.M., Gray, W.B., Ruder, T., Mendeloff, J., 2010. What kinds of injuries do OSHA inspections prevent? J. Saf. Res. 41, 339–345.

Haviland, A.M., Burns, R.M., Gray, W.B., Ruder, T., Mendeloff, J., 2012. A new estimate of the impact of OSHA inspections on manufacturing injury rates, 1998–2005. Am. J. Ind. Med. 55, 964–975.

Hinze, J., Pedersen, C., Fredley, J., 1998. Identifying root causes of construction injuries. J. Constr. Eng. Manage. 124, 67–71.

Jin, R., Zou, P.X.W., Piroozfar, P., Wood, H., Yang, Y., Yan, L., Han, Y., 2019. A science mapping approach based review of construction safety research. Saf. Sci. 113, 285–297.

Johnson, M.S., 2020. Regulation by shaming: Deterrence effects of publicizing violations of workplace safety and health laws. Am. Econ. Rev. 110, 1866–1904.

Levine, D.I., Toffel, M.W., Johnson, M.S., 2012. Randomized government safety inspections reduce worker injuries with no detectable job loss. Science 336, 907–911.

Lipsitch, M., Tchetgen Tchetgen, E., Cohen, T., 2010. Negative controls: A tool for detecting confounding and bias in observational studies. Epidemiology 21, 383–388.

McVittie, D., Banikin, H., Brocklebank, W., 1997. The effects of firm size on injury frequency in construction. Saf. Sci. 27, 19–23.

Mendeloff, J.M., 1979. Regulating Safety: An Economic and Political Analysis of Occupational Safety and Health Policy. MIT Press, Cambridge, MA.

Mischke, C., Verbeek, J.H., Job, J., Morata, T.C., Alvesalo-Kuusi, A., Neuvonen, K., Clarke, S., Pedlow, R.I., 2013. Occupational safety and health enforcement tools for preventing occupational diseases and injuries. Cochrane Database Syst. Rev. CD010183.

OSHA (Occupational Safety and Health Administration), 2019. Field Operations Manual (FOM), CPL 02-00-164. U.S. Department of Labor, Washington, DC.

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., et al., 2011. Scikit-learn: Machine learning in Python. J. Mach. Learn. Res. 12, 2825–2830.

Polinsky, A.M., Shavell, S., 2000. The economic theory of public enforcement of law. J. Econ. Lit. 38, 45–76.

Rey, R.O., de Melo, R.R.S., Costa, D.B., 2021. Design and implementation of a computerized safety inspection system for construction sites using UAS and digital checklists – Smart Inspecs. Saf. Sci. 143, 105430.

Scholz, J.T., Gray, W.B., 1990. OSHA enforcement and workplace injuries: A behavioral approach to risk assessment. J. Risk Uncertain. 3, 283–305.

Smith, R.S., 1979. The impact of OSHA inspections on manufacturing injury rates. J. Hum. Resour. 14, 145–170.

Stigler, G.J., 1970. The optimum enforcement of laws. J. Polit. Econ. 78, 526–536.

Suraji, A., Duff, A.R., Peckitt, S.J., 2001. Development of causal model of construction accident causation. J. Constr. Eng. Manage. 127, 337–344.

VanderWeele, T.J., Ding, P., 2017. Sensitivity analysis in observational research: Introducing the E-value. Ann. Intern. Med. 167, 268–274.

Viscusi, W.K., 1979. The impact of occupational safety and health regulation. Bell J. Econ. 10, 117–140.

Viscusi, W.K., 1986. The impact of occupational safety and health regulation, 1973–1983. RAND J. Econ. 17, 567–580.

Wager, S., Athey, S., 2018. Estimation and inference of heterogeneous treatment effects using random forests. J. Am. Stat. Assoc. 113, 1228–1242.

Walters, D., Nichols, T., 2007. Worker Representation and Workplace Health and Safety. Palgrave Macmillan, Basingstoke.

Weil, D., 1991. Enforcing OSHA: The role of labor unions. Ind. Relat. 30, 20–36.

Weil, D., 1996. If OSHA is so bad, why is compliance so good? RAND J. Econ. 27, 618–640.

Weil, D., 2001. Assessing OSHA performance: New evidence from the construction industry. J. Policy Anal. Manage. 20, 651–674.

Zohar, D., 2010. Thirty years of safety climate research: Reflections and future directions. Accid. Anal. Prev. 42, 1517–1522.

---

### 投稿备注（非稿件内容，投稿前删除）

- **口径变化**：v1 的 −10% 伤害率结论来自合成校准数据，**不可用于真实投稿**。v2 全部数字来自真实 OSHA 执法数据（142,354 条企业内转换、59,621 家企业），结局为 serious 违规数。
- **核心卖点是"符号反转"**：+22.6%（混合）vs −3.5%（企业内），差距约 26pp，是效应本身的 7 倍。这比"效应 −3.5%"更有发表价值，也更难被审稿人击破。
- **必须主动写进 Limitations 的**：安慰剂在企业内仍显著（+10.4%）、E-value 仅 1.28、2015 后无效应、罚金无变化。主动写比被审稿人问出来好。
- **未使用的原卖点**：事故叙述文本 embedding 在真实数据上**不可用**——2010–2019 事故表与检查表仅 0.4% 可链接（联邦/州计划口径差异）。已在正文以合规口径替代，不再声称 embedding 控制。若审稿人问"为何不用文本控制"，用此数据事实回答。
- 表 2/3/4 数字全部可由 `robustness_real.py`、`build_within_firm.py`、`within_firm_heterogeneity.py` 复现。

#### 作者信息（已全部就绪）

| 项 | 内容 |
|---|---|
| 署名 | **Bin Jiang (Jared)** |
| 单位 | Qingdao Bohai Construction Group, Qingdao, China |
| 通讯邮箱 | 13963901396@163.com（纯 ASCII 域名，可通过 Elsevier / Emerald 校验） |
| ORCID | 0009-0008-3989-0924（已核验：校验位有效、公开记录可解析，姓名与署名一致） |

**投稿系统填写提示**：Editorial Manager 的作者元数据分 Given / Family 两栏，填 `Bin` / `Jiang`；英文名 `Jared` 若系统有 Middle name 栏可填，没有就只在正文作者行保留括号即可，不必强塞。

正文已统一为单作者第一人称 "I"（原 "we" / "our" 按语境改写；唯一保留的复数在 6.1 节标题 `tell us`，属固定搭配）。

#### 参考文献的两套格式

- 本稿用的是 **Elsevier Harvard**（Safety Science），44 条，见文末 References。
- 若改投 **ECAM（Emerald）**，用 `references_ECAM_Harvard.md`（同 44 条，Emerald Harvard 排版），**正文的 in-text 引用不需改动**。由 `make_ecam_refs.py` 从 `references.bib` 生成。
