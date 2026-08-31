### Define
 
A **Claim** (`mp:Claim`) is a specialized type of **Statement** (`mp:Statement`) that represents the **central scientific assertion** within a Micropublication — the principal proposition to be evaluated.
It functions as the **argumentative nucleus**, serving as the focal point that other Representations (e.g., `whu:DataSet`, `mp:Statement`, `mp:Method`, `mp:Reference`) may explicitly **support** or **challenge**.
Every valid `mp:Claim` should be anchored by at least one piece of evidence, typically a `whu:DataSet`, through `mp:supports` or `mp:challenges` relations.

---

### Purpose

* **Central argumentation role**: Capture the key assertion that a Micropublication is built around.  
* **Evidence linkage**: Act as the target of supporting/challenging relations from datasets, statements, and methods.  
* **Scientific evaluation**: Provide the focal point for assessing the validity of evidence and reasoning.
---

### Context

Extract a `mp:Claim` when the text **explicitly presents a principal scientific assertion** that is argued, supported, or refuted.  
Do **not** extract as Claim if the text only describes observations, methods, or contextual background (these are better represented as `mp:Statement`).

---

### Semantic Links

* `whu:DataSet` → `mp:supports` / `mp:challenges` → `mp:Claim`  
* `mp:Statement` → `mp:supports` / `mp:challenges` → `mp:Claim`  
 

### Notes

* While optional, once an `mp:Claim` has been identified, make every effort to also extract its **evidence relations**.  
* Specifically, check whether the text establishes one of the following links:  
  - `whu:DataSet` → (`mp:supports` / `mp:challenges`) → `mp:Claim`  
  - `mp:Statement` → (`mp:supports` / `mp:challenges`) → `mp:Claim`  
* These relations ensure that each Claim is properly anchored to the evidence (datasets, statements) that support or refute it.  
------
### Examples

*   **mp:Claim**: Biochar significantly reduces methylmercury (MeHg) bioaccumulation in rice plants, specifically in hulls and grains. This finding was observed with both original and modified biochar treatments.
    *   **Original Text**: "The results showed that the addition of biochar, whether in original or modified form, **significantly reduced the bioaccumulation of MeHg in rice plants, especially in hulls and grains** ( p < 0.05)". "Application of biochar, regardless of its original or modified form, can **significantly decrease the bioaccumulation of MeHg in rice plants, especially in hulls and grains**".

*   **mp:Claim**: Only modified biochar effectively inhibits MeHg production in soils. The original biochar did not show a significant difference from the control in influencing MeHg production in soil.
    *   **Original Text**: "However, MeHg production in soils was **only inhibited by the modified biochar**". "In soil phases, the influence of the original biochar on Hg dynamics was **not evident** (...) because the total Hg content (THg), MeHg content, and the degree of methylation (...) **were not significantly different from those of the control** ( p > 0.05)". "Unlike Se-modified biochar, the **original biochar did not significantly differ from the control in influencing MeHg production**".

*   **mp:Claim**: Biochar addition leads to significant changes in dissolved organic matter (DOM) characteristics in soil porewater, specifically increasing DOM's aromaticity and molecular weight. These changes are posited to decrease mercury (Hg) bioavailability.
    *   **Original Text**: "**Biochar addition induced a significant increase in DOM’s aromaticity and molecular weight** ( p < 0.05), which **decreased Hg bioavailability**". "These changes imply that the **DOM in soil amended with biochar showed greater aromaticity, molecular weight, and chromophoric components**".
 