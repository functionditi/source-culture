import contextlib
import io
import json
from pathlib import Path
import smtplib
import subprocess
import tomllib
import unittest
from unittest.mock import patch

from server import check_gmail_smtp as setup


class SMTPSetupTests(unittest.TestCase):
    def test_verified_update_keeps_password_out_of_files_arguments_and_output(self):
        secret = 'syntheticsecretx'
        calls = []

        def run(command, **options):
            calls.append(command)
            self.assertNotIn(secret, ' '.join(command))
            self.assertEqual(options['env'][setup.PASSWORD_VARIABLE], secret)
            self.assertEqual(command[command.index('--project-ref') + 1], setup.PROJECT_REF)
            root = Path(command[command.index('--workdir') + 1])
            content = (root / 'supabase/config.toml').read_text()
            self.assertNotIn(secret, content)
            config = tomllib.loads(content)
            self.assertEqual(set(config), {'project_id', 'auth'})
            self.assertEqual(set(config['auth']), {'email'})
            self.assertEqual(set(config['auth']['email']), {'smtp'})
            self.assertEqual(config['auth']['email']['smtp']['user'], 'functionditi@gmail.com')
            self.assertEqual(config['auth']['email']['smtp']['pass'], 'env(' + setup.PASSWORD_VARIABLE + ')')
            status = 'sent' if len(calls) == 1 else 'unchanged'
            return subprocess.CompletedProcess(command, 0, json.dumps({'secrets': {status: [setup.PASSWORD_PATH]}}), '')

        output = io.StringIO()
        with patch.object(setup.subprocess, 'run', side_effect=run), contextlib.redirect_stdout(output):
            result = setup.configure_supabase('functionditi@gmail.com', secret)
        self.assertEqual(result, 0)
        self.assertEqual(len(calls), 2)
        self.assertIn('SUPABASE_UPDATED', output.getvalue())
        self.assertNotIn(secret, output.getvalue())
        self.assertFalse(Path(calls[0][calls[0].index('--workdir') + 1]).exists())

    def test_failed_cli_output_cannot_disclose_credentials_or_report_success(self):
        secret = 'syntheticsecretx'
        output = io.StringIO()
        failure = subprocess.CompletedProcess([], 1, secret, secret)
        with patch.object(setup.subprocess, 'run', return_value=failure), contextlib.redirect_stdout(output):
            result = setup.configure_supabase('functionditi@gmail.com', secret)
        self.assertEqual(result, 1)
        self.assertNotIn(secret, output.getvalue())
        self.assertNotIn('SUPABASE_UPDATED', output.getvalue())

    def test_rejected_gmail_password_never_reaches_supabase(self):
        output = io.StringIO()
        with patch.object(setup.sys, 'argv', ['check_gmail_smtp.py', '--configure-supabase']), \
             patch.object(setup.sys.stdin, 'isatty', return_value=True), \
             patch.object(setup.getpass, 'getpass', return_value='abcdefghijklmnop'), \
             patch.object(setup.smtplib, 'SMTP') as smtp, \
             patch.object(setup, 'configure_supabase') as configure, \
             contextlib.redirect_stdout(output):
            smtp.return_value.__enter__.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b'Bad credentials')
            self.assertEqual(setup.main(), 1)
            configure.assert_not_called()
        self.assertIn('AUTH_REJECTED', output.getvalue())


if __name__ == '__main__':
    unittest.main()
