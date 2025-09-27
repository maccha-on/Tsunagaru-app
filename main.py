
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


# 動作モードの選択　# 09/23よこ修正
mode_1 = "共通点探し"
mode_2 = "特徴探し"
mode_3 = "相関図(ローカル環境のみ動作)"
operation_mode_of = {mode_1,mode_2,mode_3}

# JSONデータを読み込み、メニューバーに反映
data_json = analyze.read_json()
names = data_json["Name"].dropna().unique().tolist()

#-------------------------------
#  　　　サイドバー ここから　　　　
#-------------------------------
with st.sidebar:
    st.title("つながるアプリ")
    st.caption("アプリの説明")
    # st.sidebar.write("どんな繋がりを見つける？")
    # st.sidebar.pills("選んでください。：",["共通点探し","特徴探し","その他"])
    operation_mode = st.selectbox("どんな繋がりを見つける？", options=operation_mode_of)
    #coice = st.sidebar.radio("選んでください。：",["共通点探し","特徴探し","その他"])

    #mode_1:共通点探しを選択した場合のサイドバー表示
    if operation_mode == mode_1:
        st.write("あなたの仲間について教えて")
        # ニックネームを入力してもらう
        st.caption('あなたの名前は？')
        name = st.selectbox("選んでね", names)
        # st.sidebar.selectbox("選んでください。：",["AAA(固定値)","BBB","CCC"])

    #mode_2:特徴探しを選択した場合のサイドバー表示
    elif operation_mode == mode_2:
        st.write("探したい特徴を入力して")
        # 特徴を入力してもらう
        st.caption('調べたい特徴は？')
        common_point = st.text_input("特徴を入力")
        #user_features = st.text_input("特徴を入力")

    #mode_3:相関図を選択した場合のサイドバー表示
    elif operation_mode == mode_3:
        st.caption('相関図を描こう')

    # 以下は無効化(コメントアウト)した機能
        # アップロード機能
        # メンバー情報の読み込み
        # data = st.file_uploader("Upload to CSV")

        # ダウンロード機能
        # text = "これはテスト用のテキストです"
        # st.download_button(label="Download", data=text, file_name="test.txt", mime="text/plain")


    #探そう！をクリックした場合に処理が起動
    #  09/23よこ追加
    search_clicked = st.button("探そう！")

#-------------------------------
#  　　　サイドバー ここまで　　　　
#-------------------------------


#-------------------------------
#  　　　トップ画面の表示　　
#-------------------------------
# トップ画像 or キャラクター
st.image("img/top_image.png")



# データ分析を実行し、表示
# ユーザー名を引数に渡して、共通点を探した結果をテキストで返す
# # 09/23よこ編集 「探そう！」をクリックすることで処理が走るように改修
if search_clicked:
    try:
        # 画面上に結果を出力
        # tab1, tab2, tab3 = st.tabs(["共通点","特徴","相関"])
        #　mode_1:共通点探しを選択した場合の結果表示
        if operation_mode == mode_1:
            #共通点を取得する関数を呼び出す
            out_text1 = analyze.find_major_commons(name, client, data_json)
            out_text2 = analyze.find_similar_person(name, client, data_json)
            out_text3 = analyze.find_team_member(name, client, data_json)

            #関数の取得結果を表示
            tab1, tab2, tab3 = st.tabs(["みんなとの共通点","似ている人","チーム提案"])
            with tab1:
                st.write(out_text1)
            with tab2:
                st.write(out_text2)
            with tab3:
                st.write(out_text3)
        #mode_2:特徴探しを選択した場合の結果表示
        elif operation_mode == mode_2:
            #特徴を取得する関数を呼び出す
            out_text3 = analyze.search_by_common(common_point, client, data_json)

            #関数の取得結果を表示
            tab1, tab2 = st.tabs(["同じ特徴のある人","似ている人"])
            with tab1:
                st.write(out_text3)
            with tab2:
                st.write(out_text3)

        #mode_3:相関図を選択した場合の結果表示
        elif operation_mode == mode_3:
            tab1 = st.tabs(["相関図"])
            tab1.write("工事中")
    except Exception as e:
        st.error(f"エラーが発生しました:{e}")

