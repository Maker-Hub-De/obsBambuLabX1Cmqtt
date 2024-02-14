# OBS python script for reading status data from a BambuLab X1C
# Author: Mia Sophie Behrendt; Maker-Hub.de
# Description: Read status data from a BambuLab X1C

import obspython as obs
import paho.mqtt.client as mqtt
import ssl
import json
import datetime
import threading
import time
import ftplib
from io import BytesIO
import zipfile
import os

class ImplicitFTP_TLS(ftplib.FTP_TLS):
    """FTP_TLS subclass to support implicit FTPS."""
    """Constructor takes a boolean parameter ignore_PASV_host whether o ignore the hostname"""
    """in the PASV response, and use the hostname from the session instead"""
    def __init__(self, *args, **kwargs):
        self.ignore_PASV_host = kwargs.get('ignore_PASV_host') == True
        super().__init__(*args, {k: v for k, v in kwargs.items() if not k == 'ignore_PASV_host'})
        self._sock = None

    @property
    def sock(self):
        """Return the socket."""
        return self._sock

    @sock.setter
    def sock(self, value):
        """When modifying the socket, ensure that it is ssl wrapped."""
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value)
        self._sock = value

    def ntransfercmd(self, cmd, rest=None):
        """Override the ntransfercmd method"""
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        conn = self.sock.context.wrap_socket(
            conn, server_hostname=self.host, session=self.sock.session
        )
        return conn, size        
     
    def makepasv(self):
        host, port = super().makepasv()
        return (self.host if self.ignore_PASV_host else host), port  

# environment variables
environment = {
    "host": "",
    "mqttPort": 8883,
    "ftpPort": 990,
    "user": "bblp",
    "secret": "",
    "serialNumber": "",
    "interval": 5,
    "stopThread": False, # control the thread
    "thread": None, # hold the thread
    "updateThread": None, # Initialize the update thread
    "mqttClient": None, # MQTT client
    "taskId": "", # Task id
    "imageFolderPath": "" # Path to the images   
}

# Textvariable
hardenedSteel = "gehärteter Stahl"
undefine = "nicht definiert"
stainlessSteel = "Edelstahl"
singularMinute = "Minute"
singularHour = "Stunde"
pluralMinute = "Minuten"
pluralHour = "Stunden"

# Source variable
sourcesName = {
    "nozzleType": "",
    "nozzleTemp": "",
    "bedTemp": "",
    "chamberTemp": "",
    "remainingTime": "",
    "layer": "",
    "filament": "",
    "filamentColor": "",
    "percentFinish": "",
    "model": ""
}

"""
Logs the given message with a timestamp.

Args:
    *args: Variable number of positional arguments.
    **kwargs: Variable number of keyword arguments.
"""
def log(*args, **kwargs):
    # Get the current time and format it
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Print the timestamp along with the original message
    print(f"[{current_time}]", *args, **kwargs)


"""
Returns the description of the script.
"""
def script_description():
    return "Read status data from a BambuLab X1C\n\nBy Mia Sophie Behrendt\nMaker-Hub.de"


"""
Updates the text source with the given text.

Args:
    source_name (str): The name of the text source.
    text (str): The text to update the source with.
"""
def update_text_source(source_name, text):
    source_obj = obs.obs_get_source_by_name(source_name)
    if source_obj:
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", text)
        obs.obs_source_update(source_obj, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source_obj)


"""
Formats the remaining time.

Args:
    mc_remaining_time (int): The remaining time in minutes.

Returns:
    str: The formatted remaining time.
"""
def formatTime(remainingTime):
     global singularMinute
     global singularHour
     global pluralMinute
     global pluralHour

     # Überprüfe, ob mc_remaining_time eine Zeichenkette ist und versuche sie in eine Ganzzahl umzuwandeln
     if isinstance(remainingTime, str):
          try:
               remainingTime = int(remainingTime)
          except ValueError:
               return "0 " + pluralMinute

     # Stelle sicher, dass mc_remaining_time eine positive Ganzzahl ist
     if remainingTime < 0:
          return "0 " + pluralMinute

     # Umrechnung von Minuten in Stunden und Minuten
     hours = remainingTime // 60
     minutes = remainingTime % 60
    
     # Erstellung der formatierten Zeitangabe
     formattedTime = ""
     if hours > 0:
          formattedTime += f"{hours} {singularHour if hours == 1 else pluralHour} "
     formattedTime += f"{minutes} {singularMinute if minutes == 1 else pluralMinute}"
    
     return formattedTime


