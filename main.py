import cv2
import time
import json
import serial
import requests
from playsound import playsound
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

DEVICE_ID = 1
backbone_url = ''
TRY_TIME = 3
CAMERA_INDEX = 0
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
    '可回收垃圾': 'recyclable_waste',
    '厨余垃圾': 'kitchen_waste',
    '有害垃圾': 'hazardous_waste',
    '其他垃圾': 'other_waste'
}

index_map = {
    'recyclable_waste': 1,
    'kitchen_waste': 2,
    'hazardous_waste': 3,
    'other_waste': 4
}

garbage_classification = pipeline(Tasks.image_classification,
                                  model=MODEL_PATH)


def get_garbage_classify_result():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    result_score = 0
    final_label = '其他垃圾'

    last_time = time.time()

    for i in range(TRY_TIME):
        _, frame = cap.read()
        cur_result = garbage_classification(frame)
        top_score = cur_result['scores'][0]
        top_label = cur_result['labels'][0]

        print(f'{i + 1}. {top_label}: {top_score:.3f}')
        if top_score > 0.8 and top_score > result_score:
            final_label = top_label
        now_time = time.time()
        print(f'took {now_time - last_time:.2f} s')
        last_time = now_time

    cap.release()
    return final_label


def process_serial_data(serial_data: dict):
    if serial_data['type'] == 'health':
        for trash_type, health in serial_data['data'].items():
            bins_state[trash_type] = health
        return

    if serial_data['type'] == 'income':
        final_label = get_garbage_classify_result()
        trash_type = name_map[final_label]

        if bins_state['health'][trash_type] == 1:
            playsound(f'{trash_type}.wav')
            requests.get(url=backbone_url + f'/full/{DEVICE_ID}/{trash_type}')
            return

        bins_state['count'][trash_type] += 1
        requests.get(url=backbone_url + f'/update/{DEVICE_ID}/{trash_type}')
        return trash_type

    if serial_data['type'] == 'clean':
        for trash_type in bins_state['health']:
            bins_state['health'][trash_type] = 0
        requests.get(url=backbone_url + f'/clean/{DEVICE_ID}')


if __name__ == "__main__":

    with serial.Serial(port=COM_PORT, baudrate=BAUDRATE) as ser:
        while True:
            data = ser.read_all().decode('utf-8')
            if not data:
                continue

            try:
                # 尝试解析完整的 JSON 对象
                json_data = json.loads(data)
            except json.JSONDecodeError:
                # 如果解析失败，继续读取直到缓冲区包含完整的 JSON
                continue

            proc_res = process_serial_data(json_data)
            if proc_res:
                ser.write(proc_res.encode('utf-8'))
