"""Build and compare participant-level activity clusters from Fitbit daily records."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


ROOT = Path(__file__).resolve().parents[1]
FEATURES = ["mean_steps", "mean_active_share", "mean_vigorous_minutes", "step_variability"]


def participant_features(days):
    """Require at least three recorded days to estimate within-person variation."""
    days = days.copy()
    days["active_share"] = (
        days["lightly_active_minutes"] + days["fairly_active_minutes"]
        + days["very_active_minutes"]
    ) / days["total_recorded_minutes"]
    features = days.groupby("id").agg(
        recorded_days=("activity_date", "size"),
        mean_steps=("total_steps", "mean"),
        mean_active_share=("active_share", "mean"),
        mean_vigorous_minutes=("very_active_minutes", "mean"),
        step_variability=("total_steps", "std"),
    )
    return features.loc[features["recorded_days"].ge(3)].dropna(subset=FEATURES)


def scores(values, labels):
    return {
        "silhouette": silhouette_score(values, labels),
        "davies_bouldin": davies_bouldin_score(values, labels),
        "calinski_harabasz": calinski_harabasz_score(values, labels),
    }


def analyze(features, output):
    output.mkdir(parents=True, exist_ok=True)
    values = StandardScaler().fit_transform(features[FEATURES])
    kmeans_results = []
    models = {}
    for k in range(2, min(6, len(features) - 1) + 1):
        model = KMeans(n_clusters=k, n_init=20, random_state=42).fit(values)
        sizes = pd.Series(model.labels_).value_counts()
        if len(sizes) != k:
            continue
        models[k] = model
        kmeans_results.append({
            "k": k, "inertia": model.inertia_, "smallest_cluster": sizes.min(),
            **scores(values, model.labels_),
        })

    if not kmeans_results:
        raise ValueError("Too few distinct participant profiles for K-Means evaluation.")
    evaluation = pd.DataFrame(kmeans_results)
    evaluation.to_csv(output / "kmeans_scores.csv", index=False)
    eligible = evaluation.loc[evaluation["smallest_cluster"].ge(2)]
    if eligible.empty:
        raise ValueError("No K-Means candidate has at least two participants in every cluster.")
    selected_k = int(eligible.sort_values(["silhouette", "k"], ascending=[False, True]).iloc[0]["k"])
    profiles = features.assign(cluster=models[selected_k].labels_)
    profiles.to_csv(output / "participants.csv")
    profiles.groupby("cluster")[FEATURES].mean().join(
        profiles.groupby("cluster").size().rename("participants")
    ).to_csv(output / "cluster_profiles.csv")

    density_results = []
    for min_samples in (3, 4, 5):
        for eps in (0.75, 1.0, 1.25, 1.5, 2.0):
            labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(values)
            retained = labels != -1
            groups = len(set(labels[retained]))
            row = {
                "eps": eps, "min_samples": min_samples,
                "clusters": groups, "noise": int((~retained).sum()),
            }
            if 2 <= groups < retained.sum():
                row.update(scores(values[retained], labels[retained]))
            density_results.append(row)
    pd.DataFrame(density_results).to_csv(output / "dbscan_scores.csv", index=False)

    pca = PCA().fit(values)
    components = [f"PC{i}" for i in range(1, len(FEATURES) + 1)]
    pd.DataFrame(pca.components_.T, index=FEATURES, columns=components).to_csv(
        output / "pca_loadings.csv"
    )
    variance = pd.Series(pca.explained_variance_ratio_, index=components)
    pd.DataFrame({"variance_ratio": variance, "cumulative": variance.cumsum()}).to_csv(
        output / "pca_variance.csv"
    )
    coordinates = pca.transform(values)
    fig, ax = plt.subplots()
    for cluster in sorted(profiles["cluster"].unique()):
        mask = profiles["cluster"].eq(cluster).to_numpy()
        ax.scatter(coordinates[mask, 0], coordinates[mask, 1], label=f"Cluster {cluster}")
    ax.set(xlabel=f"PC1 ({variance.iloc[0]:.1%})", ylabel=f"PC2 ({variance.iloc[1]:.1%})")
    ax.legend()
    fig.savefig(output / "pca_clusters.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"{output.name}: {len(features)} participants, K={selected_k}, PC1–2={variance.iloc[:2].sum():.1%}")
    return profiles["cluster"]


def main():
    path = ROOT / "data" / "processed" / "daily_activity_clean.csv"
    days = pd.read_csv(path, dtype={"id": "string"})
    # A zero-minute day cannot supply a valid activity share. Keep zero-step days
    # with positive duration because they are valid recorded observations.
    days = days.loc[days["total_recorded_minutes"].gt(0)]
    output = ROOT / "reports" / "generated" / "activity_clustering"
    with threadpool_limits(limits=1):
        all_labels = analyze(participant_features(days), output / "all_days")
        complete_labels = analyze(
            participant_features(days.loc[days["is_complete_day"]]), output / "complete_days"
        )
    shared = all_labels.index.intersection(complete_labels.index)
    agreement = adjusted_rand_score(all_labels.loc[shared], complete_labels.loc[shared])
    print(f"Cohort comparison: {len(shared)} shared participants, adjusted Rand index {agreement:.3f}")


if __name__ == "__main__":
    main()
