import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict
#from deep_translator import GoogleTranslator
from geminiAPI import translate_text
import colorsys

# 建立翻譯器
#translator = GoogleTranslator(source='auto', target='zh-TW')
translator = translate_text
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def remove_text(image_path, output_path):
    # 讀取圖片
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("無法讀取圖片")
    
    # 設定預設的lightdeck值
    lightdeck = 128  # 預設值設為中間值
    
    # 轉換為PIL Image以使用Tesseract (只需轉換一次)
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    # 使用Tesseract獲取所有文字區域，修改配置以包含更多字符
    data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT, lang='eng+chi_tra', config='--oem 3 --psm 6 -c tessedit_char_blacklist="●▲■□"')
    # 創建遮罩 (只需一次)
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    # 標記所有文字區域並打印偵測到的文字
    print("\n---進行遍歷資訊---")
    # 先收集所有文字和位置信息
    lines = defaultdict(lambda: {"texts": [], "positions": [], "confs": [], "color": None})
    
    # 第一次遍歷：收集文字和位置信息
    i = 0
    while i < len(data['text']):
        text = str(data['text'][i]).strip()
        if text and int(data['conf'][i]) > 10:  # 只收集非空且信心度大於10的文字
            # 檢查文字是否有效
            is_valid_text = True
            if data['width'][i] < 20:  # 寬度太小可能是 ICON
                is_valid_text = False
            # 檢查是否為單個英文字母或兩個以上的英文字母
            if text.isascii():  # 如果是英文
                if len(text) >= 2 and 'a' in text.lower():
                    is_valid_text = True

            if text and is_valid_text:
                # 初始化當前行資訊
                current_line = {
                    'text': [text],
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'conf': [data['conf'][i]]
                }

                # 尋找同一行的其他文字
                next_idx = i + 1
                while next_idx < len(data['text']):
                    if int(data['conf'][next_idx]) > 10:    # 只收集信心度大於10的文字
                        next_text = data['text'][next_idx].strip()
                        if next_text:
                            # 計算間距
                            vertical_diff = abs(data['top'][next_idx] - current_line['y'])
                            horizontal_gap = data['left'][next_idx] - (current_line['x'] + current_line['width'])
                            
                            # 判斷是否屬於同一行
                            VERTICAL_THRESHOLD = 1    # 垂直差異閾值
                            HORIZONTAL_THRESHOLD = .8 # 水平間距閾值
                            
                            if (vertical_diff < current_line['height'] * VERTICAL_THRESHOLD and
                                horizontal_gap < current_line['height'] * HORIZONTAL_THRESHOLD and
                                horizontal_gap >= 0):  # 確保文字由左到右排列
                                
                                # 更新當前行資訊
                                current_line['text'].append(next_text)
                                current_line['width'] = (data['left'][next_idx] + data['width'][next_idx]) - current_line['x']
                                current_line['height'] = max(current_line['height'], data['height'][next_idx])
                                current_line['conf'].append(data['conf'][next_idx])
                                next_idx += 1
                                continue
                    break

                # 將當前行加入到 lines 中
                line_num = len(lines)
                lines[line_num]["texts"] = current_line['text']
                lines[line_num]["positions"].append({
                    'x': current_line['x'],
                    'y': current_line['y'],
                    'w': current_line['width'],
                    'h': current_line['height']
                })
                lines[line_num]["confs"] = current_line['conf']
                i = next_idx
                continue
        i += 1

    # 第二次遍歷：處理每一行文字
    texts_to_translate = []  # 儲存所有需要翻譯的文字
    line_info = {}  # 儲存每行的相關資訊

    for line_num in sorted(lines.keys()):
        if lines[line_num]["texts"]:
            positions = lines[line_num]["positions"]
            current_x = min(pos['x'] for pos in positions)
            current_y = min(pos['y'] for pos in positions)
            total_width = max(pos['x'] + pos['w'] for pos in positions) - current_x
            max_height = max(pos['h'] for pos in positions)
            
            # 取得文字區域
            text_area = img[current_y:current_y+max_height, current_x:current_x+total_width]

            # 將圖片轉換為灰度圖
            img_gray = cv2.cvtColor(text_area, cv2.COLOR_BGR2GRAY)
            
            # 使用 OTSU 自適應二值化
            _, binary = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 獲取邊緣3像素的背景區域
            h, w = binary.shape
            edge_mask = np.zeros_like(binary)
            edge_mask[0:3, :] = 1  # 上邊緣
            edge_mask[h-3:h, :] = 1  # 下邊緣
            edge_mask[:, 0:3] = 1  # 左邊緣
            edge_mask[:, w-3:w] = 1  # 右邊緣
            
            # 計算背景區域的平均灰度
            lightdeck = np.mean(img_gray[edge_mask == 1])
            
            # 根據背景灰度決定文字遮罩
            if lightdeck < 145:
                text_mask = (binary == 255)  # 深底淺字
            else:
                text_mask = (binary == 0)    # 淺底深字
            
            # 從原始圖片中獲取顏色
            img_rgb = cv2.cvtColor(text_area, cv2.COLOR_BGR2RGB)
            
            # 使用遮罩只取得文字區域的顏色
            if np.any(text_mask):
                # 獲取文字區域的所有顏色像素
                text_colors = img_rgb[text_mask]
                
                # 將RGB值組合成唯一的數字以找出最常見的顏色組合
                text_colors = text_colors.astype(np.int32)  # 確保類型為 int32
                color_codes = text_colors[:, 0] * 65536 + text_colors[:, 1] * 256 + text_colors[:, 2]
                most_common_code = np.bincount(color_codes).argmax()
                
                # 將最常見的顏色代碼轉回RGB
                r = most_common_code // 65536
                g = (most_common_code % 65536) // 256
                b = most_common_code % 256
                text_color = (int(r), int(g), int(b))
                
                text_color = color_up(text_color, 1.6, 1.2, (20,200)) #增加飽和度(60%) 明暗(20%) 色階()
                if lightdeck > 175: #lightdeck偏亮時 文字自動變深
                    text_color = color_up(text_color, 0.7, 0.7, (160,255)) #增加飽和度(-30%) 明暗(-30%)色階()
            else:
                text_color = (0, 0, 0)  # 預設黑色
            
            # 儲存顏色信息
            lines[line_num]["color"] = text_color
            
            # 儲存當前行的資訊
            current_line = ' '.join(lines[line_num]["texts"])
            texts_to_translate.append(current_line)
            
            line_info[line_num] = {
                'original_text': current_line,
                'confidence': sum(lines[line_num]['confs']) / len(lines[line_num]['confs']),
                'lightdeck': lightdeck,
                'text_color': text_color,
                'positions': positions
            }

    # 一次性翻譯所有文字
    SEPARATOR = "◆★◆"  # 使用更不常見的分隔符
    combined_text = SEPARATOR.join(texts_to_translate)
    translated_combined = translator(combined_text, "繁體中文")
    translated_texts = [text.strip() for text in translated_combined.split(SEPARATOR)] if translated_combined else texts_to_translate

    # 印出所有資訊
    print("\n偵測到的文字：")
    print("-" * 50)
    
    for line_num, translated_text in zip(sorted(line_info.keys()), translated_texts):
        info = line_info[line_num]
        print(f"原文({line_num}): {info['original_text']}")
        print(f"翻譯({line_num}): {translated_text}")
        print(f"信心度: {info['confidence']:.1f}%")
        print(f"背景明暗度: {info['lightdeck']:.0f}")
        print(f"文字顏色: {info['text_color']}")
        for i, pos in enumerate(info['positions']):# 顯示文字區域位置
            print(f"文字區域: x={pos['x']}, y={pos['y']}, 寬={pos['w']}, 高={pos['h']}")
        print("-" * 50)

    # **手動查看填充區域**
    #img[np.where(mask == 255)] = (0, 255, 0)  # 用綠色填補
    #result = img
    # 先進行塗銷處理
    # result = cv2.inpaint(img, mask, 21, cv2.INPAINT_TELEA)  # 註釋掉原本的inpaint處理
    
    # 使用遮罩直接填充背景色
    result = img.copy()
    
    # 1. 批量處理所有文字區域
    all_masks = np.zeros_like(img)
    for line_num in sorted(lines.keys()):
        if lines[line_num]["texts"]:
            for pos in lines[line_num]["positions"]:
                x = max(0, pos['x'] - 10)
                y = max(0, pos['y'] - 10)
                w = pos['w'] + 15
                h = pos['h'] + 10
                
                # 創建當前區域的遮罩
                current_mask = np.zeros_like(img[:,:,0])
                current_mask[y:y+h, x:x+w] = 1
                
                # 獲取邊緣
                kernel = np.ones((3,3), np.uint8)
                edge_mask = cv2.dilate(current_mask, kernel) - current_mask
                
                # 獲取邊緣顏色的平均值
                edge_color = cv2.mean(img, mask=edge_mask)[:3]
                
                # 填充區域
                all_masks[y:y+h, x:x+w] = edge_color

    # 2. 一次性應用所有遮罩
    mask_bool = (all_masks != [0,0,0]).any(axis=2)
    result[mask_bool] = all_masks[mask_bool]

    # 3. 優化文字繪製
    pil_result = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB)) 
    draw = ImageDraw.Draw(pil_result) 
    
    # 預先載入字體
    try:
        default_font = ImageFont.truetype("msjh.ttc", 100)  # 載入一個基礎大小
    except:
        try:
            default_font = ImageFont.truetype("NotoSansCJK-Regular.ttc", 100)
        except:
            default_font = ImageFont.truetype("Arial.ttf", 100)

    def is_sentence(text):
        # 判斷是否為句子的規則
        # 1. 檢查是否以標點符號結尾
        sentence_endings = ['。', '！', '？', '…', '.', '!', '?', '...']
        if any(text.strip().endswith(end) for end in sentence_endings):
            return True
        # 2. 檢查字數是否大於特定長度（假設超過5個字可能是句子）
        if len(text.strip()) > 5:
            return True
        # 3. 檢查是否包含動詞或完整語意（這裡用簡單的方法：檢查是否包含常見的動詞詞尾）
        verb_endings = ['的', '了', '著', '過', '是', '有']
        if any(ending in text for ending in verb_endings):
            return True
        return False

    # 直接處理每一行文字
    for line_num in sorted(lines.keys()):
        if not lines[line_num]["texts"] or line_num >= len(translated_texts):
            continue
            
        positions = lines[line_num]["positions"]
        if not positions:
            continue
            
        try:
            # 獲取原始文字的位置信息
            x = positions[0]['x']
            y = positions[0]['y']
            total_width = sum(pos['w'] for pos in positions)
            max_height = max(pos['h'] for pos in positions)
            
            # 計算適當的字體大小
            translated_text = translated_texts[line_num]
            original_text = ' '.join(lines[line_num]["texts"])
            base_font_size = max(6,max_height*1.2)  # 使用原文高度作為基準調整(1.2)
            
            # 調整字體大小以適應原文寬度
            font = default_font.font_variant(size=base_font_size)
            bbox = draw.textbbox((0, 0), translated_text, font=font)
            text_width = bbox[2] - bbox[0]
            
            # 如果翻譯後的文字寬度超過原文寬度，進行縮放
            if text_width > total_width*1.15:
                scale_factor = total_width / text_width * 0.95  # 留一點邊距
                base_font_size = max(6,int(base_font_size * scale_factor)) #最小為6
                font = default_font.font_variant(size=base_font_size)
                bbox = draw.textbbox((0, 0), translated_text, font=font)
            
            # 計算文字的實際寬度和高度
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 判斷是否為句子
            is_sentence_text = is_sentence(original_text) or is_sentence(translated_text)
            
            # 根據是否為句子決定文字位置
            if is_sentence_text:
                # 句子靠左對齊，只需要考慮垂直置中
                text_x = x
                text_y = y + (max_height - text_height) // 2
            else:
                # 非句子水平垂直都置中
                text_x = x + (total_width - text_width) // 2
                text_y = y + (max_height - text_height) // 2
            
            # 繪製文字
            draw.text((text_x, text_y-5), translated_text, font=font, fill=lines[line_num]["color"])
            
        except Exception as e:
            print(f"警告：處理行 {line_num} 時出現錯誤: {str(e)}")
            continue

    # 將最終結果轉換回OpenCV格式並保存
    result_img = cv2.cvtColor(np.array(pil_result), cv2.COLOR_RGB2BGR)
    cv2.imwrite(output_path, result_img)
    # 在函數末尾修改返回值
    result_info = {
        'lines': lines,
        'lightdeck': lightdeck
    }
    
    return result_info

def color_up(rgb_color, RGB=1.0, light=1.0, levels=(0, 255)):
    # 確保輸入的 rgb_color 是列表或元組
    rgb_color = tuple(map(int, rgb_color))  # 將所有值轉換為整數
    
    # 轉換為 HSV 以調整飽和度
    r, g, b = np.array(rgb_color) / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b*.85)
    # 調整飽和度與明亮度
    s = np.clip(s * RGB, 0, 1) 
    v = np.clip(v * light, 0, 1) 
    # 轉回 RGB
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    # 轉換為 0~255 整數
    color_array = np.array([r, g, b]) * 255
    # 色階調整
    black_point, white_point = levels
    new_color = 255 * (color_array - black_point) / (white_point - black_point)
    new_color = np.clip(new_color, 0, 255).astype(int)   
    return tuple(new_color)

if __name__ == "__main__":
    input_path = "exp04.png"  # 請替換為你的輸入圖片路徑
    output_path = "exp00.png"  # 請替換為你想要的輸出圖片路徑
    
    try:
        result_info = remove_text(input_path, output_path)
        print("\n已成功翻譯，結果已保存至", output_path)
    except Exception as e:
        print("處理過程中發生錯誤:", str(e))