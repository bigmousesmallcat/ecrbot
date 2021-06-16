import slack
from flask import Flask
from slackeventsapi import SlackEventAdapter
import os
import json
from dotenv import load_dotenv
import boto3
from datetime import datetime as dt

aws_session = boto3.session.Session(profile_name=os.environ['AWS_PROFILE'])
ecr_client = aws_session.client('ecr')

load_dotenv()


app = Flask(__name__)
slack_client = slack.WebClient(token=os.environ['SLACK_TOKEN_'])

BOT_ID = slack_client.api_call("auth.test")['user_id']

slack_events_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET_'], "/slack/events", app)


## create a list of all available ECR repo names
def listAllEcrRepos():
    response = ecr_client.describe_repositories(
        registryId=os.environ['AWS_ACCOUNT_NUMBER']
    )

    allecrrepos=[]
    for elem in response['repositories']:
        allecrrepos.append(elem['repositoryName'])

    return allecrrepos


def repoValidation(CHANNEL_ID, inputrepolist, allecrrepos):
    validRepoIndicatorList=list()
    for elem in inputrepolist:
        if elem not in allecrrepos:
            # bot sends a message pn channel
            slack_client.chat_postMessage(channel=CHANNEL_ID, text=f'{elem} repo is not present in ECR - continuing if other valid repo names are given.')
            validRepoIndicatorList.append(False)
        else:
            validRepoIndicatorList.append(True)
    return validRepoIndicatorList


def deletebydate(repoName,date):
    response = ecr_client.describe_images(
        registryId=os.environ['AWS_ACCOUNT_NUMBER'],
        repositoryName=repoName
    )

    for elem in response["imageDetails"]:
        if elem['imagePushedAt'].replace(tzinfo=None) < dt.strptime(date, "%d/%m/%y"):
            response = ecr_client.batch_delete_image(
                registryId=os.environ['AWS_ACCOUNT_NUMBER'],
                repositoryName=repoName,
                imageIds=[
                    {
                        'imageDigest': elem['imageDigest']
                    }
                ]
            )

def deletebydigest(repoName,imageDigest):
    response = ecr_client.batch_delete_image(
                registryId=os.environ['AWS_ACCOUNT_NUMBER'],
                repositoryName=repoName,
                imageIds=[
                    {
                        'imageDigest': imageDigest
                    }
                ]
            )

def deletebytag(repoName,excludetaglist):
    response = ecr_client.describe_images(
        registryId=os.environ['AWS_ACCOUNT_NUMBER'],
        repositoryName=repoName
    )

    for elem in response["imageDetails"]:
        for tag in elem["imageTags"]:
            if tag not in excludetaglist:
                response = ecr_client.batch_delete_image(
                    registryId=os.environ['AWS_ACCOUNT_NUMBER'],
                    repositoryName=repoName,
                    imageIds=[
                        {
                            'imageDigest': elem['imageDigest'],
                            'imageTag': tag
                        }
                    ]
                )

def sortrepo(repoName):
    response = ecr_client.describe_images(
        registryId=os.environ['AWS_ACCOUNT_NUMBER'],
        repositoryName=repoName
    )

    tempdict=dict()
    for elem in response["imageDetails"]:
        tempdict[elem["imageDigest"]]=elem["imagePushedAt"].replace(tzinfo=None)

    sort_tempdict=sorted(tempdict.items(),key=lambda x:x[1])
    return sort_tempdict

def deleterepo(repoName):
    response = ecr_client.delete_repository(
        registryId=os.environ['AWS_ACCOUNT_NUMBER'],
        repositoryName=repoName,
        force=True
    )
     
