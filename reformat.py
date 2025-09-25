import pandas as pd
import json
from openai import OpenAI
import os
from pathlib import Path

# ######################## re_format.pyの説明 ##########################
# 
#  out.csvを成形したファイルをいくつか返します。
#   - out_sprited_wide.csv : 特徴データを横展開したもの
#   - out.json : 上記をjson化したもの
#   - onehot.csv : one-hot化したもの
# 
# #####################################################################

df = pd.read_csv("out.csv", index_col=0)

# ---------------CSVの特徴をカンマで分割--------------------------
# カンマで分割してDataFrameに展開
features_df = df["Features"].str.split(",", expand=True)

# 特徴を1つずつ列に横展開
# 列名を「Feature_1」「Feature_2」…のようにする
features_df.columns = [f"Feature_{i+1}" for i in range(features_df.shape[1])]
# Name列と結合
df_wide = pd.concat([df["Name"], features_df], axis=1)

# 出力
print(df_wide.head())
df_wide.to_csv("out_sprited_wide.csv", index=False, encoding="utf-8-sig")
print("特徴を分割したout_sprited_wide.csvを出力しました")



# ------------- JSONファイルに出力 ----------------
df_json = df

# --- カンマで分割してリストに変換 ---
df_json["Features"] = df_json["Features"].apply(lambda x: [item.strip() for item in x.split(",")])

# --- JSONに変換してファイルに出力 ---
# orient="records" → 各行を辞書形式のリストにする
# force_ascii=False → 日本語をそのまま出力
df_json.to_json("out.json", orient="records", force_ascii=False, indent=4)
print("DataFrameをout.jsonに出力しました")



# -------------ワンホット化（カンマ区切りを列に展開して0/1化）---------------
onehot = df["Features"].fillna("").str.get_dummies(sep=",")
# 余分なスペースを除去（列名の前後空白を削る）
onehot = onehot.rename(columns=lambda c: c.strip())
# Nameをインデックスにして結合（行＝人）
result = pd.concat([df["Name"], onehot], axis=1).set_index("Name")
# CSVに保存（Excelで文字化けしにくいUTF-8 BOM付き）
result.to_csv("onehot.csv", encoding="utf-8-sig")

print("ワンホット化したデータをonehot.csv に出力しました。")

