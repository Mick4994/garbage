import cv2
import time
import json
import uuid
import serial
import requests
import threading
from playsound import playsound
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

# 终端垃圾站运行参数
backbone_url = 'http://106.52.164.17:5000/api'
TRY_TIME = 3

COM_PORT = 'COM1'
BAUDRATE = 115200

DISPLAY_MODE = False
CAMERA_INDEX = 0
CONFIDENCE = 0.5
MODEL_PATH = 'damo/cv_convnext-base_image-classification_garbage'


def request_backbone(method, url, payload={}):
    def requests_request(_method, _url, _payload):
        try:
            requests.request(method=_method, url=_url, data=_payload)
        except:
            print("Error: backbone disconnected")

    threading.Thread(target=requests_request, args=(method, url, payload, )).start()


def update_bins_state(**update_state):
    with open('bins_state.json', 'w', encoding='utf-8') as f:
        for key, value in update_state.items():
            bins_state[key] = value
        f.write(json.dumps(bins_state))
    print(f'write to bins_state: {update_state}')


def bin_init():
    with open('bins_state.json', 'r', encoding='utf-8') as f:
        _bins_state = json.loads(f.read())
        if _bins_state['id'] is None:
            _bins_state['id'] = uuid.uuid4().int
            payload = {
                "id": _bins_state['id'],
                "name": _bins_state['name'],
                "longitude": _bins_state['longitude'],
                "latitude": _bins_state['latitude'],
                "temperature": _bins_state['temperature'],
                "humidity": _bins_state['humidity'],
                "status": "active"
            }
            update_bins_state(payload)
            request_backbone("POST", backbone_url+"/create", payload)
    return _bins_state


bins_state = bin_init()

name_map = {
    '可回收物': 'recyclable_waste',
    '厨余垃圾': 'kitchen_waste',
    '有害垃圾': 'hazardous_waste',
    '其他垃圾': 'other_waste'
}

index_map = {
    'recyclable_waste': '1',
    'kitchen_waste': '2',
    'hazardous_waste': '3',
    'other_waste': '4'
}

garbage_classification = pipeline(Tasks.image_classification,
                                  model=MODEL_PATH)

if DISPLAY_MODE:
    cap = cv2.VideoCapture(CAMERA_INDEX)
    frame = None
    res = []


def get_garbage_classify_result():
    global cap, frame, res
    if not DISPLAY_MODE:
        cap = cv2.VideoCapture(CAMERA_INDEX)
    result_score = 0
    final_label = '其他垃圾'

    last_time = time.time()

    for i in range(TRY_TIME):
        if not DISPLAY_MODE:
            _, frame = cap.read()

        cur_result = garbage_classification(frame)
        top_score = cur_result['scores'][0]
        top_label = cur_result['labels'][0]

        print(f'{i + 1}. {top_label}: {top_score:.3f}')
        if top_score > CONFIDENCE and top_score > result_score:
            final_label = top_label
        now_time = time.time()
        print(f'took {now_time - last_time:.2f} s')
        last_time = now_time

    final_label = final_label.split('-')[0]

    if not DISPLAY_MODE:
        cap.release()
    else:
        res.append(final_label)

    return final_label


def process_serial_data(serial_data: dict):
    if serial_data['type'] == 'health':
        payload = {
            "id": bins_state["id"],
            "temperature": serial_data['data']['temperature'],
            "humidity": serial_data['data']['humidity']
        }
        update_bins_state(payload)
        request_backbone("POST", url=backbone_url + f'/update', payload=payload)

        return

    if serial_data['type'] == 'income':
        final_label = get_garbage_classify_result()
        trash_type = 'other_waste'
        if final_label in name_map:
            trash_type = name_map[final_label]
            playsound(f'tts/tip/{trash_type}.wav')

        if bins_state['count'][trash_type] > 5:
            playsound(f'tts/full/{trash_type}.wav')
            payload = {
                "id": bins_state["id"],
                "status": "inactive"
            }
            update_bins_state(payload)
            request_backbone("POST", url=backbone_url + f'/update', payload=payload)
            return

        bins_state['count'][trash_type] += 1
        return index_map[trash_type]

    if serial_data['type'] == 'clean':
        for trash_type in bins_state['health']:
            bins_state['health'][trash_type] = 0


if __name__ == "__main__":
    try:
        with serial.Serial(port=COM_PORT, baudrate=BAUDRATE) as ser:
            print(f'connect to {COM_PORT}')

            last_time = time.time()

            buffer = ''

            while True:
                now_time = time.time()
                if now_time - last_time > 3:
                    print(bins_state)
                    last_time = now_time

                if DISPLAY_MODE:
                    _, frame = cap.read()
                    cv2.imshow('frame', frame)
                    if ord('z') == cv2.waitKey(1):
                        threading.Thread(target=get_garbage_classify_result).start()

                    if res:
                        try:
                            trash_type = name_map[res[-1]]
                            threading.Thread(target=playsound, args=(f'tts/tip/{trash_type}.wav',)).start()
                            res.clear()
                        except:
                            pass

                while ser.in_waiting:
                    buffer += ser.read(ser.in_waiting or 1).decode('utf-8')

                if not buffer:
                    continue

                try:
                    # 尝试解析完整的 JSON 对象
                    json_data = json.loads(buffer)
                except json.JSONDecodeError:
                    # 如果解析失败，继续读取直到缓冲区包含完整的 JSON
                    print(f"receive not json data:\n{buffer}")
                    continue

                proc_res = process_serial_data(json_data)
                if proc_res:
                    ser.write(proc_res.encode('utf-8'))

                buffer = ''

    except:
        update_bins_state()

