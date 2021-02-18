import copy
import datetime
import json
from threading import Thread

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings()


class magnum_cache:
    def return_source(self, mcast):

        try:

            return self.source_db[mcast]

        except Exception:
            pass

        return None

    def return_host(self, host):

        try:

            return {
                "device_name": self.link_db[host]["device_name"],
                "device_type": self.link_db[host]["device_type"],
                "device_size": self.link_db[host]["device_size"],
                "device": self.link_db[host]["device"],
            }

        except Exception:
            pass

        return None

    def return_port(self, host, interface):

        try:

            if self.port_remap:
                port = copy.deepcopy(self.link_db[host][self.port_remap[interface]])

            else:

                # "Ethernet1/4"
                inf_parts = interface.split("/")

                if len(inf_parts) == 2:
                    port = copy.deepcopy(self.link_db[host][int(inf_parts[1])])

            if "end_port" in port.keys() and port["end_type"] == "core" and self.core_link_prefix:
                port["end_port"] = self.core_link_prefix + str(port["end_port"])

            return port

        except Exception:
            pass

        return None

    def catalog_cache(self):

        cache = self.cache_fetch()

        if cache:

            self.link_db = {}
            holders = []

            """
            self.link_db = {
                <device_ip> : {
                    'device-name': <name>,
                    'device-type': <core, edge>,
                    'device-size': <36x36>,
                    <Port #> : {
                        'end_type': <core,edge>,
                        'end_name': <device name>,
                        'end_port': <port>,
                        'end-device': <device descr>,
                        'end-size': <36x36>
            """

            # create core linkage db
            for device in cache["magnum"]["magnum-controlled-devices"]:

                if device["device"] == "CISCO-NBM":

                    for setting in ["control-1-address", "control-2-address"]:

                        if setting in device.keys():

                            # create base parameters of the device
                            ip = device[setting]["host"]

                            self.link_db[ip] = {}
                            self.link_db[ip].update(
                                {
                                    "device_name": device["device-name"],
                                    "device_type": device["device-type"],
                                    "device_size": device["device-size"],
                                    "device": device["device"],
                                }
                            )

                            # update link information for leaf switches
                            if "link-connections" in device.keys():

                                for link in device["link-connections"]:

                                    # port id is used to key object
                                    port_id = link["start-port"]

                                    port = {
                                        port_id: {
                                            "end_name": link["end-device"],
                                            "start_port": port_id,
                                            "end_port": link["end-port"],
                                            "end_device": device["device"],
                                            "end_size": device["device-size"],
                                            "end_type": device["device-type"],
                                            "from_device": device["device-name"],
                                        }
                                    }

                                    # list to update the spine switches later
                                    holders.append(port)

                                    self.link_db[ip].update(port)

            # go back and update linkage for spines with leafs
            for port in holders:

                for _, value in port.items():

                    for db_key, db_value in self.link_db.items():

                        # if the port end point name in the holder is equal to the
                        # spine in the link_db dictionary device name then create a object
                        # key for the spine switch
                        if db_value["device_name"] == value["end_name"]:

                            port_id = value["end_port"]

                            _port = {
                                port_id: {
                                    "end_name": value["from_device"],
                                    "end_port": value["start_port"],
                                    "end_device": value["end_device"],
                                    "end_size": value["end_size"],
                                    "end_type": value["end_type"],
                                }
                            }

                            self.link_db[db_key].update(_port)

            # go through each edge and link into the spine if there.
            for device in cache["magnum"]["magnum-controlled-devices"]:

                if device["device-type"] == "edge":

                    try:

                        for sfp in device["sfps"]:

                            for db_key, db_value in self.link_db.items():

                                if sfp["link"]["device"] == db_value["device_name"]:

                                    port_id = sfp["link"]["port"]

                                    _port = {
                                        port_id: {
                                            "end_name": device["device-name"],
                                            "end_type": device["device-type"],
                                            "end_device": device["device"],
                                            "end_size": device["device-size"],
                                            "end_port": sfp["number"],
                                        }
                                    }

                                    self.link_db[db_key].update(_port)

                    except Exception:
                        continue

            """
                self.source_db = {
                    <multicast_ip> : {
                        'signal_descr': <Video & Emb. (J2K)>,
                        'signal_type': <video>,
                        'signal_group': <Main>,
                        'interface_Global': <DC-IO-1 SRC-4>,
                        'source_device_name': <DC-IO-1>,
                        'source_device_type': <edge>,
                        'source_device': <570J2K-U9E>,
                        'source_device_size': <9x9>
            """

            # collect all the destination multicast addresses from every device
            # and every stream if possible and add it to the source_db dictionary
            self.source_db = {}

            for device in cache["magnum"]["magnum-controlled-devices"]:

                try:

                    # stream list if exists in edge device
                    for stream in device["streams"]:

                        # video, audio or ANC object collections. not every stream has data-address object
                        if "data-addresses" in stream.keys():
                            for data_name, data_group in stream["data-addresses"].items():

                                # single out just the destinations for main and back object collection
                                # not sources
                                for dst in ["destination", "backup-destinations"]:
                                    if dst in data_group.keys():

                                        # each object in the data group list i.e multiple audio destinations or 1 video or ANC
                                        for element in data_group[dst]:

                                            signal = {
                                                element["ip"]: {
                                                    "signal_descr": element["name"],
                                                    "signal_type": data_name,
                                                    "signal_group": "Main"
                                                    if dst == "destination"
                                                    else "Backup",
                                                }
                                            }

                                            # if mnemonics exist, then traverse the list of objects
                                            if "mnemonics" in stream.keys():
                                                for mnemonic in stream["mnemonics"]:

                                                    signal[element["ip"]].update(
                                                        {
                                                            "interface_"
                                                            + mnemonic["interface"]: mnemonic[
                                                                "mnemonic"
                                                            ]
                                                        }
                                                    )

                                            # create a device information dictionary of the edge device having the signal
                                            device_details = {
                                                "source_device_name": device["device-name"],
                                                "source_device_type": device["device-type"],
                                                "source_device": device["device"],
                                                "source_device_size": device["device-size"],
                                            }

                                            signal[element["ip"]].update(device_details)

                                            self.source_db.update(signal)
                                            # print(signal)

                except Exception:
                    continue

            # print(self.source_db)
            # print(self.link_db)

    def cache_fetch(self):

        try:

            response = requests.get(self.cache_url, verify=False, timeout=6.0)

            return json.loads(response.text)

        except Exception as e:

            with open(self.host, "a+") as f:
                f.write(
                    str(datetime.datetime.now())
                    + " --- "
                    + "magnum_cache_builder"
                    + "\t"
                    + str(e)
                    + "\r\n"
                )

            return None

    def remap_ports(self):

        body = self.__handlers.fetch()

        if body:

            try:

                index = 1
                self.port_remap = {}

                for port in body["TABLE_interface"]["ROW_interface"]:

                    if port["interface"] not in ("loopback0", "mgmt0"):

                        self.port_remap.update({port["interface"]: index})
                        index = index + 1

            except Exception:
                self.port_remap = None

    def __init__(self, **kwargs):

        self.host = None
        self.insite = None
        self.nature = "mag-1"
        self.cluster_ip = None
        self.core_link_prefix = None
        self.port_remap = None

        for key, value in kwargs.items():

            if ("insite" in key) and value:
                self.insite = value

            if ("host" in key) and value:
                self.host = value

            if ("nature" in key) and value:
                self.nature = value

            if ("cluster_ip" in key) and value:
                self.cluster_ip = value

            if ("core_link_prefix" in key) and value:
                self.core_link_prefix = value

        self.cache_url = "http://{}/proxy/insite/{}/api/-/model/magnum/{}".format(
            self.insite, self.nature, self.cluster_ip
        )

        self.catalog_cache()

        if "sub_interfaces" in kwargs.keys():

            kwargs["port_remap"].update(
                {"cmd": "show interface brief", "logfile": "port_remap_fetch"}
            )
            self.__handlers = parameters(**kwargs["port_remap"])

            self.remap_ports()


