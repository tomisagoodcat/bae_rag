 
### Define

A **scalar measurement datum** representing a **single numeric value** (or range), with an optional **unit** (string label) and an optional **logical comparator** (e.g., `<`, `<=`, `between`).

* It is modeled as a subclass of **iao\:DataItem** and aligned with **qudt\:QuantityValue**, ensuring compatibility with scientific data representation.
* **whu\:ScalarMeasurementDatum** always belongs to a parent `whu:Data` (dataset) and provides fine-grained measurement detail within a table, figure, or experimental record.
* This class captures explicit values from scientific text, e.g., *“2.1 mg/kg Cd concentration”*, where `value=2.1`, `unit=mg/kg`.

---

### Purpose

* **Granularity**: Represent fine-grained numeric measurements inside a dataset.
* **Evidence anchoring**: Enable specific values (e.g., *“Hg < 0.2 mg/kg”*) to support or challenge a `mp:Claim` via their parent dataset.
* **Unit consistency**: Preserve scientific units for interoperability with ontologies such as QUDT.
* **Range & comparator handling**: Support expressions like `> 20`, `< 5`, or `12–15`.

---

### Context

Use this class **only when the text provides explicit numeric values** (with optional unit and comparator).
Avoid vague descriptions without numbers.

* Trigger when a **measurement value** (float/int) appears with or without a unit.
* Trigger when there is a **comparator** (`<`, `>`, `<=`, `>=`, `between`) tied to the value.
* Trigger when there is a **range** (e.g., `12–15 mg/kg`).
* **Do not** create if only qualitative descriptions appear (e.g., “high concentration”, “elevated level”).
* Always link the `whu:ScalarMeasurementDatum` to its parent `whu:DataSet` via `dcterms:hasPart`.

---

### Notes

* Extract **value**, **unit**, and **comparator** separately when present.
* If multiple numbers appear in a range, represent them as `[lower bound, upper bound]`.
* If no unit is given, record value but leave unit field empty.
* One dataset (`whu:DataSet`) can contain multiple `whu:ScalarMeasurementDatum` entries.
---
### Use semantic links

* `whu:DataSet` → `dcterms:hasPart` → `whu:ScalarMeasurementDatum`
* `whu:ScalarMeasurementDatum` → `iao:hasMeasurementUnit` → sting value
* `whu:ScalarMeasurementDatum` → `iao:hasMeasurementValue` →float value
* `whu:ScalarMeasurementDatum` → `whu:hascomparator` → comparator symbol (`<`, `>`, `<=`, `>=`, `between`)
---
### Examples

* “Cadmium concentration was **0.15 mg/kg**.” → `value=0.15`, `unit=mg/kg`
* “Hg **< 0.2 mg/kg**.” → `value=0.2`, `unit=mg/kg`, `comparator=<`
* “Temperature **25 °C**.” → `value=25`, `unit=°C`
* “Lead concentration ranged **12–15 mg/kg**.” → `value=[12,15]`, `unit=mg/kg`, `comparator=between`


