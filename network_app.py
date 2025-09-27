
import unicodedata, re, io, itertools, json
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st

# --------------------------------------------------------
# 固定ファイル名（JSON）
#  - ブラウザからのファイル指定はせず、同ディレクトリのJSONを読む。
#  - out_network.json は [{ "Name": "...", "Features": ["...", ...] }, ...] を想定。
#  - outに関しては、ネットワーク図ではout.jsonではなく、out_network.jsonを参照する点に注意。（out_betwork.jsonの方が繋がり計算に適した言語区切り採用）
# --------------------------------------------------------

# ========== Constants (fixed filenames; no sidebar file pickers) ==========
OUT_NETWORK_JSON = "out_network.json"  # [{"Name": "...", "Features": ["...", ...]}, ...]
CITY_TO_PREF_JSON = "geo_city_to_pref.json"          # [{"city":"名古屋","pref":"愛知県"}, ...] or {"名古屋":"愛知県",...}
PREF_ALIASES_JSON  = "geo_pref_aliases.json"         # [{"alias":"愛知","pref":"愛知県"}, ...] or {"愛知":"愛知県",...}
PREF_TO_REGION_JSON = "geo_pref_to_region.json"      # [{"pref":"愛知県","region":"東海"}, ...] or {"愛知県":"東海",...}
TOKEN_CATEGORY_JSON = "token_category.json"          # [{"token":"温泉","category":"hobby","subcategory1":"spa_sauna","subcategory2":"other"}, ...]
CANONICAL_MAP_JSON  = "canonical_map.json"           # {"温泉♨️":"温泉","onsen":"温泉",...}
STOPWORDS_JSON      = "stopwords.json"               # ["旅行","学び",...]

# Optional (if present)
SUBCAT_WEIGHTS_JSON = "subcategory_weights.json"     # [{"category":"hobby","subcategory1":"sports","subcategory2":"running","weight":1.4}, ...]
                                                     # or { "(cat,sub1,sub2)": weight } not recommended

# ===================== 基本ウェイト ===================== 09/27まっと追加
CATEGORY_WEIGHTS = {"geo":2, "role":2, "industry":2, "hobby":1, "education":1, "age":1, "other":1}
GEO_LEVEL_WEIGHTS= {"city":3, "pref":2, "region":1}


# --------------------------------------------------------
# ユーティリティ
#  - normalize_key: 表記ゆれ対策（NFKC→trim→空白除去→lower）
#  - load_json_any: JSONを読み込む薄いラッパ
#  - load_kv_from_json: {"key":"value"} or [{"key":..,"value":..}] → dict 正規化
#  - load_list_from_json: ["a","b"] などの配列JSON→正規化済みリスト
#  - load_token_category_json: token→(category, sub1, sub2) に正規化
#  - load_subcat_weights_json: (cat,sub1,sub2) → weight（ワイルドカード対応）
# --------------------------------------------------------

# ========== Normalizer（正規化ユーティリティ）========== 09/27まっと修正
def normalize_key(s: str) -> str:
    if s is None: return ""
    t = unicodedata.normalize("NFKC", str(s)).strip().lower()
    return re.sub(r"\s+", "", t)

