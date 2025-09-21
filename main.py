
# ######################## main.pyの説明 ##########################
# 
# フロントエンドの処理は、main.py内に記載する。
# - webページのレイアウト情報を記述
# - ユーザーからの入力情報をもとに、分析メソッドを呼び出す
# - メソッドからの戻り値をもとに、webページに表示する。
# 
# ################################################################

import streamlit as st 
import pandas as pd
import requests #JSON用
from openai import OpenAI
import os

# .env読み込みのため追加
from dotenv import load_dotenv
load_dotenv()

# 分析用プログラムの読み込み
import analyze 

# よこさんへ
# デザインは、よこさんのコードに丸ごと置き替えでokだと思います。
# GPT初期設定の2行の命令と、最後の2行の共通点のある人を探す関数(find_commons)を呼びだすところは、
# 残しておく必要があります。
#
# 余力あれば... 以下ご検討いただけるとうれしいです。
# - find_commmonsの戻り値について、現状のテキスト(str)形式ではなくて、
#   pandas表形式で共通趣味のあるメンバーを返す形式でも出力できるか？
# - マップ生成は、どんな入力や中間データがあれば生成できそうか？


# 25/09/21修正
# ChatGPTクライアントを起動するモジュール
# APIキーをstreamlit上から拾ってくるコードに差し替え
def get_api_key(env_key: str = "OPENAI_API_KEY") -> str | None:
    # 環境変数優先で API キーを取得。secrets は存在しない環境でも例外にならないように参照。
    key = os.getenv(env_key)
    if key:
        return key
    try:
        return st.secrets[env_key]  # secrets.toml が無い場合もあるため例外安全にする
    except Exception:
        return None
api_key = get_api_key()

if not api_key:
    st.error(
        "OpenAI APIキーが見つかりません。\n\n"
        "■ 推奨（ローカル学習向け）\n"
        "  1) .env を作成し OPENAI_API_KEY=sk-xxxx を記載\n"
        "  2) このアプリを再実行\n\n"
        "■ 参考（secrets を使う場合）\n"
        "  .streamlit/secrets.toml に OPENAI_API_KEY を記載（※リポジトリにコミットしない）\n"
        "  公式: st.secrets / secrets.toml の使い方はドキュメント参照"
    )
    st.stop()
    # ノートブック上では停止しません。実アプリでは st.stop() します。


@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=api_key)
client = get_openai_client()


# 動作モードの選択
mode_1 = "共通点探し"
mode_2 = "工事中。Comming Soon"
mode_3 = "工事中。Comming Soon."
operation_mode_of = {mode_1,mode_2,mode_3}


###↓↓↓ サイドバー ここから↓↓↓###
st.sidebar.title("ほにゃららアプリ")
st.sidebar.caption("アプリの説明")
# st.sidebar.write("どんな繋がりを見つける？")
# st.sidebar.pills("選んでください。：",["共通点探し","特徴探し","その他"])
operation_mode = st.sidebar.selectbox("どんな繋がりを見つける？", options=operation_mode_of)
#coice = st.sidebar.radio("選んでください。：",["共通点探し","特徴探し","その他"])

st.sidebar.write("あなたの仲間について教えて")
# ニックネームを入力してもらう
st.sidebar.caption('あなたのニックネームは？')
user_name = st.sidebar.text_input("ニックネームを入力")
# st.sidebar.selectbox("選んでください。：",["AAA(固定値)","BBB","CCC"])


# アップロード機能
# メンバー情報の読み込み
# data = st.sidebar.file_uploader("Upload to CSV")

# ダウンロード機能
# text = "これはテスト用のテキストです"
# st.sidebar.download_button(label="Download", data=text, file_name="test.txt", mime="text/plain")

st.sidebar.button("探そう！")

###↑↑↑ サイドバー ここまで ↑↑↑###


# トップ画像 or キャラクター
st.image("http://marvel-force-chart.surge.sh/marvel_force_chart_img/top_ironman.png", caption="キャラクターなど表示")

st.write("開発メモ: 現在は以下のメンバーに対応しています。")
st.write("まっちゃん,よこ,まっと,あらぴー,まる,けーすけ,りいちろー,りょーま,えーちゃん")

# データ分析を実行
# ユーザー名を引数に渡して、共通点を探した結果をテキストで返す
out_text1 = analyze.find_major_commons(user_name, client)
out_text2 = analyze.find_similar_person(user_name, client)
# 画面上に結果を出力

# 画面上に結果を出力
tab1, tab2, tab3 = st.tabs(["共通点","特徴","相関"])
with tab1:
    st.header("共通点タブ")
    col1,col2=st.columns(2)
    with col1:
        st.write("みんなとの共通点")
        st.write(out_text1)
    with col2:
        st.write("共通点のある人")
        st.write(out_text2)
tab2.write("いいい")
tab3.write("ううう")








######以下、まっちゃんコード　ここから######
# # 動作モードの定義
# mode_1 = "私と共通点のある人を見つける"
# mode_2 = "工事中。Comming Soon"
# mode_3 = "工事中。Comming Soon."
# operation_mode_of = {mode_1,mode_2,mode_3}

# ## Streamlit 表示用コード ###
# st.sidebar.title('ほにゃららアプリ ＃名前募集中') 

# # 動作モードの選択
# operation_mode = st.sidebar.write("どんな繋がりを見つける？",options=operation_mode_of)
# # メンバー情報の読み込み
# st.sidebar.write('ここにDBファイルをアップロード？（今回はローカルの(DB_sample.csv)を使う仕様）')
# # トップ画像 or キャラクター
# st.image("https://www.xxxx/image.jpg", caption="キャラクターなど表示")
# # ニックネームを入力してもらう
# st.write('あなたのニックネームは？')
# user_name = st.text_input("ニックネームを入力")

# # データ分析を実行
# # ユーザー名を引数に渡して、共通点を探した結果をテキストで返す
# out_text = find_commons(user_name, client)
# # 画面上に結果を出力
# st.write(out_text)
######以上、まっちゃんコード　ここまで######
