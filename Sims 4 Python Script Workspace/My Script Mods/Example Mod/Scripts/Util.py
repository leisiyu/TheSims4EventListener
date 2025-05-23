import os

def getPath():

    script_dir = os.path.dirname(os.path.dirname(__file__))

    # Construct the relative path
    relative_path = os.path.join(script_dir, 'visualization_log.txt')
    return relative_path

def timeToTimeStamp(simTime):
    """
    Converts a sim time object to a timestamp string.
    :param simTime: The time object to convert. e.g. "14:13:43.920 day:0 week:3"
    :return: A timestamp
    """
    time = simTime.second() + (simTime.minute() * 60) + (simTime.hour() * 3600) + (simTime.day() * 86400) + (simTime.week() * 604800)
    return time


