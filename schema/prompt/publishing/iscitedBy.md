 

### Define

`cito:isCitedBy` specifies that a **work (e.g., paper, dataset, method, software, reference)** is **cited by** another work.

* It is the **inverse relation** of `cito:cites`.
* Domain and range are both **citable scholarly entities** (e.g., publications, datasets, references).
* Use it when the text indicates that **another work has cited this one**.

---

### Purpose

* **Citation provenance**: Track incoming citations to a given work.
* **Evidence chaining**: Represent how knowledge units (claims, datasets, methods) are **referenced in later works**.
* **Bidirectional linking**: Ensure consistency with `cito:cites` by recording the inverse relation.

---

### Context

Use this property **only when a source is explicitly described as being cited by another source**.

* Trigger when text describes **citation reception** (e.g., “This study is cited by …”, “Dataset X has been cited in multiple papers”).
* Do **not** use when only citing **outgoing references** (that belongs to `cito:cites`).
* Typically found in bibliometric statements, metadata, or citation indices (e.g., “Google Scholar shows 25 citations of this article”).

---

### Examples

 

* “**This dataset has been cited by over 20 subsequent studies.**” → `DatasetX cito:isCitedBy Paper1, Paper2, …`
* “**Smith (2020) is cited by Jones (2022).**” → `Smith2020 cito:isCitedBy Jones2022`
* “**The method described in Brown et al. (2018) was cited by WHO (2020).**” → `Brown2018 cito:isCitedBy WHO2020`
* “**According to Smith (2020)…**” → this is `cito:cites`, not `cito:isCitedBy`.
* “**Previous research has been influential.**” → vague, no explicit citing work.

 