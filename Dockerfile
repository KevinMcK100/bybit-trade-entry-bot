# syntax=docker/dockerfile:1

FROM python:3.9-slim-buster

WORKDIR /bybit_trade_entry_bot

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "-m" , "main"]