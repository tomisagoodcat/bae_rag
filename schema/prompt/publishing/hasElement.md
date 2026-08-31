

### Define

`whu:hasElement` connects a **Micropublication (`mp:Micropublication`)** to its **constituent elements**, such as `mp:Claim`, `mp:Statement`, `whu:DataSet`, `whu:Method`, `mp:Reference`, or `mp:Attribution`.

* It represents a **containment / composition relation**: the Micropublication is the **argumentation container**, and its elements are explicitly included within it.
* This property does **not** indicate argumentative roles (support/challenge); it only records **membership** of elements inside the MPU.

---

### Purpose

* **Structural linkage**: Ensure each MPU is connected to its **core elements**.
* **Argumentation integrity**: Guarantee that all Claims, Statements, Data, Methods, References, and Attributions are correctly grouped under the MPU.
* **Graph completeness**: Provide a clear container structure for downstream reasoning and visualization.

---

### Context

Use this property **only when the text explicitly indicates that an element belongs to a Micropublication**.

* Trigger when authors describe that a Claim, Statement, Dataset, Method, Reference, or Attribution is **part of / included in** a Micropublication.
* Do **not** infer this relation from simple co-mention (e.g., if Claim and Data appear in the same sentence without an explicit MPU container, skip).
* Prioritize explicit expressions such as *“Micropublication X contains Claim Y”*, *“MPU includes Dataset Z”*, etc.

---

### Notes

* This property is **structural**, not argumentative. Use `mp:support` / `mp:challenge` for evidential relations.
* Every `mp:Micropublication` must have **at least one `mp:Claim` or `mp:Statement`** as its nucleus.
* Additional elements (Data, Method, Attribution, Reference) may be linked when explicitly mentioned.

---

### Use semantic links

* `mp:Micropublication` → `whu:hasElement` → `mp:Claim`
* `mp:Micropublication` → `whu:hasElement` → `mp:Statement`
* `mp:Micropublication` → `whu:hasElement` → `whu:DataSet`
* `mp:Micropublication` → `whu:hasElement` → `whu:Method`
* `mp:Micropublication` → `whu:hasElement` → `mp:Reference`
* `mp:Micropublication` → `whu:hasElement` → `mp:Attribution`

---

### Examples

*   **Micropublication 1 (Biochar altered DOM and enhanced microbial activity) `whu:hasElement` mp:Claim**:
    *   **mp:Claim**: "Biochar addition **significantly altered porewater dissolved organic matter (DOM) characteristics** and **enhanced microbial activity** in paddy soils."

*   **Micropublication 1 (Biochar altered DOM and enhanced microbial activity) `whu:hasElement` whu:Data**:
    *   **whu:Data**: "Measurements of DOM properties in porewater (DOC, SUVA$_{254}$, S$_{R}$, a$_{355}$, HIX, BIX)."

*   **Micropublication 1 (Biochar altered DOM and enhanced microbial activity) `whu:hasElement` whu:Method**:
    *   **whu:Method**: "Porewater collected via Rhizon sampler. DOC measured with TOC analyzer. Optical analyses (fluorescence, UV-Vis) performed with Aqualog® spectrometer. Spectral parameters calculated using established methods."

