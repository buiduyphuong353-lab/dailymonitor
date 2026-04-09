import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.express as px

# ==========================================
# Cấu hình trang Streamlit
# ==========================================
st.set_page_config(page_title="Dashboard Phân Tích Tưới", page_icon="🌱", layout="wide")

st.title("🌱 Dashboard Phân Tích Giai Đoạn Tưới Nhỏ Giọt")

# ==========================================
# ⚙️ GIAO DIỆN CÀI ĐẶT (SIDEBAR)
# ==========================================
st.sidebar.header("📁 Tải Dữ Liệu Lên")
file_tuoi_upload = st.sidebar.file_uploader("1. Tải file Lịch nhỏ giọt (.json)", type=['json'])
file_cham_phan_upload = st.sidebar.file_uploader("2. Tải file Châm phân (.json)", type=['json'])

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Cấu hình thông số")

STT_CAN_TIM = st.sidebar.text_input("STT Cần Phân Tích", value="4")

st.sidebar.subheader("Ngưỡng phân chia Giai đoạn")
# Thêm ô setting "Số ngày ổn định" để chống nhiễu 1 ngày
SO_NGAY_ON_DINH = st.sidebar.number_input("⏳ Số ngày ổn định (Chống nhiễu)", value=2, step=1, min_value=1, help="Số ngày liên tiếp có giá trị same same nhau để được công nhận là một Giai đoạn mới.")

SAI_SO_EC_TT = st.sidebar.number_input("1. Sai số EC Thực Tế", value=0.20, step=0.05)
SAI_SO_EC_YC = st.sidebar.number_input("2. Sai số EC Yêu Cầu", value=0.15, step=0.05)
SAI_SO_TONG_PHUT = st.sidebar.number_input("3. Sai số Tổng Thời Gian (Phút)", value=10.0, step=1.0)

st.sidebar.subheader("Ngưỡng lọc dữ liệu")
GIAY_TUOI_TOI_THIEU = st.sidebar.number_input("Giây tưới tối thiểu", value=20)
GIAY_TUOI_TOI_DA = st.sidebar.number_input("Giây tưới tối đa (Lọc lỗi)", value=3600)
SO_NGAY_CHUYEN_VU = 2.0
SO_NGAY_TOI_THIEU = 7

# ==========================================
# 🧠 HÀM XỬ LÝ DỮ LIỆU CỐT LÕI
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
    """Thuật toán xét tính ổn định liên tiếp để chia giai đoạn"""
    stages = {}
    gd_current = 1
    goc_val = None
    buffer = []
    
    for i, ngay in enumerate(danh_sach_ngay):
        val = values[i]
        
        # Ngày đầu tiên khởi tạo gốc
        if goc_val is None:
            goc_val = val
            stages[ngay] = gd_current
            continue
            
        # Nếu lệch khỏi gốc hiện tại vượt ngưỡng sai số
        if abs(val - goc_val) >= sai_so:
            buffer.append({'ngay': ngay, 'val': val})
            
            # Đủ số ngày liên tiếp bị lệch
            if len(buffer) >= so_ngay_on_dinh:
                buf_vals = [x['val'] for x in buffer]
                # Kiểm tra các ngày lệch này có "same same" với nhau không (độ chênh lệch giữa chúng <= sai_so)
                if max(buf_vals) - min(buf_vals) <= sai_so:
                    # Chính thức xác nhận tạo Giai đoạn mới!
                    gd_current += 1
                    goc_val = sum(buf_vals) / len(buf_vals) # Gốc mới là trung bình của đợt ổn định này
                    for item in buffer:
                        stages[item['ngay']] = gd_current
                    buffer = []
                else:
                    # Dữ liệu dao động lung tung, không tạo thành trend. Đẩy ngày cũ nhất ra, coi như nhiễu.
                    oldest = buffer.pop(0)
                    stages[oldest['ngay']] = gd_current
        else:
            # Dữ liệu đã quay lại mức bình thường, các cảnh báo trước đó là nhiễu ảo -> Xoá sổ
            for item in buffer:
                stages[item['ngay']] = gd_current
            buffer = []
            stages[ngay] = gd_current
            
    # Xử lý nốt các ngày còn kẹt trong buffer cuối vụ
    for item in buffer:
        stages[item['ngay']] = gd_current
        
    return stages

