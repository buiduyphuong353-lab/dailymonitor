import json
from datetime import datetime, timedelta
import plotly.express as px
from IPython.display import display, Markdown

# ==========================================
# ⚙️ 1. CẤU HÌNH THÔNG SỐ
# ==========================================
FILE_TUOI = 'Lich nho giot.json' 
FILE_CHAM_PHAN = 'châm phân trung gian.json'

STT_CAN_TIM = "4" # Nhập STT bạn muốn phân tích

# Ngưỡng phân chia Giai đoạn
SO_NGAY_ON_DINH = 2
SAI_SO_EC_TT = 0.20
SAI_SO_EC_YC = 0.15
SAI_SO_TONG_PHUT = 10.0

# Ngưỡng lọc dữ liệu
GIAY_TUOI_TOI_THIEU = 20
GIAY_TUOI_TOI_DA = 3600
SO_NGAY_CHUYEN_VU = 2.0
SO_NGAY_TOI_THIEU = 7

# ==========================================
# 🧠 2. HÀM XỬ LÝ DỮ LIỆU CỐT LÕI
# ==========================================
def lay_ec_yeu_cau_tai_thoi_diem(tg_tuoi, lich_su_ec):
    ec_hien_tai = 0.0
    for record in lich_su_ec:
        if record['Thoi_gian'] <= tg_tuoi:
            ec_hien_tai = record['EC_YC']
        else:
            break
    return ec_hien_tai

def phan_tich_giai_doan_array(danh_sach_ngay, values, sai_so, so_ngay_on_dinh):
    stages = {}; gd_current = 1; goc_val = None; buffer = []
    
    for i, ngay in enumerate(danh_sach_ngay):
        val = values[i]
        if goc_val is None:
            goc_val = val
            stages[ngay] = gd_current
            continue
            
        if abs(val - goc_val) >= sai_so:
            buffer.append({'ngay': ngay, 'val': val})
            if len(buffer) >= so_ngay_on_dinh:
                buf_vals = [x['val'] for x in buffer]
                if max(buf_vals) - min(buf_vals) <= sai_so:
                    gd_current += 1
                    goc_val = sum(buf_vals) / len(buf_vals) 
                    for item in buffer:
                        stages[item['ngay']] = gd_current
                    buffer = []
                else:
                    oldest = buffer.pop(0)
                    stages[oldest['ngay']] = gd_current
        else:
            for item in buffer:
                stages[item['ngay']] = gd_current
            buffer = []
            stages[ngay] = gd_current
            
    for item in buffer:
        stages[item['ngay']] = gd_current
        
    return stages

