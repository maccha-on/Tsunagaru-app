import streamlit as st 
import pandas as pd
import requests #JSON用
from openai import OpenAI
import os

# ############### data_extraction.pyの説明 ################
#
# 同ディレクトリにある DB.csvを読み込む。
# DB.csvには、ニックネーム、自己紹介文、個人webページURLが掛かれている。
# そこから趣味・特徴を抽出して、out.csvに出力するプログラム。
# まっと注）DB.csvは実際に使う適切なファイル名にあとで修正
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
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


# ######### 関数定義 ##########

# 与えられたテキストからキーワードを抽出する関数。
# 引数：Notion自己紹介文(Introduction)とLPからスクレイピングしたテキスト群(LP_text)
# exclude_keywords に既存のキーワードを渡すと、それらを除外するようGPTへ指示します。
def run_gpt_intro_to_keywords(text, exclude_keywords=None, label='Introduction'):
    if text is None or pd.isna(text):
        return ''
    text = str(text).strip()
    if not text or text.lower() == 'nan':
        return ''
    exclude_list = []
    if exclude_keywords:
        if isinstance(exclude_keywords, str):
            exclude_list = [kw.strip() for kw in exclude_keywords.split(',') if kw.strip()]
        else:
            exclude_list = [str(kw).strip() for kw in exclude_keywords if str(kw).strip()]
    instruction = (
        f"以下のデータは、ある人の{label}です。"
        f"この人の特徴となるキーワードを抽出してください。"
        f"キーワード間は,（半角カンマ）を入力してください。"
        f"最大文字数は100までとしてください。"
        f"ただし、人名（趣味に関する芸名・アーティスト名は除く）と会社名・所属組織名は日本語・英語表記問わず抽出しないでください。"
    )
    if exclude_list:
        listed = ', '.join(exclude_list)
        instruction += (
            f"既に以下のキーワードが抽出済みなので、重複する内容は含めないでください：{listed}"
        )
    request_to_gpt = (
        instruction +
        f"\n\n#データ\n{text}"
    )
    response = client.chat.completions.create(
        # モデル選択
        # 5-nanoから4o-miniに変更しています。
        # 5-nanoだと、謎キーワードがいくつか生じる印象
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": request_to_gpt},
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

## 元のデータの人数と実際の処理人数が合うようにコードを修正
def has_text(value):
    if value is None:
        return False
    if pd.isna(value):
        return False
    text = str(value).strip()
    if not text or text.lower() == 'nan':
        return False
    return True

# 特徴データをまとめたcsv(out.csv)を生成
# パターン1を採用：まずはnotion自己紹介文からキーワード抽出し、さらにLP掲載テキストからnotion自己紹介文に含まれないキーワードを追加抽出
# (注)何度も使うとAPI利用料がかさむかもなので、必要最小限で。
processed_count = 0
for index, row in input_df.iterrows():
    if not (has_text(row.get('Introduction')) or has_text(row.get('LP_text'))):
        continue
    processed_count += 1
    out_index = len(out_df)
    name_value = row.get('Name', '')
    out_df.loc[out_index, 'Name'] = str(name_value).strip() if has_text(name_value) else ''
    intro_text = row.get('Introduction')
    feature_list = []
    if has_text(intro_text):
        intro_features = run_gpt_intro_to_keywords(intro_text, label='Introduction')
        if intro_features:
            feature_list = [kw.strip() for kw in intro_features.split(',') if kw.strip()]
    lp_text = row.get('LP_text')
    if has_text(lp_text):
        lp_features = run_gpt_intro_to_keywords(lp_text, exclude_keywords=feature_list, label='LP_text')
        if lp_features:
            for kw in [item.strip() for item in lp_features.split(',') if item.strip()]:
                if kw not in feature_list:
                    feature_list.append(kw)
    out_df.loc[out_index, 'Features'] = ','.join(feature_list)
    print(f"{processed_count}人目を確認中...")

# CSVファイルに出力
out_df.to_csv("out.csv", encoding="utf-8-sig")
