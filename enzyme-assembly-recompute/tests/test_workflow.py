"""Regression checks for configuration and user-visible run-state contracts."""
import copy
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import run_analysis
from run_analysis import make_report, track_run_status


class WorkflowContracts(unittest.TestCase):
    def test_invalid_configuration_creates_no_results(self):
        baseline = json.loads((BASE / 'configs/quick.json').read_text())
        cases = [('permutations', 0), ('bootstrap_replicates', 1),
                 ('seed', -1), ('workers', 0), ('fit.lambda', float('nan')),
                 ('fit.max_iter', 0), ('unknown_key', 1)]
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            for index, (field, value) in enumerate(cases):
                with self.subTest(field=field):
                    config = copy.deepcopy(baseline)
                    config['output_dir'] = str(temp / f'output_{index}')
                    if field.startswith('fit.'):
                        config['fit'][field.split('.')[1]] = value
                    else:
                        config[field] = value
                    path = temp / f'config_{index}.json'
                    path.write_text(json.dumps(config), encoding='utf-8')
                    run = subprocess.run([sys.executable, str(BASE / 'run_analysis.py'),
                                          '--config', str(path)], capture_output=True, text=True)
                    self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                    self.assertIn('ERROR:', run.stderr)
                    self.assertNotIn('Fitting', run.stdout)
                    self.assertFalse(Path(config['output_dir']).exists())

    def test_failed_run_is_not_marked_running(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            with self.assertRaisesRegex(RuntimeError, 'injected failure'):
                with track_run_status(output):
                    raise RuntimeError('injected failure')
            status = json.loads((output / 'run_status.json').read_text())
            self.assertEqual(status['status'], 'failed')
            self.assertEqual(status['error_type'], 'RuntimeError')

    def test_runner_failure_updates_the_created_output(self):
        config = json.loads((BASE / 'configs/quick.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            output = temp / 'run'
            config['output_dir'] = str(output)
            path = temp / 'config.json'
            path.write_text(json.dumps(config), encoding='utf-8')
            with mock.patch.object(sys, 'argv', ['run_analysis.py', '--config', str(path)]):
                with mock.patch('run_analysis.crossval_predictions', side_effect=RuntimeError('injected fit failure')):
                    with contextlib.redirect_stdout(io.StringIO()):
                        with self.assertRaisesRegex(RuntimeError, 'injected fit failure'):
                            run_analysis.main()
            status = json.loads((output / 'run_status.json').read_text())
            self.assertEqual(status['status'], 'failed')
            self.assertEqual(status['error_message'], 'injected fit failure')

    def test_interrupt_has_explicit_status(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            with self.assertRaises(KeyboardInterrupt):
                with track_run_status(output):
                    raise KeyboardInterrupt()
            self.assertEqual(json.loads((output / 'run_status.json').read_text())['status'], 'interrupted')

    def test_report_uses_actual_input_dimensions(self):
        summary = json.loads((BASE / 'examples/reference_run/summary.json').read_text())
        summary.update(n=42, n_positive=20, n_negative=22)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            make_report(output, summary)
            self.assertIn('Samples: 42 (20 positive, 22 negative)',
                          (output / 'report.md').read_text())
            self.assertIn('42个条目、14项特征，20阳性、22阴性',
                          (output / 'REPORT_结果解读.md').read_text())


if __name__ == '__main__':
    unittest.main()