@st.cache_data
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
            
            # Tính toán mảng dữ liệu trung bình ngày
            ec_tt_vals = [thong_ke[n]['Tong_EC_TT'] / thong_ke[n]['So_lan'] for n in danh_sach_ngay]
            ec_yc_vals = [thong_ke[n]['Tong_EC_YC'] / thong_ke[n]['So_lan'] for n in danh_sach_ngay]
            tong_phut_vals = [thong_ke[n]['Tong_giay'] / 60 for n in danh_sach_ngay]
            
            # 👉 ÁP DỤNG THUẬT TOÁN CHỐNG NHIỄU, TÍNH GIAI ĐOẠN 👈
            stages_ec_tt = phan_tich_giai_doan_array(danh_sach_ngay, ec_tt_vals, ss_ec_tt, so_ngay_on_dinh)
            stages_ec_yc = phan_tich_giai_doan_array(danh_sach_ngay, ec_yc_vals, ss_ec_yc, so_ngay_on_dinh)
            stages_tuoi = phan_tich_giai_doan_array(danh_sach_ngay, tong_phut_vals, ss_tong_phut, so_ngay_on_dinh)

            bang_bao_cao_ngay = []
            for i, ngay in enumerate(danh_sach_ngay):
                bang_bao_cao_ngay.append({
                    "Ngày": ngay, "Ngày_Str": ngay.strftime("%d/%m/%Y"),
                    "GĐ_EC_Thực": f"GĐ {stages_ec_tt[ngay]}",
                    "GĐ_EC_YC": f"GĐ {stages_ec_yc[ngay]}",
                    "GĐ_Tưới": f"GĐ {stages_tuoi[ngay]}",
                    "Số Lần": thong_ke[ngay]['So_lan'],
                    "Tổng_TG_Phút": round(tong_phut_vals[i], 2),
                    "EC_Yêu_Cầu": round(ec_yc_vals[i], 2),
                    "EC_Thực_Tế": round(ec_tt_vals[i], 2),
                    "pH_TB": round(thong_ke[ngay]['Tong_pH'] / thong_ke[ngay]['So_lan'], 2)
                })

            df = pd.DataFrame(bang_bao_cao_ngay)
            ket_qua_bao_cao.append({"ngay_bat_dau": ngay_bat_dau, "ngay_ket_thuc": ngay_ket_thuc, "tong_lan_tuoi": tong_lan, "data": df})
            
        return ket_qua_bao_cao, "Thành công"
    except Exception as e: return None, f"❌ Lỗi xử lý dữ liệu: {e}"

# ==========================================
# 📊 QUẢN LÝ LUỒNG CHẠY & HIỂN THỊ
# ==========================================
if file_tuoi_upload is None or file_cham_phan_upload is None:
    st.info("👈 Vui lòng tải lên cả 2 file JSON ở thanh bên trái để bắt đầu phân tích dữ liệu.")