class parameters:
    def fetch(self):

        try:

            response = requests.post(
                self.url,
                data=json.dumps(self.payload),
                headers=self.headers,
                auth=(self.user, self.password),
                timeout=30.0,
            )
            response.close()

            data = json.loads(response.text)

            if data["ins_api"]["outputs"]["output"]["msg"] == "Success":
                return data["ins_api"]["outputs"]["output"]["body"]

        except Exception as e:

            with open(self.host, "a+") as f:
                f.write(
                    str(datetime.datetime.now()) + " --- " + self.logfile + "\t" + str(e) + "\r\n"
                )

                # with open('cisco_webcall', 'a+') as f:
                #     f.write(str(datetime.datetime.now()) + " --- " + host + "\t" + response.text + "\r\n")

        return None

    def __init__(self, **kwargs):

        self.user = None
        self.password = None
        self.cmd = None
        self.host = None
        self.url_route = "ins"
        self.logfile = None

        self.headers = {"content-type": "application/json"}

        for key, value in kwargs.items():

            if ("user" in key) and value:
                self.user = value

            if ("password" in key) and value:
                self.password = value

            if ("cmd" in key) and value:
                self.cmd = value

            if ("host" in key) and value:
                self.host = value

            if ("logfile" in key) and value:
                self.logfile = value

        self.url = "http://%s/%s" % (self.host, self.url_route)

        self.payload = {
            "ins_api": {
                "version": "1.0",
                "type": "cli_show",
                "chunk": "0",
                "sid": "sid",
                "input": self.cmd,
                "output_format": "json",
            }
        }


