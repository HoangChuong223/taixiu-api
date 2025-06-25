from flask import Flask, jsonify
import websocket
import threading
import json
import ssl
import time
import os

app = Flask(__name__)

# Biến toàn cục
history = []
last_phien = 0
ket_qua_hien_tai = None
du_doan_hien_tai = "Tài"
tong_hien_tai = 0
xuc_xac = [0, 0, 0]

def ai_noi_bo(ket_qua):
    if not ket_qua:
        return "Tài"
    tai_count = ket_qua.count("Tài")
    xiu_count = ket_qua.count("Xỉu")
    return "Xỉu" if tai_count > xiu_count else "Tài"

def tao_pattern_tu_lichsu(hist):
    return ''.join(['t' if x == "Tài" else 'x' for x in hist[-20:]]).ljust(20, 'x')

def on_open(ws):
    print("[WS] Đã kết nối, gửi dữ liệu đăng nhập...", flush=True)
    messages_to_send = [
        [1, "MiniGame", "SC_bottxabc", "binhlamtool", {
            "info": "{\"ipAddress\":\"116.110.43.11\",\"userId\":\"a307c0d6-6978-457a-8459-7c2a843ac06f\",\"username\":\"SC_bottxabc\",\"timestamp\":1749921371723,\"refreshToken\":\"78e21b1b18214e87a5aa26bf26bb955d.26f0c71a6a7a4300af8f9e529d2f7054\"}",
            "signature": "29687BAE3041CA1DA1601C3E225D6072FC4FF3E958C8066805019AD98772F11B19184D861F615ACAF508142E323A1FBDF3AE229F29AF1610652FBEAD2B8C4DA4C3B09AFA6EF6F6ACCE9C7E15C9118B9183EDA3AB6CE999C6B67C1EB110F98F6AA822CA0028252880B4C59A41BAAADB168451DF3B86D8ADFCA4198E38032920BD"
        }],
        [6, "MiniGame", "taixiuPlugin", {"cmd": 1005}],
        [6, "MiniGame", "lobbyPlugin", {"cmd": 10001}]
    ]
    for msg in messages_to_send:
        try:
            ws.send(json.dumps(msg))
            time.sleep(1)
        except Exception as e:
            print(f"[WS ERROR] Gửi msg lỗi: {e}", flush=True)

def on_message(ws, message):
    global last_phien, history, ket_qua_hien_tai, du_doan_hien_tai, tong_hien_tai, xuc_xac
    try:
        data = json.loads(message)
        if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], dict):
            if data[1].get("cmd") == 1008 and "sid" in data[1]:
                sid = data[1]["sid"]
                if sid != last_phien:
                    last_phien = sid
                    du_doan_hien_tai = ai_noi_bo(history[-10:])
                    print(f"[Phiên mới] {last_phien} | Dự đoán: {du_doan_hien_tai}", flush=True)

            if data[1].get("cmd") == 1003 and "gBB" in str(data):
                d1 = data[1].get("d1")
                d2 = data[1].get("d2")
                d3 = data[1].get("d3")
                if d1 and d2 and d3:
                    tong = d1 + d2 + d3
                    result = "Tài" if tong > 10 else "Xỉu"
                    ket_qua_hien_tai = result
                    history.append(result)
                    if len(history) > 50:
                        history.pop(0)
                    tong_hien_tai = tong
                    xuc_xac = [d1, d2, d3]
                    print(f"[KQ phiên {last_phien}] {result} | {d1}-{d2}-{d3} = {tong}", flush=True)
    except Exception as e:
        print(f"[Lỗi xử lý WS] {e}", flush=True)

def on_error(ws, error):
    print(f"[WebSocket Error] {error}", flush=True)

def on_close(ws, code, msg):
    print(f"[WebSocket đóng] {code}, {msg}", flush=True)

def run_websocket():
    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://websocket.azhkthg1.net/websocket",
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                header={
                    "Host": "websocket.azhkthg1.net",
                    "Origin": "https://play.sun.win",
                    "User-Agent": "Mozilla/5.0"
                }
            )
            ws.run_forever(
                sslopt={"cert_reqs": ssl.CERT_NONE},
                ping_interval=20,
                ping_timeout=7
            )
        except Exception as e:
            print(f"[Lỗi kết nối lại WS] {e}", flush=True)
        time.sleep(5)

@app.route("/")
def api():
    prediction = du_doan_hien_tai or "Tài"
    pattern = tao_pattern_tu_lichsu(history)
    response = {
        "Phien": last_phien,
        "Next_phien": last_phien + 1,
        "pattern": pattern,
        "prediction": prediction,
        "expert_votes": [{"rule_D": prediction}],
        "reason": f"Phân tích 1 mô hình: ['rule_D: {prediction}']",
        "tincay": "0%",
        "id": "djthanhbinh"
    }
    if ket_qua_hien_tai:
        response.update({
            "Ket_qua": ket_qua_hien_tai,
            "Phien_cu": last_phien - 1,
            "Tong": tong_hien_tai,
            "Xuc_xac_1": xuc_xac[0],
            "Xuc_xac_2": xuc_xac[1],
            "Xuc_xac_3": xuc_xac[2],
            "Dudoan_dung": int(prediction == ket_qua_hien_tai),
            "Dudoan_sai": int(prediction != ket_qua_hien_tai)
        })
    return jsonify(response)

@app.before_first_request
def start_ws_thread():
    threading.Thread(target=run_websocket, daemon=True).start()

if __name__ == "__main__":
    print("🚀 API TÀI XỈU WS_SEND ĐANG CHẠY...", flush=True)
    port = int(os.environ.get("PORT", 7723))
    app.run(host="0.0.0.0", port=port)
