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
import base64
import time

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

# 処理中に表示するgifを非表示にする関数　09/29よこ修正
def show_temporary_success(message_holder, message="処理が完了しました！", delay=0.3):
    gif_holder.empty()
    message_holder.success(message)
    time.sleep(delay)
    message_holder.empty()

# 動作モードの選択　# 09/23よこ修正
# ローカルかどうかでメニュー変更 25/09/28まっちゃん修正
try:
    env_flg = st.secrets[DEPLOY_ENV]  # type: ignore
    st.sidebar.caption('クラウド実行モード')
except Exception:
    env_flg = "local"
    print('ローカル環境として実行します。（つながり線モードあり）')
    st.sidebar.caption('ローカル実行モード')
    # 25/10/02 上の場合分けと重複感があるため、コメントアウトしました。
    # きちんと例外処理を実装するなら、全jsonファイルを走査した方が良さそうです。
    # try:
    #     OUT_NETWORK_JSON = "out_network.json" 
    #     exists(OUT_NETWORK_JSON)
    # except:
    #     print('エラー発生したため、つながり線モードなしで実行します。')

mode_1 = "仲間を見つける"
mode_2 = "特徴から探す"
mode_3 = "繋がり線を描く"


## モード3 繋がり線機能の前処理
if env_flg == "local":
    operation_mode_of = [mode_1,mode_2,mode_3]
    # --- network_app から相関図表示に必要な関数・定数を最小限取り込み --- 25/09/29まっと（コード記載位置変更）
    from network_app import (
        OUT_NETWORK_JSON,  # JSON版で定義されているパス 例: out_network.json
        CITY_TO_PREF_JSON, PREF_ALIASES_JSON, PREF_TO_REGION_JSON,
        TOKEN_CATEGORY_JSON, CANONICAL_MAP_JSON, STOPWORDS_JSON, SUBCAT_WEIGHTS_JSON,
        load_json_any, load_token_category_json, load_kv_from_json, load_stopwords, load_canonical_map, load_subcat_weights_json,
        build_geo_dicts_from_json, build_graph, show_pyvis
    )
    
    # --- 外部辞書/データファイルの読み込み（サイドバーの選択肢にも必要） --- 09/28まっと追記
    data_records = load_json_any(OUT_NETWORK_JSON)
    all_names = sorted({str(r.get("Name","")).strip() for r in data_records if str(r.get("Name","")).strip()})
    # data_jsonからPandas DFで名前を取得しているが、ネットワーク図はdata_records（JSONリスト）を使用するため、こちらを優先。
    # 'names' は analyze.read_json() の戻り値から取得済みだが、'all_names'はネットワーク図用に再定義。
    # -------------------------------------------------------------------

    # --- ネットワーク図に必要なJSONリストと全メンバーリストを先に読み込む --- 09/28まっと追記
    from os.path import exists
    if exists(OUT_NETWORK_JSON):
        data_records = load_json_any(OUT_NETWORK_JSON)
        all_names = sorted({str(r.get("Name","")).strip() for r in data_records if str(r.get("Name","")).strip()})
    else:
        st.error(f"必須ファイル {OUT_NETWORK_JSON} が見つかりません。")
        st.stop()
else:
    operation_mode_of = [mode_1,mode_2]



# モード1,2用にJSONデータを読み込み、メニューバーに反映
data_json = analyze.read_json()
names = data_json["Name"].dropna().unique().tolist()



