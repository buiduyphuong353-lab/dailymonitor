import streamlit as st
import json
from datetime import datetime, timedelta

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN (Làm cho app trông chuyên nghiệp hơn)
# ==========================================
st.set_page_config(page_title="Nhật Ký Vườn Thông Minh", page_icon="🍅", layout="wide")

# CSS để trang trí các ô số và khung lộ trình
st.markdown("""
    <style>
        div[data-testid="metric-container"] {
            background-color: #f0fdf4; border: 1px solid #22c55e; 
            padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        }
        .timeline-box {
            background-color: #fffbeb; border-left: 5px solid #f59e0b;
            padding: 20px; margin-bottom: 25px; border-radius: 8px;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #f8fafc; border-radius: 5px 5px 0 0; padding: 10px 20px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🍅 Trợ Lý Theo Dõi & Phân Chia Giai Đoạn Mùa Vụ")
st.markdown("---")

# ==========================================
# 2. THANH ĐIỀU KHIỂN BÊN TRÁI (SIDEBAR)
# ==========================================
st.sidebar.header("⚙️ Bảng Tải Dữ Liệu")
uploaded_file = st.sidebar.file_uploader("📂 Tải file dữ liệu (JSON) của vườn:", type=['json'])
STT_CAN_TIM = st.sidebar.selectbox("🎯 Chọn Khu Vực:", ["1", "2", "3", "4"], index=3) 

with st.sidebar.expander("🛠️ Cài đặt kỹ thuật (Dành cho chuyên gia)"):
    SO_NGAY_CHUYEN_VU = st.slider("Số ngày nghỉ để cắt vụ:", 1.0, 10.0, 2.0, 0.5)
    SO_NGAY_TOI_THIEU = st.slider("Một vụ thật phải dài ít nhất (Ngày):", 1, 30, 7)

# ==========================================
# 3. LOGIC PHÂN TÍCH CHÍNH
# ==========================================
if st.sidebar.button("🚀 XEM PHÂN TÍCH CHI TIẾT", type="primary", use_container_width=True):
    if uploaded_file is None:
        st.warning("⚠️ Bác vui lòng tải file dữ liệu ở Menu bên trái lên trước nhé!")
    else:
        try:
            # --- ĐỌC VÀ LỌC DỮ LIỆU ---
            data = json.load(uploaded_file)
            du_lieu_raw = [] 
            for item in data:
                if str(item.get('STT')) == STT_CAN_TIM and item.get('Thời gian'):
                    du_lieu_raw.append({
                        'Thời gian': datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S'),
                        'Trạng thái': str(item.get('Trạng thái', '')).strip(),
                        'EC': float(item.get('TBEC', 0)) / 100.0,
                        'pH': float(item.get('TBPH', 0)) / 100.0
                    })

            if not du_lieu_raw:
                st.error(f"❌ Không tìm thấy dữ liệu của Khu {STT_CAN_TIM}.")
            else:
                du_lieu_raw.sort(key=lambda x: x['Thời gian'])

                # --- CHIA MÙA VỤ ---
                danh_sach_mua_vu = [] 
                mua_hien_tai = [du_lieu_raw[0]] 
                for i in range(1, len(du_lieu_raw)):
                    if (du_lieu_raw[i]['Thời gian'] - du_lieu_raw[i-1]['Thời gian']) > timedelta(days=SO_NGAY_CHUYEN_VU):
                        danh_sach_mua_vu.append(mua_hien_tai) 
                        mua_hien_tai = [] 
                    mua_hien_tai.append(du_lieu_raw[i])
                if mua_hien_tai:
                    danh_sach_mua_vu.append(mua_hien_tai)

                # --- LỌC VỤ THẬT ---
                mua_vu_that = [mv for mv in danh_sach_mua_vu if (mv[-1]['Thời gian'] - mv[0]['Thời gian']).days >= SO_NGAY_TOI_THIEU]

                if not mua_vu_that:
                    st.info("ℹ️ Không tìm thấy mùa vụ nào đủ dài để phân tích.")
                else:
                    st.success(f"🎉 Đã tìm thấy **{len(mua_vu_that)}** mùa vụ trồng trọt chính thức.")

                    # --- HIỂN THỊ THEO THẺ TABS ---
                    tabs = st.tabs([f"🌾 Mùa Vụ {i+1}" for i in range(len(mua_vu_that))])
                    
                    for idx, (tab, mua_vu) in enumerate(zip(tabs, mua_vu_that)):
                        with tab:
                            ngay_dau = mua_vu[0]['Thời gian']
                            ngay_cuoi = mua_vu[-1]['Thời gian']
                            tong_ngay = (ngay_cuoi - ngay_dau).days
                            
                            # Cột thông số tổng quan
                            col1, col2, col3 = st.columns(3)
                            col1.metric("🌱 Bắt đầu vụ", ngay_dau.strftime('%d/%m/%Y'))
                            col2.metric("🍅 Kết thúc vụ", ngay_cuoi.strftime('%d/%m/%Y'))
                            col3.metric("⏳ Thời gian trồng", f"{tong_ngay} ngày")
                            st.markdown("---")
                            
                            # --- Tính toán số liệu từng ngày (Bật/Tắt) ---
                            cac_cu_tuoi = []
                            tg_bat_tam = None 
                            for dong in mua_vu:
                                if dong['Trạng thái'] == 'Bật':
                                    tg_bat_tam = dong['Thời gian']
                                elif dong['Trạng thái'] == 'Tắt' and tg_bat_tam is not None:
                                    cac_cu_tuoi.append({
                                        'Ngày': tg_bat_tam.date(),
                                        'Giây': (dong['Thời gian'] - tg_bat_tam).total_seconds(),
                                        'EC': dong['EC']
                                    })
                                    tg_bat_tam = None 

                            thong_ke_ngay = {}
                            for cu in cac_cu_tuoi:
                                d = cu['Ngày']
                                if d not in thong_ke_ngay:
                                    thong_ke_ngay[d] = {'lan': 0, 'giay': 0, 'ec': 0}
                                thong_ke_ngay[d]['lan'] += 1
                                thong_ke_ngay[d]['giay'] += cu['Giây']
                                thong_ke_ngay[d]['ec'] += cu['EC']

                            data_ngay = []
                            for d in sorted(thong_ke_ngay.keys()):
                                n = thong_ke_ngay[d]['lan']
                                data_ngay.append({
                                    "Ngày": d.strftime("%d/%m"),
                                    "Ngày Chi Tiết": d.strftime("%d/%m/%Y"),
                                    "Số Lần Tưới": n,
                                    "Tổng Phút Tưới": round(thong_ke_ngay[d]['giay'] / 60, 2),
                                    "EC TB": round(thong_ke_ngay[d]['ec'] / n, 2),
                                    "Giai Đoạn": ""
                                })

                            # --- AI CHIA GIAI ĐOẠN ---
                            if data_ngay:
                                max_ec = max(x['EC TB'] for x in data_ngay)
                                max_lan = max(x['Số Lần Tưới'] for x in data_ngay)
                                sl_ngay = len(data_ngay)

                                for i, day in enumerate(data_ngay):
                                    vi_tri = i / sl_ngay
                                    if vi_tri < 0.2 and day['EC TB'] <= 1.2:
                                        day['Giai Đoạn'] = "🌱 1. Cây non / Bén rễ"
                                    elif vi_tri > 0.8 and (day['EC TB'] <= max_ec * 0.6 or day['Số Lần Tưới'] <= max_lan * 0.6):
                                        day['Giai Đoạn'] = "🍅 4. Cuối vụ / Thu hoạch"
                                    elif day['EC TB'] >= max_ec * 0.85:
                                        day['Giai Đoạn'] = "🌼 3. Ra hoa / Nuôi trái"
                                    else:
                                        day['Giai Đoạn'] = "🌿 2. Sinh trưởng mạnh"

                                # --- HIỂN THỊ LỘ TRÌNH (TIMELINE) ---
                                st.markdown("#### ⏳ Lộ trình phát triển thực tế:")
                                gd_list = []
                                cur_gd = data_ngay[0]['Giai Đoạn']
                                start_d = data_ngay[0]['Ngày Chi Tiết']
                                for i in range(1, len(data_ngay)):
                                    if data_ngay[i]['Giai Đoạn'] != cur_gd:
                                        gd_list.append(f"- **{cur_gd}**: {start_d} ➔ {data_ngay[i-1]['Ngày Chi Tiết']}")
                                        cur_gd = data_ngay[i]['Giai Đoạn']
                                        start_d = data_ngay[i]['Ngày Chi Tiết']
                                gd_list.append(f"- **{cur_gd}**: {start_d} ➔ {data_ngay[-1]['Ngày Chi Tiết']}")
                                
                                st.markdown(f"<div class='timeline-box'>{'<br>'.join(gd_list)}</div>", unsafe_allow_html=True)

                                # --- BIỂU ĐỒ ---
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown("**💧 Thời gian tưới mỗi ngày (Phút)**")
                                    st.bar_chart(data_ngay, x="Ngày", y="Tổng Phút Tưới", color="#3498db")
                                with c2:
                                    st.markdown("**🧪 Chỉ số phân bón (EC)**")
                                    st.line_chart(data_ngay, x="Ngày", y="EC TB", color="#2ecc71")

                                with st.expander("🔍 Xem bảng dữ liệu chi tiết từng ngày"):
                                    st.dataframe(data_ngay, use_container_width=True)

        except Exception as e:
            st.error(f"Lỗi: {e}")