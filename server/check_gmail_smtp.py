"""Check Gmail SMTP authentication in Terminal without sending any email.

The app password is read with echo disabled, never printed or written to a file
or command argument. --configure-supabase passes it to the official CLI through
a temporary child-process environment and saves it in hosted Supabase Auth.
"""
import argparse
import getpass
import json
import os
from pathlib import Path
import shutil
import smtplib
import ssl
import subprocess
import sys
import tempfile


PROJECT_REF = 'amaydubnseyippnzdglh'
PASSWORD_VARIABLE = 'SOURCE_CULTURE_SMTP_APP_PASSWORD'
PASSWORD_PATH = ['auth', 'email', 'smtp', 'pass']


def configure_supabase(email, password):
    """Use the CLI's existing login; persist only an environment reference locally."""
    prepared_cli = Path('/tmp/source-culture-tools/node_modules/.bin/supabase')
    cli = str(prepared_cli) if prepared_cli.is_file() else shutil.which('supabase')
    if not cli:
        print('SUPABASE_NOT_UPDATED: The Supabase CLI was not found.')
        return 1
    child_env = {**os.environ, PASSWORD_VARIABLE: password}
    try:
        with tempfile.TemporaryDirectory(prefix='source-culture-smtp-') as temporary:
            directory = Path(temporary) / 'supabase'
            directory.mkdir()
            config = directory / 'config.toml'
            config.write_text('\n'.join([
                'project_id = "source-culture"', '[auth.email.smtp]',
                'enabled = true', 'host = "smtp.gmail.com"', 'port = 587',
                'user = ' + json.dumps(email),
                'admin_email = ' + json.dumps(email),
                'sender_name = "Source Culture"',
                'pass = "env(' + PASSWORD_VARIABLE + ')"', '',
            ]))
            config.chmod(0o600)
            command = [cli, 'config', 'push', '--workdir', temporary,
                       '--project-ref', PROJECT_REF, '--yes', '--output-format', 'json']
            print(f'Saving Gmail SMTP to Supabase project {PROJECT_REF}...')
            # First reconcile the settings, then independently verify the saved
            # secret's remote digest. Capture all CLI output so no raw response
            # or accidental debug text can disclose the password to the caller.
            for attempt in range(2):
                result = subprocess.run(command, env=child_env, capture_output=True,
                                        text=True, timeout=90)
                if result.returncode:
                    print('SUPABASE_NOT_VERIFIED: CLI update failed; output withheld to protect credentials.')
                    return 1
                report = json.loads(result.stdout)
                if PASSWORD_PATH in report.get('secrets', {}).get('unchanged', []):
                    print('SUPABASE_UPDATED: SMTP saved and password match verified. No email was sent.')
                    return 0
                if attempt == 0:
                    print('Verifying the saved password matches...')
            print('SUPABASE_NOT_VERIFIED: The CLI did not confirm a matching saved password.')
            return 1
    except (OSError, subprocess.TimeoutExpired, ValueError):
        print('SUPABASE_NOT_VERIFIED: Could not complete the update verification.')
        return 1
    finally:
        child_env.pop(PASSWORD_VARIABLE, None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email', default='functionditi@gmail.com',
                        help='Gmail account that created the app password')
    parser.add_argument('--configure-supabase', action='store_true',
                        help='After Gmail accepts the password, save and verify SMTP in the Source Culture Supabase project')
    args = parser.parse_args()
    if not sys.stdin.isatty():
        print('Run this command directly in Terminal so password input stays hidden.')
        return 2

    print(f'Checking Gmail SMTP for {args.email}. No email will be sent.')
    try:
        password = ''.join(getpass.getpass('Google app password (hidden): ').split())
    except (EOFError, KeyboardInterrupt):
        print('\nCheck cancelled.')
        return 2
    if len(password) != 16 or not password.isascii() or not password.isalnum():
        print('Expected a 16-character Google app password. Nothing was sent.')
        return 2

    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=20) as client:
            client.ehlo()
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
            client.login(args.email, password)
        print('PASS: Gmail accepted this app password. No email was sent.')
        if args.configure_supabase:
            return configure_supabase(args.email, password)
        print('Enter this same app password in Supabase SMTP Password and save.')
        return 0
    except smtplib.SMTPAuthenticationError as error:
        print(f'AUTH_REJECTED: Gmail rejected this account/app-password pair (SMTP {error.smtp_code}).')
        print('Check the Google account shown on the App Passwords page matches the email above.')
        return 1
    except (smtplib.SMTPException, OSError):
        print('CONNECTION_FAILED: Could not complete the Gmail SMTP connection.')
        print('This does not establish whether the app password is valid.')
        return 1
    except KeyboardInterrupt:
        print('\nCheck cancelled.')
        return 2
    finally:
        del password


if __name__ == '__main__':
    raise SystemExit(main())