"""
Sets the color for a given source.

Args:
    source_name (str): The name of the source.
    color (int): The color to set.
"""
def set_color(source_name, color):
    sourceField = obs.obs_get_source_by_name(source_name)
    if sourceField is None:
        return

    settings = obs.obs_source_get_settings(sourceField)
    obs.obs_data_set_int(settings, "color", color) 
    obs.obs_source_update(sourceField, settings)
    obs.obs_data_release(settings)
    obs.obs_source_release(sourceField)


"""
Sets the value for a given source.

Args:
    sourceName (str): The name of the source.
    value (str): The value to set.
"""
def setSourceValue(sourceName, value):
    sourceField = None
    if sourceName == "" or sourceName == "[No source]":
        return

    sourceField  = obs.obs_get_source_by_name(sourceName) 
    if sourceField is None:
        return

    text_settings = obs.obs_data_create()
    obs.obs_data_set_string(text_settings, "text", value)

    obs.obs_source_update(sourceField, text_settings)
    obs.obs_data_release(text_settings)
    obs.obs_source_release(sourceField)


"""
Gets the plate key from the given value.

Args:
    value (str): The value to get the key for.

Returns:
    str: The plate key.
"""
def get_plate_key_from_value(value):
    if value == "Bambu Cool Plate":
        return "BambuCoolPlate.png"
    elif value == "Bambu Engineering Plate":
        return "BambuEngineeringPlate.png"
    elif value == "Bambu High Temperature Plate (PEI)":
        return "BambuSmoothPEIPlateHighTempPlate.png"
    elif value == "Bambu Dual-Sided Smooth PEI Plate":
        return "BambuSmoothPEIPlateHighTempPlate.png"
    elif value == "Bambu Textured PEI Plate":
        return "BambuTexturedPEIPlate.png"
    else:
        return None

"""
Gets the current model image from the printer via ftp

Args:
    nodePrint (array): Json node printer

"""
def getModelImage(nodePrint):
    global sourcesName
    global environment

    if not environment["imageFolderPath"] or not sourcesName["model"] or sourcesName["model"] == "[No source]":
        return

    imageFolderPath = os.path.join(environment["imageFolderPath"], "model")

    # Getting current model file name
    modelFileName = nodePrint.get("subtask_name", "")
    if not modelFileName:
        return

    # Getting operation mode
    printType  = nodePrint.get("print_type", "")

    if printType == "cloud":
        modelFileName += ".3mf"
        modelFileName = "cache/" + modelFileName
    else:
        modelFileName += ".gcode.3mf"

    # Getting current plate which represents the image file
    modelImageFileName = nodePrint.get("gcode_file", "")
    if not modelImageFileName:
        return

    log("Loading model image")

    modelImageFileName = os.path.basename(modelImageFileName)
    modelImageFileName = os.path.splitext(modelImageFileName)[0]
    modelImageFileName += ".png"

    # Create a BytesIO object to store data in memory
    modelZipBinary = BytesIO()
    imageFileBinary = BytesIO()

    # Establish implicit ftp connection via TLS connection
    try:
        with ImplicitFTP_TLS() as ftpClient:
            ftpClient.connect(host=environment["host"], port=environment["ftpPort"])
            ftpClient.login(user=environment["user"], passwd=environment["secret"])
            ftpClient.prot_p()
            ftpClient.retrbinary('RETR ' + modelFileName, modelZipBinary.write)

    except ConnectionError:
        log("Error establishing FTP connection:")
        return
    except PermissionError:
        log("Failed to authenticate. Check your username and password.")
        return
    except Exception as e:
        log("ftp error:", e)
        return

    # Reset the file pointer to the beginning of the BytesIO object

    # Checking if the file is a zipfile
    if not zipfile.is_zipfile(modelZipBinary):
        return

    modelZipBinary.seek(0)

    # Unpacking needed image from zip file
    with zipfile.ZipFile(modelZipBinary, 'r') as modelZipObject:
        desiredImage = "Metadata/" + modelImageFileName
        if desiredImage not in modelZipObject.namelist():
            return  # Image not found in the zip file

        imageFileBinary = modelZipObject.read(desiredImage)

    # Checking if the file already exists and creating if not so
    os.makedirs(imageFolderPath, exist_ok=True)

    # Save the image data to the desired directory
    modelImageFileName = os.path.join(imageFolderPath, modelImageFileName)

    with open(modelImageFileName, 'wb') as outputImageFile:
        outputImageFile.write(imageFileBinary)

    # Setting model image path to the image source
    modelSource = obs.obs_get_source_by_name(sourcesName["model"])
    if modelSource is None:
        return

    # Setting image path to image source
    text_settings = obs.obs_data_create()
    obs.obs_data_set_string(text_settings, "file", modelImageFileName)
    obs.obs_source_update(modelSource, text_settings)
    obs.obs_data_release(text_settings)
    obs.obs_source_release(modelSource)


