import cv2
import time
import json
import serial
import requests
import threading
from playsound import playsound
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

DEVICE_ID = 1
DISPLAY_MODE = True
backbone_url = 'http://localhost'
TRY_TIME = 3
CAMERA_INDEX = 0
CONFIDENCE = 0.5
COM_PORT = 'COM1'
BAUDRATE = 115200
MODEL_PATH = 'damo/cv_convnext-base_image-classification_garbage'

bins_state = {
    'health': {
        'recyclable_waste': 0,
        'kitchen_waste': 0,
        'hazardous_waste': 0,
        'other_waste': 0
    },
    'count': {
        'recyclable_waste': 0,
        'kitchen_waste': 0,
        'hazardous_waste': 0,
        'other_waste': 0
    }
}

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

def request_backbone(url):
    def requests_get(get_url):
        try:
            requests.get(get_url)
        except:
            print("Error: backbone disconnected")

    threading.Thread(target=requests_get, args=(url,)).start()


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
        for trash_type, health in serial_data['data'].items():
            bins_state[trash_type] = health
        return

    if serial_data['type'] == 'income':
        final_label = get_garbage_classify_result()
        trash_type = 'other_waste'
        if final_label in name_map:
            trash_type = name_map[final_label]
            playsound(f'tts/tip/{trash_type}.wav')

        if bins_state['count'][trash_type] > 5:
            playsound(f'tts/full/{trash_type}.wav')
            request_backbone(url=backbone_url + f'/full/{DEVICE_ID}/{trash_type}')
            return

        bins_state['count'][trash_type] += 1
        request_backbone(url=backbone_url + f'/update/{DEVICE_ID}/{trash_type}')
        return index_map[trash_type]

    if serial_data['type'] == 'clean':
        for trash_type in bins_state['health']:
            bins_state['health'][trash_type] = 0
        request_backbone(url=backbone_url + f'/clean/{DEVICE_ID}')


if __name__ == "__main__":

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

