import os
import json

nameJson = {
	"info": {
		"participants": []
	}
}

def checkHasName(name, nameList):
	for sim in nameList:
		if sim["championName"] == name:
			return True
	return False

def addParticipant(name):
	participant = {}
	participant["participantId"] = len(nameJson["info"]["participants"]) + 1
	participant["championName"] = name
	nameJson["info"]["participants"].append(participant)


# generate sims id file
with open("./visualization_log.txt") as f:
	for line in f:
		jsonObj = json.loads(line)
		hasParticipant = checkHasName(jsonObj["sim_name"], nameJson["info"]["participants"])
		if not hasParticipant: 
			addParticipant(jsonObj["sim_name"])
		hasParticipant = checkHasName(jsonObj["target_name"], nameJson["info"]["participants"])
		if not hasParticipant: 
			addParticipant(jsonObj["target_name"])

f.close()

with open("./sims.json", "w") as f:
	json.dump(nameJson, f)

f.close()


# generate event json file
eventJson = []

# def getCharacterId(name):
# 	jsonObj = []
# 	with open("./sims.json") as simsFile:
# 		jsonObj = json.loads(simsFile.read())
# 	simsFile.close()

# 	for sim in jsonObj["info"]["participants"]:
# 			if sim["championName"] == name:
# 				return sim["participantId"]
# 	return False
def getCharacterId(name):
	for item in nameJson["info"]["participants"]:
		if name == item["championName"]:
			return item["participantId"]
	return False

with open("./visualization_log.txt") as f:
	firstTimeStamp = 0
	idx = 0
	for line in f:
		jsonObj = json.loads(line)
		simId = getCharacterId(jsonObj["sim_name"])
		targetId = getCharacterId(jsonObj["target_name"])
		#if int(simId) <= 5 and int(targetId) <= 5:
		currentJson = {}
		if idx == 0:
			firstTimeStamp = int(jsonObj["time"])
		currentJson["timestamp"] = int(jsonObj["time"]) - firstTimeStamp
		currentJson["interactor"] = jsonObj["sim_name"]
		currentJson["interactee"] = jsonObj["target_name"]
		currentJson["position"] = jsonObj["building_name"]
		currentJson["eventType"] = jsonObj["interaction_name"]
		# currentJson["killType"] = "CHAMPION_KILL"
		currentJson["interactorID"] = getCharacterId(jsonObj["sim_name"])
		currentJson["interacteeID"] = getCharacterId(jsonObj["target_name"])
		currentJson["eventDetails"] = ""
		eventJson.append(currentJson)
		idx = idx + 1
f.close()

with open("./simEvents.json", "w") as f:
	json.dump(eventJson, f)
f.close()


# generate event interaction type file
interactions = []

def checkHasInteraction(interaction):
	for item in interactions:
		if item == interaction:
			return True
	return False

for event in eventJson:
	isInInteractions = checkHasInteraction(event["eventType"])
	if not isInInteractions:
		interactions.append(event["eventType"])

with open("./interactions.json", "w") as f:
	json.dump(interactions, f)
f.close


# generate info file
infoJson = {
	"Story":{
		"Locations":{

		},
		"Characters":{

		}
	}
}

def checkHasPos(pos, posList):
	for key, value in posList.items():
		if key == pos:
			return True
	return False

def getLocationIdx(location):
	for key, value in infoJson["Story"]["Locations"].items():
		if key == location:
			return value[0]

	return False



locationIdx = 1
for event in eventJson:
	location = event["position"]
	if not checkHasPos(location, infoJson["Story"]["Locations"]):
		infoJson["Story"]["Locations"][location] = []
		infoJson["Story"]["Locations"][location].append(locationIdx)
		locationIdx = locationIdx + 1
	

def updateSessionData(characterKey, event):
	if not (characterKey in infoJson["Story"]["Characters"]):
		infoJson["Story"]["Characters"][characterKey] = []
	interactorSessions = infoJson["Story"]["Characters"][characterKey]
	if len(interactorSessions) == 0:
		tempSession = {}
		tempSession["Start"] = event["timestamp"]
		tempSession["End"] = event["timestamp"]
		tempSession["Session"] = getLocationIdx(event["position"])
		interactorSessions.append(tempSession)
	else: 
		if interactorSessions[len(infoJson["Story"]["Characters"][characterKey]) - 1]["Session"] == getLocationIdx(event["position"]):
			interactorSessions[len(infoJson["Story"]["Characters"][characterKey]) - 1]["End"] = event["timestamp"]
		else:
			tempSession = {}
			tempSession["Start"] = event["timestamp"]
			tempSession["End"] = event["timestamp"]
			tempSession["Session"] = getLocationIdx(event["position"])
			interactorSessions.append(tempSession)



for event in eventJson:
	# interactor
	interactorId = event["interactorID"]
	interactorKey = "Player" + str(interactorId)
	updateSessionData(interactorKey, event)
	# interactee
	interacteeId = event["interacteeID"]
	interacteeKey = "Player" + str(interacteeId)
	updateSessionData(interacteeKey, event)

	
	

	
with open("./simSessions.json", "w") as f:
	json.dump(infoJson, f)
f.close