#---------------------------------------------------
#  　　　CSSの読み込み（初期表示）　9/27追加　　　
#---------------------------------------------------
st.markdown(
    """
    <style>
    /* サイドバー全体 */
    /* ① サイドバーが展開されている時の幅を強制 */
    [data-testid="stSidebar"][aria-expanded="true"]{
        width: 350px !important;
        min-width: 350px !important;
        }
    [data-testid="stSidebar"] {
        background: #F8D7B3; /* 単一色 */
        color: #444;
        font-family: "Rounded Mplus 1c", "Hiragino Maru Gothic ProN", sans-serif; /* 丸めのフォント */
        padding: 20px 15px;
        border-right: 2px solid #e0e6ef;
        box-shadow: 4px 0 8px rgba(0,0,0,0.05);
    }
    /* カード風の囲み */
    [data-testid="stSidebar"] .sidebar-content {
        background: #FFF8F0;
        border-radius: 16px;  /* 丸みを強める */
        padding: 18px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }
    /* 見出し */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #E2873B;
        font-weight: 600;
        border-bottom: 2px solid #8f6539;
        padding-bottom: 6px;
    }
    /* 選択ボックスや入力 */
    [data-testid="stSidebar"] .stSelectbox,
    [data-testid="stSidebar"] .stTextInput,
    [data-testid="stSidebar"] .stSlider {
        background: #FFF8F0;
        border-radius: 12px;
        padding: 6px 10px;
        margin: 10px 0;
        border: 1px solid #e6eaf2;
    }
    /* プルダウンの選択肢部分 */
    [data-testid="stSelectbox"] > div {
        background-color: #FFF8F0;
        color: #4A4A4A;
        font-weight: bold;
    }
    /* プルダウンの内部テキスト*/
    [data-testid="stSelectbox"] label {
        color: #E2873B;
        font-weight: bold;
    }
    /* ボタン */
    [data-testid="stSidebar"] button {
        background:#E2873B;
        color: #FDF6EC;
        border: none;
        border-radius: 20px;
        padding: 10px 18px;
        font-weight: bold;
        cursor: pointer;
        transition: 0.3s;
    }
    /* ボタンにカーソルを当てた際 */
    [data-testid="stSidebar"] button:hover {
        background-color: #B8CEC4;
        color: #336C62;
        font-weight: bold;
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    /* Streamlitの中央コンテンツ領域 */
    [data-testid="stAppViewContainer"] {
        background-color: #FFF8F0;
        color: #8F6539;
    }
    /* Streamlitのツールバー領域 */
    [data-testid="stHeader"] {
        background-color: #FFF8F0;
        color: #8F6539
    }
    </style>
    """,
    unsafe_allow_html=True
)

#-------------------------------
#  　　　サイドバー ここから　　　　
#-------------------------------
with st.sidebar:
    st.title("なかまっぷ") #09/29よこ修正
    st.caption("仲間や繋がりを探そう！")
    # st.sidebar.write("どんな繋がりを見つける？")
    # st.sidebar.pills("選んでください。：",["共通点探し","特徴探し","その他"])
    operation_mode = st.selectbox("どんな繋がりを見つける？", options = operation_mode_of, index=0)
    #coice = st.sidebar.radio("選んでください。：",["共通点探し","特徴探し","その他"])

    #mode_1:共通点探しを選択した場合のサイドバー表示
    if operation_mode == mode_1:
        # st.write("あなたの仲間について教えて")
        # ニックネームを入力してもらう
        name = st.selectbox("あなたの名前を教えて。", names)
        # st.sidebar.selectbox("選んでください。：",["AAA(固定値)","BBB","CCC"])

    #mode_2:特徴探しを選択した場合のサイドバー表示
    elif operation_mode == mode_2:
        # st.write("探したい特徴を入力して")
        # 特徴を入力してもらう
        common_point = st.text_input("どんな特徴や趣味の人を探す？")
        #user_features = st.text_input("特徴を入力")

    #mode_3:相関図を選択した場合のサイドバー表示
    elif operation_mode == mode_3:
        st.caption('繋がりを線で描こう')
        st.header("表示パラメータ")
        min_edge_score = st.slider("エッジ採用しきい値（合計スコア）", 0.0, 20.0, 6.0, 0.5) #初期表示を2.0から6.0に修正09/29よこ修正
        graph_height   = st.number_input("グラフ高さ(px)", min_value=400, max_value=1600, value=400, step=50) #初期表示を800から400に修正09/29よこ修正
        label_font_size = st.number_input("ラベル文字サイズ", min_value=8, max_value=30, value=16, step=1)
        st.divider()
        # ★ メンバー選択リストをサイドバーに追加（修正） 09/28まっと追加
        # all_names = sorted({str(r.get("Name","")).strip() for r in data_json.get("records", []) if str(r.get("Name","")).strip()}) # data_jsonから名前リストを構築
        # all_names は 'search_clicked' の外側で定義されているものを使用
        selected_people = st.multiselect("表示する人を選択（未選択なら全員）", options=all_names, default=st.session_state.get("selected_people_default", []))
        st.session_state["selected_people_default"] = selected_people # 選択を保持するためのセッションステート
        st.divider() # 区切り線を追加
        enable_link_sub1 = st.checkbox("subcategory1一致で“ゆるいつながり”を作る", value=True)
        enable_link_sub2 = st.checkbox("subcategory2一致で“ゆるいつながり”を作る", value=True)
        link_sub1_weight = st.slider("sub1リンクの重み", 0.0, 5.0, 0.6, 0.1)
        link_sub2_weight = st.slider("sub2リンクの重み", 0.0, 5.0, 0.6, 0.1)

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
# st.image("img/top_image.png")
# 09/28 クリック時に画像が切り替わるように修正

