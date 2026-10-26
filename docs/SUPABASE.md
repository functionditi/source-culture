# Connect Source Culture to Supabase

The existing GitHub Pages website can accept contributions using Supabase Auth,
Postgres, Edge Functions, and a private Storage bucket. The design and form stages
stay the same. The Python app remains available for local development.

The hosted project is `amaydubnseyippnzdglh` (`source-culture`). Its migrations,
private image bucket, Edge Function, website redirects, and 15-minute sign-in
expiry are deployed. The editor allowlist contains `netia078@newschool.edu` and
`functionditi@gmail.com`. The hosted email templates and public GitHub build
variables are configured. Gmail SMTP is enabled, its saved password was verified
against the Gmail-tested app password, and a live sign-in email request passed.
The GitHub Pages workflow enables contributions when it builds with the two
public variables below. No Supabase credentials are included in the source code.

## 1. Create a free project

Create a project at <https://supabase.com/dashboard>. Choose the Free plan and a
region near your expected visitors. Keep the database password in your password
manager. To let Codex apply the remaining setup, connect the Supabase plugin and
identify this project and the email that should have editor access.

The manual steps below are an alternative to the plugin. They use the Supabase
CLI, installed following the [official CLI guide](https://supabase.com/docs/guides/local-development/cli/getting-started).

From this repository:

```sh
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

The first migration creates private tables, transactional API functions, and the
private image bucket. The second imports only the six curated projects/readings
already on the public site. It never imports local submissions or demo records,
grants authorship, or creates consent records for the named creators. Re-running
the editorial import preserves existing records and withdrawals.

The remaining migration restricts browser execution of Supabase's optional
automatic-RLS event-trigger helper without disabling automatic RLS.
Alternatively, run the SQL files under `supabase/migrations/` in filename order
using the project's SQL Editor. Leave `source_culture` out of the exposed API schemas.

## 2. Set the function's website URL and editor email

In Supabase's Edge Function secrets, add:

| Name | Value |
| --- | --- |
| `APP_URL` | `https://functionditi.github.io/source-culture/` |
| `EDITOR_EMAILS` | Your email, or a comma-separated list of editor emails |

Use the exact website URL, including `/source-culture/` and the final slash.
Supabase automatically provides the function's database service credentials.
No service key, secret key, database password, or access token belongs in the
website, a GitHub repository variable, or a chat message.

Then deploy the function:

```sh
supabase secrets set --env-file supabase/.env
supabase functions deploy source-culture
```

The ignored `supabase/.env` file is prepared locally with the website URL and
the two editor addresses you supplied. If setting this up from a fresh checkout,
copy `supabase/.env.example` to `supabase/.env` and enter your editor addresses.

The function has `verify_jwt = false` because it also handles public browsing and
anonymous submissions. It independently validates supplied user tokens through
Supabase Auth before any private read, revision, confirmation, or review. Editor
status comes from `EDITOR_EMAILS`, never a profile field or browser parameter.

## 3. Configure sign-in links

In **Authentication → URL Configuration**, set:

| Setting | Value |
| --- | --- |
| Site URL | `https://functionditi.github.io/source-culture/` |
| Allowed redirect URL | `https://functionditi.github.io/source-culture/manage/` |

Enable email sign-in and sign-up, require email confirmation, and set **Email OTP
Expiration** to **900 seconds**. Copy the contents of
`supabase/templates/sign-in.html` into both **Confirm signup** and **Magic link**
email templates. The template uses `{{ .RedirectTo }}#token={{ .TokenHash }}`:
opening the page does not consume the link; the visitor must press the sign-in
button. Keep the exact redirect allowlist rather than allowing arbitrary URLs.

The local `supabase/config.toml` provides the same 15-minute expiry and templates
for CLI development. It contains local URLs; do not push it directly to the
production project. Use the dashboard or a separate production configuration.

Supabase's default email sender only sends to project-team email addresses and
has a small testing limit. **Public contributor sign-in needs custom SMTP.**
New Free projects require custom SMTP before email templates can be customized.
Configure Gmail first, then install both templates above.

For the selected Gmail setup, enable Google 2-Step Verification on
`functionditi@gmail.com`, create an [app password](https://myaccount.google.com/apppasswords)
named `Source Culture`, and configure **Authentication → Email → SMTP settings**:

| Setting | Value |
| --- | --- |
| Host | `smtp.gmail.com` |
| Port | `587` |
| Username | `functionditi@gmail.com` |
| Password | The Google app password, not the normal account password |
| Sender email | `functionditi@gmail.com` |
| Sender name | `Source Culture` |

Enable custom SMTP and save. Enter the app password directly in Supabase; do not
put it in chat, repository files, GitHub variables, or CLI arguments. Gmail account
sending limits still apply. [Google app-password help](https://support.google.com/mail/answer/185833).

If Auth logs report Gmail `535 5.7.8`, check the same app password directly in
your own Terminal:

```sh
python3 server/check_gmail_smtp.py
```

The prompt hides the app password, removes formatting spaces, checks Gmail over
TLS, and sends no email. `PASS` means Gmail accepted that password from your
computer; enter that same value in Supabase and save. `AUTH_REJECTED` means Gmail
also rejected it directly; confirm the Google account on the App Passwords page
is `functionditi@gmail.com`. `CONNECTION_FAILED` is a network/TLS result and does
not establish whether the credentials are valid. Share only the result label.

If Gmail accepts the password but hosted Auth still reports bad credentials, use:

```sh
python3 server/check_gmail_smtp.py --configure-supabase
```

This first checks Gmail, then uses the existing Supabase CLI login to save the
same normalized password to project `amaydubnseyippnzdglh`. The temporary config
contains only SMTP settings and an environment reference; the password is passed
to the CLI in a child-process environment, never a file or command argument.
The helper verifies the saved password digest before reporting
`SUPABASE_UPDATED`. It sends no email. This requires a CLI version with secret
comparison support (the prepared CLI is 2.122.0).

An alternative is Resend's free email allowance. Verify a domain you own and use:

| Setting | Value |
| --- | --- |
| Host | `smtp.resend.com` |
| Port | `587` |
| Username | `resend` |
| Password | Your Resend API key |
| Sender email | An address at your verified domain |
| Sender name | `Source Culture` |

Enter that password directly in Supabase. Disable link tracking for sign-in
emails. SMTP credentials are no longer environment variables in the Python app
when using this backend; Supabase Auth sends the email.

References: [Supabase email delivery](https://supabase.com/docs/guides/auth/auth-smtp),
[email templates](https://supabase.com/docs/guides/auth/auth-email-templates),
[Resend SMTP](https://resend.com/docs/send-with-smtp).

## 4. Enable the GitHub Pages integration

In GitHub, open **source-culture → Settings → Secrets and variables → Actions →
Variables**. Add these **repository variables**, using the project's dashboard
Connect/API Keys panel:

| Variable | Value |
| --- | --- |
| `SUPABASE_URL` | `https://YOUR_PROJECT_REF.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | The public `sb_publishable_…` key (legacy `anon` keys also work) |

These two values are intentionally public. The build rejects known secret and
`service_role` keys. When both values are absent, the existing read-only export
is preserved; partial settings fail the build instead of silently disabling the
connection.

Commit/push the integration and run **Actions → Deploy notebook to GitHub Pages →
Run workflow**, or let a push to `main` run it. The configured build enables the
existing Contribute, Manage, and Admin pages. Published entries come live from
Supabase; approving a contribution does not require another GitHub deployment.

For a local static preview, set these same public variables in your shell and
run `npm run build:pages`. A local preview needs a matching `APP_URL` and Auth
redirect configuration in a separate development project.

## 5. Verify the complete flow

1. Visit the public site and submit a small practice, with an image if useful.
2. Check that it is not publicly visible. Request private management access.
3. Receive the email, open the link, press the sign-in button, and confirm that
   specific submission and its sharing permissions.
4. Request a sign-in link using an email in `EDITOR_EMAILS`. Open `/admin`, review
   the contribution, and publish. Linked source suggestions need their own review
   before the practice can be published.
5. Confirm that the approved entry and image appear. Submit a revision and check
   that the old version stays public until the new one is approved.
6. Withdraw as the contributor. The entry and image endpoint should stop serving
   the public, including a fresh request to a previously copied image URL.

Images are decoded, EXIF-rotated, limited to 1800 pixels, and re-encoded as WebP
without inherited metadata in the Edge Function. The input limits are four images,
5 MB each, and 24 megapixels. The hosted function's CPU/memory limits can require
smaller images. Images are processed sequentially. Failed database transactions
remove newly uploaded objects when the request can finish; an interrupted request
can leave an unreferenced private object, which can be cleaned up administratively.

Images are served through a live authorization proxy with `Cache-Control:
no-store`. Storage signed URLs are not used, because they would remain valid for
their lifetime after withdrawal. Private image previews use authenticated fetches
and temporary blob URLs. Access tokens are stored only in the current tab's
session storage, without refresh tokens, and cleared on expiry or sign-out.

## Limits and operational follow-up

Supabase Free has usage quotas and can pause after a week of inactivity. Its
default email service is for testing only. Set up database exports and private
image backups, a retention policy, and a public contact address before inviting
contributors broadly. Storage persistence is separate from recoverable backups.
Current limits: <https://supabase.com/pricing>.

## Local verification

```sh
npm test
deno check --config=supabase/functions/source-culture/deno.json supabase/functions/source-culture/index.ts
deno test --config=supabase/functions/source-culture/deno.json --allow-read --allow-env tests/test_supabase_function.ts tests/test_supabase_images.ts
python3 tests/verify_supabase_browser.py
```

`python3 tests/verify_supabase_db.py` tests the actual migrations and transactions
against an isolated local PostgreSQL server. It expects a Unix socket directory
at `/tmp/source-culture-supabase-pg`, port `55483`; override with
`SUPABASE_TEST_SOCKET` and `SUPABASE_TEST_PORT`. It creates and drops its own test
database and never contacts a hosted project. Its storage table is a local stub;
hosted Storage and SMTP still require the live verification above.
