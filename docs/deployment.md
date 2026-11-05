# Deploy CyberRisk Manager

Use the free PythonAnywhere app as a small HTTPS demonstration with sanitized
data. The public GitHub repository contains source, migrations, tests and
synthetic samples. Keep database files, backups, private keys and real alerts
outside Git and outside the web server's static directory.

## Publish the code

Create an empty public repository named `cyberrisk-manager` on GitHub. From the
project root, initialize Git if needed, check the staged paths, and commit under
your Git identity. Git Credential Manager on Windows can prompt you to
authenticate in your browser.

```powershell
git init -b main
git add --all
git diff --cached --name-only
git commit -m "Publish CyberRisk Manager"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/cyberrisk-manager.git
git push -u origin main
```

Open **Actions** in the GitHub repository and check both Python jobs.

## PythonAnywhere

1. In the **Web** tab choose **Add a new web app**, **Manual configuration**,
   and Python 3.12 if available. Use the same Python version for the virtual
   environment. Copy the exact hostname shown in the Web tab.
2. From a PythonAnywhere Bash console, run the following. Replace the GitHub
   username and hosted hostname with your own values.

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/cyberrisk-manager.git ~/cyberrisk-manager
cd ~/cyberrisk-manager
python3.12 -m venv ~/.virtualenvs/cyberrisk
source ~/.virtualenvs/cyberrisk/bin/activate
python -m pip install --no-cache-dir -r requirements.txt
umask 077
mkdir -p ~/.config/cyberrisk
test -s ~/.config/cyberrisk/secret_key || python -c 'import secrets; print(secrets.token_hex(32))' > ~/.config/cyberrisk/secret_key
printf '%s\n' 'YOUR_USERNAME.pythonanywhere.com' > ~/.config/cyberrisk/hostname
export CYBERRISK_ENV=production
export CYBERRISK_SECRET_KEY="$(cat ~/.config/cyberrisk/secret_key)"
python -m flask --app app db upgrade
python -m flask --app app create-user --username supervisor --role admin
python -m flask --app app create-user --username operator --role analyst
```

3. Set **Virtualenv** to `/home/YOUR_USERNAME/.virtualenvs/cyberrisk`. Replace
   the contents of the WSGI configuration file linked in the Web tab with
   [the PythonAnywhere WSGI configuration](../deploy/pythonanywhere_wsgi.py).
   This configuration serves the app with secure session cookies and the
   production database in `instance/cyberrisk-production.db`.
4. Enable **Force HTTPS**, then click **Reload**. Open the HTTPS URL and sign
   in as the operator. Create asset `lab-ssh-01`, import the synthetic
   [alert file](../examples/wazuh-alerts.jsonl), convert an alert, then download
   an incident report. Reload and verify the case is still present.
5. Review the free account expiry in the Web tab and renew it before expiry.
   The free plan has one worker and 512 MiB of disk space. Use local files
   for alert and vulnerability imports.

Sources for platform setup: [Flask WSGI configuration](https://help.pythonanywhere.com/pages/Flask/),
[forcing HTTPS](https://help.pythonanywhere.com/pages/ForcingHTTPS/), and
[free account features](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/).

## Updates and backups

In the activated virtual environment, set the same production environment
variables as above. Before a deployment, create a backup in a private path.
Run Git updates and migrations from the project root during a maintenance
window, then reload the application and check the login and latest case.

```bash
mkdir -p ~/cyberrisk-backups
python -m flask --app app backup-db "$HOME/cyberrisk-backups/cyberrisk-$(date -u +%Y%m%d-%H%M%S).db"
```

The backup command requires a new file and checks SQLite
integrity. Keep a private copy outside the hosting account. To test restore,
open the backup in a separate workspace, run SQLite integrity and foreign-key
checks, and verify that expected records are present. For a live restore, stop
the app first, preserve the current database as a separate rollback copy,
restore the verified database and matching code revision, then reload.
