import json
import time

import socketio
import requests

sio = socketio.Client()


@sio.on('connect')
def on_connect():
    print('Connected to server')


@sio.on("cut_status",namespace="/video")
def on_status(data):
    print(str(data))

@sio.on('cut_done',namespace="/video")
def on_my_event(data):
    print('received json: ' + str(data))
    sio.disconnect()



rep = requests.post("http://localhost:8080/auth",json={"username":"admin","password":123456})
sio.connect('ws://127.0.0.1:8080',headers={"Authorization":"JWT "+json.loads(rep.text)["access_token"]})
time.sleep(1)
sio.emit('video_cut', {"url":"D:\\videos\\e073999e6645394c59950628ff218285.mp4","start":"00:00:0F","end":"00:00:05"},namespace="/video")
sio.wait()