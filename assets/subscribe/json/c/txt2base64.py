import os
import base64

target_dir = "."
txt_files = [f for f in os.listdir(target_dir) if f.lower().endswith(".txt")]
if not txt_files:
    print("❌ 未找到任何.txt文件，请先放入txt文件到该文件夹")
    exit(1)

for filename in txt_files:
    try:
        with open(filename, "rb") as f:
            content = f.read().decode("utf-8", errors="replace")
        base64_str = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        output_file = f"{os.path.splitext(filename)[0]}_base64.txt"
        with open(output_file, "w", encoding="utf-8") as out_f:
            out_f.write(base64_str)
        print(f"✅ 成功：{filename} → {output_file}")
    except Exception as e:
        print(f"❌ 失败：{filename} 错误：{str(e)}")

print("\n🎉 全部处理完成！")
