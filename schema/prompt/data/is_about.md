 
### **Definition**
The relation `iao:is_about` (from the Information Artifact Ontology, IAO) links an *information content entity* (e.g., a `whu:DataSet`) to the entity it is about (e.g., a `whu:Specimen` or `whu:Reagent`).
In this project, `iao:is_about` captures when a `whu:DataSet` explicitly refers to or describes specific properties of specimens or reagents — such as **quantity, weight, concentration, or count of collected items**.

### **Context**
Extract this relation **only** when the text clearly states that a `whu:DataSet` is about a `whu:Specimen` or `whu:Reagent`.

* Do **not** infer from co-mention or background knowledge.
* Prefer explicit mentions (e.g., “the dataset records the weight of samples” or “the dataset contains counts of reagents used”).
* Ensure the **subject** is a `whu:DataSet` and the **object** is either `whu:Specimen` or `whu:Reagent`.

### **Examples**
 
1.  **Example 1: Total and Methylmercury Content in Soil**
    *   **The information content entity (`whu:DataSet`)**: The reported values of total mercury (THg) and methylmercury (MeHg) in purple soils.
    *   **The relationship (`iao:is_about`)**: These values explicitly describe the content of mercury in the specified soil.
    *   **The entity it is about (`whu:Specimen`)**: Purple soils.
    *   **Specific property described**: **Concentration/content** of THg and MeHg (152.10 ng/g and 0.08 ng/g, respectively).

2.  **Example 2: Added Mercury Content in Soil**
    *   **The information content entity (`whu:DataSet`)**: The specified amount of exogenous mercury (HgCl2 solution) added to the pots.
    *   **The relationship (`iao:is_about`)**: This amount explicitly indicates the content of added mercury in the soil.
    *   **The entity it is about (`whu:Specimen`)**: The soil in the pots.
    *   **Specific property described**: **Quantity/concentration** of added mercury (approximately 5 μg/g).

3.  **Example 3: Quantities of Fertilizers (Reagents) Added to Soil**
    *   **The information content entity (`whu:DataSet`)**: The specified amounts of various fertilizers added.
    *   **The relationship (`iao:is_about`)**: These amounts explicitly state the quantities of the reagents used to adjust soil nutrients.
    *   **The entity it is about (`whu:Reagent`)**: Ammonium acetate, Ca(H2PO4)2, and KCl.
    *   **Specific property described**: **Quantities/concentrations** of reagents (150 μg/g ammonium acetate, 100 μg/g Ca(H2PO4)2, and 85 μg/g KCl).