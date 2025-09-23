import streamlit as st 
import pandas as pd
import requests #JSON用
from openai import OpenAI
import os
from pathlib import Path

# ######################## analyze.pyの説明 ##########################
# 
# 現状は、「指定ユーザーと共通点のある人を探す」機能のみ実装済み。(find_commons関数)
# 分析もChatGPTに全て任せちゃっています。
# 
# ####################################################################


# ######### 関数定義 ##########
# chatGPTにリクエストするメソッド
# 使い方
#   name: ユーザーの名前
#   data: 探す元となる情報データ CSVを想定


# 解説：選んだユーザー起点に、共通点を見つける関数
# いちばん多くの人とつながりそうな共通点を出力する。
def find_major_commons(name, client):
    # データファイルの読み込み
    # 現状は特徴を詰め込んだだけのout.csvを利用
    try:
        # Cloud環境なら st.secrets["DATA"] が使える
        data_txt = st.secrets["MEMBER_DATA"]
        st.sidebar.caption('secretsから取得中...')
    except Exception:
        p = Path(__file__).parent / "out.csv"
        if p.exists():
            data_txt = str(pd.read_csv("out.csv"))
            st.write('ローカルcsvから取得中...')
         
    # ChatGPTを呼び出しスクリプト
    request_to_gpt = (
        f"「{name}」が持つ特徴について、他の多くのメンバーとも共通するものを最大３つほど教えてください。"
        f"各共通点については、誰と共通しているのかも説明してください。"
        f"回答は、前置き無しで結論を記載。最大でも300字程度にしてください。\n"
        f"メンバーとその特徴は、以下のとおりです。\n\n"
        f"{data_txt}"
        )
    # 決めた内容を元にchatGPTへリクエスト
    response =  client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": request_to_gpt},
        ],
    )
    # 返って来たレスポンスの内容
    output_content = response.choices[0].message.content.strip()
    return output_content 



# 解説：選んだユーザー起点に、共通点を見つける関数
#      いちばん共通点が多そうな人をを出力する。
#      *スクリプト意外はfind_commonsと同じ。
#      直前のクライアントで、データファイルは読み込み済みが前提。
def find_similar_person(name, client):
    # データファイルの読み込み
    try:
        # Cloud環境なら st.secrets["DATA"] が使える
        data_txt = st.secrets["MEMBER_DATA"]
        st.sidebar.caption('secretsから取得中...')
    except Exception:
        p = Path(__file__).parent / "out.csv"
        if p.exists():
            data_txt = str(pd.read_csv("out.csv"))
            st.sidebar.caption('ローカルcsvから取得中...')
         
        
    # ChatGPTを呼び出しスクリプト
    request_to_gpt = (
        f"「{name}」と、多くの共通点がある人を3人教えてください。"
        f"回答形式については、共通点の多いメンバーの名前を書き、共通や類似するポイントを箇条書きで教えてください。"
        f"回答は、最大でも300文字程度としてください。\n"
        f"#回答例のイメージ\n"
        f"1人目: たっちゃん\n"
        f"理由: xxxxx \n\n"
        f"#メンバーとその特徴リスト\n"
        f"{data_txt}"
        )
    # 決めた内容を元にchatGPTへリクエスト
    response =  client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": request_to_gpt},
        ],
    )
    # 返って来たレスポンスの内容
    output_content = response.choices[0].message.content.strip()
    return output_content 
