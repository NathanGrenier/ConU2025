# About

Question: In the city of Montreal, does the violation of environmental regulations by companies have a direct an noticeable impact on the city's air and water quality? (Water quality is a stretch goal)

## Team Members

| Name           | Email                     |
| -------------- | ------------------------- |
| Nathan Grenier | nathangrenier01@gmail.com |
| Neil Fisher    | neil3524@gmail.com        |

# Contributing

## Stations Data

The station data downloaded from the [Montreal Open API](https://donnees.montreal.ca/dataset/rsqa-liste-des-stations) had a malformed heading. They duplicated the column names. You should remove them or just us the existing file in the repo.

# Regulations

## [Summary of Montreal's Regulation 2001-10 on Atmospheric Discharges](https://cmm.qc.ca/documentation/reglements/reglement-sur-les-rejets-a-latmosphere/)

**Code:** 2001-10

### 1. Scope and Purpose
The regulation aims to control air pollution by setting strict standards for emissions from industrial, commercial, and municipal activities within the Montreal Agglomeration. It covers pollutants from chimneys, incinerators, vehicles, fuels, and industrial processes.

### 2. Key Provisions

#### A. Pollutant Limits (Articles 3.01–3.07)
- **Table 3.01** lists **maximum allowable concentrations** for over 200 pollutants (e.g., benzene, formaldehyde, sulfur dioxide, particulate matter) over varying timeframes (0.25h, 1h, 8h, etc.).
- **Formulas** are provided to calculate pollutant dispersion (e.g., effective chimney height, wind speed).
- **Opacity restrictions**: Smoke opacity must not exceed Ringelmann Scale No. 1 (20% black).

#### B. Fuel and Combustion Standards (Articles 4.01–4.15)
- **Sulfur limits** for fuels:
  - Light oil: ≤ 0.4% sulfur
  - Intermediate oil: ≤ 1.0% sulfur
  - Heavy oil: ≤ 1.25–1.5% sulfur (depending on location and usage).
- Prohibits burning coal if sulfur emissions exceed those from compliant oils.
- **Diesel fuel** must contain ≤ 0.05% sulfur (exemptions for locomotives).

#### C. Waste Management (Articles 5.01–5.94)
- **Incineration rules** for:
  - **Municipal waste**: Requires continuous monitoring (CO, O₂, particulates), 1100°C combustion for ≥1.2 seconds, and annual performance tests.
  - **Biomedical waste**: Separate storage at <4°C, radioactive detection systems, and strict emission limits.
  - **Soil treatment**: Must achieve 99.99–99.9999% destruction efficiency for contaminants.
  - **Wood/residues**: Particulate limits (70–100 mg/m³) and efficiency standards.
- **Open burning** is banned except for authorized fires (e.g., fire drills).

#### D. Industrial and Commercial Activities (Article 6)
- **Emission reduction requirements** for sectors like:
  - Dry cleaning (97% VOC reduction).
  - Painting (90% VOC reduction).
  - Metal plating (50 mg/m³ particulate limit).
  - Petrochemicals: Leak detection and repair (LDAR) programs for organic compounds.
- **Storage tanks** ≥75 m³ must use floating roofs or equivalent controls.

#### E. Fugitive Emissions (Article 7)
- Prohibits visible dust beyond 2 meters from emission sources.
- Requires dust suppression (e.g., water spraying, enclosures) for construction, demolition, and material handling.

### 3. Administrative Requirements
- **Permits** (Article 8.04): Required for constructing/modifying emission sources (e.g., incinerators, crematoriums, industrial equipment).
- **Reporting**: Annual reports on emissions, fuel usage, and compliance (e.g., sulfur content in fuels).
- **Monitoring**: Continuous emission monitoring for incinerators and periodic testing for industrial equipment.

### 4. Enforcement and Penalties
- **Non-compliance** (e.g., exceeding emission limits, improper waste incineration) can lead to fines or operational shutdowns.
- **Landowners** are liable for illegal open burning on their property.

### 5. Key Definitions
- **Atmosphere**: Outdoor air excluding indoor/underground spaces.
- **Particulates**: Airborne particles <20 micrometers.
- **Odorous pollutants**: Must not exceed 1 odor unit/m³ beyond property limits.

### Significance
This regulation is a cornerstone of Montreal’s air quality management, targeting industrial emissions, waste management, and fuel quality to protect public health and the environment. Its strict standards align with Quebec’s broader environmental goals, emphasizing pollution prevention through technology and compliance.