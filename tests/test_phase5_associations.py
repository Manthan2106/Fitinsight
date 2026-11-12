import unittest
from datetime import date

from src.association_rules import (
    DEFAULT_MAX_ITEMSET_SIZE,
    EXCLUDED_FAMILY_PAIRS,
    apriori,
    build_rules,
    build_transactions,
    minimum_support_count,
    participant_balanced_sensitivity,
)
from src.phase5_common import load_daily_rows


def transaction(participant, items, day=1):
    return {
        "id": participant,
        "date": f"2016-03-{day:02d}",
        "items": items,
        "is_complete_day": False,
    }


class AprioriMetricTests(unittest.TestCase):
    def test_five_percent_support_uses_ceiling_of_observed_denominator(self):
        self.assertEqual(minimum_support_count(457, 0.05), 23)
        self.assertEqual(minimum_support_count(4, 0.05), 1)
        self.assertEqual(minimum_support_count(0, 0.05), 0)
        with self.assertRaises(ValueError):
            minimum_support_count(10, 0)

    def test_four_transaction_example_has_expected_metrics(self):
        transactions = [
            transaction("p1", ["A", "B"]),
            transaction("p2", ["B", "A"]),
            transaction("p3", ["A"]),
            transaction("p4", ["B"]),
        ]
        families = {"A": "family_a", "B": "family_b"}
        frequent, _ = apriori(transactions, families, min_support=0.5, max_size=2)
        rules = build_rules(
            frequent, 4, min_support=0.5, min_confidence=0.60,
            min_lift=1.0, min_participants=2,
        )
        self.assertAlmostEqual(frequent[("A",)]["support"], 0.75)
        self.assertAlmostEqual(frequent[("B",)]["support"], 0.75)
        self.assertAlmostEqual(frequent[("A", "B")]["support"], 0.50)
        rule = next(
            row for row in rules
            if row["antecedent"] == ("A",) and row["consequent"] == ("B",)
        )
        self.assertAlmostEqual(rule["confidence"], 2 / 3)
        self.assertAlmostEqual(rule["lift"], 8 / 9)
        self.assertAlmostEqual(rule["leverage"], -0.0625)
        self.assertEqual(rule["distinct_participants"], 2)
        self.assertFalse(rule["eligible"])

    def test_duplicate_items_and_input_order_do_not_change_counts(self):
        families = {"A": "a", "B": "b"}
        transactions_a = [
            transaction("p1", ["B", "A", "A"]),
            transaction("p2", ["A", "B"]),
        ]
        transactions_b = list(reversed([
            transaction("p1", ["A", "B"]),
            transaction("p2", ["B", "A"]),
        ]))
        result_a, _ = apriori(transactions_a, families, 0.5, 2)
        result_b, _ = apriori(transactions_b, families, 0.5, 2)
        self.assertEqual(result_a, result_b)
        self.assertEqual(result_a[("A", "B")]["count"], 2)

    def test_same_family_categories_never_form_an_itemset(self):
        families = {"steps:zero": "steps", "steps:upper": "steps"}
        transactions = [
            transaction("p1", ["steps:zero", "steps:upper"]),
            transaction("p2", ["steps:zero", "steps:upper"]),
        ]
        frequent, metrics = apriori(transactions, families, 0.5, 2)
        self.assertNotIn(("steps:upper", "steps:zero"), frequent)
        self.assertGreater(metrics["family_incompatible_candidates_pruned"], 0)

    def test_related_input_denominator_families_are_excluded(self):
        families = {
            "active_share:upper": "active_share",
            "very_active:upper": "very_active_minutes",
            "coverage:complete": "coverage",
        }
        transactions = [
            transaction("p1", list(families)),
            transaction("p2", list(families)),
        ]
        frequent, metrics = apriori(
            transactions,
            families,
            0.5,
            3,
            EXCLUDED_FAMILY_PAIRS,
        )
        self.assertNotIn(
            ("active_share:upper", "very_active:upper"), frequent
        )
        self.assertNotIn(
            ("active_share:upper", "coverage:complete"), frequent
        )
        self.assertGreater(metrics["dependency_related_candidates_pruned"], 0)

    def test_apriori_prunes_triple_when_a_pair_subset_is_infrequent(self):
        transactions = [
            transaction("p1", ["A", "B", "C"]),
            transaction("p2", ["A", "B"]),
            transaction("p3", ["A", "C"]),
            transaction("p4", ["A"]),
        ]
        families = {"A": "a", "B": "b", "C": "c"}
        frequent, metrics = apriori(transactions, families, 0.5, 3)
        self.assertIn(("A", "B"), frequent)
        self.assertIn(("A", "C"), frequent)
        self.assertNotIn(("A", "B", "C"), frequent)
        self.assertGreater(metrics["subset_pruned_candidates"], 0)

    def test_empty_transactions_return_no_itemsets_or_rules(self):
        frequent, metrics = apriori([], {}, min_support=0.05, max_size=3)
        self.assertEqual(frequent, {})
        self.assertEqual(metrics["minimum_support_count"], 0)
        self.assertEqual(build_rules(frequent, 0), [])

    def test_rule_generation_is_unique_and_canonical(self):
        transactions = [
            transaction("p1", ["C", "A", "B"]),
            transaction("p2", ["B", "C", "A"]),
            transaction("p3", ["A", "B", "C"]),
        ]
        families = {"A": "a", "B": "b", "C": "c"}
        frequent, _ = apriori(transactions, families, 1.0, 3)
        rules = build_rules(frequent, 3, 1.0, 0.0, 0.0, 1)
        keys = [(row["antecedent"], row["consequent"]) for row in rules]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(keys, sorted(keys))
        self.assertTrue(all(row["joint_count"] == 3 for row in rules))
        self.assertTrue(all(row["distinct_participants"] == 3 for row in rules))

    def test_participant_balanced_confidence_does_not_equal_pooled_confidence(self):
        transactions = [
            transaction("p1", ["A", "B"]),
            transaction("p1", ["A"]),
            transaction("p1", ["A"]),
            transaction("p2", ["A"]),
        ]
        families = {"A": "a", "B": "b"}
        frequent, _ = apriori(transactions, families, 0.25, 2)
        rules = build_rules(frequent, 4, 0.25, 0.0, 0.0, 1)
        balanced = participant_balanced_sensitivity(transactions, frequent, rules)
        row = next(
            item for item in balanced
            if item["entity_type"] == "rule_confidence"
            and item["entity"] == "('A',) -> ('B',)"
        )
        self.assertAlmostEqual(row["pooled_rate"], 0.25)
        self.assertAlmostEqual(row["participant_balanced_rate"], 1 / 6)
        self.assertEqual(row["participants_contributing"], 2)


class TransactionConstructionTests(unittest.TestCase):
    def test_real_daily_rows_map_to_one_transaction_with_distinct_families(self):
        rows = load_daily_rows()
        transactions, family_by_item, dictionary, cutpoints = build_transactions(rows)
        self.assertEqual(len(transactions), len(rows))
        self.assertEqual(len({row["id"] for row in transactions}), 35)
        self.assertEqual(len(family_by_item), 17)
        self.assertEqual(len(dictionary), len(family_by_item))
        self.assertEqual(cutpoints["calories_q1"], 1776.0)
        self.assertEqual(cutpoints["calories_q3"], 2667.0)
        for tx in transactions:
            self.assertEqual(len(tx["items"]), 6)
            self.assertEqual(
                len({family_by_item[item] for item in tx["items"]}), 6
            )
            self.assertEqual(len(tx["items"]), len(set(tx["items"])))

    def test_maximum_itemset_size_is_bounded(self):
        self.assertEqual(DEFAULT_MAX_ITEMSET_SIZE, 3)


if __name__ == "__main__":
    unittest.main()
