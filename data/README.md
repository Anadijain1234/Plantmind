# Data sources and credits

The raw datasets are **not** stored in this repository (some are hundreds of MB, and some licences do not allow re-sharing). Only small processed files (`data/processed/`) and the industry packs (`data/packs/`) are included.

| Dataset | Source | Licence / terms | What we keep |
|---|---|---|---|
| Team sensor readings | Shared by a team member (`sensor_data.csv`) | Team data | 3 machines, first ~33 hours of readings |
| Microsoft Azure Predictive Maintenance | Kaggle — search "Microsoft Azure Predictive Maintenance" | As published on Kaggle | Model card, risk per machine on one test day, failures by month |
| AI4I 2020 Predictive Maintenance | [UCI ML Repository](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset) | CC BY 4.0 | Failure-mode counts and rules |
| Indian Food 101 | Kaggle — "Indian Food 101" | As published on Kaggle | 255 dishes (name, ingredients, times, region) |
| Zomato Bangalore Restaurants | Kaggle — "Zomato Bangalore Restaurants" (scraped 2019) | Unclear → we keep **counts only**, no review text | Complaint counts per dish |
| NYC restaurant inspections | [NYC Open Data — DOHMH Restaurant Inspection Results](https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j) (cuisine = Indian) | NYC Open Data terms (public) | Top violations and counts |
| FDA MAUDE device reports | [openFDA](https://open.fda.gov/apis/device/event/) | Public domain | 276 malfunction reports (patient details removed) |
| NHTSA owner complaints | [NHTSA API](https://www.nhtsa.gov/nhtsa-datasets-and-apis) — Honda Civic 2018, Toyota Corolla 2018 | Public domain | 732 complaints (VINs removed) |
| Public post-mortems | [danluu/post-mortems](https://github.com/danluu/post-mortems) | As published on GitHub | 240 short summaries with links |
| Loghub | [logpai/loghub](https://github.com/logpai/loghub) | Free for research/academic use, cite the repo | Top log patterns per system |

Facts used inside expert tips: ISO 10816-1 vibration zones, FSSAI used-cooking-oil rule (25% total polar compounds), NYC Health hot/cold holding temperatures, WHO Surgical Safety Checklist, WHO sterilisation guidance, SAE J2012 OBD-II code meanings, GitLab 2017 public post-mortem.

**People and companies in the demo are fictional.**

## Rebuild the processed files

Put the raw files in one folder (names listed at the top of `scripts/process_public_data.py`), then:

```bash
python scripts/process_public_data.py <raw folder> && python scripts/train_failure_model.py <folder with PdM_*.csv> && python scripts/build_packs.py
```
