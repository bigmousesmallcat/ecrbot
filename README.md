# ECR BOT
This is a slack bot built for the purpose of performing some actions on AWS ECR repository.

---

## Prerequisites:
1. AWS account with an IAM user credentials (access keys) to make CLI calls
    - The user should have necessary IAM permissions on ECR service to delete images/repos
2. A slack account with API access</li>
3. *Python3* and *pip3* installed</li>
4. *AWS CLI version 2* installed</li>
5. env variables to be stored in a `.env` file at the root of the directory:
    - `SLACK_TOKEN_=</li>`
    - `SIGNING_SECRET_=</li>`
    - `AWS_PROFILE=</li>`
    - `AWS_ACCOUNT_NUMBER=</li>`
6. Docker images are present on ECR for the bot to perform its necessary action</li>
7. Docker installed on local machine to push images to ECR if required</li>


## Set-up:
1.  Update the .env file with all variables
2. Install ngrok:
    - https://ngrok.com/download (or) use the binary included with this repo
3. Run ngrok web server - `./ngrok`
4. Use the grok public endpoint to forward slack events API traffic to your local machine where flask app will be running
5. set up a python virtual environemnt and install dependencies</li>
    - `python3 -m venv .venv`
    - `source .venv/bin/activate`
    - `pip3 install -r requirements.txt`
    - `python3 ./bot.py`

<br>

---
<br>
Guide to set up slack account and create a bot account:
https://api.slack.com/start/building/bolt-python