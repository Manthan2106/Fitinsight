# Phase 4 activity clustering

Install the project dependencies with `python -m pip install -r requirements.txt` under Python 3.12. From the project root, run `python src/activity_clustering.py` using the processed `data/processed/daily_activity_clean.csv`. Outputs go under `reports/generated/activity_clustering/`.

The script builds one row per participant with at least three eligible days. It uses mean steps, mean active share of recorded minutes, mean very active minutes, and step-count standard deviation. It keeps zero-step records with positive recorded time. Sleep coverage is limited. Distance closely tracks steps, and sedentary share is redundant with active share. These variables are omitted from the model.

Each cohort is standardized separately. K-Means compares inertia, silhouette, Davies–Bouldin, and Calinski–Harabasz across K values. Selection uses the highest silhouette among candidates with at least two participants per cluster. DBSCAN reports noise separately and computes scores on assigned participants only. PCA visualizes the standardized features and exports loadings and explained variance.

| Cohort | Participants | Selected K | Cluster sizes | Variance explained by first two PCs |
| --- | ---: | ---: | --- | ---: |
| All days with positive recorded time | 35 | 3 | 17, 16, 2 | 85.7% |
| Complete days | 24 | 2 | 18, 6 | 88.9% |

The all-days clusters average approximately 3,100, 8,992, and 16,131 steps per day. The highest-step group contains two participants. Comparing the two fits on their 24 shared participants gives an adjusted Rand index of 0.537. Filtering changes both the input days and who qualifies, so treat the profiles as exploratory.

For all days, DBSCAN with `eps=1.0` and `min_samples=3` found three groups and marked eight participants as noise. Many other settings produced a single group. The density-based results depend on the chosen parameters.
