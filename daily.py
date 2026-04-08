import streamlit as st
import json
from datetime import datetime, timedelta

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN (Giao diện rộng, tên thân thiện)
# ==========================================
st.set_page_config(page_title="Nhật Ký Vườn Thông Minh", page_icon="🍅", layout="wide")

st.title("🍅 Bảng Theo Dõi Mùa Vụ Sinh Trưởng")
st.markdown("---")

# ==========================================
# 2. KHU VỰC ĐIỀU KHIỂN (Dành cho người quản lý)
# ==========================================
st.sidebar.header("⚙️ Bảng Cài Đặt")

# Nâng cấp: Cho phép tải file trực tiếp từ máy tính
uploaded_file = st.sidebar.file_uploader("📂 Tải file dữ liệu (JSON)", type=['json'])

STT_CAN_TIM = st.sidebar.selectbox("🎯 Chọn Khu vực (Ví dụ: Khu 4):", ["1", "2", "3", "4"], index=3) 

# Thanh kéo đơn giản, giải thích dễ hiểu cho nông dân
SO_NGAY_CHUYEN_VU = st.sidebar.slider(
    "Khoảng nghỉ chuyển vụ (Ngày):", 
    min_value=1.0, max_value=10.0, value=2.0, step=0.5,
    help="Nếu vườn ngừng tưới lâu hơn số ngày này, hệ thống tự hiểu là bắt đầu vụ mới."
)

SO_NGAY_TOI_THIEU = st.sidebar.slider(
    "Độ dài 1 vụ tối thiểu (Ngày):", 
    min_value=1, max_value=30, value=7,
    help="Bỏ qua các đợt test máy, rửa ống ngắn ngày (dưới 7 ngày)."
)

