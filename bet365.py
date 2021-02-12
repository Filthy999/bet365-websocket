import json
import re
import websockets
from websockets.extensions import permessage_deflate
import asyncio
from aiohttp import request
import collections
import traceback
import requests
import subprocess

_REQ_EXTENSIONS = [permessage_deflate.ClientPerMessageDeflateFactory(
    server_max_window_bits=15,
    client_max_window_bits=15,
    compress_settings={'memLevel': 4},
)]
_REQ_PROTOCOLS = ['zap-protocol-v1']
R_HEADER = collections.namedtuple('Header','name value')
_REQ_HEADERS = [
      R_HEADER('Sec-WebSocket-Version', '13'),
      R_HEADER('Accept-Encoding', 'gzip, deflate, br'),
      R_HEADER('Pragma', 'no-cache'),
      R_HEADER('User-Agent','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36'),
      R_HEADER('Connection', 'keep-alive, Upgrade'),
      R_HEADER('Upgrade', 'websocket'),
      R_HEADER('Cache-Control', 'no-cache')
]
PATH = "/home/dume/"

async def fetch(url, headers):
    async with request("GET", url=url, headers=headers) as response:
        return await response.text()

async def get_server_time(session_id):
    headers = {
        'Host': 'www.bet365.es',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.bet365.es/',
        'Connection': 'keep-alive',
        'Cookie': 'aps03=cf=N&cg=4&cst=0&ct=171&hd=N&lng=3&oty=2&tzi=4; pstk=' + session_id + '; rmbs=3',
        'DNT': '1',
        'Referer': 'https://www.bet365.es/',
    }
    
    resp = await fetch('https://www.bet365.es/defaultapi/sports-configuration', headers)
    resp = json.loads(resp)
    return resp["ns_weblib_util"]["WebsiteConfig"]["SERVER_TIME"]

async def get_session_id():
    headers = {
        'Host': 'www.bet365.es',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.bet365.es/',
        'Connection': 'keep-alive',
        'Cookie': 'aps03=ct=171&lng=3',
        'DNT': '1',
        'Referer': 'https://www.bet365.es/',
        'Cache-Control': 'max-age=0',
    }
    
    resp = await fetch('https://www.bet365.es/defaultapi/sports-configuration', headers)
    resp = json.loads(resp)
    return resp["flashvars"]["SESSION_ID"]