# 初期化
if "search_triggered" not in st.session_state:
    st.session_state.search_triggered = False

# 検索ボタン
if search_clicked:
    st.session_state.search_triggered = True

# 表示制御
if st.session_state.search_triggered == False:
    st.image("img/top_image.png")
else:
    st.image("img/top_image_small.png", width = 800)

#---------------------------------------------
#  　　　処理中のgifの表示 #09/29よこ修正
#---------------------------------------------

# GIFをbase64で読み込む
with open("img/walking_flag_10.gif", "rb") as file_:
    contents = file_.read()
    data_url = base64.b64encode(contents).decode("utf-8")

# プレースホルダーを用意
gif_holder = st.empty()
message_holder = st.empty()

# ボタンを押したらGIFを表示して処理開始
if search_clicked:
    # GIFを表示（HTMLで埋め込み）
    gif_holder.markdown(
        f'<img src="data:image/gif;base64,{data_url}" alt="loading gif" width="300">', 
        unsafe_allow_html=True
    )


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
            # 09/28 出力するタブにcssを適用
            st.markdown(
                """
                <style>
                /* タブ全体の背景 */
                div[data-baseweb="tab-list"] {
                    background-color: #FDF6EC;
                    padding: 10px;
                    border-radius: 10px;
                }
                /* タブ1つ1つ */
                button[data-baseweb="tab"] {
                    font-size: 18px;
                    color: #FDF6EC;
                    background-color: #F8D7B3;
                    border-radius: 8px;
                    margin-right: 5px;
                    padding: 10px 20px;
                }
                /* アクティブなタブ */
                button[data-baseweb="tab"][aria-selected="true"] {
                    background-color: #E2873B;
                    color: #F8D7B3;
                    font-weight: bold;
                }
                /* 非アクティブなタブのホバー時 */
                button[data-baseweb="tab"]:not([aria-selected="true"]):hover {
                    background-color: #B8CEC4;
                    color: #336C62;
                    font-weight: bold;
                    transform: translateY(-2px);
                }
                /* サイドバー全体の幅を調整 */
                [data-testid="stSidebar"] {
                    width: 500px;  /* デフォルトは約250px */
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            # 処理完了後にGIFを非表示する関数を呼び出す 09/29よこ修正
            show_temporary_success(message_holder,"仲間が見つかりました！",delay=0.3)
            
            # 関数の取得結果を表示
            # 09/28 出力エリアをカード形式に変更
            tab1, tab2, tab3 = st.tabs(["みんなとの共通点","似ている人","チーム提案"])
            with tab1:
                card_html = f"""
                <div style="background-color:#F8D7B3; color:#E2873B; border:1px solid #ccc; padding:20px; border-radius:10px; box-shadow:2px 2px 10px rgba(0,0,0,0.1);">
                <h3>共通点を見つけたよ！！</h3>
                <p>{out_text1}</p>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
            with tab2:
                #st.write(out_text2)
                card_html = f"""
                <div style="background-color:#F8D7B3; color:#E2873B; border:1px solid #ccc; padding:20px; border-radius:10px; box-shadow:2px 2px 10px rgba(0,0,0,0.1);">
                <h3>似ている人を見つけたよ！！</h3>
                <p>{out_text2}</p>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
            with tab3:
                #st.write(out_text3)
                card_html = f"""
                <div style="background-color:#F8D7B3; color:#E2873B; border:1px solid #ccc; padding:20px; border-radius:10px; box-shadow:2px 2px 10px rgba(0,0,0,0.1);">
                <h3>この人と組んでみる？？</h3>
                <p>{out_text3}</p>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
        #mode_2:特徴探しを選択した場合の結果表示
        elif operation_mode == mode_2:
            #特徴を取得する関数を呼び出す
            out_text3 = analyze.search_by_common(common_point, client, data_json)

            # 処理完了後にGIFを非表示する関数を呼び出す 09/29よこ修正
            show_temporary_success(message_holder,"仲間が見つかりました！",delay=0.3)

            #関数の取得結果を表示
            # 09/28 出力エリアをカード形式に変更
            #st.write(out_text3)
            card_html = f"""
            <div style="background-color:#F8D7B3; color:#E2873B; border:1px solid #ccc; padding:20px; border-radius:10px; box-shadow:2px 2px 10px rgba(0,0,0,0.1);">
            <h3>同じ特徴の仲間を見つけたよ</h3>
            <p>{out_text3}</p>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
        #mode_3:相関図を選択した場合の結果表示
        elif operation_mode == mode_3:
            if env_flg == "cloud":
                tab1 = st.tabs(["相関図"])
                st.write("クラウドでは未実装のため、ローカル環境で実行お願いします <(_ _)>")
                # 処理完了後にGIFを非表示する関数を呼び出す 09/29よこ修正
                show_temporary_success(message_holder,"ローカル環境で実行お願いします",delay=0.5)
            else:
                print('相関図を描画します。')
                # ---- 相関図（network_app の処理を main から呼び出し） ----
                # 必要JSONを読み込み（重複読み込みを整理：canonical_mapは load_canonical_map で統一）
                data_records = load_json_any(OUT_NETWORK_JSON)
                TOKEN_CATEGORY = load_token_category_json(TOKEN_CATEGORY_JSON)
                CANONICAL_MAP  = load_canonical_map(CANONICAL_MAP_JSON)
                STOPWORDS      = load_stopwords(STOPWORDS_JSON)
                CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET = build_geo_dicts_from_json(
                    CITY_TO_PREF_JSON, PREF_ALIASES_JSON, PREF_TO_REGION_JSON
                )
                try:
                    SUBCAT_WEIGHTS = load_subcat_weights_json(SUBCAT_WEIGHTS_JSON)
                except Exception:
                    SUBCAT_WEIGHTS = {}

                # ---------- メンバー選択処理（大幅に簡略化） ---------- 09/28まっと修正
                if st.session_state.get("selected_people_default"):
                    # サイドバーで選択されたリストを取得し、subsetとして利用
                    subset = st.session_state["selected_people_default"]
                else:
                    subset = None

                # ---------- グラフ構築 ----------
                G = build_graph(
                    data_records, min_edge_score,
                    TOKEN_CATEGORY, SUBCAT_WEIGHTS, CANONICAL_MAP, STOPWORDS,
                    CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET,
                    subset=subset,
                    enable_link_sub1=enable_link_sub1, enable_link_sub2=enable_link_sub2,
                    link_sub1_weight=link_sub1_weight, link_sub2_weight=link_sub2_weight
                )
                
                # もしフィルタで0件なら、明示メッセージを出す（空白/表記ゆれの切り分け用） *メンバー選択時表示用修正 09/28まっと追記
                if G.number_of_nodes() == 0:
                    st.warning("選択に一致するメンバーが見つかりませんでした。名前の表記をご確認ください。")
                    # フォールバックで全員表示したい場合は下を有効化：
                    # G = build_graph(data_records, min_edge_score, TOKEN_CATEGORY, SUBCAT_WEIGHTS,
                    #                 CANONICAL_MAP, STOPWORDS, CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET,
                    #                 subset=None, enable_link_sub1=enable_link_sub1, enable_link_sub2=enable_link_sub2,
                    #                 link_sub1_weight=link_sub1_weight, link_sub2_weight=link_sub2_weight)
                    
                # ---------- レイアウト：図＋エッジ一覧 ----------
                # 処理完了後にGIFを非表示する関数を呼び出す 09/29よこ修正
                show_temporary_success(message_holder,"繋がりを見つけたよ",delay=0.5)

                col1, col2 = st.columns([3,3], gap="large")# タイトルが収まるように表示を半々に修正 09/29よこ修正
                with col1:
                    st.subheader("ネットワーク図")
                    st.caption("趣味や特徴の傾向が似ている仲間を繋げました")# 説明を追加 09/29よこ修正
                    show_pyvis(G, height_px=int(graph_height), label_font_size=int(label_font_size))
                with col2:
                    st.subheader("エッジ一覧（重い順）")
                    st.caption("特徴が似ている仲間を順番に表示しています")# 説明を追加 09/29よこ修正
                    if G.number_of_edges() == 0:
                        st.info("エッジがありません。選択メンバーやしきい値を見直してください。")
                    else:
                        rows = []
                        for u, v, d in G.edges(data=True):
                            rows.append({
                                "A": u, "B": v,
                                "score": d.get("weight", 0),
                                "common_count": d.get("common_count", 0),
                                "common_features": d.get("common_features", "")
                                })
                        import io
                        edge_df = pd.DataFrame(rows).sort_values(["score","common_count"], ascending=False)
                        st.dataframe(edge_df, use_container_width=True)
                        csv_buf = io.StringIO()
                        edge_df.to_csv(csv_buf, index=False)
                        st.download_button("エッジCSVをダウンロード", data=csv_buf.getvalue(), file_name="edges.csv", mime="text/csv")

    except Exception as e:
        st.error(f"エラーが発生しました:{e}")

