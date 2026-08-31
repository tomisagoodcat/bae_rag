 
### Define

`mp:argues` links a **Micropublication (`mp:Micropublication`)** to the **central Claim (`mp:Claim`)** that it advances.

* It expresses the **primary argumentative direction**: every Micropublication is constructed to argue exactly **one central Claim**.
* This relation is **obligatory** for a valid MPU: without it, the MPU lacks an argumentative nucleus.

---

### Purpose

* **Argumentative anchoring**: Ensure each MPU is tied to a **core Claim**.
* **Graph integrity**: Distinguish the **central Claim** from supporting Statements or Data.
* **Reasoning clarity**: Provide a direct link for downstream reasoning engines and reproducibility tracking.

---

### Context

Use this property **only when the text explicitly states that a Micropublication (or evidence package) makes or advances a Claim**.

* Trigger when the MPU is described as *asserting*, *putting forward*, *arguing*, or *centering on* a Claim.
* Do **not** infer this relation from co-mention or indirect implication (e.g., a Claim and MPU appearing together without clear argumentative connection).
* Each MPU should have **exactly one `mp:argues` Claim**.

---

### Notes

* `mp:argues` is distinct from `mp:supports` / `mp:challenges`, which connect **evidence** (Data, Method, Reference) to Claims or Statements.
* Supporting `mp:Statement` nodes may be present inside the MPU, but the **nucleus Claim** must always be identified via `mp:argues`.
* A Micropublication can include multiple elements, but only **one Claim** is its argumentative target.

---

### Use semantic links

* `(mp:Micropublication)` → `mp:argues` → `(mp:Claim)`

---

### Examples
 
*   **Micropublication 1: Biochar altered DOM and enhanced microbial activity `mp:argues` its central Claim:**
    *   This relation signifies that the micropublication, titled "Biochar altered DOM and enhanced microbial activity," is built to advance the central claim that **biochar addition significantly altered porewater dissolved organic matter (DOM) characteristics and enhanced microbial activity in paddy soils**.

*   **Micropublication 2: Modified biochar decreased MeHg production in soils `mp:argues` its central Claim:**
    *   This relation indicates that the micropublication, titled "Modified biochar decreased MeHg production in soils," puts forth the central claim that **only modified biochar effectively decreased methylmercury (MeHg) production in paddy soils, while original biochar had no significant effect on soil MeHg**.

 
 
 
