import time
import json
import os
import urllib.request
import urllib.parse
from collections import OrderedDict


displays = {
    "192x48": dict(
        height=48,
        width=192,
        ip="192.168.1.119",
        hostname="led2",
        infoScreenTtl=30
    ),
    "128x32": dict(
        height=32,
        width=128,
        ip="192.168.1.118",
        hostname="led1",
        infoScreenTtl=20
    )
}


def make_display(name="192x48"):
    height = displays[name]["height"]
    width = displays[name]["width"]

    """
    
    """
    h1 = (2 * height) // 5
    h2 = (2 * height) // 5
    h3 = max(height - h1 - h2, 0)

    w11 = width // 2
    w12 = width - w11

    return dict(
        port=9527,
        displays=dict(
            main=dict(
                displayName=name,
                displayIp=displays[name]["ip"],
                displayPort=9527,
                controllerType="C15C",
                sensorBrightness="false",
                displayHeight=height,
                displayWidth=width,
                infoScreenTtl=displays[name]["infoScreenTtl"],
                layout=OrderedDict(
                    full=dict(
                        text=dict(
                            coordinates=(0, 0, width-1, height-1),
                            type="text",
                            align="center",
			    font="font.ttf",
                            fontSize=height,
                            fontColor= "255 0 0"
                        ),
                    ),
                    vsplit=OrderedDict(
                        text1=dict(
                            coordinates=(0, 0, width-1, height//2 - 1),
                            type="text",
                            align="left",
			    font="font.ttf",
                            fontSize=(height // 2 - 1),
                            fontColor= "0 255 0",
                        ),
                        text2=dict(
                            coordinates=(0, height // 2, width-1, height -1),
                            type="text",
                            align="center",
		            font="font.ttf",
                            fontSize=(height // 2 - 1),
                            fontColor= "255 255 153",
                        )
                    ),
                    L11_12_2_3=OrderedDict(
                        text11=dict(
                            coordinates=(0, 0, w11-1, h1 - 1),
                            type="text",
                            align="center",
			    font="font.ttf",
                            fontSize=(h1 - 1),
                            fontColor= "255 0 0",
                        ),
                        text12=dict(
                            coordinates=(w11, 0, width-1, h1-1),
                            type="text",
                            align="center",
			    font="font.ttf",
                            fontSize=(h1 - 1),
                            fontColor= "0 255 0",
                        ),
                        text2=dict(
                            coordinates=(0, h1, width-1, h1+h2-1),
                            type="text",
                            align="center",
		            font="font.ttf",
                            fontSize=(h2 - 1),
                            fontColor= "255 255 255",
                        ),
                        text3=dict(
                            coordinates=(0, h1 + h2, width-1, h1+h2+h3-1),
                            type="text",
                            align="center",
		            font="font.ttf",
                            fontSize=(h3 - 1),
                            fontColor= "255 255 153",
                        )
                    ),
                    L1_2_3=OrderedDict(
                        text1=dict(
                            coordinates=(0, 0, width-1, h1 - 1),
                            type="text",
                            align="center",
			    font="font.ttf",
                            fontSize=(h1 - 1),
                            fontColor= "0 255 0",
                        ),
                        text2=dict(
                            coordinates=(0, h1, width-1, h1+h2-1),
                            type="text",
                            align="center",
		            font="font.ttf",
                            fontSize=(h2 - 1),
                            fontColor= "255 255 255",
                        ),
                        text3=dict(
                            coordinates=(0, h1 + h2, width-1, h1+h2+h3-1),
                            type="text",
                            align="center",
		            font="font.ttf",
                            fontSize=(h3 - 1),
                            fontColor= "255 255 153",
                        )
                    ),
                )
            )
        )
    )


def prepare_as_json(config: dict):
    r = dict()
    for k, v in config.items():
        if isinstance(v, int):
            v = str(v)
        elif isinstance(v, str):
            pass
        elif isinstance(v, dict):
            v = prepare_as_json(v)
        elif isinstance(v, (list, tuple)):
            v = " ".join(map(str, v))
        else:
            raise NotImplementedError(f"{k}={v} ({type(v)=})")
        r[k] = v
    return r


def save_config(config: dict):
    name = config["displays"]["main"]["displayName"]
    config_file = os.path.join(os.path.dirname(__file__), 'config', time.strftime(f"{name}-%Y%m%d%H%M%S.json", time.localtime()))
    s = json.dumps(prepare_as_json(config))
    print(f'{s=}')
    f = open(config_file, 'w')
    f.write(s)
    f.close()
    return config_file


def get_ip_port(config, id=None):
    if id is None:
        for k, v in config["displays"].items():
            if "displayIp" in v:
                ip = v["displayIp"]
                port = v["displayPort"]
                break
    else:
        ip = config["displays"][id]["displayIp"]
        port = config["displays"][id]["displayPort"]
    return ip, port

def geturl(config, id=None):
    ip, port = get_ip_port(config, id=id)
    return f"http://{ip}:{port}"


def make_url(config, **params):
    items = []
    id=params.get('id', 'main')
    for k, v in params.items():
        if k in {'id', 'layout'}:
            items.append(f'{k}={v}')
        else:
            if len(v) > 255:
                print(f"Too long string ({len(v)}>255): `{v}`")
                v = v[:255]
            items.append(f'{k}={urllib.parse.quote(v)}')
    url = f"{geturl(config, id)}/mlds?" + "&".join(items)
    return url


def update(config, **params):
    try_run = params.pop('try_run', False)
    url = make_url(config, **params)
    print(f"update: {url=}")
    if not try_run:
        urllib.request.urlopen(url)


def setip():
    port = "9527"
    old_ip = "192.168.168.200"
    ip = "192.168.1.118"  # mac: 28:42:fd:aa:f6:e0  
    ip = "192.168.1.119"  # mac: 28:42:fd:aa:f6:50
    gateway = "192.168.1.1"
    dns = "192.168.1.1"
    netmask = "255.255.255.0"
    url = f"http://{old_ip}:{port}/setethernetconfig?dhcp=false&ip={ip}&netmask={netmask}&gateway={gateway}&dns={dns}"
    print(url)
    # urllib.request.urlopen(url)  # use with care

def update_config(config):
    name=["192x48", "128x32"][0]
    ip, _ = get_ip_port(config, id='main')
    port = 37670
    config_file = save_config(config)
    cmd = f'sshpass -p veemoto scp -P {port} -o User=admin -o "HostKeyAlgorithms=+ssh-rsa" -o "PubkeyAcceptedAlgorithms=+ssh-rsa" {config_file} {ip}:config.json'
    cmd = f'sshpass -p veemoto scp -P {port} -o User=admin -o "HostKeyAlgorithms=+ssh-rsa" {config_file} {ip}:config.json'
    print(cmd)
    if 1:
        s = os.system(cmd)
        assert s == 0, s
    print(f"url={geturl(config)}")
    contents = urllib.request.urlopen(f"{geturl(config)}/reload_config").read().decode()
    print(contents)

def main():
    name=["192x48", "128x32"][0]
    display1 = make_display(name=name)

    update_config(display1)

    #update(display1, id="main", layout="vsplit", text1="OSY-400", text2="1: 400, 2: 300, 3: 225")
    #update(display1, id="main", layout="matrix", text11="OSY-400", text12="Practice", text2="1: 400, 2: 300, 3: 225, 4: 127")

    if 0:
        contents = urllib.request.urlopen(f"{led_url}/reload_config").read().decode()
        print(contents)

if __name__ == "__main__":
    main()
    #setip()
