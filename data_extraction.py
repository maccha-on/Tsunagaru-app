# import streamlit as st 
import pandas as pd
# import requests #JSON用
from openai import OpenAI
import os

# ############### data_extraction.pyの説明 ################
#
# 同ディレクトリにある DB.csvを読み込む。
# DB.csvには、ニックネーム、自己紹介文、個人webページURLが掛かれている。
# そこから趣味・特徴を抽出して、out.csvに出力するプログラム。
# 
# #########################################################


# まっとさんへ
# 現状は、自己紹介文のところだけ使って、キーワードを生成しています。
# スクレイピングしたデータを合わさるように修正していただけませんか。
# 最終的に、特徴が掛かれたout.csvファイルが生成できれば、どの段階から
# 自己紹介文とスクレイピングを合体させるのでも大丈夫です。
# 
# 追伸）One-hot化などデータ分析用に加工する場合も、
# out.csvからを入力とする別プログラムとして作成することにしますので、
# このプログラム中に入れていただく必要はありません。



# ######### 定数定義 ##########

# openAIの機能をclientに代入
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(api_key=api_key)


# ######### 関数定義 ##########

# 自己紹介文からキーワードを抽出する関数。
# 引数：自己紹介文
def run_gpt_intro_to_keywords(content_to_gpt):
    request_to_gpt = (
        f"以下のデータは、ある人の自己紹介です。"
        f"この人の特徴となるキーワードを抽出してください。"
        f"キーワード間は,（半角カンマ）を入力してください。"
        f"最大文字数は100までとしてください。"
        f"ただし、実名と会社名は抽出しないでください。"
        f"\n\n"
        f"#データ/n"
        f"{content_to_gpt}"
        )
    response =  client.chat.completions.create(
        # モデル選択
        # 5-nanoから4o-miniに変更しています。
        # 5-nanoだと、謎キーワードがいくつか生じる印象
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": request_to_gpt },
        ],
    )
    output_content = response.choices[0].message.content.strip()
    return output_content 


########### これ以下が実行コード #############

print("準備中... out.csvファイルは閉じておいてね。")

# 元データの読み込み
input_df = pd.read_csv("DB.csv")

# 特徴を抽出したデータの格納先準備
out_df = pd.DataFrame(columns=['Name', 'Features'])

# 特徴データをまとめたcsv(out.csv)を生成
# (注)何度も使うとAPI利用料がかさむかもなので、必要最小限で。
for index, row in input_df.iterrows():
    out_df.loc[index, 'Name']= row['Name']
    out_df.loc[index, 'Features'] = run_gpt_intro_to_keywords(row['Introduction'])
    print(index+1,"人目を確認中...")

# CSVファイルに出力
out_df.to_csv("out.csv", encoding="utf-8-sig")
