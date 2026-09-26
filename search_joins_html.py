import sys
import re
import json
import html

sys.stdout.reconfigure(encoding='utf-8')

with open("debug_joins.html", "r", encoding="utf-8") as f:
    text = f.read()

print("HTML Length:", len(text))

# Search for any group names the user mentioned from screenshot:
# "Cộng đồng bị nợ xấu tại VN"
# "Nghiện Nha Trang"
# "NhaTrangClub.vn"
# "HỘI VỠ NỢ"
test_names = ["Nha Trang", "nợ xấu", "Nghiện", "NhaTrangClub", "VỠ NỢ"]
for tn in test_names:
    found = tn.lower() in text.lower()
    print(f"Contains '{tn}': {found}")
    if found:
        # Find context around match
        idx = 0
        while True:
            idx = text.lower().find(tn.lower(), idx)
            if idx == -1:
                break
            print(f"  Match at {idx}:")
            print("   ", repr(text[max(0, idx-100):min(len(text), idx+200)]))
            idx += len(tn) + 50