def process_data(stt, so_ngay_on_dinh, ss_ec_tt, ss_ec_yc, ss_tong_phut, giay_min, giay_max, data_tuoi, data_cp):
    try:
        lich_su_ec_yc = []
        for item in data_cp:
            if str(item.get('STT')) == stt and item.get('Thời gian') and 'EC yêu cầu' in item:
                try:
                    tg = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                    ec_val = float(item.get('EC yêu cầu', 0)) / 100.0
                    lich_su_ec_yc.append({'Thoi_gian': tg, 'EC_YC': ec_val})
                except ValueError: pass
        lich_su_ec_yc.sort(key=lambda x: x['Thoi_gian'])

        du_lieu_da_loc = []
        for item in data_tuoi:
            if str(item.get('STT')) == stt and item.get('Thời gian'):
                tg_hien_tai = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                du_lieu_da_loc.append({
                    'Thời gian': tg_hien_tai,
                    'Trạng thái': str(item.get('Trạng thái', '')).strip(),
                    'EC_Yeu_Cau': lay_ec_yeu_cau_tai_thoi_diem(tg_hien_tai, lich_su_ec_yc),
                    'EC_Thuc_Te': float(item.get('TBEC', 0)) / 100.0,
                    'pH': float(item.get('TBPH', 0)) / 100.0
                })

        if not du_lieu_da_loc: return None, f"❌ Không có dữ liệu cho STT {stt}."
        du_lieu_da_loc.sort(key=lambda x: x['Thời gian'])

        danh_sach_mua_vu = []
        mua_hien_tai = [du_lieu_da_loc[0]]
        for i in range(1, len(du_lieu_da_loc)):
            if (du_lieu_da_loc[i]['Thời gian'] - du_lieu_da_loc[i-1]['Thời gian']) > timedelta(days=SO_NGAY_CHUYEN_VU):
                danh_sach_mua_vu.append(mua_hien_tai)
                mua_hien_tai = []
            mua_hien_tai.append(du_lieu_da_loc[i])
        if mua_hien_tai: danh_sach_mua_vu.append(mua_hien_tai)

        ket_qua_bao_cao = []
        for mua_vu in danh_sach_mua_vu:
            ngay_bat_dau = mua_vu[0]['Thời gian']
            ngay_ket_thuc = mua_vu[-1]['Thời gian']
            if (ngay_ket_thuc - ngay_bat_dau).days < SO_NGAY_TOI_THIEU: continue

            cac_cu_tuoi = []; tg_bat = None; tong_lan = 0
            for dong in mua_vu:
                if dong['Trạng thái'] == 'Bật': tg_bat = dong['Thời gian']
                elif dong['Trạng thái'] == 'Tắt' and tg_bat is not None:
                    giay_chay = (dong['Thời gian'] - tg_bat).total_seconds()
                    if giay_min <= giay_chay <= giay_max:
                        cac_cu_tuoi.append({
                            'Ngày': tg_bat.date(), 'Giây chạy': giay_chay,
                            'EC_Yeu_Cau': dong['EC_Yeu_Cau'], 'EC_Thuc_Te': dong['EC_Thuc_Te'], 'pH': dong['pH']
                        })
                        tong_lan += 1
                    tg_bat = None

            thong_ke = {}
            for cu in cac_cu_tuoi:
                ng = cu['Ngày']
                if ng not in thong_ke: thong_ke[ng] = {'So_lan': 0, 'Tong_giay': 0, 'Tong_EC_YC': 0, 'Tong_EC_TT': 0, 'Tong_pH': 0}
                thong_ke[ng]['So_lan'] += 1
                thong_ke[ng]['Tong_giay'] += cu['Giây chạy']
                thong_ke[ng]['Tong_EC_YC'] += cu['EC_Yeu_Cau']
                thong_ke[ng]['Tong_EC_TT'] += cu['EC_Thuc_Te']
                thong_ke[ng]['Tong_pH'] += cu['pH']

            danh_sach_ngay = sorted(thong_ke.keys())
            
            ec_tt_vals = [thong_ke[n]['Tong_EC_TT'] / thong_ke[n]['So_lan'] for n in danh_sach_ngay]
            ec_yc_vals = [thong_ke[n]['Tong_EC_YC'] / thong_ke[n]['So_lan'] for n in danh_sach_ngay]
            tong_phut_vals = [thong_ke[n]['Tong_giay'] / 60 for n in danh_sach_ngay]
            
            stages_ec_tt = phan_tich_giai_doan_array(danh_sach_ngay, ec_tt_vals, ss_ec_tt, so_ngay_on_dinh)
            stages_ec_yc = phan_tich_giai_doan_array(danh_sach_ngay, ec_yc_vals, ss_ec_yc, so_ngay_on_dinh)
            stages_tuoi = phan_tich_giai_doan_array(danh_sach_ngay, tong_phut_vals, ss_tong_phut, so_ngay_on_dinh)

            bang_bao_cao_ngay = []
            for i, ngay in enumerate(danh_sach_ngay):
                bang_bao_cao_ngay.append({
                    "Ngày_Str": ngay.strftime("%d/%m/%Y"),
                    "GĐ_EC_Thực": f"GĐ {stages_ec_tt[ngay]}",
                    "GĐ_EC_YC": f"GĐ {stages_ec_yc[ngay]}",
                    "GĐ_Tưới": f"GĐ {stages_tuoi[ngay]}",
                    "Số_Lần": thong_ke[ngay]['So_lan'],
                    "Tổng_TG_Phút": round(tong_phut_vals[i], 2),
                    "EC_Yêu_Cầu": round(ec_yc_vals[i], 2),
                    "EC_Thực_Tế": round(ec_tt_vals[i], 2),
                    "pH_TB": round(thong_ke[ngay]['Tong_pH'] / thong_ke[ngay]['So_lan'], 2)
                })

            ket_qua_bao_cao.append({"ngay_bat_dau": ngay_bat_dau, "ngay_ket_thuc": ngay_ket_thuc, "tong_lan_tuoi": tong_lan, "data": bang_bao_cao_ngay})
            
        return ket_qua_bao_cao, "Thành công"
    except Exception as e: return None, f"❌ Lỗi xử lý dữ liệu: {e}"

