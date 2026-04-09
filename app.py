import streamlit as st
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 1. CẤU HÌNH TRANG
# ==========================================
st.set_page_config(page_title="Nhật Ký Vườn Thông Minh", page_icon="🍅", layout="wide")

# CSS để làm đẹp các thẻ hiển thị
st.markdown("""
    <style>
        div[data-testid="metric-container"] {
            background-color: #f8fafc; border: 1px solid #e2e8f0; 
            padding: 15px; border-radius: 10px;
        }
        .stExpander { border: 1px solid #22c55e; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("🍅 Hệ Thống Phân Tích Mùa Vụ Chuyên Sâu")

# ==========================================
# 2. MENU BÊN TRÁI & TẢI FILE
# ==========================================
st.sidebar.header("📁 Dữ Liệu Đầu Vào")
file_lich = st.sidebar.file_uploader("Tải file Lịch nhỏ giọt (JSON)", type=['json'])
file_cham = st.sidebar.file_uploader("Tải file Châm phân trung gian (JSON)", type=['json'])
STT_CAN_TIM = st.sidebar.selectbox("🎯 Chọn Khu Vực:", ["1", "2", "3", "4"], index=3)

# Dùng mũi tên xổ xuống cho phần cấu hình theo ý bạn
with st.sidebar.expander("🛠️ Cấu hình thông số hệ thống", expanded=False):
    SO_NGAY_CHUYEN_VU = st.slider("Ngày nghỉ để ngắt vụ:", 1.0, 10.0, 2.0)
    SO_NGAY_TOI_THIEU = st.slider("Vụ tối thiểu (Ngày):", 1, 30, 7)
    GIAY_MIN = st.number_input("Bỏ qua lần tưới dưới (Giây):", value=20)

# ==========================================
# 3. XỬ LÝ DỮ LIỆU KẾT HỢP
# ==========================================
if file_lich and file_cham:
    try:
        # Đọc Kế hoạch (EC Yêu cầu)
        data_cp = json.load(file_cham)
        ke_hoach = {item.get('Thời gian', '').split(' ')[0]: float(item.get('EC yêu cầu', 0))/100.0 
                    for item in data_cp if str(item.get('STT')) == STT_CAN_TIM}

        # Đọc Thực tế (Lịch tưới)
        data_l = json.load(file_lich)
        thuc_te_raw = []
        for item in data_l:
            if str(item.get('STT')) == STT_CAN_TIM and item.get('Thời gian'):
                thuc_te_raw.append({
                    'tg': datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S'),
                    'tt': str(item.get('Trạng thái', '')).strip(),
                    'ec': float(item.get('TBEC', 0)) / 100.0
                })
        thuc_te_raw.sort(key=lambda x: x['tg'])

        # Chia mùa vụ
        vụ_list = []
        tam = [thuc_te_raw[0]]
        for i in range(1, len(thuc_te_raw)):
            if (thuc_te_raw[i]['tg'] - thuc_te_raw[i-1]['tg']) > timedelta(days=SO_NGAY_CHUYEN_VU):
                vụ_list.append(tam)
                tam = []
            tam.append(thuc_te_raw[i])
        if tam: vụ_list.append(tam)
        
        vụ_thật = [v for v in vụ_list if (v[-1]['tg'] - v[0]['tg']).days >= SO_NGAY_TOI_THIEU]

        # Hiển thị TABS
        tabs = st.tabs([f"🌾 Mùa Vụ {i+1}" for i in range(len(vụ_thật))])

        for idx, (tab, data_vu) in enumerate(zip(tabs, vụ_thật)):
            with tab:
                # Tính toán hàng ngày
                daily_data = []
                # (Logic bắt cặp Bật/Tắt giữ nguyên như lõi tối ưu)
                bat_tam = None
                day_agg = {}
                for d in data_vu:
                    if d['tt'] == 'Bật': bat_tam = d['tg']
                    elif d['tt'] == 'Tắt' and bat_tam:
                        giay = (d['tg'] - bat_tam).total_seconds()
                        if giay >= GIAY_MIN:
                            ngay_str = bat_tam.strftime('%Y-%m-%d')
                            if ngay_str not in day_agg: day_agg[ngay_str] = {'lan':0, 's':0, 'ec':0}
                            day_agg[ngay_str]['lan'] += 1
                            day_agg[ngay_str]['s'] += giay
                            day_agg[ngay_str]['ec'] += d['ec']
                        bat_tam = None

                for d_s in sorted(day_agg.keys()):
                    ec_yq = ke_hoach.get(d_s, 0)
                    ec_tt = round(day_agg[d_s]['ec']/day_agg[d_s]['lan'], 2)
                    
                    # Phân loại giai đoạn để đổ màu
                    if ec_yq <= 0.8: gd, color = "Cây non", "rgba(34, 197, 94, 0.2)"
                    elif ec_yq <= 1.5: gd, color = "Sinh trưởng", "rgba(59, 130, 246, 0.2)"
                    else: gd, color = "Thúc quả", "rgba(239, 68, 68, 0.2)"

                    daily_data.append({
                        "Ngày": d_s,
                        "EC yêu cầu": ec_yq,
                        "EC thực tế": ec_tt,
                        "Tổng thời gian tưới": round(day_agg[d_s]['s']/60, 2),
                        "Giai đoạn": gd,
                        "Màu": color
                    })

                df = pd.DataFrame(daily_data)

                # ==========================================
                # 4. BIỂU ĐỒ ĐA MÀU (PHÂN VÙNG GIAI ĐOẠN)
                # ==========================================
                st.subheader(f"📊 Biểu đồ so sánh Mùa vụ {idx+1}")
                
                fig = go.Figure()

                # Vẽ vùng màu cho từng giai đoạn
                for i in range(len(df)):
                    fig.add_vrect(
                        x0=i-0.5, x1=i+0.5,
                        fillcolor=df['Màu'][i], opacity=1,
                        layer="below", line_width=0,
                    )

                # Đường EC Yêu cầu (Kế hoạch)
                fig.add_trace(go.Scatter(x=df['Ngày'], y=df['EC yêu cầu'], name="EC Yêu cầu", line=dict(color='black', width=3, dash='dash')))
                
                # Đường EC Thực tế
                fig.add_trace(go.Scatter(x=df['Ngày'], y=df['EC thực tế'], name="EC Thực tế", line=dict(color='green', width=3)))
                
                # Cột Tổng thời gian tưới (Trục Y thứ 2)
                fig.add_trace(go.Bar(x=df['Ngày'], y=df['Tổng thời gian tưới'], name="Tổng TG Tưới (Phút)", yaxis="y2", marker_color='rgba(100, 100, 255, 0.5)'))

                fig.update_layout(
                    xaxis=dict(title="Ngày trong vụ"),
                    yaxis=dict(title="Chỉ số EC", side="left"),
                    yaxis2=dict(title="Phút tưới", side="right", overlaying="y", showgrid=False),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=20, r=20, t=50, b=20),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Bảng số liệu rút gọn
                st.write("🔍 **Chi tiết số liệu:**")
                st.dataframe(df[["Ngày", "EC yêu cầu", "EC thực tế", "Tổng thời gian tưới", "Giai đoạn"]], use_container_width=True)

    except Exception as e:
        st.error(f"Lỗi xử lý: {e}")
else:
    st.info("👋 Bác vui lòng tải đủ 2 file 'Lịch nhỏ giọt' và 'Châm phân trung gian' để bắt đầu nhé!")
