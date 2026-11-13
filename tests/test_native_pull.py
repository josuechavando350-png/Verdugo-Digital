"""Bounded registry-download retries; these tests NEVER download Docker images."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native_pull',root/'scripts/native-pair-acceptance.py')
native=importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)

class PullGuards(unittest.TestCase):
    def test_success_without_sleep(self):
        docker=Mock(return_value='pulled')
        delay=Mock()
        self.assertEqual(native.pull_image(docker,'registry/image@sha256:'+'a'*64,sleeper=delay),'pulled')
        docker.assert_called_once()
        delay.assert_not_called()

    def test_rate_limit_only_then_success(self):
        errors=[native.AcceptanceError('registry_rate_limited')]*2
        outputs=iter(errors+['pulled'])
        def fake(*a,**k):
            v=next(outputs)
            if isinstance(v,Exception):raise v
            return v
        sleeps=[]
        self.assertEqual(native.pull_image(fake,'image',sleeper=sleeps.append),'pulled')
        self.assertEqual(sleeps,[15,30])

    def test_other_errors_are_not_retried(self):
        docker=Mock(side_effect=native.AcceptanceError('command_failed_docker_pull_1'))
        delay=Mock()
        with self.assertRaisesRegex(native.AcceptanceError,'command_failed'):
            native.pull_image(docker,'bad',sleeper=delay)
        docker.assert_called_once()
        delay.assert_not_called()

    def test_exhausted_throttle_fails_closed(self):
        docker=Mock(side_effect=native.AcceptanceError('registry_rate_limited'))
        delays=[]
        with self.assertRaisesRegex(native.AcceptanceError,'registry_rate_limited'):
            native.pull_image(docker,'image',max_attempts=4,sleeper=delays.append)
        self.assertEqual(docker.call_count,4)
        self.assertEqual(delays,[15,30,60])

    def test_docker_error_classification_is_only_for_pulls(self):
        for args, expected in [
            (['docker','pull','image'],'registry_rate_limited'),
            (['docker','run','image'],'command_failed_docker_run_1'),
            (['docker','restart','container'],'command_failed_docker_restart_1'),
        ]:
            with self.subTest(args=args):
                fake=Mock(returncode=1,stdout='',stderr='toomanyrequests: Rate exceeded')
                with patch.object(native.subprocess,'run',return_value=fake):
                    with self.assertRaises(native.AcceptanceError) as error:
                        native.command(args)
                self.assertEqual(str(error.exception),expected)

    def test_attempt_bound_is_strict(self):
        for count in (0,7,-1,True):
            with self.subTest(count=count):
                with self.assertRaises(native.AcceptanceError):
                    native.pull_image(lambda *a,**k:None,'image',max_attempts=count)

if __name__=='__main__':
    unittest.main()
