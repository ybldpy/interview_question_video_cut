import datetime

from flask_sqlalchemy import SQLAlchemy
import subprocess
import threading
import time
import uuid
import requests
from flask import Flask, render_template,jsonify,request
from flask_socketio import SocketIO, emit
import eventlet
from eventlet import wsgi

from flask_jwt import JWT, jwt_required, current_identity

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root062400@localhost/videoApp'
socketio = SocketIO(app,async_handlers=True)
namespace = '/video'

db = SQLAlchemy(app)


def authenticate(username, password):
    user = db.session.query(User).filter(User.username==username,User.password==password).first()
    return user


def identity(payload):
    user_id = payload['identity']
    return db.session.get(User,user_id)

jwt = JWT(app=app,authentication_handler=authenticate,identity_handler=identity)




class User(db.Model):
    __tablename__="t_user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)




class VideoProcess(db.Model):
    __tablename__="t_video_process"
    id = db.Column(db.String(200), primary_key=True)
    uid = db.Column(db.Integer, nullable = True)
    ctime = db.Column(db.Integer)
    video_url = db.Column(db.String(200), nullable=False)
    local_url = db.Column(db.String(200), nullable=True)

    def __init__(self,id,uid,ctime,url,local_path = None):
        self.id = id
        self.uid = uid
        self.ctime = ctime
        self.video_url = url
        self.local_url = local_path


# @app.route("login")
# def login(username,password):
#     user = db.session.query().filter(User.username == username,User.password==password).first()
#
#     if user:
#         return jsonify({"msg": "Invalid username or password"},401),
#
#     access_token = create_access_token(identity=user.id)
#     return jsonify({"access_token": access_token})

@app.route("/")
@jwt_required()
def index():
    return current_identity.id


@socketio.on('connect')
def test_connect():
    print('Client connected')

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')



def validateField(json):
    necessary_field = json!=None and json.get("url")!=None and json.get("start")!=None and json.get("end")!=None
    if not necessary_field:
        return False
    start = json.get("start")
    times = start.split(":")
    if len(times)!=3:
        return False
    for i in range(0,3):
        if not str.isnumeric(times[i]):
            return False
        if i!=0 and int(times[i])>=60:
            return False
    return True

video_id = []

progress_map = {}



id_lock = threading.Lock()
# video的id，提供查询进度
def create_video_id():
    id_lock.acquire()
    vid = str(uuid.uuid4())
    id_lock.release()
    return vid

@app.route("/video/progress/<vid>")
def check_progress(vid):
    return {"vid":vid,"progress":progress_map.get(vid)}


# 先下载再存入临时文件
def read_URL(vid,url):
    if True:
        return url
    response = requests.get(url)
    content_type = response.headers.get("Content-type")
    if response.status_code!=200 or not content_type.startswith("video"):
        return {"code":403,"message":"url error"}
    total_size_in_bytes = int(response.headers.get('content-length', 0))
    file_name = "vid_tmp"
    block_size = 1024  # 1 Kibibyte
    with open(file_name, 'wb') as file:
        for data in response.iter_content(block_size):
            file.write(data)
# 本地直接读取
def read_local(url):
    return url

def update_progress(vid,progress):
    progress_map[vid] = progress


def get_progress(vid):
    return progress_map[vid]

def check_cut_Progress(vid,process):
    update_progress(vid,1)
    return True


@socketio.on('video_cut',namespace=namespace)
@jwt_required()
def handle_video_cut(json):
    if not validateField(json):
        emit("cut_status",{"code":400,"message":"参数缺失"})
        return
    vid = create_video_id()
    db.session.add(VideoProcess(id=vid,uid=current_identity.id,ctime=time.time_ns(),url = json['url']))
    db.session.commit()
    progress_map[vid] = 0
    emit("cut_status",{"code":200,"message":"vid","vid":vid})
    emit("cut_status",{"code":200,"message":"reading url"})
    # 使用本地路径方便测试
    local_path = read_URL(vid,url=json.get("url"))
    progress_map[vid] = 0.5
    start,end =json['start'],json['end']
    command = f"ffmpeg -i {local_path} -ss {start} -to {end} -c copy {vid}_output.mp4"
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    res = False
    # try:
    #     res = check_cut_Progress(vid,proc)
    # except Exception as ex:
    #     import traceback
    #     traceback.print_exc()
    #     emit("cut_done", {"code": 500, "message": "error"})
    #     return

    proc.wait()

    prefix = "/video/output/"
    code = proc.returncode
    if code!=0:
        emit("cut_done",{"code":500,"message":"error"})
    else:
        emit("cut_done",{"code":200,"url":f"{vid}.mp4"})
        db.session.query(VideoProcess).filter(VideoProcess.id==vid).update({"local_url":local_path})
        db.session.commit()
    del progress_map[vid]
    
@socketio.on_error()
def handle_error(e):
    print(e)


if __name__ == '__main__':
    wsgi.server(eventlet.listen(('localhost', 8080)), app)
