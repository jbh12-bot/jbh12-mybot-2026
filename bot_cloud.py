# -*- coding: utf-8 -*-
"""Telegram 演示机器人 - 云平台常驻版（零第三方依赖 + 保活端口）"""
import re, json, ssl, time, random, threading, logging, os
import urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
PORT = int(os.environ.get("PORT", "10000"))
API = "https://api.telegram.org/bot" + TOKEN + "/"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=[logging.StreamHandler()])
log = logging.getLogger("bot")

W = [7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]
CUV = ['1','0','X','9','8','7','6','5','4','3','2']
AREAS = ["110101","310101","440305","510107","420106","330106"]
SURNAMES = "王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾"
GIVEN = "伟芳娜敏静丽强磊洋艳勇军杰娟涛明超霞平刚建华文辉俊峰"
base17 = lambda i: AREAS[i%6] + str(1980 + i%30) + "0101" + "%03d" % (i%1000)
check = lambda b: CUV[sum(int(b[k])*W[k] for k in range(17))%11]
full_id = lambda i: (lambda b: b + check(b))(base17(i))
make_name = lambda i: SURNAMES[i%len(SURNAMES)] + GIVEN[(i*7)%len(GIVEN)] + GIVEN[(i*13)%len(GIVEN)]
photo = lambda i: "https://q1.qlogo.cn/g?b=qq&nk=%d&s=640" % (10000+i)
MOCK_DB = {full_id(i): {"name": make_name(i), "photo_url": photo(i)} for i in range(500)}
validate_id_card = lambda n: bool(re.match(r'^\d{17}[\dXx]$', n)) and CUV[sum(int(n[k])*W[k] for k in range(17))%11] == n[-1].upper()
query_face = lambda name, id_num: {"code":400,"msg":"姓名和身份证号都要填哦"} if not (name and id_num) else {"code":400,"msg":"身份证号格式有误"} if not validate_id_card(id_num) else {"code":404,"msg":"没查到对应信息"} if id_num not in MOCK_DB else {"code":403,"msg":"姓名和证件号对不上"} if MOCK_DB[id_num]["name"] != name else {"code":200,"msg":"查询成功","data":{"name":name,"id_card":id_num[:6]+"********"+id_num[-4:],"photo_url":MOCK_DB[id_num]["photo_url"]}}

def handle(text):
    if text == "/start": return "您好，我是演示机器人～ 输入 /help 看功能"
    if text == "/help": return "命令：\n/start 问候\n/help 帮助\n/query 姓名 身份证号 查询\n/rand 随机名单\n/id 查看库容量"
    if text == "/rand":
        i = random.randint(0,499)
        return "试试：/query " + MOCK_DB[full_id(i)]["name"] + " " + full_id(i)
    if text == "/id": return "当前演示库共 " + str(len(MOCK_DB)) + " 条模拟数据"
    if text.startswith("/query"):
        p = text.split()
        if len(p) != 3: return "用法：/query 姓名 身份证号"
        r = query_face(p[1], p[2])
        if r["code"] == 200:
            d = r["data"]
            return "查询成功\n姓名:" + d["name"] + "\n证件:" + d["id_card"] + "\n照片:" + d["photo_url"]
        return r["msg"]
    return "未知命令，输入 /help 查看"

CTX = ssl.create_default_context()
def api_raw(method, params=None):
    url = API + method + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=10, context=CTX).read().decode())
def send(chat_id, text, reply_id=None):
    p = {"chat_id":chat_id, "text":text}
    if reply_id: p["reply_to_message_id"] = reply_id
    return api_raw("sendMessage", p)

class KeepAlive(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"OK - bot is running"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass

def keepalive_server():
    srv = HTTPServer(("0.0.0.0", PORT), KeepAlive)
    log.info("保活端口已启动: %d", PORT)
    srv.serve_forever()

def main():
    threading.Thread(target=keepalive_server, daemon=True).start()
    offset, fails = 0, 0
    log.info("机器人已启动，监听私聊/群聊/频道消息…")
    while True:
        try:
            ups = api_raw("getUpdates", {"offset":offset, "timeout":5}).get("result", [])
            fails = 0
            for u in ups:
                offset = u["update_id"] + 1
                msg = u.get("message") or u.get("channel_post") or {}
                text = msg.get("text", "")
                if text.startswith("/"):
                    send(msg["chat"]["id"], handle(text), msg.get("message_id"))
                    log.info("已回复 chat=%s cmd=%s", msg["chat"]["id"], text.split()[0])
        except Exception as e:
            fails += 1
            wait = min(2 * fails, 30)
            log.warning("网络异常(%d): %s -> %ds后重试", fails, type(e).__name__, wait)
            time.sleep(wait)

if __name__ == "__main__":
    main()
