"""Small, deterministic clustering and PCA primitives for Phase 4.

This module intentionally uses only Python's standard library. Its algorithms
are tested against synthetic cases and documented as repository-local
implementations, not as bit-for-bit replacements for scikit-learn.
"""

from __future__ import annotations

import math
import random
from collections import Counter, deque
from typing import Sequence

Vector = Sequence[float]
Matrix = Sequence[Vector]


def mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("mean requires at least one value")
    return sum(values) / len(values)


def sample_standard_deviation(values: Sequence[float]) -> float:
    """Return the sample SD (n - 1); a single observation has no SD."""
    if len(values) < 2:
        raise ValueError("sample standard deviation requires at least two values")
    center = mean(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / (len(values) - 1))


def euclidean(left: Vector, right: Vector) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have equal dimensions")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def squared_euclidean(left: Vector, right: Vector) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have equal dimensions")
    return sum((a - b) ** 2 for a, b in zip(left, right))


def pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    mean_left = mean(left)
    mean_right = mean(right)
    centered_left = [value - mean_left for value in left]
    centered_right = [value - mean_right for value in right]
    denominator = math.sqrt(
        sum(value * value for value in centered_left)
        * sum(value * value for value in centered_right)
    )
    if denominator == 0:
        return None
    return sum(a * b for a, b in zip(centered_left, centered_right)) / denominator


def standardize(
    values: Matrix, *, tolerance: float = 1e-12
) -> tuple[list[list[float]], list[dict[str, float | bool]]]:
    """Z-score columns using population SD; constant columns map to zero."""
    if not values or not values[0]:
        raise ValueError("standardization requires a non-empty rectangular matrix")
    width = len(values[0])
    if any(len(row) != width for row in values):
        raise ValueError("matrix rows must have equal dimensions")
    if any(not math.isfinite(value) for row in values for value in row):
        raise ValueError("standardization requires finite values")

    metadata: list[dict[str, float | bool]] = []
    columns: list[list[float]] = []
    for column_index in range(width):
        column = [row[column_index] for row in values]
        center = mean(column)
        population_sd = math.sqrt(sum((value - center) ** 2 for value in column) / len(column))
        constant = population_sd <= tolerance
        metadata.append({
            "mean": center,
            "population_sd": population_sd,
            "constant": constant,
        })
        columns.append(
            [0.0 for _ in column]
            if constant
            else [(value - center) / population_sd for value in column]
        )
    return [
        [columns[column_index][row_index] for column_index in range(width)]
        for row_index in range(len(values))
    ], metadata


def _nearest_labels(points: Matrix, centers: Matrix) -> list[int]:
    return [
        min(range(len(centers)), key=lambda index: squared_euclidean(point, centers[index]))
        for point in points
    ]


def _centroids(points: Matrix, labels: Sequence[int], k: int) -> list[list[float]]:
    width = len(points[0])
    counts = [0] * k
    totals = [[0.0] * width for _ in range(k)]
    for point, label in zip(points, labels):
        counts[label] += 1
        for column, value in enumerate(point):
            totals[label][column] += value
    if any(count == 0 for count in counts):
        raise ValueError("cannot calculate a centroid for an empty cluster")
    return [[value / counts[index] for value in totals[index]] for index in range(k)]


def _repair_empty_clusters(
    points: Matrix, labels: list[int], centers: list[list[float]], k: int
) -> tuple[list[int], list[list[float]]]:
    """Move a farthest point from a non-singleton donor to each empty cluster."""
    counts = Counter(labels)
    for empty in range(k):
        if counts[empty]:
            continue
        candidates = sorted(
            (
                squared_euclidean(point, centers[label]),
                -index,
                index,
                label,
            )
            for index, (point, label) in enumerate(zip(points, labels))
            if counts[label] > 1
        )
        if not candidates:
            raise ValueError("could not repair an empty K-Means cluster")
        _, _, point_index, donor = candidates[-1]
        labels[point_index] = empty
        counts[donor] -= 1
        counts[empty] += 1
        centers[empty] = list(points[point_index])
    return labels, centers