class ports:
    def ports_fetch(self):

        body = self.__handlers.fetch()

        documents = []

        if body:

            for interface in body["TABLE_interface"]["ROW_interface"]:

                fields = {}
                fields.update(interface)

                for key in interface.keys():
                    for fn in (int, float):

                        try:

                            t = "l_" if fn == int else "d_"

                            fields[key] = fn(fields[key])
                            fields[t + key] = fields.pop(key)

                            break

                        except ValueError:
                            pass

                if self.cache:

                    host_annotations = self.return_host(self.__handlers.host)
                    port_annotations = self.return_port(self.__handlers.host, fields["interface"])

                    if port_annotations:
                        fields.update(port_annotations)

                    if host_annotations:
                        fields.update(host_annotations)

                document = {
                    "fields": fields,
                    "host": self.__handlers.host,
                    "name": "ports",
                }

                documents.append(document)

        return documents

    def __init__(self, **kwargs):

        kwargs.update({"cmd": "show interface", "logfile": "port_fetch"})

        self.__handlers = parameters(**kwargs)


class system_resources:
    def resource_fetch(self):

        body = self.__handlers.fetch()

        documents = []

        if body:

            for cpu in body["TABLE_cpu_usage"]["ROW_cpu_usage"]:

                fields = {}
                fields.update(cpu)

                for key in cpu.keys():
                    for fn in (int, float):

                        try:

                            t = "i_" if fn == int else "d_"

                            fields[key] = fn(fields[key])

                            # override to convert cpu percent to decimal
                            if t == "d_":
                                fields[t + key] = round(fields.pop(key) / 100, 3)

                            break

                        except ValueError:
                            pass

                if self.cache:

                    host_annotations = self.return_host(self.__handlers.host)
                    if host_annotations:
                        fields.update(host_annotations)

                document = {
                    "fields": fields,
                    "host": self.__handlers.host,
                    "name": "cpu_core",
                }

                documents.append(document)

            for Key, Params in self.__parameter_control.items():

                fields = {}

                for param in Params["list"]:

                    func = Params["type"]
                    fields.update({Params["prefix"] + param: func(body[param])})

                    # overrides to convert memory from KB to B, and cpu percent to decimal
                    if Key == "memory":
                        fields[Params["prefix"] + param] = fields[Params["prefix"] + param] * 1000

                    if Key == "cpu" and "cpu" in param:
                        fields[Params["prefix"] + param] = round(
                            fields[Params["prefix"] + param] / 100, 3
                        )

                if Key == "memory":
                    fields.update({"current_memory_status": body["current_memory_status"]})
                    fields.update(
                        {
                            "d_memory_used_pct": round(
                                fields["l_memory_usage_used"] / fields["l_memory_usage_total"], 3,
                            )
                        }
                    )

                if self.cache:

                    host_annotations = self.return_host(self.__handlers.host)
                    if host_annotations:
                        fields.update(host_annotations)

                document = {"fields": fields, "host": self.__handlers.host, "name": Key}

                documents.append(document)

        return documents

    def __init__(self, **kwargs):

        kwargs.update({"cmd": "show system resources", "logfile": "sys_resources_fetch"})

        self.__handlers = parameters(**kwargs)

        self.__parameter_control = {
            "processes": {
                "list": ["processes_total", "processes_running"],
                "prefix": "i_",
                "type": int,
            },
            "memory": {
                "list": ["memory_usage_total", "memory_usage_used", "memory_usage_free",],
                "prefix": "l_",
                "type": int,
            },
            "cpu": {
                "list": [
                    "load_avg_1min",
                    "load_avg_5min",
                    "load_avg_15min",
                    "cpu_state_user",
                    "cpu_state_kernel",
                    "cpu_state_idle",
                ],
                "prefix": "d_",
                "type": float,
            },
        }


