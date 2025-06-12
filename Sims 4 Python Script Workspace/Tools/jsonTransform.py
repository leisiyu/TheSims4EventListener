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

def getCharacterId(name):
	jsonObj = []
	with open("./sims.json") as simsFile:
		jsonObj = json.loads(simsFile.read())
	simsFile.close()

	for sim in jsonObj["info"]["participants"]:
			if sim["championName"] == name:
				return sim["participantId"]
	return False

getCharacterId("haha")
with open("./visualization_log.txt") as f:
	for line in f:
		jsonObj = json.loads(line)
		simId = getCharacterId(jsonObj["sim_name"])
		targetId = getCharacterId(jsonObj["target_name"])
		if int(simId) <= 5 and int(targetId) <= 5:
			currentJson = {}
			currentJson["timestamp"] = int(jsonObj["time"]) - 1965125
			currentJson["killerName"] = jsonObj["sim_name"]
			currentJson["victimName"] = jsonObj["target_name"]
			currentJson["position"] = jsonObj["building_name"]
			currentJson["killType"] = jsonObj["interaction_name"]
			# currentJson["killType"] = "CHAMPION_KILL"
			currentJson["killerID"] = getCharacterId(jsonObj["sim_name"])
			currentJson["victimID"] = getCharacterId(jsonObj["target_name"])
			eventJson.append(currentJson)
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
	isInInteractions = checkHasInteraction(event["killType"])
	if not isInInteractions:
		interactions.append(event["killType"])

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
sessions = []
def checkHasPos(pos, posList):
	for key, value in posList.items():
		if key == pos:
			return True
	return False

locationIdx = 1
for event in eventJson:
	if not checkHasPos(event["position"], infoJson["Story"]["Locations"]):
		infoJson["Story"]["Locations"][event["position"]] = []
		infoJson["Story"]["Locations"][event["position"]].append(locationIdx)
		locationIdx = locationIdx + 1
	location = event["position"]
	if len(sessions) <= 0:
		sessions.append({"location": location, "start": event["timestamp"], "end": event["timestamp"]})
		infoJson["Story"]["Locations"][location].append(1)
	else: 
		if sessions[len(sessions) - 1]["location"] == location:
			sessions[len(sessions) - 1]["end"] = event["timestamp"]
		else:
			sessions.append({"location": location, "start": event["timestamp"], "end": event["timestamp"]})
			infoJson["Story"]["Locations"][location].append(len(sessions))


# for event in eventJson:
# 	for player in nameJson["info"]["participants"]:
# 		if player["championName"]
	










