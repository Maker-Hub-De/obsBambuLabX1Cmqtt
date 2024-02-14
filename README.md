<h1>obsbambuLabX1Cmqtt - OBS Script for BambuLab X1C Status Monitoring</h1>

<h2>Description</h2>
This OBS script allows users to monitor status data from a BambuLab X1C printer. It retrieves print information via MQTT and FTP protocols.

<h2>Features</h2>
<ul>
<li>Real-time monitoring of printer status</li>
<li>Supports MQTT for data retrieval</li>
<li>Fetches print information such as nozzle temperature, bed temperature, remaining time, etc.</li>
<li>Updates text sources in OBS with the obtained data</li>
<li>Periodic updates with user-defined intervals</li>
<li>Integration with OBS sources for visual representation of print status</li>
</ul>
<h2>Setup</h2>
<ol>
<li>Ensure that the required MQTT broker and FTP server are accessible.</li>
<li>Fill in the necessary environment variables including the MQTT host, port, user credentials, and printer serial number.</li>
<li>Set up OBS text sources for displaying different print parameters such as nozzle temperature, bed temperature, etc.</li>
<li>Configure the script properties including the update interval and image paths for model and plate images.</li>
</ol>
<h2>Settings</h2>
<ul>
<li>MQTT Host: Host address of the MQTT broker.</li>
<li>Access Code: Password for accessing the MQTT broker.</li>
<li>Serial Number: Serial number of the BambuLab X1C printer.</li>
<li>Update Interval (seconds): Time interval for updating printer status information.</li>
<li>Image path: Path to the directory containing model and plate images.</li>
<li>Plate: Selection of different printer plates for visual representation.</li>
<li>Picture source for plate: OBS source for displaying plate images.</li>
<li>Picture source for model: OBS source for displaying model images.</li>
<li>Text source for nozzle type: OBS source for displaying nozzle type information.</li>
<li>Text source for nozzle temperature: OBS source for displaying nozzle temperature information.</li>
<li>Text source for bed temperature: OBS source for displaying bed temperature information.</li>
<li>Text source for chamber temperature: OBS source for displaying chamber temperature information.</li>
<li>Text source for remaining print time: OBS source for displaying remaining print time information.</li>
<li>Text source for current layer: OBS source for displaying current layer information.</li>
<li>Text source for filament: OBS source for displaying filament information.</li>
<li>Text source for filament color: OBS source for displaying filament color information.</li>
<li>Text source for print completion percentage: OBS source for displaying print completion percentage.</li>
</ul>
Notes
Ensure that the required OBS sources are properly configured for accurate display of print status data.
Make sure to provide valid MQTT broker credentials and printer details for successful data retrieval.

<h2>Usage</h2>
<ol>
<li>Start the script by clicking the "START" button.</li>
<li>The script will connect to the MQTT broker and start retrieving printer status data.</li>
<li>Monitor the OBS sources configured with the script for real-time updates on print status.</li>
<li>Stop the script by clicking the "STOP" button when monitoring is no longer required.</li>
</ol>