def getTrayInformation(nodePrint):
    trayType = ""
    trayColor = "FFFFFF"

    # Der Tray-Index befindet sich in nodeAms
    nodeAms = nodePrint.get("ams", None)

    if nodeAms is None:
        return trayType, trayColor

    # Aktuellen Tray-Index abrufen
    currentTrayId = nodeAms.get("tray_now", "")

    if int(currentTrayId) < 0:
        return trayType, trayColor

    # Externer Tray
    if currentTrayId == "254": 
        nodeVtTray = nodePrint.get("vt_tray", None)

        # Externer Tray-Knoten überprüfen
        if nodeVtTray is None:
            return trayType, trayColor

        trayType = nodeVtTray.get("tray_type", "")
        trayColor = nodeVtTray.get("tray_color", "")
        return trayType, trayColor

    # Handle tray id from AMS
    nodeAmsArray = nodeAms.get("ams", None)

    # Kein verbundenes AMS gefunden
    if nodeAmsArray is None or len(nodeAmsArray) == 0:
        return trayType, trayColor

    # Alle Trays von aktuellem AMS erhalten
    nodeCurrentAmsTrays = nodeAmsArray[0].get("tray", None)

    if nodeCurrentAmsTrays is None or len(nodeCurrentAmsTrays) == 0:
        return trayType, trayColor

    for index, nodeTray in enumerate(nodeCurrentAmsTrays):
        # Tray-ID abrufen
        trayId = nodeTray.get("id", None)
        if trayId is None or trayId != currentTrayId:
            continue

        trayType = nodeTray.get("tray_type", "")
        trayColor = nodeTray.get("tray_color", "")

    return trayType, trayColor


"""
Callback function for handling MQTT messages.

Args:
    mqttClient: The mqtt client instance.
    userdata: The user data.
    msg: The MQTT message.
"""
def onMessage(mqttClient, userdata, msg):
    global sourcesName
    global environment

    try:
        # Extract the message content and decode it from JSON
        jsonData = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        # Im Fehlerfall, gib None zurück
        return

    nodePrint =  jsonData.get("print", None)

    if nodePrint is None:
        return

    # Extrahiere die gewünschten Informationen aus der Nachricht
    bedTargetTemper = nodePrint.get("bed_target_temper", 0)
    bedTemper = nodePrint.get("bed_temper", 0)
    chamberTemper = nodePrint.get("chamber_temper", 0)
    mcPercent = nodePrint.get("mc_percent", 0)
    mcRemainingTime = nodePrint.get("mc_remaining_time", 0)
    nozzleType = nodePrint.get("nozzle_type", "")
    nozzleDiameter = nodePrint.get("nozzle_diameter", "")
    nozzleTargetTemper = nodePrint.get("nozzle_target_temper", 0)
    nozzleTemper = nodePrint.get("nozzle_temper", 0)
    totalLayerNum = nodePrint.get("total_layer_num", 0)
    currentLayer = nodePrint.get("layer_num", 0)

    currentTaskId = nodePrint.get("task_id", "")

    if currentTaskId != environment["taskId"]:
        environment["taskId"] = currentTaskId

        if sourcesName["model"] != "" and sourcesName["model"] != "[No source]":
            # Load Model image
            getModelImage(nodePrint)


    # Getting tray information
    trayType, trayColor = getTrayInformation(nodePrint)

    # Set text for nozzle type
    if nozzleType == "hardened_steel":
        setSourceValue(sourcesName["nozzleType"], nozzleDiameter + " " + hardenedSteel)
    elif nozzleType == "stainless_steel":
        setSourceValue(sourcesName["nozzleType"], nozzleDiameter + " " + stainlessSteel)
    else:
        setSourceValue(sourcesName["nozzleType"], nozzleDiameter + " " + undefine)	

    # Set text for nozzle temp
    setSourceValue(sourcesName["nozzleTemp"], f"{nozzleTemper}°C / {nozzleTargetTemper}°C")

    # Set text for bed temp
    setSourceValue(sourcesName["bedTemp"], f"{bedTemper}°C / {bedTargetTemper}°C")

    # Set text for chamber temp
    setSourceValue(sourcesName["chamberTemp"], f"{chamberTemper}°C")

    # Set text for remaining time
    setSourceValue(sourcesName["remainingTime"], formatTime(mcRemainingTime))

    # Set text for layer
    setSourceValue(sourcesName["layer"], f"{currentLayer}  /  {totalLayerNum}")

    # Set text for percent finish
    setSourceValue(sourcesName["percentFinish"], f"{mcPercent}%")

    # Set text for filament
    setSourceValue(sourcesName["filament"], trayType)

    # Set backgrund color for filament color
    if sourcesName["filamentColor"] != "" and sourcesName["filamentColor"] != "[No source]":
        set_color(sourcesName["filamentColor"], int(trayColor[:2] + trayColor[4:6] + trayColor[2:4] + trayColor[6:8], 16))


