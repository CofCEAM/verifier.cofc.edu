
# Service Desk Identity Verifier - verifier.charleston.edu

Twilio-integrated Django application hosted on Linode used by IT Service Desk to verify user identities (user provides CWID and confirms the provided CWID is theirs with a secret code). 

When a user contacts the service desk, they are asked for their CWID. Service Desk enters the CWID in this app, which queries Ethos with GraphQL to pull and return a cell phone number corresponding to that person. The Service Desk member sends a randomly generated secret code to that number (via Twilio). The calling user must provide the correct code back to the Service Desk member. If they verify correctly, Service Desk marks that user as verified; otherwise, unverified. 



## Authors

- [@austinjhunt](https://www.github.com/austinjhunt)


## Environment Variables

To run this project, you will need to add the following environment variables to your .env file
```
# Ethos Data Access API Settings
ETHOS_API_KEY=CHANGEME

# Twilio Settings
TWILIO_ACCOUNT_SID=CHANGEME
TWILIO_AUTH_TOKEN=CHANGEME 
TWILIO_MESSAGING_SERVICE_SID=CHANGEME

# Length of secret code sent to user phone for verification
PASSPHRASE_LENGTH=4

# Django Settings
DJANGO_SECRET_KEY=CHANGEME
DJANGO_DEBUG=1
DJANGO_LOGLEVEL=info
PRODUCTION=0

# Only used in production; dev uses sqlite3
MYSQL_HOST=CHANGEME
MYSQL_DATABASE=CHANGEME
MYSQL_USER=CHANGEME
MYSQL_PASSWORD=CHANGEME
MYSQL_DEFAULT_CHARACTER_SET="utf8"


# Microsoft Azure Settings for SSO
# App registration 
MICROSOFT_AUTH_CLIENT_ID=CHANGEME
MICROSOFT_AUTH_CLIENT_SECRET=CHANGEME
MICROSOFT_AUTH_TENANT_ID=CHANGEME
MICROSOFT_AUTH_REDIRECT_URI=http://localhost:8000/custom-microsoft-callback/
MICROSOFT_AUTH_SCOPES=openid profile offline_access user.read
# Enterprise app id corresponding to app registration - use to grant access
MICROSOFT_AUTH_SERVICE_PRINCIPAL_ID=CHANGEME

 
```


## Microsoft Azure Application Setup 

The service principal (enterprise application) ID and the app registration (client) ID will not need to change unless you create completely different Azure applications. The only thing you need to change (renew) is the app registration's client secret under the Manage > Certificates & Secrets tab.

### Single Sign On 
Please note this is not using the "Single sign-on" tab under the Enterprise app. Instead, this is a modern form of authentication that integrates Azure AD as an identity provider using an Open ID Connect flow. This means all you really need is the app registration with a Graph API User.Read API permission to start the sign in (client ID and client secret). Once signed in, the app makes one additional Graph API call (on behalf of the signed in user, which means it does not need an admin permission) to `url = f"{graph_url}/beta/servicePrincipals/{settings.MICROSOFT_AUTH_SERVICE_PRINCIPAL_ID}/appRoleAssignedTo"` to check if the user has access to the service principal (enterprise app), defined by the enterprise app's users and groups tab. 

## Twilio Config
An admin of the IT twilio account will need to assist with Twilio configuration troubleshooting if anything goes awry with SMS. Usually it's an account balance issue and it just needs to be refilled. 

The service used by this app is User Phone Verification under the Information Technology account. (Develop > Messaging > Services > User Phone Verification). 

## Contributing

1. Clone the repository: `git clone https://github.com/CofCEAM/verifier.cofc.edu`

2. Open in your IDE of choice. 

3. Create a Python 3.12 virtual environment. Activate it and install Python requirements.
```
python3.12 -m venv venv 
source venv/bin/activate 
pip install -r requirements.txt 
```

4. Copy the `.env-sample` file ([Verifier/Verifier/.env-sample](Verifier/Verifier/.env-sample)) to your own `.env` file and be sure to set `PRODUCTION=0` for local development. This file is ignored by git to keep secret values out of version control. You'll need to replace all `CHANGEME` values with real values. **IMPORTANT: if you add any new environment variables for the app to run, you will need to also manually add those environment variables to the production server's `.env` file**. 

5. Migrate models to a .sqlite database. `python manage.py migrate`. This will generate a .sqlite3 database file for dev. 

6. Collect static files: `python manage.py collectstatic`

7. Run the development server on port 8000. `python manage.py runserver`

8. Create a new branch named after the fix or feature you are working on: 
```
git checkout -b feature/cool-new-feature-name
```

9. Make your changes. Stage them, commit them with descriptive messages, then open a new pull request on the repository:

``` 

git add -p # selectively stage the changes you made with y/N
git commit -m 'my commit message describing the staged changes'
git push -u origin feature/cool-new-feature-name # use same branch name 

# click the link shown in the CLI to open new PR. 
```

10. Request review from another team member before merging with main.

11. Merge with main when ready. Now you can deploy changes to server by pulling to the server from main. See **Deployment**. 


## Deployment

To deploy this project take the following steps. 

1. Connect to the Ivanti VPN. 

2. Connect via SSH to the Django app linode. Do not use root for SSH connections. If necessary, request that an existing admin of the server add a user account for you and provide you with a username and password. Then store creds in LastPass. You will need sudo access as well. 

3. If your SSH connection the Django app Linode server times out and you're on VPN, you may need to contact the NetSec team to request new VPN access; there are specific policies allowing web team members to connect to Linode servers via the VPN connections. You must be connected to VPN to connect, because the Linode firewall blocks SSH traffic from all other sources. 

3. Once connected:

```bash
sudo -i 
cd /var/www/verifier.cofc.edu
git pull # enter credentials 
# reset recursive file ownership to www-data 
chown -R www-data:www-data . 
# restart apache web server 
systemctl restart apache2 
# verify app is running by tailing log and opening app in browser 
tail -f /var/log/apache2/verifier-[access/error].log # now open verifier.charleston.edu in a browser and monitor the log 
```


## How to Connect to the Production Database 

1. Log into the production web server (django linode). 
3. Use the MySQL creds in the environment file: `cat /var/www/verifier.charleston.edu/Verifier/Verifier/.env`.