def repoprocessing(CHANNEL_ID, query_dict,validRepoIndicatorList):
    if "date" in query_dict.keys():
        date_string=query_dict["date"]
        date_format = "%d/%m/%y"

        try:
            dt.strptime(date_string, date_format)

            for i in range(len(validRepoIndicatorList)):
                if (validRepoIndicatorList[i]==True):
                    deletebydate(query_dict["repo"][i],date_string)
                else:
                    slack_client.chat_postMessage(channel=CHANNEL_ID, text=f'{query_dict["repo"][i]} - repo is not present in ECR - skippnig deletion')

        except ValueError:
            # bot should messaage on channel - wrong date format
            slack_client.chat_postMessage(channel=CHANNEL_ID, text='date provided in invalid format, for clarification use - @bot help')

    if "latest_images" in query_dict.keys():
        # take each repo from input
            # list all image data
            # sort the list elems beased on time
            # delete first/last n images
        #process for images numbers
        number_of_excluded_images=query_dict["latest_images"]

        for i in range(len(validRepoIndicatorList)):
            if (validRepoIndicatorList[i]==True):
                sortedrepo = sortrepo(query_dict["repo"][i])

                if len(sortedrepo) < int(number_of_excluded_images):
                    slack_client.chat_postMessage(channel=CHANNEL_ID, text=f'{query_dict["repo"][i]} - repo does not contain enough images in ECR to keep latest {number_of_excluded_images}')

                else:
                    for i in range(0, len(sortedrepo)-number_of_excluded_images):
                        deletebydigest(query_dict["repo"][i], sortedrepo[0])

            else:
                slack_client.chat_postMessage(channel=CHANNEL_ID, text=f'{query_dict["repo"][i]} - repo is not present in ECR - skippnig deletion')


    if "exclude-tags" in query_dict.keys():
        for i in range(len(validRepoIndicatorList)):
            if (validRepoIndicatorList[i]==True):
                deletebytag(query_dict["repo"][i],query_dict["exclude-tags"])

    if "delete" in query_dict.keys():
        for i in range(len(validRepoIndicatorList)):
            if (validRepoIndicatorList[i]==True):
                deleterepo(query_dict["repo"][i])

    
def ecraction(event):
    CHANNEL_ID = event.get('channel')
    print(CHANNEL_ID, BOT_ID)

    text = event.get('text')
    keys = text.replace(f"<@{BOT_ID}>", "").split()

    print(keys)

    query_dict=dict()

    for key in keys:
        if "repo" in key:
            query_dict["repo"] = key.split("=")[1].split(",")
        if "date" in key:
            query_dict["date"] = key.split("=")[1]
        if "exclude-tags" in key:
            query_dict["exclude-tags"] = key.split("=")[1].split(",")
        if "latest_images" in key:
            query_dict["latest_images"] = key.split("=")[1]
        if "delete" in key:
            query_dict["delete"] = True

    if(len(query_dict)!=2):
        slack_client.chat_postMessage(channel=CHANNEL_ID, text="Invalid command! check available commands - @bot help")
    else:
        allecrrepos = listAllEcrRepos()

        ## if the user requests action on all repos then genrerate a list of all 
        ## available repos for further action
        if query_dict.get('repo')[0]=='all':
            query_dict['repo']=allecrrepos

        validRepoIndicatorList = repoValidation(CHANNEL_ID, query_dict["repo"],allecrrepos)
        repoprocessing(CHANNEL_ID, query_dict,validRepoIndicatorList)


# Create an event listener for "app_mention" events
@ slack_events_adapter.on('app_mention')
def mention(payload):
    event = payload.get('event', {})
    user_id = event.get('user')
    CHANNEL_ID = event.get('channel')

    if user_id != BOT_ID:
        if "help" in event.get('text'):
            slack_client.chat_postMessage(
                channel=CHANNEL_ID, 
                text="""Hi there, my name is ECRbot and I'm here to help you with various actions on your ECR repositories.
                Following list of commands are acceptable. Wherever possible I'll bring to your attention any errors in your input.
                1) @bot repo=<list> date=<mm/dd/yy> eg. repo=alpine date=10/01/21 
                2) @bot repo=<list> latest_images=<number> eg. repo=alpine,swarm,busybox latest_images=10
                3) @bot repo=<list> exclude-tags=<list> eg. repo=all exclude-tags=prod,staging
                4) @bot repo=<list> delete eg. repo=all delete
                """
            )
        else:
            ecraction(event)

# Start the server on port 3000
if __name__ == "__main__":
  app.run(debug=True, port=3000)