"""
Thread function to update data periodically.
"""
def threadedUpdate():
    global environment

    while True:
        if environment["stopThread"]:
            disconnect()
            log("update thread stoped")
            break
        
        start_time = time.time()

        try:
            if environment["mqttClient"] is not None:
                environment["mqttClient"].loop()
        except Exception as e:
            log(f'Error in mqtt client loop: {e}')
        
        # Calculate the remaining time to sleep
        elapsed_time = time.time() - start_time
        sleep_time = max(0, environment["interval"] - elapsed_time)
        
        # Sleep in small intervals to allow responding quickly to the environment["stopThread"] flag
        while sleep_time > 0 and not environment["stopThread"]:
            time.sleep(min(1, sleep_time))
            sleep_time = max(0, environment["interval"] - (time.time() - start_time))


"""
Connects to the MQTT broker.
"""
def connect():
    global environment

    if environment["mqttClient"] is not None and environment["mqttClient"].is_connected():
        environment["mqttClient"].disconnect()

    if environment["mqttClient"] is not None:
        environment["mqttClient"] = None

    log("Connecting to MQTT broker...")

    try:
        environment["mqttClient"] = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        # Set username and password if provided
        environment["mqttClient"].username_pw_set(environment["user"], environment["secret"])

        # Set the callback function
        environment["mqttClient"].on_message = onMessage
        environment["mqttClient"].on_disconnect = onDisconnect
        environment["mqttClient"].on_connect = onConnect

        # Set TLS parameters
        environment["mqttClient"].tls_set(cert_reqs=ssl.CERT_NONE)
        environment["mqttClient"].connect( environment["host"], environment["mqttPort"], 60)

    except Exception as e:
        log("Error connecting to MQTT broker:", e)
        return False

    return True

"""
Reconnects to the MQTT broker.
"""
def reconnect():
    global environment

    environment["mqttClient"].connect( environment["host"], environment["mqttPort"], 60)


"""
Disconnects from the MQTT broker.
"""
def disconnect():
    global environment

    if environment["mqttClient"] is not None and environment["mqttClient"].is_connected():
        environment["mqttClient"].disconnect()
    environment["mqttClient"] = None  


"""
Callback function for MQTT connection.

Args:
    mqttClient: The MQTT clientinstance.
    userdata: The user data.
    flags: The flags.
    rc: The return code.
"""
def onConnect(mqttClient, userdata, flags, rc, prop):
    global environment

    if not mqttClient.is_connected():
        return

    log("MQTT connection successful")

    mqttTopic = "device/" + environment["serialNumber"] + "/report"
    mqttClient.subscribe(mqttTopic)


"""
Callback function for MQTT disconnection.

Args:
    mqttClient: The MQTT client instance.
    userdata: The user data associated with the client.
    rc: The disconnection return code.
"""
def onDisconnect(mqttClient, userdata, flags, rc, prop):
    if rc == 5:
        log("Incorrect access code; please verify it")
        environment["stopThread"] = True
        return

    elif rc != 0:
        log(f"Unexpected disconnection from MQTT broker: {rc}")
        reconnect()
        return


