 

### Define

An **Attribution** specifies the **agent(s)** responsible for **creating, asserting, or being accountable**  ( mp:supports/mp:challenges) for a  Representation e.g., `mp:Claim`, `mp:Statement`, `whu:DataSet`,`whu:Method``).

* Typical agents include **persons**, **institutions**, or **projects**.
* It is modeled as a subclass of  **prov:Agent** for provenance alignment.
* Attribution provides the **responsibility layer** in the micropublication framework, connecting content with its accountable source.

---

### Purpose

* **Responsibility binding**: Link representations (claims, data, methods) to their authors or accountable parties.
* **Provenance tracking**: Preserve authorship and source information to ensure accountability and reproducibility.
* **Agent integration**: Connect with `prov:Agent` instances (e.g., persons, labs, organizations).

---

### Context

Use this class **only when authorship, responsibility, or source agency is explicitly stated**.

* Trigger when a **claim, statement, or dataset** is linked to a **named agent** (person, institution, project, authority).
* Do **not** trigger for vague or generic phrases (e.g., “scientists believe”, “it is known that”).
* Avoid inference: extract only when attribution is **explicitly mentioned** in the text.

---

### Notes

* Attribution does **not** indicate whether a claim is true or false; it only records **who is responsible**.
* Link via:

  * `mp:Attribution` → `mp:suppots/mp:challenges` → `mp:Claim'
  * `mp:Attribution` → `mp:suppots/mp:challenges` → `mp:Statement`
  * `mp:Attribution` → `mp:suppots/mp:challenges` → `mp:Reference`
  * `mp:Attribution` → `mp:suppots/mp:challenges` → `whu:DataSet`
  * `mp:Attribution` → `mp:suppots/mp:challenges` → `whu:Method`
---

### Examples

*   **Attribution 1: The Authors of the Study**
    The **group of individuals** credited with conducting the research and asserting the scientific claims and findings presented in the paper. These authors are: **Siqi Zhang, Mingxing Wang, Jiang Liu, Shanyi Tian, Xueling Yang, Guangquan Xiao, Guomin Xu, Tao Jiang, and Dingyong Wang**. They are collectively accountable for the entire scientific work, including its experimental design, execution, data interpretation, and reported conclusions.

*   **Attribution 2: Environmental Biogeochemistry Laboratory of Natural Organic Matter (NOM-Lab)**
    This **institution/laboratory** is directly responsible for the execution and accountability of the **Dissolved Organic Matter (DOM) characterization**. Specifically, it conducted measurements of DOM concentration, optical analyses (fluorescence and UV-Vis measurements), and the calculation of various spectral parameters, which are key supporting elements for the study's claims regarding DOM characteristics. The NOM-Lab is located at Southwest University (SWU).
 
 
 