else:
    try:
        raw_data_tuoi = json.load(file_tuoi_upload)
        raw_data_cp = json.load(file_cham_phan_upload)
        
        with st.spinner('Đang phân tích dữ liệu...'):
            ket_qua, thong_bao = process_data(
                STT_CAN_TIM, SO_NGAY_ON_DINH, SAI_SO_EC_TT, SAI_SO_EC_YC, SAI_SO_TONG_PHUT, 
                GIAY_TUOI_TOI_THIEU, GIAY_TUOI_TOI_DA, raw_data_tuoi, raw_data_cp 
            )

        if ket_qua is None:
            st.error(thong_bao)
        else:
            st.success(f"Phân tích hoàn tất cho STT = {STT_CAN_TIM}!")
            for idx, mua_vu in enumerate(ket_qua):
                st.markdown(f"### 🌿 MÙA VỤ SỐ {idx + 1}")
                st.caption(f"Từ **{mua_vu['ngay_bat_dau'].strftime('%d/%m/%Y')}** đến **{mua_vu['ngay_ket_thuc'].strftime('%d/%m/%Y')}** | 💧 Tổng cữ tưới hợp lệ: **{mua_vu['tong_lan_tuoi']}** lần")
                
                df = mua_vu['data']
                
                tieuchi_mapping = {
                    "🎯 EC Yêu Cầu (Trung bình)": {"cot_gia_tri": "EC_Yêu_Cầu", "cot_giai_doan": "GĐ_EC_YC"},
                    "🧪 EC Thực Tế (Trung bình)": {"cot_gia_tri": "EC_Thực_Tế", "cot_giai_doan": "GĐ_EC_Thực"},
                    "⏱️ Tổng Thời Gian Tưới / Ngày (Phút)": {"cot_gia_tri": "Tổng_TG_Phút", "cot_giai_doan": "GĐ_Tưới"}
                }
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown("<br>", unsafe_allow_html=True)
                    tieuchi_chon = st.selectbox(f"📊 Chọn tiêu chí biểu đồ (Mùa vụ {idx + 1}):", list(tieuchi_mapping.keys()), key=f"selectbox_{idx}")
                
                cot_du_lieu = tieuchi_mapping[tieuchi_chon]["cot_gia_tri"]
                cot_giai_doan = tieuchi_mapping[tieuchi_chon]["cot_giai_doan"]
                
                fig = px.bar(
                    df, x="Ngày_Str", y=cot_du_lieu, color=cot_giai_doan, text=cot_du_lieu,
                    title=f"Biểu đồ {tieuchi_chon.split('(')[0].strip()}",
                    labels={"Ngày_Str": "Ngày", cot_du_lieu: "Giá trị", cot_giai_doan: "Giai đoạn"},
                    color_discrete_sequence=px.colors.qualitative.Plotly 
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45, yaxis=dict(range=[0, df[cot_du_lieu].max() * 1.2])) 
                st.plotly_chart(fig, use_container_width=True)
                
                # --- PHẦN CODE NÂNG CẤP XEM CHI TIẾT GIAI ĐOẠN ---
                st.markdown("---")
                st.markdown(f"#### 🔍 Chi Tiết Theo {cot_giai_doan.replace('_', ' ')}")
                
                # 1. Lấy danh sách các giai đoạn duy nhất hiện có và sắp xếp theo số (GĐ 1, GĐ 2...)
                danh_sach_gd = df[cot_giai_doan].unique().tolist()
                danh_sach_gd.sort(key=lambda x: int(x.replace('GĐ ', ''))) # Sắp xếp chuẩn số học
                danh_sach_chon = ["Tất cả các Giai đoạn"] + danh_sach_gd
                
                # 2. Tạo cửa sổ xổ xuống (Selectbox) để chọn Giai đoạn
                gd_chon = st.selectbox(
                    "👉 Chọn Giai đoạn để xem chi tiết:", 
                    danh_sach_chon, 
                    key=f"select_gd_{idx}"
                )
                
                # 3. Lọc dữ liệu theo Giai đoạn đã chọn
                if gd_chon == "Tất cả các Giai đoạn":
                    df_filtered = df
                else:
                    df_filtered = df[df[cot_giai_doan] == gd_chon]
                    
                    # Hiện thống kê tóm tắt
                    st.info(f"**📊 Thống kê tóm tắt cho {gd_chon}:**")
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    
                    ngay_dau = df_filtered['Ngày_Str'].iloc[0]
                    ngay_cuoi = df_filtered['Ngày_Str'].iloc[-1]
                    so_ngay = len(df_filtered)
                    
                    col_m1.metric("Thời gian", f"{ngay_dau} ➡️ {ngay_cuoi}")
                    col_m2.metric("Kéo dài", f"{so_ngay} ngày")
                    col_m3.metric("EC Yêu Cầu (Trung bình)", f"{round(df_filtered['EC_Yêu_Cầu'].mean(), 2)}")
                    col_m4.metric("Thời gian tưới (Trung bình)", f"{round(df_filtered['Tổng_TG_Phút'].mean(), 2)} phút")
                    st.markdown("<br>", unsafe_allow_html=True)

                # 4. Hiển thị bảng dữ liệu đã lọc
                st.markdown("#### 📋 Bảng Dữ Liệu")
                df_display = df_filtered.rename(columns={
                    "Ngày_Str": "📅 Ngày", "GĐ_EC_Thực": "🏷️ GĐ(EC.Thực)", "GĐ_EC_YC": "🏷️ GĐ(EC.YC)",
                    "GĐ_Tưới": "🏷️ GĐ(Tưới)", "Số Lần": "💧 Số Lần", "Tổng_TG_Phút": "⏱️ Tổng TG (Ph)",
                    "EC_Yêu_Cầu": "🎯 EC Y.Cầu", "EC_Thực_Tế": "🧪 EC T.Tế", "pH_TB": "⚗️ pH TB"
                }).drop(columns=["Ngày"])
                
                st.dataframe(df_display, use_container_width=True)
                st.divider()

    except json.JSONDecodeError:
        st.error("❌ Lỗi định dạng file! Vui lòng đảm bảo bạn đã tải lên đúng file .json.")
