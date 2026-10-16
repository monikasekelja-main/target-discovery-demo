"""Regression checks for fixture arithmetic and decision semantics; no LLM is invoked."""
import copy
import json
from pathlib import Path
import unittest

from evaluate import assess, below

ROOT=Path(__file__).parent
POLICY=json.loads((ROOT/'runtime/policy.json').read_text())
RECORDS={p.stem:json.loads(p.read_text()) for p in (ROOT/'runtime/experiments').glob('*.json')}
EXPECTED=json.loads((ROOT/'evaluation/expected.json').read_text())['cases']


class ContractChecks(unittest.TestCase):
    def test_all_eight_experimental_cases(self):
        for key, record in RECORDS.items():
            with self.subTest(key=key):
                result=assess(record,POLICY)
                self.assertEqual(result['proposed_action'],EXPECTED[key]['action'])
                self.assertTrue(result['human_review_required'])

    def test_donor_level_effect_and_interval(self):
        # Reference values independently checked with scipy.stats.t.interval.
        stats=assess(RECORDS['X101'],POLICY)['statistics']['KD-A']
        self.assertAlmostEqual(stats['functional_reduction_pct']['mean'],32.0)
        self.assertAlmostEqual(stats['functional_reduction_pct']['lower_95'],29.511922118076697)
        self.assertAlmostEqual(stats['functional_reduction_pct']['upper_95'],34.4880778819233)
        self.assertAlmostEqual(stats['donor_functional_reductions_pct']['D01'],32.0)

    def test_cell_loss_blocks_apparent_benefit(self):
        result=assess(RECORDS['X104'],POLICY)
        self.assertGreater(result['statistics']['KD-A']['functional_reduction_pct']['lower_95'],20)
        self.assertFalse(result['prerequisites_passed'])
        self.assertTrue(any(x.startswith('G4:') for x in result['failed_gates']))

    def test_variability_is_not_a_negative_result(self):
        result=assess(RECORDS['X103'],POLICY)
        self.assertTrue(result['prerequisites_passed'])
        self.assertEqual(result['proposed_action'],'INCONCLUSIVE')

    def test_donor_order_does_not_change_mean_or_mapping(self):
        r=copy.deepcopy(RECORDS['X101'])
        r['assays']['KD-A'].reverse()
        result=assess(r,POLICY)
        self.assertEqual(result['proposed_action'],'ADVANCE_TO_REPLICATION')
        self.assertAlmostEqual(result['statistics']['KD-A']['donor_functional_reductions_pct']['D01'],32.0)

    def test_donor_and_denominator_failures_do_not_create_support(self):
        for mode in ['missing','duplicate','zero','not_finite']:
            r=copy.deepcopy(RECORDS['X101'])
            if mode=='missing':r['assays']['KD-A'].pop()
            if mode=='duplicate':r['assays']['KD-A'][1]['donor_id']='D01'
            if mode=='zero':r['assays']['KD-A'][0]['ntc_il17_positive_pct']=0
            if mode=='not_finite':r['assays']['KD-A'][0]['kd_il17_positive_pct']=float('nan')
            with self.subTest(mode=mode):self.assertEqual(assess(r,POLICY)['proposed_action'],'INCONCLUSIVE')

    def test_model_output_cannot_replace_functional_measurement(self):
        r=copy.deepcopy(RECORDS['X101'])
        r['assays']['KD-A'][0].pop('kd_il17_positive_pct')
        r['assays']['KD-A'][0]['model_predicted_reduction_pct']=32
        self.assertEqual(assess(r,POLICY)['proposed_action'],'INCONCLUSIVE')

    def test_stale_policy_blocks_action(self):
        r=copy.deepcopy(RECORDS['X101']);r['policy_version']='demo-policy-v0'
        self.assertEqual(assess(r,POLICY)['proposed_action'],'INCONCLUSIVE')

    def test_exact_useful_threshold_is_inclusive(self):
        # A boundary semantics test, not a biologically realistic zero-variance study.
        r=copy.deepcopy(RECORDS['X101'])
        for rows in r['assays'].values():
            for row in rows:
                row['ntc_il17_positive_pct']=25
                row['kd_il17_positive_pct']=20
                row['positive_control_il17_positive_pct']=10
        self.assertEqual(assess(r,POLICY)['proposed_action'],'ADVANCE_TO_REPLICATION')
        self.assertFalse(below(20.0,20.0))
        self.assertTrue(below(19.99999,20.0))


if __name__=='__main__':unittest.main(verbosity=2)
