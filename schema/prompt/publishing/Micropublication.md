 

### Define:

A **Micropublication (MPU)** is a **structured evidence graph** that captures a **scientific assertion** (central `mp:Claim` ) together with its **supporting or challenging elements**.
And  the **Micropublication (MPU)**  `mp:argues` the central `mp:Claim`
* **Core components**: `mp:Claim` (argumentative nucleus).
* **Has Support Elements**:  `mp:Statement` ,`whu:DataSet`, `whu:Method`, `mp:Attribution`, `mp:Reference`.
 

---

### Purpose:

* **Evidence integration**: Bundle a central claim with its supporting/challenging evidence.
* **Argumentation tracking**: Ensure each MPU forms a coherent subgraph of Claim–Evidence relations.
* **Provenance capture**: Attribute responsibility and link references, enabling transparency and reproducibility.

---

### Context

Use this class **only when the text explicitly presents a scientific assertion with its associated evidence**.

* Trigger when a **claim/statement** is paired with **data, method, attribution, or references**.
* **Do not** trigger if only a claim appears without evidence, or if the text only describes background context.
* Always link the MPU to its central Claim and connect to supporting elements using evidence relations (`mp:support`, `mp:challenge`).

 
---

### Notes

* In a scientific article or lecture, multiple MPUs may appear: some introduced directly by the author, others attributed to external researchers or cited references.  
* Each MPU must contain **exactly one central `mp:Claim`** as its argumentative nucleus.  
* Supporting elements (`mp:Statement`, `whu:Data`, `whu:Method`, `mp:Attribution`, `mp:Reference`) are **optional**, but should be linked to the MPU whenever they are **explicitly mentioned** in the text. Avoid inferring elements that are not stated.

#### Relations within a Micropublication

* `whu:Method` → `mp:support` → `whu:DataSet`
* `whu:DataSet` → (`mp:support` / `mp:challenge`) → `mp:Claim` / `mp:Statement`
* `mp:Statement` may provide intermediate reasoning linking **DataSet** and **Claim**.

#### Relations between Micropublication
* `mp:Micropublication` → (`mp:argues`) → `mp:Claim`
* `mp:Micropublication` → (`whu:hasElement`) → `mp:Claim`
* `mp:Micropublication` → (`whu:hasElement`) → `whu:Method`
* `mp:Micropublication` → (`whu:hasElement`) → `mp:Attribution`
* `mp:Micropublication` → (`whu:hasElement`) → `mp:Reference`
* `mp:Micropublication` → (`whu:hasElement`) → `whu:DataSet`
---

### Examples

*   **Micropublication 1: Biochar altered DOM and enhanced microbial activity.**
    *   **mp:Claim**: Biochar addition **significantly altered porewater dissolved organic matter (DOM) characteristics** and **enhanced microbial activity** in paddy soils.
    *   **mp:Statement**: DOM in biochar-amended soil showed **increased aromaticity, molecular weight, and chromophoric components** (higher SUVA$_{254}$, a$_{355}$ values; lower S$_{R}$ values). An **increase in humic character** (higher HIX, normalized CDOM, humic-like fluorescence peaks) and **enhanced microbial activity** (higher BIX, DOC-normalized peak M) were observed.
    *   **whu:DataSet**: Measurements of DOM properties in porewater (DOC, SUVA$_{254}$, S$_{R}$, a$_{355}$, HIX, BIX).
    *   **whu:Method**: Porewater collected via Rhizon sampler. DOC measured with TOC analyzer. Optical analyses (fluorescence, UV-Vis) performed with Aqualog® spectrometer. Spectral parameters calculated using established methods.
    *   **mp:Attribution**: Environmental Biogeochemistry Laboratory of Natural Organic Matter (NOM-Lab) at Southwest University (SWU).
    *   **mp:Reference**: Calculation methods for spectral parameters, and similar observations or biological implications of BIX, are supported by various studies.

*   **Micropublication 2: Modified biochar decreased MeHg production in soils.**
    *   **mp:Claim**: Only **modified biochar effectively decreased methylmercury (MeHg) production** in paddy soils; original biochar had no significant effect on soil MeHg.
    *   **mp:Statement**: **MeHg content and MeHg/THg ratios were significantly lower** in soil with modified biochar. MeHg in porewaters was also significantly lower in *both* biochar treatments. The original biochar showed no significant difference from the control in soil THg, MeHg, or MeHg/THg ratio. This effect involves competition between decreasing Hg bioavailability and increasing microbial activity.
    *   **whu:DataSet**: Measurements of total mercury (THg), MeHg, and MeHg/THg ratios in soil and porewater samples.
    *   **whu:Method**: THg measured by cold vapor atomic fluorescence spectroscopy (CVAAS). MeHg by ethylated isothermal gas chromatography-cold atomic fluorescence (GC-CVAFC) or distillation-ethylation method. USEPA method 1631 used for porewater THg. Quality control procedures applied.
    *   **mp:Attribution**: Mercury Biogeochemistry Laboratory (MBL) at SWU.
    *   **mp:Reference**: Biochar's ability to decrease MeHg production is supported by prior studies. The antagonistic interaction of selenium (in modified biochar) with Hg is also referenced.

 
 

---
 