class env_health:
    def env_fetch(self):
        def doc_create(_data, name, *override):

            fields = {}
            fields.update(_data)

            if override[0]:

                for key in self.__key_int_override:
                    if key in fields.keys():

                        fields[override[1] + key] = int(fields.pop(key))

                for key in self.__key_watts_override:
                    if key in fields.keys():

                        fields[key] = int(float(fields[key].strip()[:-1]))
                        fields[override[1] + key] = fields.pop(key)

            if self.cache:

                host_annotations = self.return_host(self.__handlers.host)
                if host_annotations:
                    fields.update(host_annotations)

            document = {"fields": fields, "host": self.__handlers.host, "name": name}

            return document

        body = self.__handlers.fetch()

        documents = []

        if body:

            documents.extend(
                [
                    doc_create(faninfo, "fan", None)
                    for faninfo in body["fandetails"]["TABLE_faninfo"]["ROW_faninfo"]
                ]
            )

            documents.extend(
                [
                    doc_create(tempinfo, "temp", True, "i_")
                    for tempinfo in body["TABLE_tempinfo"]["ROW_tempinfo"]
                ]
            )

            documents.extend(
                [
                    doc_create(psuinfo, "psu", True, "i_")
                    for psuinfo in body["powersup"]["TABLE_psinfo"]["ROW_psinfo"]
                ]
            )

        return documents

    def __init__(self, **kwargs):

        kwargs.update({"cmd": "show environment", "logfile": "env_fetch"})

        self.__handlers = parameters(**kwargs)

        self.__key_int_override = [
            "tempmod",
            "majthres",
            "minthres",
            "curtemp",
            "psnum",
        ]

        self.__key_watts_override = ["actual_out", "actual_input", "tot_capa"]