async def get_first_part_token(server_time):
    filename = PATH + "first_part_nst.js"
    f = open(filename, "w")
    f.write(" \
            (function() { \
                const jsdom = require('jsdom'); \
                try { \
                  const { JSDOM } = jsdom; \
                  const doom = new JSDOM('<!DOCTYPE html><p>Bet365</p><script>")
    f.write("\
            function ConvertEpochToBase64(e) { \
                var tt = new DataView(new ArrayBuffer(4)); \
                tt.setUint32(0, e); \
                var str = \"\"; \
                for(var i = 3; i >=0; i--) \
                    str += String.fromCharCode(tt.getUint8(i)); \
                return btoa(str); \
             }; \
             document.puto_token = ConvertEpochToBase64(" + str(server_time) + " + 300);")

    f.write("</script></html>', { runScripts: 'dangerously'}); \
                  console.log(doom.window.document.puto_token); \
                } catch (err) { \
                  console.error(err) \
                } \
                process.exit(); \
             })();")
    f.close()

    result = subprocess.run(
        ['node',  filename],
        cwd=PATH,
        text=True,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    if result.returncode == 0:
        tkn = result.stdout.strip('\n')
    else:
        raise Exception('Error while evaluating the token generation script:\n\n' + result.stderr)
    return tkn

async def get_second_part_token():
    headers = {
            'Host': 'www.bet365.es',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.bet365.es/',
            'Connection': 'keep-alive',
            'Cookie': 'aps03=ct=171&lng=3',
            'DNT': '1'
    }

    resp = await fetch('https://www.bet365.es/#/HO', headers)
    
    # # testing purposes:
    # f = open(PATH + "evaluator_code.js", "r")
    # resp = f.read()
    # f.close()

    evaluator_code = resp.split("<script id='bootjs'>")[1].split("</script>")[0]
    evaluator_code = evaluator_code.replace("new f();", "new f();document.puto_token = q.split('.')[1];")

    filename = PATH + "evaluator_code.js"
    f = open(filename, "w")
    f.write(evaluator_code)
    f.close()

    filename = PATH + "evaluator.js"
    f = open(filename, "w")
    f.write(" \
            (function() { \
                const jsdom = require('jsdom'); \
                const fs = require('fs'); \
                const data = fs.readFileSync('/home/dume/evaluator_code.js', 'utf8'); \
                try { \
                  const { JSDOM } = jsdom; \
                  const doom = new JSDOM('<!DOCTYPE html><p>Bet365</p><script id=\"bootjs\">' + data + '</script></html>', \
                    { pretendToBeVisual: true, runScripts: 'dangerously', url: 'https://www.bet365.es', resources: 'usable' }); \
                  console.log(doom.window.document.puto_token); \
                } catch (err) { \
                  console.error(err) \
                } \
                process.exit(); \
             })();")
    f.close()

    result = subprocess.run(
        ['node',  filename],
        cwd=PATH,
        text=True,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    if result.returncode == 0:
        tkn = result.stdout.strip('\n')
    else:
        raise Exception('Error while evaluating the token generation script:\n\n' + result.stderr)
    return tkn



def decrypt_token(t):
    n = ""
    i = ""
    o = len(t)
    r = 0
    s = 0
    MAP_LEN = 64
    charMap = [["A", "d"], ["B", "e"], ["C", "f"], ["D", "g"], ["E", "h"], ["F", "i"], ["G", "j"], ["H", "k"], ["I", "l"], ["J", "m"], ["K", "n"], ["L", "o"], ["M", "p"], ["N", "q"], ["O", "r"], ["P", "s"], ["Q", "t"], ["R", "u"], ["S", "v"], ["T", "w"], ["U", "x"], ["V", "y"], ["W", "z"], ["X", "a"], ["Y", "b"], ["Z", "c"], ["a", "Q"], ["b", "R"], ["c", "S"], ["d", "T"], ["e", "U"], ["f", "V"], [
        "g", "W"], ["h", "X"], ["i", "Y"], ["j", "Z"], ["k", "A"], ["l", "B"], ["m", "C"], ["n", "D"], ["o", "E"], ["p", "F"], ["q", "0"], ["r", "1"], ["s", "2"], ["t", "3"], ["u", "4"], ["v", "5"], ["w", "6"], ["x", "7"], ["y", "8"], ["z", "9"], ["0", "G"], ["1", "H"], ["2", "I"], ["3", "J"], ["4", "K"], ["5", "L"], ["6", "M"], ["7", "N"], ["8", "O"], ["9", "P"], ["\n", ":|~"], ["\r", ""]]
    for r in range(0, o):
        n = t[r]
        for s in range(0, MAP_LEN):
            if ":" == n and ":|~" == t[r:3]:
                n = "\n"
                r = r + 2
                break
            if n == charMap[s][1]:
                n = charMap[s][0]
                break
        i = i+n
    return i


async def on_message_aux(message, websocket):
    print("aux " + message)
    if "SPTBK_D23" in message:
        tok = re.findall("\x01(.*?)$", message)
        if len(tok) > 0:
            nst = decrypt_token(tok[0])
            print(nst)

            await websocket.send("\x16\x00CONFIG_3_0,OVInPlay_3_0,Media_L3_Z0\x01")
            await websocket.send("\x02\x00command\x01nst\x01" + nst + "\x02SPTBK")


async def on_message(message, websocket):
    print(message)


async def async_processing():
    nst_token_second_part = await get_second_part_token()
    session_id = await get_session_id()
    
    server_time = await get_server_time(session_id)
    
    # server_time = 1613115247
    # session_id = "551EAB9C1668462CA42C122D10DC847F000003"

    nst_token = await get_first_part_token(server_time) + "." + nst_token_second_part
    # nst_token = "qy0mYA==" + "." + nst_token_second_part
    # nst_token = await get_first_part_token(server_time) + "." + "bkWuDoRkx47EWEtFR05IKwqnASC+O45q56xlm2HHcuI="
    # nst_token = "BjImYA==.OUmptd/7jjH++TloXY4C5AyZIYOMRGYi8RPDN/7B4X4="
    
    # print(await get_first_part_token(server_time))


    async with websockets.connect('wss://premws-pt3.365lpodds.com/zap/', extra_headers=_REQ_HEADERS, extensions=_REQ_EXTENSIONS, subprotocols=_REQ_PROTOCOLS, 
                                      max_size=None, ping_interval=None, ping_timeout=None) as websocket:
        print("opened")
        global init_msg
        init_msg = "#\x03P\x01__time,S_{},D_{}\x00".format(session_id, nst_token)
        await websocket.send(init_msg)

        asyncio.create_task(ws_aux(websocket))

        while True:
            try:
                message = await websocket.recv()
                await on_message(message, websocket)
            except Exception as e:
                print(traceback.format_exc())
                print('Connection Closed')
                # print(message)
                raise

async def ws_aux(websocket):
    async with websockets.connect('wss://pshudws.365lpodds.com/zap/', extra_headers=_REQ_HEADERS,extensions=_REQ_EXTENSIONS, subprotocols=_REQ_PROTOCOLS, 
                                    ping_interval=None, ping_timeout=None) as websocket_aux:
        print("opened")
        print(init_msg)
        await websocket_aux.send(init_msg)

        while True:
            try:
                message = await websocket_aux.recv()
                await on_message_aux(message, websocket)
            except Exception as e:
                print(traceback.format_exc())
                print('Connection AUX Closed')
                print(message)
                raise

asyncio.get_event_loop().run_until_complete(asyncio.wait([   
    async_processing(),
], return_when=asyncio.FIRST_EXCEPTION))
