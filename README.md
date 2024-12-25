# 智慧垃圾桶终端

这是一个智慧垃圾桶系统的终端，作为节点部署在智能垃圾桶本地，负责管理垃圾桶与控制单元和传感器的协同工作，集成垃圾分类识别，存储节点基本运行配置，更新节点传感数据，如温湿度，垃圾桶是否已满，稍加封装传至服务端等功能。

## 垃圾分类：
使用 `damo/cv_convnext-base_image-classification_garbage` 模型：
- 支持识别4个标准的生活垃圾大类：可回收垃圾、厨余垃圾、有害垃圾、其他垃圾
- 支持识别265个生活垃圾品类

## 节点数据:
其中固定数据是注册是发送服务端，动态数据是实时轮询
- 固定数据
  1. 节点唯一标识符 uuid
  2. 节点的经纬度 "latitude" 和 “longitude”
- 动态数据：
  1. 节点工作状态"state"（正常/已满） 
  2. 节点温湿度 "temperature" 和 "humidity"

## 对接控制单元：
通过串口通讯：
- 接受esp32收集的实时轮询的传感器信息
- 发送垃圾分类的指令使esp32执行运动控制

## 安装与运行
1. 克隆项目
```bash
git clone https://github.com/Mick4994/garbage
cd garbage
```
2. 安装依赖
确保你已经安装了 Python 3 和 pip，然后安装项目依赖：
```bash
pip install -r requirements.txt
```
3. 运行程序
```
python main.py
```

## 部署到 Docker

为了方便部署，你可以使用 Docker 来容器化应用。使用项目下的Dockerfile即可（执行docker build）。

```bash
docker build -t <name:tag> .
```

运行 Docker 容器：
```
docker run --device <path/to/camera> <image_name:tag>
```

## 总结
本项目实现了智慧垃圾桶的节点客户端，通过与控制单元和传感器，服务端的协同工作，共同实现了垃圾桶自主分类的核心功能。通过 Docker 部署运行在容器化环境中，可以方便地将节点快速迁移，以适应不同的生产需求。