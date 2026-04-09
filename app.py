import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.express as px

# Cấu hình trang Streamlit
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
SAI_SO_EC_TT = st.sidebar.number_input("1. Sai số EC Thực Tế", value=0.2, step=0.05)
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

@st.cache_data
def process_data(stt, ss_ec_tt, ss_ec_yc, ss_tong_phut, giay_min, giay_max, data_tuoi, data_cp):
    try:
        # Bước 1: Lấy lịch sử EC Yêu Cầu
        lich_su_ec_yc = []
        for item in data_cp:
            if str(item.get('STT')) == stt and item.get('Thời gian') and 'EC yêu cầu' in item:
                try:
                    tg = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                    ec_val = float(item.get('EC yêu cầu', 0)) / 100.0
                    lich_su_ec_yc.append({'Thoi_gian': tg, 'EC_YC': ec_val})
                except ValueError:
                    pass
        lich_su_ec_yc.sort(key=lambda x: x['Thoi_gian'])

        # Bước 2: Lọc dữ liệu Tưới
        du_lieu_da_loc = []
        for item in data_tuoi:
            if str(item.get('STT')) == stt and item.get('Thời gian'):
                tg_hien_tai = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                ec_yc_chuan = lay_ec_yeu_cau_tai_thoi_diem(tg_hien_tai, lich_su_ec_yc)

                du_lieu_da_loc.append({
                    'Thời gian': tg_hien_tai,
                    'Trạng thái': str(item.get('Trạng thái', '')).strip(),
                    'EC_Yeu_Cau': ec_yc_chuan,
                    'EC_Thuc_Te': float(item.get('TBEC', 0)) / 100.0,
                    'pH': float(item.get('TBPH', 0)) / 100.0
                })

        if not du_lieu_da_loc:
            return None, f"❌ Không có dữ liệu hợp lệ cho STT {stt}."

        du_lieu_da_loc.sort(key=lambda x: x['Thời gian'])

        # Bước 3: Cắt Mùa Vụ
        danh_sach_mua_vu = []
        mua_hien_tai = [du_lieu_da_loc[0]]
        for i in range(1, len(du_lieu_da_loc)):
            if (du_lieu_da_loc[i]['Thời gian'] - du_lieu_da_loc[i-1]['Thời gian']) > timedelta(days=SO_NGAY_CHUYEN_VU):
                danh_sach_mua_vu.append(mua_hien_tai)
                mua_hien_tai = []
            mua_hien_tai.append(du_lieu_da_loc[i])
        if mua_hien_tai:
            danh_sach_mua_vu.append(mua_hien_tai)

        ket_qua_bao_cao = []

        # Bước 4: Phân tích từng mùa vụ
        for mua_vu in danh_sach_mua_vu:
            ngay_bat_dau = mua_vu[0]['Thời gian']
            ngay_ket_thuc = mua_vu[-1]['Thời gian']

            if (ngay_ket_thuc - ngay_bat_dau).days < SO_NGAY_TOI_THIEU:
                continue

            cac_cu_tuoi_thanh_cong = []
            tg_bat_tam_thoi = None
            tong_lan_tuoi_ca_mua = 0

            for dong in mua_vu:
                if dong['Trạng thái'] == 'Bật':
                    tg_bat_tam_thoi = dong['Thời gian']
                elif dong['Trạng thái'] == 'Tắt':
                    if tg_bat_tam_thoi is not None:
                        giay_chay = (dong['Thời gian'] - tg_bat_tam_thoi).total_seconds()
                        if giay_min <= giay_chay <= giay_max:
                            cac_cu_tuoi_thanh_cong.append({
                                'Ngày': tg_bat_tam_thoi.date(),
                                'Giây chạy': giay_chay,
                                'EC_Yeu_Cau': dong['EC_Yeu_Cau'],
                                'EC_Thuc_Te': dong['EC_Thuc_Te'],
                                'pH': dong['pH']
                            })
                            tong_lan_tuoi_ca_mua += 1
                        tg_bat_tam_thoi = None

            thong_ke_ngay = {}
            for cu in cac_cu_tuoi_thanh_cong:
                ngay = cu['Ngày']
                if ngay not in thong_ke_ngay:
                    thong_ke_ngay[ngay] = {'So_lan': 0, 'Tong_giay': 0, 'Tong_EC_YC': 0, 'Tong_EC_TT': 0, 'Tong_pH': 0}

                thong_ke_ngay[ngay]['So_lan'] += 1
                thong_ke_ngay[ngay]['Tong_giay'] += cu['Giây chạy']
                thong_ke_ngay[ngay]['Tong_EC_YC'] += cu['EC_Yeu_Cau']
                thong_ke_ngay[ngay]['Tong_EC_TT'] += cu['EC_Thuc_Te']
                thong_ke_ngay[ngay]['Tong_pH'] += cu['pH']

            danh_sach_ngay = sorted(thong_ke_ngay.keys())
            
            gd_ec_tt = 1; goc_ec_tt = None
            gd_ec_yc = 1; goc_ec_yc = None
            gd_tuoi = 1;  goc_tong_phut = None 

            bang_bao_cao_ngay = []
            stt_ngay = 1

            for ngay in danh_sach_ngay:
                so_lan = thong_ke_ngay[ngay]['So_lan']
                tong_phut = thong_ke_ngay[ngay]['Tong_giay'] / 60
                ec_yc_tb = thong_ke_ngay[ngay]['Tong_EC_YC'] / so_lan
                ec_tt_tb = thong_ke_ngay[ngay]['Tong_EC_TT'] / so_lan
                ph_tb = thong_ke_ngay[ngay]['Tong_pH'] / so_lan

                if goc_ec_tt is None: goc_ec_tt = ec_tt_tb
                elif abs(ec_tt_tb - goc_ec_tt) > ss_ec_tt:
                    gd_ec_tt += 1; goc_ec_tt = ec_tt_tb

                if goc_ec_yc is None: goc_ec_yc = ec_yc_tb
                elif abs(ec_yc_tb - goc_ec_yc) >= ss_ec_yc:
                    gd_ec_yc += 1; goc_ec_yc = ec_yc_tb

                if goc_tong_phut is None: goc_tong_phut = tong_phut
                elif abs(tong_phut - goc_tong_phut) >= ss_tong_phut:
                    gd_tuoi += 1; goc_tong_phut = tong_phut

                bang_bao_cao_ngay.append({
                    "Ngày": ngay, 
                    "Ngày_Str": ngay.strftime("%d/%m/%Y"),
                    "GĐ_EC_Thực": f"GĐ {gd_ec_tt}",
                    "GĐ_EC_YC": f"GĐ {gd_ec_yc}",
                    "GĐ_Tưới": f"GĐ {gd_tuoi}",
                    "Số Lần": so_lan,
                    "Tổng_TG_Phút": round(tong_phut, 2),
                    "EC_Yêu_Cầu": round(ec_yc_tb, 2),
                    "EC_Thực_Tế": round(ec_tt_tb, 2),
                    "pH_TB": round(ph_tb, 2)
                })
                stt_ngay += 1

            df = pd.DataFrame(bang_bao_cao_ngay)
            ket_qua_bao_cao.append({
                "ngay_bat_dau": ngay_bat_dau,
                "ngay_ket_thuc": ngay_ket_thuc,
                "tong_lan_tuoi": tong_lan_tuoi_ca_mua,
                "data": df
            })
            
        return ket_qua_bao_cao, "Thành công"

    except Exception as e:
        return None, f"❌ Lỗi xử lý dữ liệu: {e}"

