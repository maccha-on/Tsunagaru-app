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



def read_json():
    try:
        # Cloud環境なら st.secrets["DATA"] が使える
        data_json = st.secrets["MEMBER_DATA_JSON"]
        st.sidebar.caption('secrets')
    except Exception:
        p = Path(__file__).parent / "out.json"
        if p.exists():
            data_json = pd.read_json("out.json")
            st.sidebar.caption('Local csv')
    return data_json



# 解説：選んだユーザー起点に、共通点を見つける関数
# いちばん多くの人とつながりそうな共通点を出力する。
def find_major_commons(name, client, data_json):
    st.sidebar.caption("共通点が多い人を探索中....")
         
    # ChatGPTを呼び出しスクリプト
    request_to_gpt = (
        f"「{name}」が持つ特徴のうち、他のメンバーと会話が弾みそうな共通点を３つほど教えてください。\n"
        f"各共通点について、誰と共通しているのかも説明してください。\n"
        f"回答形式： 前置き無しで結論を記載。締めくくりの言葉は不要。\n"
        f"文字数： 最大でも300字程度にしてください。\n"
        f"メンバーとその特徴は、次のJSONを参照してください。\n"
        f"{data_json}"
        )
    # 決めた内容を元にchatGPTへリクエスト
    response =  client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたはJSONデータを解析するAIです。親しみやすく楽しい口調で、回答します。"},
            {"role": "user", "content": request_to_gpt}
        ]
    )
    # 返って来たレスポンスの内容
    output_content = response.choices[0].message.content.strip()
    return output_content 



# 解説：選んだユーザー起点に、共通点を見つける関数
#      いちばん共通点が多そうな人をを出力する。
#      *スクリプト意外はfind_commonsと同じ。
#      直前のクライアントで、データファイルは読み込み済みが前提。
def find_similar_person(name, client, data_json):
    st.sidebar.caption("共通点が多い人を探索中....")
    # ChatGPTを呼び出しスクリプト
    request_to_gpt = (
        f"「{name}」と、共通点が多い人を3人教えてください。"
        f"回答形式: 共通点の多いの名前を太字で書いたあと、共通や類似するポイントを書いてください。\n"
        f"文字数: 最大でも300文字程度\n"
        f"#回答例のイメージ\n"
        f"1人目: たっちゃん\n"
        f"理由:  \n"
        f"#メンバーとその特徴は、次のJSONを参照してください。\n"
        f"{data_json}"
        )
    # 決めた内容を元にchatGPTへリクエスト
    response =  client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたはJSONデータを解析するAIです。親しみやすいキャラクターです。"},
            {"role": "user", "content": request_to_gpt}
        ]
    )
    # 返って来たレスポンスの内容
    output_content = response.choices[0].message.content.strip()
    return output_content 
