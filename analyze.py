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



# ローカルのJSONファイル（クラウドの場合は toml形式のデータ）を読み込んで
# DataFrameとして返す関数。
def read_json():
    df = None
    try:
        # TOML形式のSecretsからデータ取得（Pythonのdict/リストとして読み込まれる）
        users_data = st.secrets["users"]  # [{'Name':..., 'Features':[...]}...]
        # JSON文字列に変換
        df = pd.DataFrame(users_data)
        # 表示して確認
        # st.sidebar.caption('secretsデータを利用しています')
    except Exception:
        p = Path(__file__).parent / "out.json"
        if p.exists():
            df = pd.read_json("out.json")
        #     st.sidebar.caption('Local csvデータを利用しています')
    if df is None: 
        st.sidebar.caption('データ読み込みエラー')
    return df



# mode_1-1:共通点探し
# 解説：選んだユーザー起点に、共通点を見つける関数
# いちばん多くの人とつながりそうな共通点を出力する。
def find_major_commons(name, client, data_json):
    #st.sidebar.caption("共通点が多い人を探索中....")
    placeholder = st.empty()
    placeholder.info("みんなとの共通点を探索中....")

    # ChatGPTを呼び出しスクリプト
    request_to_gpt = (
        f"「{name}」が持つ特徴のうち、他のメンバーも同じような特徴を持つものを３つ教えてください。\n"
        f"#探索条件: 人数が多い特徴を優先する。話が弾みそうな特徴を優先する。\n"
        f"#回答形式:\n"
        f"共通している特徴・キーワードをまず太字で記載。続けて、誰とどのように共通しているか説明する。\n"
        f"文字数は、最大でも500字程度\n\n"
        f"前置き無しで結論を記載。締めくくりの言葉は不要。\n\n"
        f"#回答例（イメージ）\n"
        f"「温泉」Aさん、Bさんも温泉に興味があるみたい！ Cさん、Dさんも国内旅行が好きだから温泉もよく知っているかもしれないよ！\n\n"
        f"#参照データ：メンバーとその特徴は、以下のJSONを参照してください。\n"
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
    placeholder.empty()
    # 返って来たレスポンスの内容
    output_content = response.choices[0].message.content.strip()
    return output_content 


# mode_1-2:共通点探し
# 解説：選んだユーザー起点に、共通点を見つける関数
#      いちばん共通点が多そうな人をを出力する。
#      *スクリプト意外はfind_commonsと同じ。
def find_similar_person(name, client, data_json):
    #st.sidebar.caption("共通点が多い人を探索中....")
    placeholder = st.empty()
    placeholder.info("共通点のある人を探索中....")
    # ChatGPTを呼び出しスクリプト
    request_to_gpt = (
        f"「{name}」と、共通点が多い人を、「似ている人」として5人教えてください。"
        f"#探索条件: 共通点が多い人が5人見つからない場合は、3人くらいでよいです。\n"
        f"#回答形式: 共通点の多いの名前を太字で書いたあと、共通や類似するポイントを書いてください。\n"
        f"#前置きは無しで、名前と理由だけ回答してください。\n"
        f"#1人につき、100文字から150文字程度にしてください。\n"
        f"#回答例のイメージ\n"
        f"1位: たっちゃん\n"
        f"理由: ... \n\n"
        f"#メンバーとその特徴は、次のJSONを参照してください。\n"
        f"{data_json}"
        )
    # 決めた内容を元にchatGPTへリクエスト
    response =  client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたはJSONデータを解析するAIです。親しみやすく楽しい口調のキャラクターです。"},
            {"role": "user", "content": request_to_gpt}
        ]
    )
    placeholder.empty()
    # 返って来たレスポンスの内容
    output_content = response.choices[0].message.content.strip()
    return output_content 


# mode_1-3:チーム提案
# 解説：チームメンバーを提案してもらう機能
#      共通点探しモードのタブ3として追加
def find_team_member(name, client, data_json):
    #st.sidebar.caption("共通点が多い人を探索中....")
    placeholder = st.empty()
    placeholder.info("最適なチーム員を探索中....")
    # ChatGPTを呼び出しスクリプト
    request_to_gpt = (
        f"「{name}」さんは、これから3人のチームを組んで、ソフトウェアの開発を行います。\n"
        f"JSONデータを参照して、「{name}」さんと一緒に面白い開発が出来そうな人を教えてください。\n"
        f"#分析条件: "
        f"個人としてだけでなく、3人のチームバランスも考慮してください。\n"
        f"毎回同じ回答にならないように、ランダム性を入れてください。\n"
        f"#回答形式:\n"
        f"前置きはナシで、あと2人のメンバーを提案してください。その後、おすすめした理由を説明してください。\n"
        f"文字数は、最大でも400文字程度にしてください。\n"
        f"#文章の書きだしのイメージ: 「今回のおすすめは...Aさん、Bさんだよ！」\n\n"
        f"#メンバーとその特徴（JSON）\n"
        f"{data_json}"
        )
    # 決めた内容を元にchatGPTへリクエスト
    response =  client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたはJSONデータを解析するAIです。親しみやすく楽しい口調のキャラクターです。"},
            {"role": "user", "content": request_to_gpt}
        ]
    )
    placeholder.empty()
    # 返って来たレスポンスの内容
    output_content = response.choices[0].message.content.strip()
    return output_content


# mode_2:特徴探し
# 解説：共通点を入力して、同じ共通点を持つ人を探す機能
def search_by_common(common_point, client, data_json):
    #st.sidebar.caption("メンバーを探索中....")
    placeholder = st.empty()
    placeholder.info("同じ共通点を持つ人を探索中....")
    # ChatGPTを呼び出しスクリプト
    request_to_gpt = (
        f"JSONデータを参照して、「{common_point}」と似た特徴やキーワードを持つ人を探してください。"
        f"#分析条件: 似たキーワードも対象に含めてください。例えば「阪神ファン」と「甲子園出場」は、どちらも野球に関心がある点で共通しています。\n"
        f"#分析条件: 該当する人は、全員教えてください。"
        f"#回答形式: 名前を太字で書いたあと、その後に選んだ理由を説明してください。これを、全員分、繰り返してください。\n"
        f"#回答形式: 前置きの文章は無しで、名前から書き始めてください。\n"
        f"#メンバーとその特徴はデータ（JSON）\n"
        f"{data_json}"
        )
    # 決めた内容を元にchatGPTへリクエスト
    response =  client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたはJSONデータを解析するAIです。親しみやすく楽しい口調のキャラクターです。"},
            {"role": "user", "content": request_to_gpt}
        ]
    )
    placeholder.empty()
    # 返って来たレスポンスの内容
    output_content = response.choices[0].message.content.strip()
    
    return output_content
