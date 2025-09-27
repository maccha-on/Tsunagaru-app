
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

# --- network_app から相関図表示に必要な関数・定数を最小限取り込み --- 25/09/27まっと
from network_app import (
    OUT_NETWORK_JSON,  # JSON版で定義されているパス 例: out_network.json
    CITY_TO_PREF_JSON, PREF_ALIASES_JSON, PREF_TO_REGION_JSON,
    TOKEN_CATEGORY_JSON, CANONICAL_MAP_JSON, STOPWORDS_JSON, SUBCAT_WEIGHTS_JSON,
    load_json_any, load_token_category_json, load_kv_from_json, load_stopwords, load_canonical_map, load_subcat_weights_json,
    build_geo_dicts_from_json, build_graph, show_pyvis
)


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
mode_1 = "仲間探し"
mode_2 = "特徴探し"
mode_3 = "繋がり線(Local実行専用)"
operation_mode_of = {mode_1,mode_2,mode_3}

# JSONデータを読み込み、メニューバーに反映
data_json = analyze.read_json()
names = data_json["Name"].dropna().unique().tolist()

#---------------------------------------------------
#  　　　CSSの読み込み（初期表示）　9/27追加　　　
#---------------------------------------------------
st.markdown(
    """
    <style>
    /* サイドバー全体 */
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
        background: FFF8F0;
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
    st.title("つながるアプリ")
    st.caption("仲間や繋がりを探そう！")
    # st.sidebar.write("どんな繋がりを見つける？")
    # st.sidebar.pills("選んでください。：",["共通点探し","特徴探し","その他"])
    operation_mode = st.selectbox("どんな繋がりを見つける？", options=operation_mode_of,index=0)
    #coice = st.sidebar.radio("選んでください。：",["共通点探し","特徴探し","その他"])

    #mode_1:共通点探しを選択した場合のサイドバー表示
    if operation_mode == mode_1:
        # st.write("あなたの仲間について教えて")
        # ニックネームを入力してもらう
        st.caption('あなたが調べるのは誰？')
        name = st.selectbox("選んでね", names)
        # st.sidebar.selectbox("選んでください。：",["AAA(固定値)","BBB","CCC"])

    #mode_2:特徴探しを選択した場合のサイドバー表示
    elif operation_mode == mode_2:
        # st.write("探したい特徴を入力して")
        # 特徴を入力してもらう
        st.caption('どんな特徴を調べる？')
        common_point = st.text_input("特徴や趣味を入力")
        #user_features = st.text_input("特徴を入力")

    #mode_3:相関図を選択した場合のサイドバー表示
    elif operation_mode == mode_3:
        st.caption('繋がりを線で描こう')
        st.header("表示パラメータ")
        min_edge_score = st.slider("エッジ採用しきい値（合計スコア）", 0.0, 20.0, 2.0, 0.5)
        graph_height   = st.number_input("グラフ高さ(px)", min_value=400, max_value=1600, value=800, step=50)
        label_font_size = st.number_input("ラベル文字サイズ", min_value=8, max_value=30, value=16, step=1)
        st.divider()
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
    st.image("img/top_image_2.png", width=300)



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

                </style>
                """,
                unsafe_allow_html=True
            )

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
            mode_3_flg = "Local"
            try:
               mode_3_flg = st.secrets[DEPLOY_ENV] 
            except Exception:
                print('相関図を描画します。')
            if mode_3_flg == "cloud":
                tab1 = st.tabs(["相関図"])
                st.write("クラウドでは未実装のため、ローカル環境で実行お願いします <(_ _)>")
            else:
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

                # ---------- サイドバーで選択を確定（再描画で消えないように） ----------
                all_names = sorted({str(r.get("Name","")).strip() for r in data_records if str(r.get("Name","")).strip()})
                with st.sidebar.form("network_filter_form", clear_on_submit=False):
                    st.header("表示パラメータ")
                    default_selected = st.session_state.get("subset_people", [])
                    selected_people = st.multiselect("表示する人（未選択なら全員）", options=all_names, default=default_selected)
                    submitted = st.form_submit_button("探そう")
                if submitted:
                    st.session_state["subset_people"] = selected_people if selected_people else None
                subset = st.session_state.get("subset_people", None)

                # ---------- グラフ構築 ----------
                G = build_graph(
                    data_records, min_edge_score,
                    TOKEN_CATEGORY, SUBCAT_WEIGHTS, CANONICAL_MAP, STOPWORDS,
                    CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET,
                    subset=subset,
                    enable_link_sub1=enable_link_sub1, enable_link_sub2=enable_link_sub2,
                    link_sub1_weight=link_sub1_weight, link_sub2_weight=link_sub2_weight
                )

                # ---------- レイアウト：図＋エッジ一覧 ----------
                col1, col2 = st.columns([3,2], gap="large")
                with col1:
                    st.subheader("ネットワーク図")
                    show_pyvis(G, height_px=int(graph_height), label_font_size=int(label_font_size))
                with col2:
                    st.subheader("エッジ一覧（重い順）")
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

