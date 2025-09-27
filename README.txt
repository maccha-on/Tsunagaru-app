README

##説明
このプログラムは、複数人のメンバーの自己紹介文と個人のwebページを読み込んで、
メンバー間どうしのつながりを見つけ、コミュニティ活性化を促進するためのアプリです。
Streamlitを使用します。

##操作方法
  1. DB.csvを置く
    DB-sample.csvを参考に、ニックネーム、自己紹介文、webページURLを記載した
    DB.csvファイルをカレントディレクトリに置いてください。
    このファイルには、本名や組織名などセンシティブな個人情報は含めないことを推奨します。

  2. .envにChat-GPTのAPIキーを保存
    OPENAI_API_KEY = sk-***
    と、個人のAPI keyを記載したファイル .env を同じディレクトリに置きます。
    streamlit cloudを使用する場合は、sectretsに

  3. data_extraction.pyを実行
　  "python data_extraction.py" を実行します。

    実行すると、各メンバーの特徴を抽出した結果を、 out.csv/out.jsonファイルに出力します。
    streamlit cloudを使用する場合は、sectretsの MEMBER_DATA_JSON 変数として、
    out.jsonの内容を手入力します。

  4. main.pyを実行
    "streamlit run main.py" を実行します。



