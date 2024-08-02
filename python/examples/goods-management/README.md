# 物品管理システム
## 説明
これはJetson NanoとWebカメラを使用して物品を管理するアプリケーションです。Webカメラに映る人と物体を認識します。その状態でボタン（borrow/return）を押すといつだれが何をどうしたのかという情報がCSVとラインに送られます。カメラに映る人はクラス分類によって特定可能です。カメラに映る物体は物体検出を行うことで認識することができます。

## 背景
職場にはPCやキーボード，コード類など様々な物品が存在します．それらの物品を正しく管理しなければなりませんが，時間と手間がかかります．そのため，物品管理を自動的に行うことができるシステムがあると便利だとと考えました．そこで考えたものが，Webカメラから人と物品を同時に認識し，その情報をJetson上で管理するというシステムです．

## デモ
具体的な動作については以下のURLからデモ動画をご覧ください。
https://drive.google.com/file/d/1nlDC7s7iDI67seOBCiGJYuB6_nZgzsO1/view?usp=sharing

## 使い方
### インストール
Jetsonのローカル上で以下のコマンドを実行することで、プログラムをcloneする。
```
git clone –recursive git@github.com:ayakasakurai0213/jetson-inference.git
```

以下のコマンドを実行してdockerコンテナを起動する。
```
cd jetson-inference
./docker/run.sh
```

dockerコンテナ内のターミナルで以下のコマンドを実行する。物品管理システムのプログラムを実行するために必要なライブラリをインストールする。
```
apt-get update
apt-get install python3-tk
```

### LINEトークン発行
cd /jetson-inference/python/examples/goods-management/
vi image_detect_net.py
37行目のaccess_tokenにLINEトークンを書き込んで保存

### 実行
cd /jetson-inference/python/examples/goods-management/
python3 image_detect_net.py /dev/video0

実行すると以下の画像に示すような虹色のGUIとカメラ画像が表示される。
![image01](images/image01.png)

### 操作方法
1. 机の上に物品を置き、物品と自分の顔がカメラで認識できるように写す。
2. 左上のラベルが正しいこと、物品が検出されていることを確認する。
3. borrow/returnをクリックする
4. LINEにカメラ画像とメッセージが送られる
![image02](images/image02.png)

### 独自の学習

