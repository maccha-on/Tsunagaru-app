import streamlit as st 
import pandas as pd
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
import reformat

# ############### data_extraction.pyの説明 ################
#
# 同ディレクトリにある DB.csvを読み込む。
#   DB.csvの内容: ニックネーム、自己紹介文、個人webページURL
# そこから趣味・特徴を抽出して、out.csvに出力する。
# まっと注）DB.csvは実際に使う適切なファイル名にあとで修正
# 
# 使用方法:
#  .envに OPENAI_API_KEY を保存する必要があります。
# 
# #########################################################



# ################# 定数定義 ###################

# openAIの機能をclientに代入
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# 自己紹介文からキーワード抽出するスクリプト
script_for_introduction = (
    f"以下のデータは、ある人の自己紹介です。\n"
    f"この人の特徴を表すキーワードを抽出してください。\n"
    f"キーワード間は,（半角カンマ）を入力してください。キーワードと半角カンマ意外は出力しないでください。\n"
    f"キーワードは8文字以内を目安に、キーワード数は1人につき最大20個までとしてください。\n"
    f"その人の特徴を現わさないものはキーワードにしないでください。（例: 「よろしく」などの挨拶文, 息子の年齢）\n"
    f"人名（趣味に関する芸名・アーティスト名は除く）と会社名・所属組織名は、日本語・英語表記問わず抽出しないでください。\n"
)

# スクレイピングデータからキーワード抽出するスクリプト
script_for_LP = (
    f"以下のURLは、ある人が自分の仕事や趣味などを紹介するために作成したwebページのデータです。\n"
    f"この人が、どんな特徴のある人かを推測し、キーワードとして出力してください。\n"
    f"キーワード間は,（半角カンマ）を入力してください。\n"
    f"キーワードは8文字以内を目安に、キーワード数は1人につき最大40個までとしてください。\n"
    f"その人の特徴を現わさないものはキーワードにしないでください。（例: 「よろしく」などの挨拶文, 息子の年齢）\n"
    f"人名（趣味に関する芸名・アーティスト名は除く）と会社名・所属組織名は、日本語・英語表記問わず抽出しないでください。\n"
)



# ################### 関数定義 #####################

