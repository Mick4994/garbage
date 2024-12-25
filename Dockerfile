FROM python:3.10-bullseye

COPY . /home/
WORKDIR /home/

RUN pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