class mcast_route:
    def streams_collect(self):

        QUERY = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"match_phrase": {"host": {"query": self.__handlers.host}}},
                        {"match_phrase": {"netflow.l4_dst_port": {"query": 1234}}},
                        {"range": {"@timestamp": {"from": "now-5m", "to": "now"}}},
                    ]
                }
            },
            "aggs": {
                "address": {
                    "terms": {
                        "field": "netflow.ipv4_dst_addr.keyword",
                        "size": 100000,
                        "order": {"_term": "desc"},
                    },
                    "aggs": {
                        "in_bytes": {
                            "top_hits": {
                                "docvalue_fields": ["netflow.in_bytes"],
                                "_source": False,
                                "size": 1,
                                "sort": [{"@timestamp": {"order": "desc"}}],
                            }
                        }
                    },
                }
            },
        }

        REQUEST_URL = "%s://%s:%s/%s/_search" % (
            self.__proto,
            self.__elastichost,
            self.__elasticport,
            self.__index,
        )

        HEADERS = {"Accept": "application/json"}

        PARAMS = {"ignore_unavailable": "true"}

        try:

            resp = requests.get(
                REQUEST_URL, headers=HEADERS, params=PARAMS, data=json.dumps(QUERY), timeout=30.0
            )

            resp.close()

            response = json.loads(resp.text)

            stream_db = {}

            if response["hits"]["total"] > 0:

                for stream in response["aggregations"]["address"]["buckets"]:

                    try:

                        for hit in stream["in_bytes"]["hits"]["hits"]:

                            stream_def = {
                                stream["key"]: {"l_in_bytes": hit["fields"]["netflow.in_bytes"][-1]}
                            }

                            stream_db.update(stream_def)

                    except Exception:
                        continue

        except Exception as e:

            return e

        return stream_db

    def mroute_fetch(self):

        body = self.__handlers.fetch()

        if self.__netflow:
            stream_db = self.streams_collect()

        documents = []

        if body:

            vrfname = body["TABLE_vrf"]["ROW_vrf"]["vrf-name"]

            for route in body["TABLE_vrf"]["ROW_vrf"]["TABLE_one_route"]["ROW_one_route"]:

                fields = {
                    "mcast_addrs": route["mcast-addrs"],
                    "source_addrs": route["source_addrs"].replace("/32", ""),
                    "group_addrs": route["group_addrs"].replace("/32", ""),
                    "route_iif": route["route-iif"],
                    "uptime": route["uptime"],
                    "oif_count": int(route["oif-count"]),
                }

                fields.update({"vrf_name": vrfname})

                if fields["oif_count"] > 1:

                    oifname = [oif["oif-name"] for oif in route["TABLE_oif"]["ROW_oif"]]
                    fields.update({"oif_name": ", ".join(oifname), "as_oif_name": oifname})

                elif fields["oif_count"] == 1:
                    fields.update(
                        {
                            "oif_name": route["TABLE_oif"]["ROW_oif"]["oif-name"],
                            "as_oif_name": [route["TABLE_oif"]["ROW_oif"]["oif-name"]],
                        }
                    )

                if self.__netflow:

                    if fields["group_addrs"] in stream_db.keys():

                        fields.update(stream_db[fields["group_addrs"]])
                        fields.update({"netflow": "active"})

                    else:
                        fields.update({"netflow": "inactive"})

                else:
                    fields.update({"netflow": "disabled"})

                if self.cache:

                    if "oif_name" in fields.keys():

                        odevname = []
                        for interface in fields["oif_name"].split(", "):

                            device_annotation = self.return_port(self.__handlers.host, interface)

                            if device_annotation:
                                odevname.append(device_annotation["end_name"])

                        fields.update({"odev_name": ", ".join(odevname), "as_odev_name": odevname})

                    host_annotations = self.return_host(self.__handlers.host)
                    if host_annotations:
                        fields.update(host_annotations)

                    source_annotations = self.return_source(fields["group_addrs"])
                    if source_annotations:
                        fields.update(source_annotations)

                    port_annotations = self.return_port(self.__handlers.host, fields["route_iif"])
                    if port_annotations:
                        fields.update(port_annotations)

                document = {
                    "fields": fields,
                    "host": self.__handlers.host,
                    "name": "mroute",
                }

                documents.append(document)

        return documents

    def __init__(self, **kwargs):

        kwargs.update({"cmd": "show ip mroute", "logfile": "mroute_fetch"})

        self.__handlers = parameters(**kwargs)
        self.__netflow = None

        if "netflow" in kwargs.keys():

            self.__netflow = True
            self.__proto = "http"
            self.__elasticport = "9200"
            self.__elastichost = kwargs["netflow"]["insite"]
            self.__index = "log-netflow-*"