# 与えられたテキストからキーワードを抽出する関数。
# 引数：Notion自己紹介文(Introduction)とLPからスクレイピングしたテキスト群(LP_text)
# exclude_keywords に既存のキーワードを渡すと、それらを除外するようGPTへ指示します。
def run_gpt_to_keywords(text, script="", exclude_keywords=None):
    # 入力テキストの例外処理
    if text is None or pd.isna(text):
        return ''
    text = str(text).strip()
    if not text or text.lower() == 'nan':
        return ''

    # 除外キーワード
    exclude_list = []
    if exclude_keywords:
        if isinstance(exclude_keywords, str):
            exclude_list = [kw.strip() for kw in exclude_keywords.split(',') if kw.strip()]
        else:
            exclude_list = [str(kw).strip() for kw in exclude_keywords if str(kw).strip()]
    if exclude_list:
        listed = ', '.join(exclude_list)
        script += (
            f"既に以下のキーワードが抽出済みなので、重複する内容は含めないでください：{listed}"
        )
    request_to_gpt = (
        script + '\n\n' + text
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

# LPテキストを取得する関数を定義
def fetch_lp_text(request_url):
    res = requests.get(request_url, timeout=10)
    # resの文字データがISO-8859-1のケースがあるので、utf-8に変換して文字化けを防止
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    # 画面非表示の典型タグを削除
    for tag in soup(["script", "style", "noscript", "svg", "meta", "title", "head"]):
        tag.decompose()

    # hidden/aria-hidden/display:none/visibility:hidden を削除
    for el in soup.select("[hidden], [aria-hidden='true'], [style*='display:none'], [style*='visibility:hidden']"):
        el.decompose()

    # 表示テキストのみを取得して整形
    return "".join(s for s in soup.stripped_strings)


## 有効データが入っていたらTrueを返す関数
def has_text(value):
    if value is None:
        return False
    if pd.isna(value):
        return False
    text = str(value).strip()
    if not text or text.lower() == 'nan':
        return False
    return True


################ これ以下が実行コード ################

print("準備中... out.csvファイルは閉じておいてね。")

# 元データの読み込み
input_df = pd.read_csv("DB.csv")

# 特徴を抽出したデータの格納先準備
out_df = pd.DataFrame(columns=['Name', 'Features'])
scraping_df = pd.DataFrame(columns=['Name', 'LP_text'])

# ---- input_dfの各行についてキーワード抽出を行う処理 ----
for index, row in input_df.iterrows():
    # データが入っていない行は無視
    if not (has_text(row.get('Introduction')) or has_text(row.get('URL'))):
        continue

    # 現在の行数（出力ファイル基準）
    out_index = len(out_df)

    # 名前の格納
    name_value = row.get('Name', '')
    name = str(name_value).strip() if has_text(name_value) else ''
    out_df.loc[out_index, 'Name'] = name
    scraping_df.loc[out_index, 'Name'] = name

    # 自己紹介文からのキーワード抽出処理
    print(f"{index}: {name}さんのキーワード抽出中...")
    intro_text = row.get('Introduction')
    feature_list = []
    if has_text(intro_text):
        intro_features = run_gpt_to_keywords(intro_text, script_for_introduction, None)
        if intro_features:
            feature_list = [kw.strip() for kw in intro_features.split(',') if kw.strip()]

    # スクレイピング処理
    print(f"{index}: {name} さんURLをスクレイピング中...")
    try:
        lp_text = fetch_lp_text(row['URL'])
    except Exception as exc:
        print(f"  取得に失敗しました: {exc}")
        lp_text = ""
    scraping_df.at[out_index, 'LP_text'] = lp_text

    # スクレイピングTextからのキーワード抽出処理
    print(f"{index}: スクレイピング情報からキーワード抽出中...")
    if has_text(lp_text):
        lp_features = run_gpt_to_keywords(lp_text, script_for_LP, exclude_keywords=feature_list)
        if lp_features:
            for kw in [item.strip() for item in lp_features.split(',') if item.strip()]:
                if kw not in feature_list:
                    feature_list.append(kw)

    out_df.loc[out_index, 'Features'] = ','.join(feature_list)

# CSVファイルに出力
out_df.to_csv("out.csv", encoding="utf-8-sig")
# スクレイピングデータの出力 (アプリでは直接使わない。検証用データ)
scraping_df.to_csv("LP_text.csv", encoding="utf-8-sig")
print("キーワードをout.csvへ出力しました")


# ---------------CSVの特徴をカンマで分割--------------
# カンマで分割してDataFrameに展開
features_df = out_df["Features"].str.split(",", expand=True)

# 特徴を1つずつ列に横展開
# 列名を「Feature_1」「Feature_2」…のようにする
features_df.columns = [f"Feature_{i+1}" for i in range(features_df.shape[1])]
# Name列と結合
df_wide = pd.concat([out_df["Name"], features_df], axis=1)

# 出力
print(df_wide.head())
df_wide.to_csv("out_splited_wide.csv", index=False, encoding="utf-8-sig")
print("キーワードを分割したout_sprited_wide.csvを出力しました")


# ------------- JSONファイルに出力 ----------------
df_json = out_df.copy()

# --- カンマで分割してリストに変換 ---
df_json["Features"] = df_json["Features"].apply(lambda x: [item.strip() for item in x.split(",")])

# --- JSONに変換してファイルに出力 ---
# orient="records" → 各行を辞書形式のリストにする
# force_ascii=False → 日本語をそのまま出力
df_json.to_json("out.json", orient="records", force_ascii=False, indent=4)
print("DataFrameをout.jsonに出力しました")


# -------------ワンホット化（カンマ区切りを列に展開して0/1化）---------------
onehot = out_df["Features"].fillna("").str.get_dummies(sep=",")
# 余分なスペースを除去（列名の前後空白を削る）
onehot = onehot.rename(columns=lambda c: c.strip())
# Nameをインデックスにして結合（行＝人）
result = pd.concat([df["Name"], onehot], axis=1).set_index("Name")
# CSVに保存（Excelで文字化けしにくいUTF-8 BOM付き）
result.to_csv("onehot.csv", encoding="utf-8-sig")

print("ワンホット化したデータをonehot.csv に出力しました。")