# ==========================================
# 🚀 3. CHẠY VÀ HIỂN THỊ TRÊN COLAB (KHÔNG DÙNG PANDAS)
# ==========================================
try:
    print(f"🚀 Đang đọc dữ liệu và phân tích STT = {STT_CAN_TIM}...")
    
    with open(FILE_TUOI, 'r', encoding='utf-8') as f:
        raw_data_tuoi = json.load(f)
    with open(FILE_CHAM_PHAN, 'r', encoding='utf-8') as f:
        raw_data_cp = json.load(f)

    ket_qua, thong_bao = process_data(
        STT_CAN_TIM, SO_NGAY_ON_DINH, SAI_SO_EC_TT, SAI_SO_EC_YC, SAI_SO_TONG_PHUT, 
        GIAY_TUOI_TOI_THIEU, GIAY_TUOI_TOI_DA, raw_data_tuoi, raw_data_cp
    )

    if ket_qua is None:
        print(thong_bao)
    else:
        print(f"✅ Phân tích hoàn tất!\n")
        
        for idx, mua_vu in enumerate(ket_qua):
            so_ngay_mua_vu = (mua_vu['ngay_ket_thuc'] - mua_vu['ngay_bat_dau']).days + 1
            
            # --- Thông tin Mùa vụ ---
            display(Markdown(f"## 🌿 MÙA VỤ SỐ {idx + 1}"))
            print(f"🗓️ Từ {mua_vu['ngay_bat_dau'].strftime('%d/%m/%Y')} đến {mua_vu['ngay_ket_thuc'].strftime('%d/%m/%Y')} ({so_ngay_mua_vu} ngày)")
            print(f"💧 Tổng cữ tưới hợp lệ: {mua_vu['tong_lan_tuoi']} lần\n")
            
            data_mua_vu = mua_vu['data']
            
            # --- Vẽ Biểu đồ bằng Plotly ---
            fig1 = px.bar(data_mua_vu, x="Ngày_Str", y="EC_Yêu_Cầu", color="GĐ_EC_YC", text="EC_Yêu_Cầu",
                          title="🎯 Biểu đồ EC Yêu Cầu (Trung bình)",
                          labels={"Ngày_Str": "Ngày", "EC_Yêu_Cầu": "Giá trị EC", "GĐ_EC_YC": "Giai đoạn YC"})
            fig1.update_traces(textposition='outside')
            fig1.update_layout(xaxis_tickangle=-45, yaxis=dict(range=[0, max([row["EC_Yêu_Cầu"] for row in data_mua_vu]) * 1.2]))
            fig1.show()
            
            fig2 = px.bar(data_mua_vu, x="Ngày_Str", y="EC_Thực_Tế", color="GĐ_EC_Thực", text="EC_Thực_Tế",
                          title="🧪 Biểu đồ EC Thực Tế (Trung bình)",
                          labels={"Ngày_Str": "Ngày", "EC_Thực_Tế": "Giá trị EC", "GĐ_EC_Thực": "Giai đoạn TT"},
                          color_discrete_sequence=px.colors.qualitative.Safe)
            fig2.update_traces(textposition='outside')
            fig2.update_layout(xaxis_tickangle=-45, yaxis=dict(range=[0, max([row["EC_Thực_Tế"] for row in data_mua_vu]) * 1.2]))
            fig2.show()

            fig3 = px.bar(data_mua_vu, x="Ngày_Str", y="Tổng_TG_Phút", color="GĐ_Tưới", text="Tổng_TG_Phút",
                          title="⏱️ Biểu đồ Tổng Thời Gian Tưới / Ngày (Phút)",
                          labels={"Ngày_Str": "Ngày", "Tổng_TG_Phút": "Phút", "GĐ_Tưới": "Giai đoạn Tưới"},
                          color_discrete_sequence=px.colors.qualitative.Vivid)
            fig3.update_traces(textposition='outside')
            fig3.update_layout(xaxis_tickangle=-45, yaxis=dict(range=[0, max([row["Tổng_TG_Phút"] for row in data_mua_vu]) * 1.2]))
            fig3.show()

            # --- Hiển thị Bảng Dữ Liệu bằng Code Python Phổ Thông (print + f-string) ---
            display(Markdown("### 📋 Bảng Dữ Liệu Chi Tiết"))
            
            # In Tiêu đề cột 
            print(f"{'Ngày':<12} | {'GĐ(EC.Thực)':<12} | {'GĐ(EC.YC)':<10} | {'GĐ(Tưới)':<10} | {'Số Lần':<8} | {'Tổng TG(Ph)':<12} | {'EC Y.Cầu':<10} | {'EC T.Tế':<10} | {'pH TB':<8}")
            print("-" * 105)
            
            # Lặp qua từng dòng dữ liệu và in ra
            for row in data_mua_vu:
                print(f"{row['Ngày_Str']:<12} | {row['GĐ_EC_Thực']:<12} | {row['GĐ_EC_YC']:<10} | {row['GĐ_Tưới']:<10} | {row['Số_Lần']:<8} | {row['Tổng_TG_Phút']:<12} | {row['EC_Yêu_Cầu']:<10} | {row['EC_Thực_Tế']:<10} | {row['pH_TB']:<8}")
                
            print("\n" + "="*105 + "\n")

except FileNotFoundError as e:
    print(f"❌ Không tìm thấy file JSON. Vui lòng kiểm tra lại xem tên file (FILE_TUOI, FILE_CHAM_PHAN) đã nhập đúng chưa nhé.\nChi tiết lỗi: {e}")
except Exception as e:
    print(f"❌ Có lỗi kỹ thuật xảy ra: {e}")
