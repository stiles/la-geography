# QGIS review guide: LA County cities layer

_Purpose: Investigate fragmentation and determine best processing approach_

## The problem

The LA County cities layer has **347 features** but should represent ~88 cities + unincorporated communities.

**Key Issues to Investigate:**
1. **Fragmentation** - Are cities split into multiple polygons?
2. **Giant "Unincorporated"** - One polygon is 2,215 sq mi (54% of LA County!)
3. **Tiny slivers** - Some features are < 0.01 sq mi (data quality issue?)

---

## QGIS investigation steps

### 1. Load the data

```
File → Open → data/standard/la_county_cities.geojson
```

Or drag and drop into QGIS.

### 2. Style by city name

**Purpose**: Visualize fragmentation - same city = same color

**Steps:**
1. Right-click layer → Properties → Symbology
2. Change from "Single Symbol" to **"Categorized"**
3. Value: `city_name`
4. Click **"Classify"**
5. Color ramp: Choose "Random colors"
6. Click **OK**

**What to look for:**
- Do you see the same color (city) in multiple disconnected areas?
- How fragmented are major cities like Los Angeles, Long Beach, Pasadena?

### 3. Identify features

Click the **"Identify Features"** tool (info icon), then:

1. **Click the giant polygon** (likely in the north - Antelope Valley?)
   - What is `city_name`? 
   - What is `city_type`?
   - What is `area_sqmi`?
   - Is it labeled "Unincorporated"?

2. **Click several small slivers** (zoom in to find tiny polygons)
   - Are these legitimate small areas or data errors?
   - Do they have the same `city_name` as adjacent larger polygons?

3. **Click Los Angeles** (should be the large central area)
   - How many separate polygons make up Los Angeles?
   - Select by attributes: `city_name` = 'Los Angeles'
   - Use **Select Features** tool → hold Shift → click multiple parts
   - Check status bar: "X features selected"

### 4. Create a selection by city

**Select all "Los Angeles" features:**
1. Open Attribute Table (Right-click layer → Open Attribute Table)
2. Click **"Select features using an expression"** (yellow ε icon)
3. Expression: `"city_name" = 'Los Angeles'`
4. Click **Select Features**

**What to look for:**
- How many features are selected?
- Are they all contiguous, or are there islands/exclaves?
- Do the boundaries look clean or are there obvious data issues?

### 5. Analyze the "unincorporated" type

**Filter to unincorporated areas:**
1. Right-click layer → Filter...
2. Expression: `"city_type" = 'Unincorporated'`
3. Click OK

**Questions:**
- How many unincorporated polygons are there?
- Is there one giant polygon or many smaller ones?
- Do they represent distinct communities (e.g., "Altadena", "East LA", "Florence-Firestone")?
- Or are they all just labeled "Unincorporated"?

**To check distinct names:**
1. Open Attribute Table
2. Right-click `city_name` column header → "Show All Values"
3. How many unique unincorporated community names are there?

### 6. Check for multipart polygons

**Add a temporary field to count parts:**
1. Open Processing Toolbox (Ctrl+Alt+T)
2. Search: "Multipart to singleparts"
3. Run on the layer
4. Count features in output vs. input
   - Input: 347 features
   - Output: ??? features
   - If output > input, original has multipart polygons

### 7. Calculate total areas by city

**Field Calculator to sum areas by city:**
1. Attribute Table → Open Field Calculator
2. Create new field: `total_city_area`
3. Type: Decimal (double)
4. Expression:
   ```
   aggregate(
     layer:='la_county_cities',
     aggregate:='sum',
     expression:="area_sqmi",
     filter:="city_name" = attribute(@parent, 'city_name')
   )
   ```
5. This shows total area for each city across all fragments

**Export summary:**
1. Right-click layer → Export → Save Features As...
2. Format: CSV
3. Check "Skip attribute creation"
4. Select only fields: `city_name`, `city_type`, `area_sqmi`, `total_city_area`
5. Save as: `cities_summary.csv`

---

## Key questions to answer

Based on your QGIS investigation, answer:

### 1. **Fragmentation Pattern**
- [ ] Are ALL cities fragmented, or just a few?
- [ ] Is fragmentation due to:
  - [ ] Islands/exclaves (legitimate)
  - [ ] Data boundaries (e.g., split at parcel/tract lines)
  - [ ] Quality issues (slivers at borders)

### 2. **The Giant "Unincorporated" Polygon**
- [ ] What is its area? (Expected: ~2,215 sq mi)
- [ ] Where is it located? (Antelope Valley? Entire unincorporated area?)
- [ ] Does it have a specific `city_name` or just "Unincorporated"?
- [ ] Should it be one polygon or many distinct communities?

### 3. **Data quality**
- [ ] How many features are < 0.01 sq mi?
- [ ] Are tiny slivers legitimate (small parks, right-of-ways) or errors?
- [ ] Do city boundaries look clean or ragged?

### 4. **Processing decision**
Should we:
- **Option A**: Dissolve by `city_name` → ~88 features (one per city)
  - ✅ Clean, simple
  - ⚠️ Loses information about fragments
  - ⚠️ Creates huge "Unincorporated" blob
  
- **Option B**: Keep fragments, add `city_id` grouping → 347 features
  - ✅ Preserves all geometry
  - ✅ Allows analysis of islands/exclaves
  - ⚠️ More complex to work with
  
- **Option C**: Filter to incorporated cities only → ~157 features
  - ✅ Cleaner for city-level analysis
  - ⚠️ Loses unincorporated communities
  - 💡 Create separate layer for unincorporated areas?

- **Option D**: Use a different data source
  - Look for pre-dissolved LA County cities
  - May have cleaner community boundaries

---

## Export for further analysis

After your review, export these for discussion:

1. **Screenshot of full county** (styled by city_name)
   - Project → Import/Export → Export Map to Image
   - Save as: `cities_overview.png`

2. **Screenshot of problematic area** (e.g., giant Unincorporated polygon)
   - Zoom to area
   - Export as: `cities_problem_area.png`

3. **Attribute summary** (from Field Calculator above)
   - Save as: `cities_summary.csv`

4. **Selected features** (e.g., Los Angeles only)
   - Select Los Angeles features
   - Right-click → Export → Save Selected Features As...
   - Save as: `los_angeles_fragments.geojson`
