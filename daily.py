import streamlit as st
import json
from datetime import datetime, timedelta

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN (Mở rộng toàn màn hình)
# ==========================================
st.set_page_config(page_title="Nhật Ký Vườn Thông Minh", page_icon="🍅", layout="wide")

# Tùy chỉnh CSS để các ô hiển thị số (Metric) trông đẹp và nổi bật hơn
st.markdown("""
    <style>
        div[data-testid="metric-container"] {
            background-color: #f0fdf4; 
            border: 1px solid #22c55e; 
            padding: 15px; 
            border-radius: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

st.title("🍅 Bảng Theo Dõi Giai Đoạn Sinh Trưởng")
st.markdown("---")

# ==========================================
# 2. KHU VỰC ĐIỀU KHIỂN (Dành cho Quản lý)
# ==========================================
st.sidebar.header("⚙️ Bảng Tải Dữ Liệu")

# Cho phép upload file trực tiếp trên web
uploaded_file = st.sidebar.file_uploader("📂 Tải file dữ liệu (JSON) lên đây:", type=['json'])

STT_CAN_TIM = st.sidebar.selectbox("🎯 Chọn Khu Vực:", ["1", "2", "3", "4"], index=3) 

with st.sidebar.expander("🛠️ Cài đặt nâng cao (Dành cho kỹ thuật)"):
    SO_NGAY_CHUYEN_VU = st.slider("Số ngày nghỉ để cắt vụ:", 1.0, 10.0, 2.0, 0.5)
    SO_NGAY_TOI_THIEU = st.slider("Bỏ qua vụ ngắn hơn (Ngày):", 1, 30, 7)

# ==========================================
# 3. LÕI XỬ LÝ & VẼ GIAO DIỆN
# ==========================================
if st.sidebar.button("🚀 XEM BÁO CÁO MÙA VỤ", type="primary", use_container_width=True):
    if uploaded_file is None:
        st.warning("⚠️ Bác vui lòng tải file dữ liệu (.json) ở menu bên trái lên trước nhé!")
    else:
        try:
            # --- BƯỚC 1: ĐỌC VÀ LỌC DỮ LIỆU ---
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

                # --- BƯỚC 2: CẮT MÙA VỤ & LỌC RÁC ---
                danh_sach_mua_vu = [] 
                mua_hien_tai = [du_lieu_da_loc[0]] 
                
                for i in range(1, len(du_lieu_da_loc)):
                    if (du_lieu_da_loc[i]['Thời gian'] - du_lieu_da_loc[i-1]['Thời gian']) > timedelta(days=SO_NGAY_CHUYEN_VU):
                        danh_sach_mua_vu.append(mua_hien_tai) 
                        mua_hien_tai = [] 
                    mua_hien_tai.append(du_lieu_da_loc[i])
                if mua_hien_tai:
                    danh_sach_mua_vu.append(mua_hien_tai)

                # Chỉ lấy những mùa vụ trồng thật (dài hơn SO_NGAY_TOI_THIEU)
                mua_vu_that = [mv for mv in danh_sach_mua_vu if (mv[-1]['Thời gian'] - mv[0]['Thời gian']).days >= SO_NGAY_TOI_THIEU]

                st.success(f"🎉 Đã phân tích xong! Phát hiện **{len(mua_vu_that)}** vụ mùa đạt chuẩn.")

                # --- BƯỚC 3: VẼ GIAO DIỆN TỪNG MÙA VỤ ---
                # Tạo các thẻ (Tabs) để bấm chuyển qua lại giữa các vụ
                tab_titles = [f"🌾 Vụ Mùa {i+1}" for i in range(len(mua_vu_that))]
                tabs = st.tabs(tab_titles)
                
                for idx, (tab, mua_vu) in enumerate(zip(tabs, mua_vu_that)):
                    with tab:
                        ngay_bat_dau = mua_vu[0]['Thời gian']
                        ngay_ket_thuc = mua_vu[-1]['Thời gian']
                        tong_so_ngay = (ngay_ket_thuc - ngay_bat_dau).days
                        
                        # 3.1 KHU VỰC THÔNG SỐ TỔNG QUAN (SỐ TO)
                        st.markdown(f"### 📋 Tổng quan Vụ {idx+1}")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("🌱 Ngày xuống giống", ngay_bat_dau.strftime('%d/%m/%Y'))
                        col2.metric("🍅 Ngày ghi nhận cuối", ngay_ket_thuc.strftime('%d/%m/%Y'))
                        col3.metric("⏳ Tổng số ngày trồng", f"{tong_so_ngay} ngày")
                        st.markdown("---")
                        
                        # 3.2 TÍNH TOÁN DỮ LIỆU HÀNG NGÀY
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
                            tong_giay = thong_ke_ngay[ngay]['Tong_giay']
                            
                            bang_bao_cao_ngay.append({
                                "Ngày": ngay.strftime("%d/%m"), 
                                "Ngày Chi Tiết": ngay.strftime("%d/%m/%Y"), 
                                "Số Lần Tưới": so_lan,
                                "Tổng Thời Gian Tưới (Phút)": round(tong_giay / 60, 2),
                                "Thời Gian TB 1 Lần (Phút)": round((tong_giay / so_lan) / 60, 2),
                                "Lượng Phân Bón (EC)": round(thong_ke_ngay[ngay]['Tong_EC'] / so_lan, 2)
                            })

                        # 3.3 KHU VỰC BIỂU ĐỒ TRỰC QUAN CHO NÔNG DÂN
                        if bang_bao_cao_ngay:
                            cot_trai, cot_phai = st.columns(2)
                            
                            with cot_trai:
                                st.markdown("**💧 Biểu Đồ Lượng Nước (Tổng thời gian bơm/ngày)**")
                                st.caption("Cột càng cao, ngày đó cây càng được bơm nhiều nước.")
                                # Biểu đồ cột thể hiện Tổng thời gian tưới của 1 ngày
                                st.bar_chart(bang_bao_cao_ngay, x="Ngày", y="Tổng Thời Gian Tưới (Phút)", color="#3498db")
                                
                            with cot_phai:
                                st.markdown("**🧪 Biểu Đồ Phân Bón (Chỉ số EC Trung Bình)**")
                                st.caption("Đường cong thể hiện nồng độ phân bón. Cuối vụ thường sẽ giảm mạnh để rửa rễ.")
                                # Biểu đồ đường thể hiện EC trung bình
                                st.line_chart(bang_bao_cao_ngay, x="Ngày", y="Lượng Phân Bón (EC)", color=["#2ecc71"])

                            # 3.4 KHU VỰC BẢNG SỐ LIỆU ĐỂ ĐỐI CHIẾU
                            with st.expander("🔍 Bấm vào đây để xem chi tiết từng con số (Dành cho kỹ thuật)"):
                                # Ẩn cột 'Ngày' viết tắt đi cho bảng đẹp hơn, chỉ hiện 'Ngày Chi Tiết'
                                bang_hien_thi = [{k: v for k, v in row.items() if k != 'Ngày'} for row in bang_bao_cao_ngay]
                                st.dataframe(bang_hien_thi, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Có lỗi khi đọc file: {e}")