def _kmeans_once(
    points: Matrix, k: int, *, seed: int, max_iter: int, tolerance: float
) -> tuple[list[int], list[list[float]], float, int]:
    rng = random.Random(seed)
    chosen = [rng.randrange(len(points))]
    centers = [list(points[chosen[0]])]
    while len(centers) < k:
        weights = [
            min(squared_euclidean(point, center) for center in centers)
            if index not in chosen
            else 0.0
            for index, point in enumerate(points)
        ]
        weight_sum = sum(weights)
        if weight_sum <= tolerance:
            next_index = rng.choice([index for index in range(len(points)) if index not in chosen])
        else:
            threshold = rng.random() * weight_sum
            running = 0.0
            next_index = -1
            for index, weight in enumerate(weights):
                running += weight
                if running >= threshold and index not in chosen:
                    next_index = index
                    break
            if next_index < 0:
                next_index = next(index for index in range(len(points)) if index not in chosen)
        chosen.append(next_index)
        centers.append(list(points[next_index]))

    labels = [-1] * len(points)
    iteration = 0
    for iteration in range(1, max_iter + 1):
        assigned = _nearest_labels(points, centers)
        assigned, repaired_centers = _repair_empty_clusters(points, assigned, centers, k)
        updated = _centroids(points, assigned, k)
        movement = max(
            euclidean(before, after)
            for before, after in zip(repaired_centers, updated)
        )
        stable_labels = assigned == labels
        labels = assigned
        centers = updated
        if stable_labels and movement <= tolerance:
            break

    labels = _nearest_labels(points, centers)
    labels, centers = _repair_empty_clusters(points, labels, centers, k)
    centers = _centroids(points, labels, k)
    inertia = sum(squared_euclidean(point, centers[label]) for point, label in zip(points, labels))
    return labels, centers, inertia, iteration


def kmeans_fit(
    points: Matrix,
    k: int,
    *,
    n_init: int = 20,
    seed: int = 42,
    max_iter: int = 300,
    tolerance: float = 1e-10,
) -> dict:
    """Run deterministic K-Means++-style starts and retain minimum inertia.

    Centroid initialization, tie-breaking, and empty-cluster repair are explicit
    local choices; results need not be numerically identical to scikit-learn.
    """
    if not points or any(len(row) != len(points[0]) for row in points):
        raise ValueError("K-Means requires a non-empty rectangular matrix")
    if any(not math.isfinite(value) for row in points for value in row):
        raise ValueError("K-Means requires finite values")
    if not 1 <= k < len(points):
        raise ValueError("K-Means requires 1 <= k < number of rows")
    if n_init < 1 or max_iter < 1:
        raise ValueError("n_init and max_iter must be positive")

    best: dict | None = None
    for restart in range(n_init):
        labels, centers, inertia, iterations = _kmeans_once(
            points,
            k,
            seed=seed + restart,
            max_iter=max_iter,
            tolerance=tolerance,
        )
        candidate = {
            "labels": labels,
            "centers": centers,
            "inertia": inertia,
            "iterations": iterations,
            "seed": seed,
            "n_init": n_init,
            "max_iter": max_iter,
        }
        if best is None or (inertia, tuple(labels)) < (best["inertia"], tuple(best["labels"])):
            best = candidate
    assert best is not None
    return best


def silhouette_score(points: Matrix, labels: Sequence[int]) -> float | None:
    """Mean silhouette using Euclidean distances; invalid partitions return None."""
    if len(points) != len(labels) or len(points) < 3:
        return None
    groups: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        groups.setdefault(label, []).append(index)
    if not 2 <= len(groups) < len(points):
        return None
    distances = [
        [euclidean(left, right) for right in points]
        for left in points
    ]
    values: list[float] = []
    for index, label in enumerate(labels):
        own = groups[label]
        if len(own) == 1:
            values.append(0.0)
            continue
        within = sum(distances[index][other] for other in own if other != index) / (len(own) - 1)
        between = min(
            sum(distances[index][other] for other in members) / len(members)
            for other_label, members in groups.items()
            if other_label != label
        )
        denominator = max(within, between)
        values.append(0.0 if denominator == 0 else (between - within) / denominator)
    return mean(values)


def davies_bouldin_score(points: Matrix, labels: Sequence[int]) -> float | None:
    if len(points) != len(labels):
        return None
    groups: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        groups.setdefault(label, []).append(index)
    if not 2 <= len(groups) < len(points):
        return None
    centers = {
        label: [
            mean([points[index][column] for index in members])
            for column in range(len(points[0]))
        ]
        for label, members in groups.items()
    }
    spreads = {
        label: mean([euclidean(points[index], centers[label]) for index in members])
        for label, members in groups.items()
    }
    ratios: list[float] = []
    labels_sorted = sorted(groups)
    for label in labels_sorted:
        comparisons = []
        for other in labels_sorted:
            if other == label:
                continue
            separation = euclidean(centers[label], centers[other])
            if separation == 0:
                return None
            comparisons.append((spreads[label] + spreads[other]) / separation)
        ratios.append(max(comparisons))
    return mean(ratios)


