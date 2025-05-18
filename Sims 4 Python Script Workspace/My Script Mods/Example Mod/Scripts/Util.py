import os

def getPath():

    script_dir = os.path.dirname(os.path.dirname(__file__))

    # Construct the relative path
    relative_path = os.path.join(script_dir, 'visualization_log.txt')
    return relative_path

def timeToTimeStamp(time):
    """
    Converts a time object to a timestamp string.
    :param time: The time object to convert.
    :return: A timestamp
    """