# ========== JSON loaders ==========
def load_json_any(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _pair_list_to_dict(obj):
    """[['a','b'], ['c','d']] → {'a':'b','c':'d'}（守備範囲を広げる）"""
    out = {}
    for it in obj:
        if isinstance(it, (list, tuple)) and len(it) >= 2:
            k = normalize_key(it[0]); v = str(it[1])
            if k: out[k] = v
    return out

def load_kv_from_json(path: str, key_field: str, val_field: str):
    """key/value の JSON を辞書化（辞書・配列どちらにも対応）"""
    obj = load_json_any(path)
    if isinstance(obj, dict):
        return {normalize_key(k): str(v) for k, v in obj.items()}
    if isinstance(obj, list):
        out = {}
        for r in obj:
            if isinstance(r, dict):
                k = normalize_key(r.get(key_field, ""))
                v = str(r.get(val_field, ""))
                if k: out[k] = v
        if out: return out
        return _pair_list_to_dict(obj)
    return {}

def load_stopwords(path: str):
    obj = load_json_any(path)
    if isinstance(obj, list):
        acc = set()
        for x in obj:
            if isinstance(x, (list, tuple)) and len(x) >= 1:
                acc.add(normalize_key(x[0]))
            else:
                acc.add(normalize_key(x))
        return {w for w in acc if w}
    if isinstance(obj, dict):
        return {normalize_key(k) for k in obj.keys() if str(k).strip()}
    return set()

def load_token_category_json(path: str):
    """
    token_category.json → token -> (category, sub1, sub2)
    入力は {token:{...}} 形式 or レコード配列のどちらでも可
    """
    obj = load_json_any(path)
    out = {}
    if isinstance(obj, dict):
        for tok, v in obj.items():
            tok_n = normalize_key(tok)
            if not tok_n: continue
            if isinstance(v, dict):
                cat  = str(v.get("category", "other") or "other")
                sub1 = str(v.get("subcategory1", v.get("subcategory", "other")) or "other")
                sub2 = str(v.get("subcategory2", "other") or "other")
            elif isinstance(v, (list, tuple)):
                cat  = str(v[0]) if len(v)>0 else "other"
                sub1 = str(v[1]) if len(v)>1 else "other"
                sub2 = str(v[2]) if len(v)>2 else "other"
            else:
                cat, sub1, sub2 = str(v), "other", "other"
            out[tok_n] = (cat, sub1, sub2)
        return out
    if isinstance(obj, list):
        for r in obj:
            if isinstance(r, dict):
                tok = normalize_key(r.get("token",""))
                if not tok: continue
                cat  = str(r.get("category","other") or "other")
                sub1 = str(r.get("subcategory1", r.get("subcategory","other")) or "other")
                sub2 = str(r.get("subcategory2","other") or "other")
                out[tok] = (cat, sub1, sub2)
            elif isinstance(r, (list, tuple)):
                tok = normalize_key(r[0]) if len(r)>0 else ""
                if not tok: continue
                cat  = str(r[1]) if len(r)>1 else "other"
                sub1 = str(r[2]) if len(r)>2 else "other"
                sub2 = str(r[3]) if len(r)>3 else "other"
                out[tok] = (cat, sub1, sub2)
        return out
    return out

def load_subcat_weights_json(path: str):
    if not os.path.exists(path): return {}
    obj = load_json_any(path)
    out = {}
    if isinstance(obj, dict):
        # {"(cat,sub1,sub2)": weight} / {"cat,sub1,sub2": weight}
        for k, v in obj.items():
            try:
                kk = k.strip().strip("()")
                t = [x.strip() for x in kk.split(",")]
                cat  = t[0] if len(t)>0 else "*"
                sub1 = t[1] if len(t)>1 else "*"
                sub2 = t[2] if len(t)>2 else "*"
                out[(cat, sub1, sub2)] = float(v)
            except Exception:
                continue
        return out
    if isinstance(obj, list):
        for r in obj:
            if isinstance(r, dict):
                cat  = str(r.get("category", "other") or "other")
                sub1 = str(r.get("subcategory1", "*") or "*")
                sub2 = str(r.get("subcategory2", "*") or "*")
                try:
                    w = float(r.get("weight", 1.0))
                except Exception:
                    w = 1.0
                out[(cat, sub1, sub2)] = w
            elif isinstance(r, (list, tuple)):
                cat  = str(r[0]) if len(r)>0 else "other"
                sub1 = str(r[1]) if len(r)>1 else "*"
                sub2 = str(r[2]) if len(r)>2 else "*"
                try:
                    w = float(r[3]) if len(r)>3 else 1.0
                except Exception:
                    w = 1.0
                out[(cat, sub1, sub2)] = w
        return out
    return {}


# --------------------------------------------------------
# 地理・正規化関連
#  - build_geo_dicts_from_json: 市→県、別名→正規県、県→地域 を辞書化
#  - canonicalize_token: 同義語寄せ（canonical_map で正規名へ）
#  - geo_canonicalize: トークンが市/県/地方かを判定し正規名へ寄せる
#  - geo_expand_tokens: geo:city/geo:pref/geo:region の階層トークンに展開
#  - CATEGORY_WEIGHTS/GEO_LEVEL_WEIGHTS: 基本カテゴリと地理階層の重み
# --------------------------------------------------------

# ========== 地理辞書（JSON）==========
def build_geo_dicts_from_json(city_to_pref_path: str, pref_aliases_path: str, pref_to_region_path: str):
    CITY_TO_PREF = load_kv_from_json(city_to_pref_path, "city", "pref")
    PREF_ALIASES = load_kv_from_json(pref_aliases_path, "alias", "pref")
    PREF_TO_REGION = load_kv_from_json(pref_to_region_path, "pref", "region")
    REGION_SET = {normalize_key(v) for v in PREF_TO_REGION.values()}
    return CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET

# ===================== 同義語マップ（JSON） =====================
def load_canonical_map(path: str):
    obj = load_json_any(path)
    if isinstance(obj, dict):
        return {normalize_key(k): str(v) for k, v in obj.items()}
    if isinstance(obj, list):
        out = {}
        for r in obj:
            if isinstance(r, dict):
                k = normalize_key(r.get("key","")); v = str(r.get("value",""))
                if k: out[k] = v
            elif isinstance(r, (list, tuple)) and len(r) >= 2:
                k = normalize_key(r[0]); v = str(r[1])
                if k: out[k] = v
        return out
    return {}

# ===================== トークン正規化 & 地理展開 =====================
def canonicalize_token(tok_norm: str, CANONICAL_MAP: dict) -> str:
    return CANONICAL_MAP.get(tok_norm, tok_norm)

def is_prefecture(tok_norm: str, PREF_ALIASES: dict) -> bool:
    return tok_norm.endswith(("県","都","府","道")) or tok_norm in PREF_ALIASES

def geo_canonicalize(tok_norm: str, CITY_TO_PREF: dict, PREF_ALIASES: dict, PREF_TO_REGION: dict, REGION_SET: set):
    city = pref = region = None
    if tok_norm in CITY_TO_PREF:
        city = tok_norm
        pref_disp = CITY_TO_PREF[tok_norm]
        region_disp = PREF_TO_REGION.get(normalize_key(pref_disp), "")
        return (city, pref_disp, region_disp)
    if is_prefecture(tok_norm, PREF_ALIASES):
        pref_disp = PREF_ALIASES.get(tok_norm, tok_norm)
        region_disp = PREF_TO_REGION.get(normalize_key(pref_disp), "")
        return (None, pref_disp, region_disp)
    if tok_norm in REGION_SET:
        # 地方名（region）が直接入っていたケース
        for v in set(PREF_TO_REGION.values()):
            if normalize_key(v)==tok_norm:
                return (None, None, v)
    return (None, None, None)

def geo_expand_tokens(tok_norm: str, CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET):
    city, pref, region = geo_canonicalize(tok_norm, CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET)
    out = set()
    if city:   out.add(f"geo:city:{city}")
    if pref:   out.add(f"geo:pref:{pref}")
    if region: out.add(f"geo:region:{region}")
    return out



# --------------------------------------------------------
# 特徴解析（parse_features）
#  - raw（配列 or カンマ区切り文字列）からトークン集合を生成
#  - 地理は階層トークン geo:* に展開
#  - 非地理トークンには、カテゴリ辞書から (category, sub1, sub2) を取得
#    ・“ゆるいつながり”用の合成トークンを付与:
#       link:sub1:<name>, link:sub2:<name>
#    ・重みはサイドバーのスライダで調整
# --------------------------------------------------------

def parse_features(raw, CANONICAL_MAP, STOPWORDS,
                   CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET,
                   token_category,
                   enable_link_sub1: bool, enable_link_sub2: bool) -> set[str]:
    if raw is None: return set()
    # raw can be list or string
    items = raw if isinstance(raw, list) else [x for x in str(raw).split(",")]
    toks = set()
    for x in items:
        if not str(x).strip(): continue
        norm = normalize_key(x)
        canon = canonicalize_token(norm, CANONICAL_MAP)
        if not canon or normalize_key(canon) in STOPWORDS: continue
        c, p, r = geo_canonicalize(normalize_key(canon), CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET)
        if c or p or r:
            toks |= geo_expand_tokens(normalize_key(canon), CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET)
        else:
            tok = normalize_key(canon)
            toks.add(tok)
            cat, sub1, sub2 = token_category.get(tok, ("other","other","other"))
            if enable_link_sub1 and sub1 and sub1 != "other":
                toks.add(f"link:sub1:{sub1}")
            if enable_link_sub2 and sub2 and sub2 != "other":
                toks.add(f"link:sub2:{sub2}")
    return toks



# --------------------------------------------------------
# 重み計算
#  - geo:* は CATEGORY_WEIGHTS['geo'] × (city=3, pref=2, region=1)
#  - link:sub1/sub2 はそれぞれのリンク重みを直接足し込む
#  - 通常トークンは base×mul:
#      base = CATEGORY_WEIGHTS[category]
#      mul  = (cat,sub1,sub2) に対する重み（ワイルドカード含む最適一致）
# --------------------------------------------------------

def lookup_hier_weight(cat: str, sub1: str, sub2: str, weights: dict) -> float:
    for k in [(cat, sub1, sub2), (cat, sub1, "*"), (cat, "*", sub2), (cat, "*", "*")]:
        if k in weights: return weights[k]
    return 1.0

def token_weight(tok: str,
                 token_category: dict,
                 subcat_weights: dict,
                 link_sub1_weight: float,
                 link_sub2_weight: float) -> float:
    if tok.startswith("geo:"):
        try:
            _, level, _ = tok.split(":", 2)
        except ValueError:
            return CATEGORY_WEIGHTS.get("geo",1)
        return CATEGORY_WEIGHTS.get("geo",1) * GEO_LEVEL_WEIGHTS.get(level,1)
    if tok.startswith("link:sub1:"): return float(link_sub1_weight)
    if tok.startswith("link:sub2:"): return float(link_sub2_weight)
    cat, sub1, sub2 = token_category.get(tok, ("other","other","other"))
    base = CATEGORY_WEIGHTS.get(cat, 1)
    mul  = lookup_hier_weight(cat, sub1, sub2, subcat_weights)
    return base * mul


# --------------------------------------------------------
# スコア計算・グラフ構築
#  - 2人の特徴集合の共通部分を取り、各トークン重みを合計＝エッジ重み
#  - 共通トークンはツールチップ用に可読文字列へ整形して保存
#  - グラフは NetworkX で構築（ノードに label=name を付与）
# --------------------------------------------------------

def pair_score_and_common(f1: set, f2: set, token_category: dict, subcat_weights: dict,
                          link_sub1_weight: float, link_sub2_weight: float):
    common = sorted(list(f1 & f2))
    score = sum(token_weight(t, token_category, subcat_weights, link_sub1_weight, link_sub2_weight) for t in common)
    return score, common

# ===================== グラフ構築（JSON レコード） =====================
def build_graph(data_records: list, min_edge_score: float,
                token_category: dict, subcat_weights: dict, CANONICAL_MAP: dict, STOPWORDS: set,
                CITY_TO_PREF: dict, PREF_ALIASES: dict, PREF_TO_REGION: dict, REGION_SET: set,
                subset=None,
                enable_link_sub1=True, enable_link_sub2=True,
                link_sub1_weight=0.6, link_sub2_weight=0.6,):
    """data_records は JSON の配列（list[dict]）を想定"""
    if subcat_weights is None: subcat_weights = {}
    people = []
    for r in data_records:
        name = str(r.get("Name","")).strip()
        if not name: continue
        if subset and name not in subset: continue
        feats = parse_features(
            r.get("Features"), CANONICAL_MAP, STOPWORDS,
            CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET,
            token_category,enable_link_sub1, enable_link_sub2
        )
        people.append((name, feats))

    G = nx.Graph()
    for name, feats in people:
        G.add_node(name, size=len(feats), label=name)

    for (n1, f1), (n2, f2) in itertools.combinations(people, 2):
        score, common = pair_score_and_common(f1, f2, token_category, subcat_weights, link_sub1_weight, link_sub2_weight)
        if score >= min_edge_score and len(common) > 0:
            def pretty(t):
                if t.startswith("geo:city:")  : return t.split(":",2)[2]
                if t.startswith("geo:pref:")  : return t.split(":",2)[2]
                if t.startswith("geo:region:"): return t.split(":",2)[2]
                if t.startswith("link:sub1:"): return f"sub1:{t.split(':',2)[2]}"
                if t.startswith("link:sub2:"): return f"sub2:{t.split(':',2)[2]}"
                return t
            G.add_edge(n1, n2,
                       weight=score,
                       common_features="、".join(pretty(t) for t in common),
                       common_count=len(common))
    return G



# --------------------------------------------------------
# PyVis描画（show_pyvis）
#  - ノード名を常時表示（font/scaling設定）
#  - set_options は JSON 文字列のみ受け付けるため、json.dumps で渡す
#  - エッジのタイトルにスコア＆共通特徴を表示
# --------------------------------------------------------

def show_pyvis(G, height_px=800, label_font_size=16):
    net = Network(height=f"{height_px}px", width="100%", notebook=False, directed=False)
    net.barnes_hut()
    options = {
      "nodes": {
        "shape": "dot",
        "size": 12,
        "font": {"size": int(label_font_size), "face": "Arial", "vadjust": 0},
        "scaling": {"min": 10, "max": 40, "label": {"enabled": True, "min": 8, "max": 30}}
      },
      "edges": {"smooth": {"type": "continuous"}},
      "physics": {"solver": "barnesHut", "stabilization": {"iterations": 200}},
      "interaction": {"hover": True, "tooltipDelay": 100}
    }
    net.set_options(json.dumps(options, ensure_ascii=False))
    for n, data in G.nodes(data=True):
        label = data.get("label", n); title = f"{label}<br>特徴数: {data.get('size',0)}"
        net.add_node(n, label=label, title=title)
    for u, v, d in G.edges(data=True):
        title = f"スコア: {d.get('weight',0)}<br>共通: {d.get('common_features','')}"
        net.add_edge(u, v, value=d.get("weight",1), title=title)
    html = net.generate_html()
    st.components.v1.html(html, height=height_px, scrolling=True)



# --------------------------------------------------------
# render_network_app（今回のレイアウト要件）
#  - サイドバー：表示パラメータのみ
#  - メイン：タイトル → 表示する人セレクタ → ネットワーク図 → エッジ一覧＋CSV
#  - 外部辞書は固定ファイル名のJSONから読み込み
# --------------------------------------------------------

def render_network_app():
    try:
        st.set_page_config(page_title="相関図", layout="wide")
    except Exception:
        pass

    st.title("相関図")

    # ---- Load all JSONs (fixed filenames) ----
    data_records = load_json_any(OUT_NETWORK_JSON)
    CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET = build_geo_dicts_from_json(
        CITY_TO_PREF_JSON, PREF_ALIASES_JSON, PREF_TO_REGION_JSON)
    TOKEN_CATEGORY = load_token_category_json(TOKEN_CATEGORY_JSON)
    CANONICAL_MAP  = load_canonical_map(CANONICAL_MAP_JSON)
    STOPWORDS      = load_stopwords(STOPWORDS_JSON)
    SUBCAT_WEIGHTS = load_subcat_weights_json(SUBCAT_WEIGHTS_JSON)  # optional; empty if not found

    # ---- UI: only parameters (file pickers removed) ----
    st.sidebar.header("表示パラメータ")
    min_edge_score = st.sidebar.slider("エッジ採用しきい値（合計スコア）", 0.0, 20.0, 2.0, 0.5)
    graph_height   = st.sidebar.number_input("グラフ高さ(px)", min_value=400, max_value=1600, value=800, step=50)
    label_font_size = st.sidebar.number_input("ラベル文字サイズ", min_value=8, max_value=30, value=16, step=1)
    st.sidebar.divider()
    enable_link_sub1 = st.sidebar.checkbox("subcategory1一致で“ゆるいつながり”を作る", value=True)
    enable_link_sub2 = st.sidebar.checkbox("subcategory2一致で“ゆるいつながり”を作る", value=True)
    link_sub1_weight = st.sidebar.slider("sub1リンクの重み", 0.0, 5.0, 0.6, 0.1)
    link_sub2_weight = st.sidebar.slider("sub2リンクの重み", 0.0, 5.0, 0.6, 0.1)

    # ---- Subset selector ----
    all_names = sorted(set(str(r.get("Name","")).strip() for r in data_records if str(r.get("Name","")).strip()))
    with st.expander("表示する人を選択（未選択なら全員）", expanded=False):
        selected = st.multiselect("表示する人", options=all_names, default=[])
    subset = selected if selected else None

    # ---- Build graph ----
    G = build_graph(data_records, min_edge_score, TOKEN_CATEGORY, SUBCAT_WEIGHTS, CANONICAL_MAP, STOPWORDS,
                    CITY_TO_PREF, PREF_ALIASES, PREF_TO_REGION, REGION_SET,
                    subset=subset,
                    # 以下は UI を用意している場合のみ
                    enable_link_sub1=enable_link_sub1, enable_link_sub2=enable_link_sub2,
                    link_sub1_weight=link_sub1_weight, link_sub2_weight=link_sub2_weight)

    col1, col2 = st.columns([3,2], gap="large")
    with col1:
        st.subheader("ネットワーク図")
        show_pyvis(G, height_px=graph_height, label_font_size=label_font_size)

    with col2:
        st.subheader("エッジ一覧（重い順）")
        if G.number_of_edges() == 0:
            st.info("エッジがありません。しきい値や辞書を調整してください。")
        else:
            rows = []
            for u, v, d in G.edges(data=True):
                rows.append({"A": u, "B": v, "score": d.get("weight",0),
                             "common_count": d.get("common_count",0),
                             "common_features": d.get("common_features","")})
            edge_df = pd.DataFrame(rows).sort_values(["score","common_count"], ascending=False)
            st.dataframe(edge_df, use_container_width=True)
            csv_buf = io.StringIO()
            edge_df.to_csv(csv_buf, index=False)
            st.download_button("エッジCSVをダウンロード", data=csv_buf.getvalue(), file_name="edges.csv", mime="text/csv")

if __name__ == "__main__":
    render_network_app()