def calinski_harabasz_score(points: Matrix, labels: Sequence[int]) -> float | None:
    if len(points) != len(labels) or len(points) < 3:
        return None
    groups: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        groups.setdefault(label, []).append(index)
    k = len(groups)
    n = len(points)
    if not 2 <= k < n:
        return None
    overall = [mean([row[column] for row in points]) for column in range(len(points[0]))]
    between = 0.0
    within = 0.0
    for members in groups.values():
        center = [mean([points[index][column] for index in members]) for column in range(len(overall))]
        between += len(members) * squared_euclidean(center, overall)
        within += sum(squared_euclidean(points[index], center) for index in members)
    if within == 0:
        return None
    return (between / (k - 1)) / (within / (n - k))


def cluster_scores(points: Matrix, labels: Sequence[int]) -> dict[str, float | None]:
    return {
        "silhouette": silhouette_score(points, labels),
        "davies_bouldin": davies_bouldin_score(points, labels),
        "calinski_harabasz": calinski_harabasz_score(points, labels),
    }


def adjusted_rand_index(left: Sequence[int], right: Sequence[int]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("ARI requires aligned label vectors with at least two items")
    left_counts = Counter(left)
    right_counts = Counter(right)
    joint_counts = Counter(zip(left, right))
    choose_two = lambda count: count * (count - 1) / 2
    sum_joint = sum(choose_two(value) for value in joint_counts.values())
    sum_left = sum(choose_two(value) for value in left_counts.values())
    sum_right = sum(choose_two(value) for value in right_counts.values())
    total = choose_two(len(left))
    expected = sum_left * sum_right / total
    maximum = (sum_left + sum_right) / 2
    denominator = maximum - expected
    if denominator == 0:
        return 1.0
    return (sum_joint - expected) / denominator


def dbscan(points: Matrix, *, eps: float, min_samples: int) -> list[int]:
    """Deterministic Euclidean DBSCAN; min_samples includes the point itself."""
    if not points or any(len(row) != len(points[0]) for row in points):
        raise ValueError("DBSCAN requires a non-empty rectangular matrix")
    if eps <= 0 or not math.isfinite(eps):
        raise ValueError("eps must be positive and finite")
    if min_samples < 1:
        raise ValueError("min_samples must be positive")
    if any(not math.isfinite(value) for row in points for value in row):
        raise ValueError("DBSCAN requires finite values")

    neighborhoods = [
        [
            other
            for other, candidate in enumerate(points)
            if euclidean(point, candidate) <= eps
        ]
        for point in points
    ]
    labels: list[int | None] = [None] * len(points)
    visited: set[int] = set()
    cluster_id = 0
    for index in range(len(points)):
        if index in visited:
            continue
        visited.add(index)
        neighbors = neighborhoods[index]
        if len(neighbors) < min_samples:
            labels[index] = -1
            continue

        labels[index] = cluster_id
        queue = deque(neighbors)
        queued = set(neighbors)
        while queue:
            candidate = queue.popleft()
            if candidate not in visited:
                visited.add(candidate)
                candidate_neighbors = neighborhoods[candidate]
                if len(candidate_neighbors) >= min_samples:
                    for neighbor in candidate_neighbors:
                        if neighbor not in queued:
                            queue.append(neighbor)
                            queued.add(neighbor)
            if labels[candidate] is None or labels[candidate] == -1:
                labels[candidate] = cluster_id
        cluster_id += 1
    return [int(label) if label is not None else -1 for label in labels]


def _jacobi_eigh(matrix: Matrix, *, tolerance: float = 1e-14) -> tuple[list[float], list[list[float]], int]:
    """Eigen-decompose a small symmetric matrix by cyclic Jacobi rotations.

    Eigenvectors are returned as columns of the second result. The function is
    intended for the four-feature covariance matrix, not large matrices.
    """
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise ValueError("eigensolver requires a non-empty square matrix")
    a = [list(row) for row in matrix]
    for i in range(n):
        for j in range(n):
            if not math.isfinite(a[i][j]):
                raise ValueError("eigensolver requires finite values")
            if abs(a[i][j] - a[j][i]) > 1e-10:
                raise ValueError("eigensolver requires a symmetric matrix")
    vectors = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    max_rotations = max(1, 100 * n * n)
    rotations = 0
    for rotations in range(1, max_rotations + 1):
        p, q = max(
            ((i, j) for i in range(n) for j in range(i + 1, n)),
            key=lambda pair: abs(a[pair[0]][pair[1]]),
            default=(0, 0),
        )
        if p == q or abs(a[p][q]) <= tolerance:
            break
        angle = 0.5 * math.atan2(2.0 * a[p][q], a[q][q] - a[p][p])
        cosine = math.cos(angle)
        sine = math.sin(angle)
        app = a[p][p]
        aqq = a[q][q]
        apq = a[p][q]
        a[p][p] = cosine * cosine * app - 2 * sine * cosine * apq + sine * sine * aqq
        a[q][q] = sine * sine * app + 2 * sine * cosine * apq + cosine * cosine * aqq
        a[p][q] = a[q][p] = 0.0
        for index in range(n):
            if index in (p, q):
                continue
            aip = a[index][p]
            aiq = a[index][q]
            a[index][p] = a[p][index] = cosine * aip - sine * aiq
            a[index][q] = a[q][index] = sine * aip + cosine * aiq
        for index in range(n):
            vip = vectors[index][p]
            viq = vectors[index][q]
            vectors[index][p] = cosine * vip - sine * viq
            vectors[index][q] = sine * vip + cosine * viq
    else:
        raise ArithmeticError("Jacobi eigensolver did not converge within its rotation bound")
    eigenvalues = [a[index][index] for index in range(n)]
    order = sorted(range(n), key=lambda index: (-eigenvalues[index], index))
    sorted_values = [eigenvalues[index] for index in order]
    sorted_vectors = [
        [vectors[row][index] for index in order]
        for row in range(n)
    ]
    return sorted_values, sorted_vectors, rotations


def pca(points: Matrix) -> dict:
    """PCA from sample covariance; components are returned as row vectors."""
    if len(points) < 2 or not points or any(len(row) != len(points[0]) for row in points):
        raise ValueError("PCA requires at least two rows in a rectangular matrix")
    if any(not math.isfinite(value) for row in points for value in row):
        raise ValueError("PCA requires finite values")
    width = len(points[0])
    centers = [mean([row[column] for row in points]) for column in range(width)]
    centered = [[value - centers[column] for column, value in enumerate(row)] for row in points]
    covariance = [
        [
            sum(row[i] * row[j] for row in centered) / (len(points) - 1)
            for j in range(width)
        ]
        for i in range(width)
    ]
    eigenvalues, eigenvector_columns, rotations = _jacobi_eigh(covariance)
    tolerance = max(1.0, max(abs(value) for value in eigenvalues)) * 1e-12
    if any(value < -tolerance for value in eigenvalues):
        raise ArithmeticError("covariance matrix produced a materially negative eigenvalue")
    eigenvalues = [0.0 if value < 0 else value for value in eigenvalues]
    components = [
        [eigenvector_columns[row][column] for row in range(width)]
        for column in range(width)
    ]
    for component in components:
        largest = max(range(width), key=lambda index: abs(component[index]))
        if component[largest] < 0:
            for index in range(width):
                component[index] *= -1
    total_variance = sum(eigenvalues)
    ratios = (
        [value / total_variance for value in eigenvalues]
        if total_variance > 0
        else [0.0 for _ in eigenvalues]
    )
    coordinates = [
        [sum(value * loading for value, loading in zip(row, component)) for component in components]
        for row in centered
    ]
    orthogonality_error = max(
        (
            abs(sum(components[i][column] * components[j][column] for column in range(width))
                - (1.0 if i == j else 0.0))
            for i in range(width)
            for j in range(width)
        ),
        default=0.0,
    )
    residual = max(
        (
            math.sqrt(sum(
                (
                    sum(covariance[i][j] * components[component][j] for j in range(width))
                    - eigenvalues[component] * components[component][i]
                ) ** 2
                for i in range(width)
            ))
            for component in range(width)
        ),
        default=0.0,
    )
    return {
        "mean": centers,
        "covariance": covariance,
        "eigenvalues": eigenvalues,
        "components": components,
        "variance_ratios": ratios,
        "cumulative_variance": [
            sum(ratios[: index + 1]) for index in range(len(ratios))
        ],
        "coordinates": coordinates,
        "orthogonality_error": orthogonality_error,
        "eigen_residual": residual,
        "jacobi_rotations": rotations,
    }
