import discord
import os
import requests
import json
from discord.ext import tasks
import datetime
from datetime import date

TOKEN = os.getenv('DISCORD_TOKEN')
graphqlUrl = 'https://footium.club/beta/api/graphql'

client = discord.Client()

version = "0.4"

signed_up = []

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
    stadiumName
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
    roundIndex = checkandupdateRoundIndex()
    #print(roundIndex)
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
                return

            # loads data into python object
            data = json.loads(r.content)
            liveMatch = data['data']['liveMatch']

            #print("home: "+ str(liveMatch['params']['homeClub']) + " VS " + str(user[1]) + " away: "+ str(liveMatch['params']['awayClub']['id'])+ " VS " + str(user[1]) )
            if liveMatch['params']['homeClub']['id'] == user[1]['id'] or user[1]['id'] == liveMatch['params']['awayClub']['id']:
                homeClubName = getClubDetails(liveMatch['params']['homeClub']['id'])['name']
                awayClubName = getClubDetails(liveMatch['params']['awayClub']['id'])['name']
                stadiumName = liveMatch['stadiumName']
                prevMessage = await user[0].dm_channel.history(limit=1).flatten()
                messageContent = ""
                if liveMatch['matchTime'] == "15:00":
                    messageContent = ("Your next game is " + homeClubName + "(H) vs " + awayClubName + "(A) you can click this link to see it:\nhttps://footium.club/beta/tournaments/" + str(user[2]) + "/match/" + str(roundIndex) + "/" + str(i) + "\nand update tatics here:\nhttps://footium.club/beta/clubs/" + str(user[1]['id']) + "/tactics\nBest of luck")
                elif liveMatch['matchTime'] == "1":
                    messageContent = ("Kick off at the " + stadiumName + "!!! This is bound to be a interesting battle between " + homeClubName + " and " + awayClubName)
                elif liveMatch['matchTime'] == "HT":
                    messageContent = ("QUICK it's half time, the score is " + formatScore(homeClubName,liveMatch['homeScorers'],awayClubName,liveMatch['awayScorers']) + ", there still is time to update your tatics here:\nhttps://footium.club/beta/clubs/" + str(user[1]['id']) + "/tactics")
                elif liveMatch['matchTime'] == "FT":
                    messageContent = ("Quality Match, Final score of: " + formatScore(homeClubName,liveMatch['homeScorers'],awayClubName,liveMatch['awayScorers']))
                else:
                    if user['3'] == "g":
                        await user[0].send("[UNFINISHED]")
                        return
                    elif int(liveMatch['matchTime']) % user[3] == 0:
                        messageContent = (liveMatch['matchTime'] + " | " + formatScore(homeClubName,liveMatch['homeScorers'],awayClubName,liveMatch['awayScorers']))
                if prevMessage[0].content == messageContent or messageContent == "":
                    pass
                else:
                    await user[0].send(messageContent)

@client.event
async def on_ready():
    print("{0.user} is online!".format(client) + "| v" + version + " |")

@client.event
async def on_message(message):
    #ignores own messages
    if message.author == client.user:
        #print("this:" + str(message.guild))
        return
    elif message.guild is not None:
        #message.channel.send("DM the bot ser!!")
        #await message.reply("DM the bot ser!!")
        return
    frequency = 1
    # testing
    # print(message.author.name + " sent " + message.content)
    try:
        variables = {"clubID": int(message.content)}
        r = requests.post(graphqlUrl, json={'query': getClubdetails, 'variables': variables})

        # api error checking
        if r.status_code != 200:
            print(r.status_code)
            await message.channel.send("Error Checking api, code:" + str(r.status_code))
        elif r.status_code == 500:
            await message.channel.send("Not valid club ID")

    except ValueError:
        if message.content == "x":
            for user in signed_up:
                if user[0] == message.author:
                    signed_up.remove(user)
                    await message.reply("you have been un-subscribed from the bot!")
            return
        elif message.content.startswith('f=') == True:
            #frequency = int()
            #print(message.content[2:])
            for user in signed_up:
                if user[0] == message.author:
                    if message.content[2:] == "g":
                        await message.reply("you will only recieve goal updates [UNFINISHED]")
                    else:
                        try:
                            if int(message.content[2:]) >= 90 or int(message.content[2:]) <= 0:
                                await message.reply("invalid frequency")
                                return
                            else:
                                user[3] = int(message.content[2:])
                                await message.reply("you have updated the frequency of your bot to give updates every " + message.content[2:] + " (in game) match minutes!")
                        except ValueError:
                            await message.reply("invalid frequency")
            return
        else:
            await message.channel.send("Not valid club ID")
            return

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
            return

        # loads data into python object
        data = json.loads(r.content)
        tID = data['data']['tournaments'][0]['id']

        previous = False
        for user in signed_up:
            if user[0] == message.author:
                await message.reply("you have already signed up!! " + message.author.name + ", send a 'x' to remove your previous club subscription!")
                previous = True
                #signed_up.remove(user)
                print(user)

        if previous == False:
            await message.reply("Thank you, "+ message.author.name + " ,you have signed up with club " + club['name'] + " , hold tight and wait for your match updates!! You can now change the frequency of match updates by sending f= and a number representing how many in game match minutes the bot will wait between updates")
            sign_up = [message.author, club, tID, frequency]
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

def checkandupdateRoundIndex():
    startDate = date(2022,5,12)
    today = datetime.datetime.today().date()
    #print(str((today-startDate).days))
    roundIndex = (today-startDate).days
    return roundIndex

myLoop.start()

client.run(TOKEN)