"""
Callback function for the start button.

Args:
    props: The properties.
    prop: The property.
"""
def startButtonPressed(props, prop):
    global environment

    environment["taskId"] = ""

    # Checking if all required fields are maintained
    if environment["serialNumber"] == "" \
        and environment["host"] == "" \
        and environment["secret"] == "":
        log("Some required fields are missing")
        return

    # Checking if at least one output source is maintained
    if not any(sourcesName.values()):
        log("No output source maintained")
        return

    # If there is an existing thread, stop it
    if environment["updateThread"] is not None and environment["updateThread"].is_alive():
        environment["stopThread"] = True
        environment["updateThread"].join()  # Wait for the existing thread to exit
        log("Existing thread stopped")
    if not connect():
        return

    # Reset the environment["stopThread"] flag and start a new thread
    environment["stopThread"] = False
    environment["updateThread"] = threading.Thread(target=threadedUpdate)
    environment["updateThread"].daemon = True  # set the thread as a daemon so it will close when OBS closes
    environment["updateThread"].start()
    log("New update thread started")


"""
Callback function for the stop button.

Args:
    props: The properties.
    prop: The property.
"""
def stopButtonPressed(props, prop):
    global environment
    environment["stopThread"] = True


"""
Sets up the properties for the script.
"""
def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_button(props, "start_button", "START", startButtonPressed)
    obs.obs_properties_add_button(props, "stop_button", "STOP", stopButtonPressed)
    obs.obs_properties_add_text(props, "paragraph1", "", obs.OBS_TEXT_INFO)

    obs.obs_properties_add_text(props, "host", "MQTT Host*", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "password", "Access code*", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "serialNumber", "Serialnumber*", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(props, "interval", "Update Interval (seconds)*", 5, 3600, 1)
    obs.obs_properties_add_text(props, "requiredInfo", "* required fields", obs.OBS_TEXT_INFO)
    obs.obs_properties_add_text(props, "paragraph2", "", obs.OBS_TEXT_INFO)

    # plate selection
    dropDownPlate = obs.obs_properties_add_list(props, "plate", "Plate", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownPlate,  "Bambu Cool Plate", "Bambu Cool Plate")
    obs.obs_property_list_add_string(dropDownPlate, "Bambu Engineering Plate", "Bambu Engineering Plate")
    obs.obs_property_list_add_string(dropDownPlate, "Bambu High Temperature Plate (PEI)", "Bambu High Temperature Plate (PEI)")
    obs.obs_property_list_add_string(dropDownPlate, "Bambu Dual-Sided Smooth PEI Plate", "Bambu Dual-Sided Smooth PEI Plate")
    obs.obs_property_list_add_string(dropDownPlate, "Bambu Textured PEI Plate", "Bambu Textured PEI Plate")

    obs.obs_properties_add_path(props, "imageFolderPath", "Image path", obs.OBS_PATH_DIRECTORY, "Select directory", None)

    # Picture source for plate
    dropDownPlateSource = obs.obs_properties_add_list(props, "sourcePlate", "Picture source for plate", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownPlateSource, "[No source]", "[No source]")

    # Picture source for model
    dropDownModelSource = obs.obs_properties_add_list(props, "sourceModel", "Picture source for model", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownModelSource, "[No source]", "[No source]")

    obs.obs_properties_add_text(props, "paragraph3", "", obs.OBS_TEXT_INFO)

    # Text source for nozzle type
    dropDownNozzleType = obs.obs_properties_add_list(props, "sourceNozzleType", "Text source for nozzle type", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownNozzleType, "[No source]", "[No source]")

    # Text source for nozzle temperature
    dropDownNozzleTemp = obs.obs_properties_add_list(props, "sourceNozzleTemp", "Text source for nozzle temperature", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownNozzleTemp, "[No source]", "[No source]")

    # Text source for bed temperature
    dropDownBedTemp = obs.obs_properties_add_list(props, "sourceBedTemp", "Text source for bed temperature", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownBedTemp, "[No source]", "[No source]")

    # Text source for chamber temperature
    dropDownChamberTemp = obs.obs_properties_add_list(props, "sourceChamberTemp", "Text source for chamber temperature", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownChamberTemp, "[No source]", "[No source]")

    # Text source for remaining print time
    dropDownRemainingTime = obs.obs_properties_add_list(props, "sourceRemainingTime", "Text source for remaining print time", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownRemainingTime, "[No source]", "[No source]")

    # Text source for current layer
    dropDownLayer = obs.obs_properties_add_list(props, "sourceLayer", "Text source for current layer", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownLayer, "[No source]", "[No source]")

    # Text source for filament
    dropDownFilament = obs.obs_properties_add_list(props, "sourceFilament", "Text source for filament", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownFilament, "[No source]", "[No source]")

    # Text source for filament color
    dropDownFilamentColor = obs.obs_properties_add_list(props, "sourceFilamentColor", "Text source for filament color", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownFilamentColor, "[No source]", "[No source]")

    # Text source for print completion percentage
    dropDownPercentFinish = obs.obs_properties_add_list(props, "sourcePercentFinish", "Text source for print completion percentage", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(dropDownPercentFinish, "[No source]", "[No source]")

    # Getting sources
    sources = obs.obs_enum_sources()
    
    if sources:
        for source in sources:
            source_id = obs.obs_source_get_unversioned_id(source)
            if source_id in ("text_gdiplus", "text_ft2_source"):
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(dropDownNozzleType, name, name)
                obs.obs_property_list_add_string(dropDownNozzleTemp, name, name)
                obs.obs_property_list_add_string(dropDownBedTemp, name, name)
                obs.obs_property_list_add_string(dropDownChamberTemp, name, name)
                obs.obs_property_list_add_string(dropDownRemainingTime, name, name)
                obs.obs_property_list_add_string(dropDownLayer, name, name)
                obs.obs_property_list_add_string(dropDownFilament, name, name)
                obs.obs_property_list_add_string(dropDownFilamentColor, name, name)
                obs.obs_property_list_add_string(dropDownPercentFinish, name, name)

            if source_id == "image_source":
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(dropDownPlateSource, name, name)
                obs.obs_property_list_add_string(dropDownModelSource, name, name)

    if sources:
        obs.source_list_release(sources)

    return props

"""
Updates the script settings.
Called when the script’s settings (if any) have been changed by the user.

Args:
    settings: The settings.
"""
def script_update(settings):
    global environment

    # Source variable
    global sourcesName

    # Read user-defined settings
    environment["host"]  = obs.obs_data_get_string(settings, "host")
    environment["secret"] = obs.obs_data_get_string(settings, "password")
    environment["serialNumber"] = obs.obs_data_get_string(settings, "serialNumber")
    environment["interval"] = obs.obs_data_get_int(settings, "interval")
    environment["interval"] = obs.obs_data_get_int(settings, "interval")
    environment["imageFolderPath"] = obs.obs_data_get_string(settings, "imageFolderPath")
    
    # Read user-defined text sources
    sourcesName["nozzleType"] = obs.obs_data_get_string(settings, "sourceNozzleType")
    sourcesName["nozzleTemp"] = obs.obs_data_get_string(settings, "sourceNozzleTemp")
    sourcesName["bedTemp"] = obs.obs_data_get_string(settings, "sourceBedTemp")
    sourcesName["chamberTemp"] = obs.obs_data_get_string(settings, "sourceChamberTemp")
    sourcesName["remainingTime"] = obs.obs_data_get_string(settings, "sourceRemainingTime")
    sourcesName["layer"] = obs.obs_data_get_string(settings, "sourceLayer")
    sourcesName["filament"] = obs.obs_data_get_string(settings, "sourceFilament")
    sourcesName["filamentColor"] = obs.obs_data_get_string(settings, "sourceFilamentColor")
    sourcesName["percentFinish"] = obs.obs_data_get_string(settings, "sourcePercentFinish")
    sourcesName["model"] = obs.obs_data_get_string(settings, "sourceModel")

    sourcePlate = obs.obs_data_get_string(settings, "sourcePlate")
    plate = obs.obs_data_get_string(settings, "plate")

    if environment["imageFolderPath"] and sourcePlate != "" and sourcePlate != "[No picture source]" and plate:

        # Getting image source to show the plate
        source = obs.obs_get_source_by_name(sourcePlate)
        if source is not None:
            # Setting image path to image source
            text_settings = obs.obs_data_create()
            imageUrl = os.path.join(environment["imageFolderPath"], get_plate_key_from_value(plate))
            obs.obs_data_set_string(text_settings, "file", imageUrl)
            obs.obs_source_update(source, text_settings)
            obs.obs_data_release(text_settings)
            obs.obs_source_release(source)