 

### Define

A **Reference** (`mp:Reference`) encodes a **bibliographic citation or source link** that is explicitly tied to a `mp:Representation` (e.g., `mp:Claim`, `mp:Statement`, `whu:DataSet`, `whu:Method`).

* References typically follow **standard citation formats** (author–year, numbered references, DOI, or URL).
* In publications, references usually appear in the **References / Bibliography section**, but may also be cited **inline** (e.g., “Smith 2020”, “\[15]”, “DOI:10.1234/abcd”).
* References provide **documented provenance** and contextualize a Representation, but do **not** themselves support or challenge claims.

---

### Purpose

* **Citation anchoring**: Connect scientific statements with their bibliographic sources.
* **Provenance**: Track external works or datasets that underpin a Representation.
* **Normalization**: Represent citations in a **standard bibliographic format** (APA, numbered, DOI/URL) for consistency.

---

### Context

Use this class **only when explicit references are present in the text**.

* Trigger when a Representation cites a **work, dataset, or external source** using author–year style (“Smith 2020”), numbered style (\[12]), or persistent identifiers (DOI, URL).
* Do **not** trigger for vague mentions without explicit source (e.g., “previous studies have shown”, “it is widely known”).
* When possible, normalize the extracted reference to a **standard citation string** and link it to the Representation.

---

### Notes

* A `mp:Reference` always points to an **external source**, not to internal narrative.
* When multiple references occur together (e.g., “Smith 2020; Zhang 2021”), extract each as a **separate `mp:Reference`**.
* If a DOI/URL is present, include it in the citation entry.

---

### Use semantic links

*  `mp:Reference`→`cito:isCitedBy` → `mp:Claim/mp:Statement/whu:DataSet/whu:Method) `

---

### Examples
 
*   **Challenged Statement:** The general belief that **"biochar and its modified forms have been illustrated as a helpful way to alleviate Hg pollution"** in various soil/sediment systems.
    **Challenging Statement:** **"In contrast, some other studies have reported that the effect of biochar on the remediation of Hg-contaminated soil/sediment is not as good as expected."** For example, Shu et al. (2016) reported that biochar application **"increased the MeHg content of soils"**.

*   **Challenged Statement:** There is a **"consensus that DOM, in general, can influence Hg bioavailability and methylation potential in two ways"**.
    **Challenging Statement:** **"However, the relationships between Hg and DOM observed in both field investigations and the laboratory have been inconsistent, even concerning the above mechanisms"**.
 


 