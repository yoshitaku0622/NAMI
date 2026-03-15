import os
import base64
import json
from flask import Flask, request, jsonify, render_template
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """あなたはインテリアコーディネーターであり、引越しの家具提案の専門家です。
ユーザーがアップロードした間取り図（フロアプラン）の画像を分析し、各部屋に最適な家具の配置を提案してください。

以下のルールに従ってください：

1. **間取り図の分析**: 部屋の数、サイズ、用途（リビング、寝室、キッチンなど）を特定してください。
2. **家具の提案**: 各部屋に対して、具体的な家具を提案してください。
3. **実在する商品**: 提案する家具は、実際にオンラインで購入可能な商品にしてください。以下のブランド・ショップから選んでください：
   - 日本: IKEA Japan, ニトリ, 無印良品, LOWYA, ACTUS, unico, journal standard Furniture
   - 韓国: HANSSEM (ハンセム), iloom (イルム), Cuckoo (クック), Daily Like, JAJU, Casamia
   - その他海外: IKEA, Hay, Muji, Francfranc, Zara Home, H&M Home
4. **配置の説明**: 各家具をどこに配置すべきか、具体的に説明してください（例：「北側の壁沿いに」「窓の横に」など）。
5. **サイズの考慮**: 間取り図から推測される部屋のサイズに合った家具を選んでください。
6. **予算帯**: 各家具の概算価格も記載してください。
7. **商品検索のヒント**: 各家具について、その商品を見つけるための検索キーワードやブランド名・商品名を具体的に記載してください。

回答は必ず以下のJSON形式のみで返してください（JSON以外のテキストは含めないでください）:
{
  "overview": "間取り全体の分析と概要",
  "rooms": [
    {
      "name": "部屋名",
      "size_estimate": "推定サイズ",
      "furniture": [
        {
          "item": "家具の種類",
          "product_name": "具体的な商品名",
          "brand": "ブランド名",
          "size": "サイズ",
          "price_range": "価格帯",
          "placement": "配置場所の説明",
          "reason": "この家具を選んだ理由",
          "search_keyword": "検索キーワード"
        }
      ]
    }
  ],
  "total_budget_estimate": "合計予算の目安",
  "tips": ["インテリアのコツやアドバイス"]
}"""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "画像ファイルが必要です"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "ファイルが選択されていません"}), 400

    image_data = file.read()
    base64_image = base64.b64encode(image_data).decode("utf-8")

    mime_type = file.content_type or "image/png"

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": base64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": "この間取り図を分析して、各部屋に最適な家具の配置を提案してください。実際に購入可能な商品名とブランドを含めてください。日本のブランドだけでなく、韓国のHANSSEMやiloomなど海外ブランドも積極的に提案してください。JSON形式のみで回答してください。",
                        },
                    ],
                },
            ],
        )

        result_text = response.content[0].text

        # JSONブロックが```json ... ```で囲まれている場合に抽出
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        # JSONとしてパースできるか検証
        json.loads(result_text)

        return jsonify({"success": True, "data": result_text})

    except json.JSONDecodeError:
        return jsonify({"success": True, "data": result_text})
    except anthropic.APIError as e:
        return jsonify({"error": f"API エラー: {e.message}"}), 500
    except Exception as e:
        return jsonify({"error": f"分析中にエラーが発生しました: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
