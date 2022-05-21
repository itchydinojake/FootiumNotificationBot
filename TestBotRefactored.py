import discord
import os
import requests
import json
from discord.ext import tasks
import time
from threading import Thread

TOKEN = os.getenv('DISCORD_TOKEN')
graphqlUrl = 'https://footium.club/beta/api/graphql'

client = discord.Client()

signed_up = []

roundIndex = 9

getMatchDetails = """query getMatchDetails($tId: Int!, $rId: Int!, $fId: Int!) {
  liveMatch(tournamentId: $tId, roundIndex: $rId, fixtureIndex: $fId) {
    params {
      homeClub {
        id
      }
      awayClub {
        id
      }
    }
    matchTime
    homeScorers
    awayScorers
  }
}"""

getClubdetails = """query getClubdetails($clubID: Int!) {
            club(id: $clubID){
                id
                name
                }
            }
        """

getTIDfromclubID = """
            query getTIDfromclubID($clubID: Int!) {
                tournaments(where: {teams_contains: $clubID}) {
                    id
                }
            }
        """


@tasks.loop(seconds = 10) # repeat after every 10 seconds
async def myLoop():
    for user in signed_up:
        #print(str(user))
        for i in range(0,6):
            variables = {"tId": user[2],"rId": roundIndex,"fId": i}
            r = requests.post(graphqlUrl, json={'query': getMatchDetails, 'variables': variables})
            #print(r.status_code)

            # api error checking
            if r.status_code != 200:
                # await message.channel.send("Error Checking api")
                print(r.status_code)
                quit()
            # loads data into python object
            data = json.loads(r.content)
            liveMatch = data['data']['liveMatch']


            #print("home: "+ str(liveMatch['params']['homeClub']) + " VS " + str(user[1]) + " away: "+ str(liveMatch['params']['awayClub']['id'])+ " VS " + str(user[1]) )
            if liveMatch['params']['homeClub']['id'] == user[1]['id'] or user[1]['id'] == liveMatch['params']['awayClub']['id']:
                homeClubName = getClubDetails(liveMatch['params']['homeClub']['id'])['name']
                awayClubName = getClubDetails(liveMatch['params']['awayClub']['id'])['name']
                prevMessage = await user[0].dm_channel.history(limit=1).flatten()
                messageContent = ""
                if liveMatch['matchTime'] == "15:00":
                    messageContent = ("https://footium.club/beta/tournaments/" + str(user[2]) + "/match/" + str(roundIndex) + "/" + str(i) + "\n https://footium.club/beta/clubs/" + str(user[1]['id']) + "/tactics")
                elif liveMatch['matchTime'] == "1":
                    messageContent = ("Kick off!!! This is bound to be a interesting battle between " + homeClubName + " and " + awayClubName)
                elif liveMatch['matchTime'] == "HT":
                    messageContent = ("QUICk it's half time, the score is " + formatScore(homeClubName,liveMatch['homeScorers'],awayClubName,liveMatch['awayScorers']) + ", theres time to update your tatics here: \n https://footium.club/beta/clubs/" + str(user[1]) + "/tactics")
                elif liveMatch['matchTime'] == "FT":
                    messageContent = ("Quality Match, Final score of: " + formatScore(homeClubName,liveMatch['homeScorers'],awayClubName,liveMatch['awayScorers']))
                else:
                    messageContent = (liveMatch['matchTime'] + " | " + formatScore(homeClubName,liveMatch['homeScorers'],awayClubName,liveMatch['awayScorers']))
                if prevMessage[0].content == messageContent or messageContent == "":
                    pass
                else:
                    await user[0].send(messageContent)
@client.event
async def on_ready():
    print("{0.user} is online!".format(client))

@client.event
async def on_message(message):
    #ignores own messages
    if message.author == client.user:
        return
    # testing
    # print(message.author.name + " sent " + message.content)
    try:
        variables = {"clubID": int(message.content)}
        r = requests.post(graphqlUrl, json={'query': getClubdetails, 'variables': variables})

        # api error checking
        if r.status_code != 200:
            print(r.status_code)
            await message.channel.send("Error Checking api, code:" + str(r.status_code))
            # quit()
        elif r.status_code == 500:
            await message.channel.send("Not valid club ID")

    except ValueError:
        await message.channel.send("Not valid club ID")

    # loads data into python object
    data = json.loads(r.content)
    club = data['data']['club']

    if club == None:
        await message.channel.send("Not valid club ID")
    else:
        selectedClub = club['id']
        variables = {"clubID": selectedClub}
        r = requests.post(graphqlUrl, json={'query': getTIDfromclubID, 'variables': variables})

        # api error checking
        if r.status_code != 200:
            # await message.channel.send("Error Checking api")
            print(r.status_code)
            quit()

        # loads data into python object
        data = json.loads(r.content)
        tID = data['data']['tournaments'][0]['id']

        previous = False
        for user in signed_up:
            if user[0] == message.author:
                await message.channel.send("you have already signed up!!" + user)
                previous = True
                #signed_up.remove(user)
                print(user)

        if previous == False:
            await message.channel.send("Thank you, "+ message.author.name + " ,you have signed up with club " + club['name'] + " in tournament " + str(tID) + "!!")
            sign_up = [message.author, club, tID]
            signed_up.append(sign_up)

def formatScore(homeTeam,homeScorers,awayTeam,awayScorers):
    score = str(homeTeam) + "    " + str(calcScore(homeScorers)) + " : " + str(calcScore(awayScorers)) + "    " + str(awayTeam)
    return score

def calcScore(scorers):
    if scorers == "" :
        return 0
    else:
        score = scorers.count(",") + 1
    return score

def getClubDetails(clubID):
    variables = {"clubID": clubID}
    r = requests.post(graphqlUrl, json={'query': getClubdetails, 'variables': variables})
    if r.status_code != 200:
        print(r.status_code)
    data = json.loads(r.content)
    club = data['data']['club']
    return club

myLoop.start()

client.run(TOKEN)