"""Measurement integrity: warmups, ordered results, plan counters and ownership."""

import unittest
from unittest.mock import patch

from scripts.benchmark_databases import fingerprint, measure, mongo_metrics, owned_namespace, pg_metrics, summarize


class BenchmarkTests(unittest.TestCase):
    def test_warmups_are_excluded_and_hashing_does_not_change_samples(self):
        with patch('scripts.benchmark_databases.perf_counter_ns', side_effect=[0, 9_000_000, 10_000_000,
                12_000_000, 20_000_000, 24_000_000]):
            result = measure(lambda: [{'id': 7}], 1, 2)
        self.assertEqual(result['warmup_ms'], [9])
        self.assertEqual(result['samples_ms'], [2, 4])
        self.assertEqual(result['summary']['median_ms'], 3)
        self.assertEqual(result['result_count'], 1)

    def test_each_timed_result_must_match_the_previous_index_phase(self):
        with self.assertRaises(AssertionError):
            measure(lambda: [(2,)], 1, 2, fingerprint([(1,)]))

    def test_result_fingerprint_preserves_pagination_order_but_not_object_key_order(self):
        self.assertEqual(fingerprint([{'a': 1, 'b': 2}]), fingerprint([{'b': 2, 'a': 1}]))
        self.assertNotEqual(fingerprint([1, 2]), fingerprint([2, 1]))

    def test_median_quartiles_and_invalid_samples(self):
        self.assertEqual(summarize([4, 1, 3, 2]), {'n': 4, 'median_ms': 2.5, 'p25_ms': 1.75,
            'p75_ms': 3.25, 'min_ms': 1, 'max_ms': 4})
        for values in ([], [1], [-1, 2]):
            with self.assertRaises(ValueError):
                summarize(values)

    def test_cleanup_refuses_app_and_foreign_benchmark_names(self):
        owner = 'bench_' + 'a' * 32
        self.assertEqual(owned_namespace(owner, owner), owner)
        for value in ('public', 'complaints', 'case_details', 'bench_' + 'b' * 32, owner + ';DROP'):
            with self.assertRaises(ValueError):
                owned_namespace(value, owner)

    def test_postgres_metrics_do_not_double_count_buffers_or_bitmap_index_rows(self):
        plan = [{'Planning Time': 1, 'Execution Time': 2, 'Plan': {'Node Type': 'Nested Loop',
            'Actual Rows': 3, 'Actual Loops': 1, 'Shared Hit Blocks': 20, 'Plans': [
                {'Node Type': 'Bitmap Heap Scan', 'Actual Rows': 2, 'Actual Loops': 3,
                 'Rows Removed by Filter': 4, 'Rows Removed by Index Recheck': 1,
                 'Shared Hit Blocks': 10, 'Plans': [{'Node Type': 'Bitmap Index Scan',
                     'Actual Rows': 900, 'Actual Loops': 3, 'Shared Hit Blocks': 5}]},
                {'Node Type': 'Index Only Scan', 'Actual Rows': 1, 'Actual Loops': 6}]} }]
        metrics = pg_metrics(plan)
        self.assertEqual(metrics['shared_hit_blocks'], 20)
        self.assertEqual(metrics['scan_rows_processed_estimate'], 27)
        self.assertEqual(len(metrics['scans']), 2)

    def test_mongo_metrics_ignore_rejected_plans_and_handle_nested_sbe_plan(self):
        plan = {'queryPlanner': {'winningPlan': {'queryPlan': {'stage': 'FETCH',
                'inputStage': {'stage': 'IXSCAN', 'indexName': 'chosen'}}},
                'rejectedPlans': [{'stage': 'COLLSCAN', 'indexName': 'rejected'}]},
                'executionStats': {'nReturned': 20, 'executionTimeMillis': 0,
                    'totalDocsExamined': 20, 'totalKeysExamined': 20}}
        self.assertEqual(mongo_metrics(plan)['winning_stages'], ['FETCH', 'IXSCAN'])
        self.assertEqual(mongo_metrics(plan)['winning_indexes'], ['chosen'])


if __name__ == '__main__':
    unittest.main()