# ==========================================
# 📊 QUẢN LÝ LUỒNG CHẠY & HIỂN THỊ
# ==========================================
# Yêu cầu phải upload đủ 2 file mới chạy
if file_tuoi_upload is None or file_cham_phan_upload is None:
    st.info("👈 Vui lòng tải lên cả 2 file JSON ở thanh bên trái để bắt đầu phân tích dữ liệu.")
else:
    # Đọc dữ liệu từ file upload
    try:
        raw_data_tuoi = json.load(file_tuoi_upload)
        raw_data_cp = json.load(file_cham_phan_upload)
        
        with st.spinner('Đang phân tích dữ liệu...'):
            ket_qua, thong_bao = process_data(
                STT_CAN_TIM, SAI_SO_EC_TT, SAI_SO_EC_YC, SAI_SO_TONG_PHUT, 
                GIAY_TUOI_TOI_THIEU, GIAY_TUOI_TOI_DA, 
                raw_data_tuoi, raw_data_cp # Truyền trực tiếp data vào hàm
            )

        if ket_qua is None:
            st.error(thong_bao)
        else:
            st.success(f"Phân tích hoàn tất cho STT = {STT_CAN_TIM}!")
            
            for idx, mua_vu in enumerate(ket_qua):
                st.markdown(f"### 🌿 MÙA VỤ SỐ {idx + 1}")
                st.caption(f"Từ **{mua_vu['ngay_bat_dau'].strftime('%d/%m/%Y')}** đến **{mua_vu['ngay_ket_thuc'].strftime('%d/%m/%Y')}** | 💧 Tổng cữ tưới hợp lệ: **{mua_vu['tong_lan_tuoi']}** lần")
                
                df = mua_vu['data']
                
                # --- MENU XỔ XUỐNG CHỌN TIÊU CHÍ BIỂU ĐỒ ---
                tieuchi_mapping = {
                    "⏱️ Tổng Thời Gian Tưới / Ngày (Phút)": "Tổng_TG_Phút",
                    "🎯 EC Yêu Cầu (Trung bình)": "EC_Yêu_Cầu",
                    "🧪 EC Thực Tế (Trung bình)": "EC_Thực_Tế",
                    "⚗️ pH (Trung bình)": "pH_TB",
                    "💧 Số lần tưới / Ngày": "Số Lần"
                }
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown("<br>", unsafe_allow_html=True)
                    tieuchi_chon = st.selectbox(
                        f"📊 Chọn tiêu chí biểu đồ (Mùa vụ {idx + 1}):", 
                        list(tieuchi_mapping.keys()),
                        key=f"selectbox_{idx}"
                    )
                
                # --- VẼ BIỂU ĐỒ BẰNG PLOTLY ---
                cot_du_lieu = tieuchi_mapping[tieuchi_chon]
                fig = px.bar(
                    df, 
                    x="Ngày_Str", 
                    y=cot_du_lieu, 
                    text=cot_du_lieu,
                    title=f"Biểu đồ {tieuchi_chon.split('(')[0].strip()}",
                    labels={"Ngày_Str": "Ngày", cot_du_lieu: "Giá trị"},
                    color_discrete_sequence=['#2ecc71'] if "TG" in cot_du_lieu else ['#3498db']
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45)
                
                st.plotly_chart(fig, use_container_width=True)
                
                # --- HIỂN THỊ BẢNG SỐ LIỆU ---
                st.markdown("#### 📋 Bảng Dữ Liệu Chi Tiết")
                
                df_display = df.rename(columns={
                    "Ngày_Str": "📅 Ngày",
                    "GĐ_EC_Thực": "🏷️ GĐ(EC.Thực)",
                    "GĐ_EC_YC": "🏷️ GĐ(EC.YC)",
                    "GĐ_Tưới": "🏷️ GĐ(Tưới)",
                    "Số Lần": "💧 Số Lần",
                    "Tổng_TG_Phút": "⏱️ Tổng TG (Ph)",
                    "EC_Yêu_Cầu": "🎯 EC Y.Cầu",
                    "EC_Thực_Tế": "🧪 EC T.Tế",
                    "pH_TB": "⚗️ pH TB"
                }).drop(columns=["Ngày"])
                
                st.dataframe(df_display, use_container_width=True)
                st.divider()

    except json.JSONDecodeError:
        st.error("❌ Lỗi định dạng file! Vui lòng đảm bảo bạn đã tải lên đúng file .json.")