class hardware_info:
    def hardware_fetch(self):

        body = self.__handlers.fetch()

        documents = []

        if body:

            try:

                for count, device in enumerate(
                    body["TABLE_slot"]["ROW_slot"]["TABLE_slot_info"]["ROW_slot_info"]
                ):

                    if len(device.keys()) > 1:

                        if "type" in device.keys():
                            device["type"] = device["type"].replace('"', "")

                        if "num_slot_str" in device.keys():
                            device.pop("num_slot_str")

                        host_annotations = self.return_host(self.__handlers.host)
                        if host_annotations:
                            device.update(host_annotations)

                        document = {
                            "fields": device,
                            "host": self.__handlers.host,
                            "name": "hardware",
                        }

                        device.update({"id": count})

                        documents.append(document)

            except Exception:
                pass

            fields = {}

            for key, value in body.items():

                if key in [
                    "kern_uptm_days",
                    "kern_uptm_hrs",
                    "kern_uptm_mins",
                    "kern_uptm_secs",
                ]:
                    fields.update({key: int(value)})

            host_annotations = self.return_host(self.__handlers.host)
            if host_annotations:
                fields.update(host_annotations)

            document = {
                "fields": fields,
                "host": self.__handlers.host,
                "name": "uptime",
            }

            documents.append(document)

        return documents

    def __init__(self, **kwargs):

        kwargs.update({"cmd": "show hardware", "logfile": "hardware_fetch"})

        self.__handlers = parameters(**kwargs)


class switch_collector(
    ports, env_health, system_resources, mcast_route, magnum_cache, hardware_info
):
    def process(self, func):
        self.documents.extend(func())

    @property
    def collect(self):

        self.documents = []

        threads = [Thread(target=self.process, args=(func,)) for func in self.func_list]

        for x in threads:
            x.start()

        for y in threads:
            y.join()

        return self.documents

    def __init__(self, **kwargs):

        if "magnum_cache" in kwargs.keys():

            kwargs["magnum_cache"].update({"host": kwargs["host"]})

            if "sub_interfaces" in kwargs["magnum_cache"].keys():
                kwargs["magnum_cache"].update(
                    {
                        "port_remap": {
                            "user": kwargs["user"],
                            "password": kwargs["password"],
                            "host": kwargs["host"],
                        }
                    }
                )

            magnum_cache.__init__(self, **kwargs["magnum_cache"])
            self.cache = True

        else:
            self.cache = None

        env_health.__init__(self, **kwargs)
        ports.__init__(self, **kwargs)
        system_resources.__init__(self, **kwargs)
        mcast_route.__init__(self, **kwargs)
        hardware_info.__init__(self, **kwargs)

        # self.func_list = [self.mroute_fetch]
        self.func_list = [
            self.ports_fetch,
            self.mroute_fetch,
            self.resource_fetch,
            self.env_fetch,
            self.hardware_fetch,
        ]

        self.documents = []


def main():

    params = {
        "user": "admin",
        "password": "Evertz123",
        "host": "172.17.143.21",
        "magnum_cache": {
            "insite": "172.16.112.20",
            "nature": "mag-1",
            "cluster_ip": "172.17.143.201",
            "core_link_prefix": "Ethernet1/",
            "sub_interfaces": True,
        },
        "netflow": {"insite": "172.16.112.20"},
    }

    collector = switch_collector(**params)

    print(json.dumps(collector.collect, indent=2))


if __name__ == "__main__":
    main()