# ==========================================
# 3. LÕI XỬ LÝ DỮ LIỆU (Giữ nguyên logic tối ưu)
# ==========================================
if st.sidebar.button("🚀 XEM BÁO CÁO", type="primary", use_container_width=True):
    if uploaded_file is None:
        st.warning("⚠️ Bác vui lòng tải file dữ liệu (.json) lên trước nhé!")
    else:
        try:
            # Đọc dữ liệu từ file tải lên
            data = json.load(uploaded_file)
            
            du_lieu_da_loc = [] 
            for item in data:
                if str(item.get('STT')) == STT_CAN_TIM and item.get('Thời gian'):
                    du_lieu_da_loc.append({
                        'Thời gian': datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S'),
                        'Trạng thái': str(item.get('Trạng thái', '')).strip(),
                        'EC': float(item.get('TBEC', 0)) / 100.0,
                        'pH': float(item.get('TBPH', 0)) / 100.0
                    })

            if not du_lieu_da_loc:
                st.error(f"❌ Không tìm thấy dữ liệu của Khu {STT_CAN_TIM}.")
            else:
                du_lieu_da_loc.sort(key=lambda x: x['Thời gian'])

                # Cắt mùa vụ
                danh_sach_mua_vu = [] 
                mua_hien_tai = [du_lieu_da_loc[0]] 
                
                for i in range(1, len(du_lieu_da_loc)):
                    if (du_lieu_da_loc[i]['Thời gian'] - du_lieu_da_loc[i-1]['Thời gian']) > timedelta(days=SO_NGAY_CHUYEN_VU):
                        danh_sach_mua_vu.append(mua_hien_tai) 
                        mua_hien_tai = [] 
                    mua_hien_tai.append(du_lieu_da_loc[i])
                if mua_hien_tai:
                    danh_sach_mua_vu.append(mua_hien_tai)

                # Lọc mùa vụ thật
                mua_vu_that = []
                for mua_vu in danh_sach_mua_vu:
                    if (mua_vu[-1]['Thời gian'] - mua_vu[0]['Thời gian']).days >= SO_NGAY_TOI_THIEU:
                        mua_vu_that.append(mua_vu)

                st.success(f"🎉 Hệ thống phân tích thành công! Phát hiện **{len(mua_vu_that)}** mùa vụ đạt chuẩn.")

                # ==========================================
                # 4. VẼ GIAO DIỆN HIỂN THỊ (UX CHO NÔNG DÂN)
                # ==========================================
                # Tạo các Tabs (Thẻ) tương ứng với số mùa vụ
                tab_titles = [f"🌾 Mùa Vụ {i+1}" for i in range(len(mua_vu_that))]
                tabs = st.tabs(tab_titles)
                
                for idx, (tab, mua_vu) in enumerate(zip(tabs, mua_vu_that)):
                    with tab:
                        ngay_bat_dau = mua_vu[0]['Thời gian']
                        ngay_ket_thuc = mua_vu[-1]['Thời gian']
                        tong_so_ngay = (ngay_ket_thuc - ngay_bat_dau).days
                        
                        # --- HÀNG 1: BÁO CÁO NHANH (SỐ TO) ---
                        st.markdown("### 📊 Tổng quan khu vườn")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("🌱 Ngày bắt đầu", ngay_bat_dau.strftime('%d/%m/%Y'))
                        col2.metric("🍅 Ngày kết thúc", ngay_ket_thuc.strftime('%d/%m/%Y'))
                        col3.metric("⏳ Tổng thời gian trồng", f"{tong_so_ngay} ngày")
                        st.markdown("---")
                        
                        # --- Tính toán số liệu từng ngày ---
                        cac_cu_tuoi = []
                        tg_bat_tam_thoi = None 
                        for dong in mua_vu:
                            if dong['Trạng thái'] == 'Bật':
                                tg_bat_tam_thoi = dong['Thời gian']
                            elif dong['Trạng thái'] == 'Tắt' and tg_bat_tam_thoi is not None:
                                cac_cu_tuoi.append({
                                    'Ngày': tg_bat_tam_thoi.date(),
                                    'Giây chạy': (dong['Thời gian'] - tg_bat_tam_thoi).total_seconds(),
                                    'EC': dong['EC'],
                                    'pH': dong['pH']
                                })
                                tg_bat_tam_thoi = None 

                        thong_ke_ngay = {}
                        for cu in cac_cu_tuoi:
                            ngay = cu['Ngày']
                            if ngay not in thong_ke_ngay:
                                thong_ke_ngay[ngay] = {'So_lan': 0, 'Tong_giay': 0, 'Tong_EC': 0, 'Tong_pH': 0}
                            thong_ke_ngay[ngay]['So_lan'] += 1
                            thong_ke_ngay[ngay]['Tong_giay'] += cu['Giây chạy']
                            thong_ke_ngay[ngay]['Tong_EC'] += cu['EC']
                            thong_ke_ngay[ngay]['Tong_pH'] += cu['pH']

                        bang_bao_cao_ngay = []
                        for ngay in sorted(thong_ke_ngay.keys()):
                            so_lan = thong_ke_ngay[ngay]['So_lan']
                            bang_bao_cao_ngay.append({
                                "Mốc Thời Gian": ngay.strftime("%d/%m"), 
                                "Số Lần Tưới": so_lan,
                                "Thời Gian Tưới (Phút)": round((thong_ke_ngay[ngay]['Tong_giay'] / so_lan) / 60, 2),
                                "Lượng Phân Bón (EC)": round(thong_ke_ngay[ngay]['Tong_EC'] / so_lan, 2),
                                "Độ Chua (pH)": round(thong_ke_ngay[ngay]['Tong_pH'] / so_lan, 2)
                            })

                        # --- HÀNG 2: BIỂU ĐỒ TRỰC QUAN ---
                        if bang_bao_cao_ngay:
                            col_chart1, col_chart2 = st.columns(2)
                            
                            with col_chart1:
                                st.markdown("**💧 Nhu cầu tưới nước (Biểu đồ cột)**")
                                st.caption("Cột càng cao, cây càng cần nhiều nước (Giai đoạn vươn nhánh, nuôi quả)")
                                st.bar_chart(bang_bao_cao_ngay, x="Mốc Thời Gian", y="Số Lần Tưới", color="#3498db")
                                
                            with col_chart2:
                                st.markdown("**🧪 Nhu cầu phân bón (Biểu đồ đường)**")
                                st.caption("Sự thay đổi của chỉ số EC. Cuối vụ đường này sẽ rớt xuống đáy (Rửa rễ).")
                                st.line_chart(bang_bao_cao_ngay, x="Mốc Thời Gian", y=["Lượng Phân Bón (EC)"], color=["#2ecc71"])

                            # --- HÀNG 3: BẢNG SỐ LIỆU CHI TIẾT ---
                            with st.expander("🔍 Xem bảng số liệu chi tiết từng ngày (Dành cho kỹ thuật)"):
                                st.dataframe(bang_bao_cao_ngay, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Có lỗi khi đọc file: {e}")