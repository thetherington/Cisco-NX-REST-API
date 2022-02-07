# Cisco Nexus Metrics and Log Collection

Cisco NX metrics collector designed for the inSITE Poller program python module. Metrics collector module uses the NX-REST-API feature of a Cisco Nexus Switch. Package also contains configuration for log and netflow data collection.  Custom dashboards are included to visulize the cisco metric and log data. 

The module uses the Magnum SDVN configuration from the inSITE Magnum collector to annotate the metric data with device names and source descriptions. 

The metrics collection module has the below distinct abilities and features:

1. Collects CPU, memory, temperature and module status.
   - _show hardware_
   - _show environment_
   - _show system resources_
2. Collects physical port statistics. 
   - _show interface_
3. Collects multicast routing table information.
   - _show ip mroute_
4. Collects netflow protocol information.  Netflow data is annotated into the multicast routing table data collection.
5. Collects Cisco NX syslog and with custom log parsing.
6. Magnum SDVN configuration is annotated into the metric data collection.
7. High level dashboards to navigate and access logs and metric information.

## Minimum Requirements:

- inSITE Version 11.
- Imported Magnum SDVN Configuration containing the Cisco NBM devices.
- Python3.7 (_already installed on inSITE machine_)
- Python3.7 Requests library (_already installed on inSITE machine_)
- Netflow setup is configured on the Cisco device(s). 
  _see extra/commands for configuration reference_
- Syslog setup is configured on the Cisco device(s). 
  _see extra/commands for configuration reference_
- Sufficent knowledge of Kibana to import dashboards and configure index patterns.

## Installation of the Script Module and Logstash Configuration:

1. Installation of the metrics collection module starts with setting up the logstash template files for netflow and syslog. Below command creates a folder and copy the template files into the created _mappings_ folder.

   ```
    sudo install -d -m 0755 -o insite -g insite /opt/mappings
    cp logstash/elasticsearch-template-netflow.json /opt/mappings/
    cp logstash/elasticsearch-template-ciscolog.json /opt/mappings/
   ```
2. Load the logstash custom configuration needs to be imported.  Log into insite with user:_developer_, password:_-open-up-_
3. Find the _Collectibles (Unicast) - Logstash_ program and select the __node__ settings link.
4. Select the _Collectables_ tab, and then click the __Expert Options__ link.
5. Copy and paste the contents of logstash/__logstash.yaml__ into the panel. 
6. Press __OK__, then Press __Save__ to apply the changes.
7. Copy __CiscoNX.py__ script to the poller python modules folder:
   ```
    cp scripts/CiscoNX.py /opt/evertz/insite/parasite/applications/pll-1/data/python/modules/
   ```
8. Restart the poller application

## Configuration:

To configure a poller to use the module start a new python poller configuration outlined below:

1. Click the create a custom poller from the poller application settings page.
2. Enter a Name, Summary and Description information.
3. Enter the ip address of the Cisco switch in the _Hosts_ tab.
4. From the _Input_ tab change the _Type_ to __Python__
5. From the _Input_ tab change the _Metric Set Name_ field to __cisconx__
6. From the _Python_ tab select the _Advanced_ tab and enable the __CPython Bindings__ option
7. Select the _Script_ tab, then paste the contents of scripts/__poller_config.py__ into the script panel.
8. The poller config script reqires a couple modifications for it to access the REST-API interface, and the magnum configuration.

    1. Update the __user__ and __password__ key in the params definition with the REST API login credentials.
    ```
        'user': 'admin',
        'password': 'Evertz123',
    ```
    2. Update the __cluster_ip__ key in the params definition with the ip address of the magnum sdvn cluster ip address.
    ```
        'cluster_ip': '172.17.143.201',
    ```
    3. **Optional**: uncomment the __sub_interface__ key (remove hash tag) if the switch contains expansion modules with sub interfaces. This will help align magnum port numbers to the cisco interface labels.  It's OK to use this option even if the switch doesn't contain expansion modules.  Without this, the script will assume the magnum port number is the same as the switch port number in the interface label (Ethernet1/__##__)
    ```
        'sub_interfaces': True
    ```
9. Save changes.
10. Repeat Step 1. for additional switches in the system.
11. Restart the Poller program.

## Dashboards:

This packages contains 4x dashboards that are useful for navigating the log and metric data.  The below index patterns will need to be created in Kibana before installing the dashboards:

- log-netflow-*
- log-ciscolog-*
- log-metric-poller-cisconx-*

Incase the data collection isn't fully working (cisco syslog and netflow), you can import some sample data from the extra folder. This will allow Kibana to discover all the required fields when adding the above index patterns and installing the dashboards.  Below are the exports which can be re-imported into inSITE using the inSITE Elastic Maintenance program.

- extra/__log-ciscolog-2020.10.19.tar.gz__
- extra/__log-metric-poller-cisconx-2020.10.19.tar.gz__
- extra/__log-netflow-2020.10.19.tar.gz__

Once the index patterns are added and the pattern is verified to work in the Kibana _Discover_ tab, then you can now install the below dashboard templates into the __inSITE Kibana Template Manager__. 
_don't forget to install the dashboard from the template manager after installing the template_

- dashboards/__Cisco_Switch_Health.json__
- dashboards/__Cisco_Switch_Logs.json__
- dashboards/__Cisco_Switch_Multicast_Routes.json__
- dashboards/__Cisco_Switch_Port_List.json__

The image dashboards/__field formatters.PNG__ contains a picture of which fields need which field formatters configured in the _log-metric-poller-cisconx-*_ index pattern.