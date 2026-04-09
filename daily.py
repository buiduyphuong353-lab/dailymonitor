import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# ⚙️ CẤU HÌNH TRANG STREAMLIT
# ==========================================
st.set_page_config(page_title="Hệ Thống Phân Tích Tưới Tiêu", page_icon="🌱", layout="wide")

# ==========================================
# 🧠 HÀM XỬ LÝ LÕI DỮ LIỆU
# ==========================================
def process_data(json_data, stt_can_tim, so_ngay_chuyen_vu, so_ngay_toi_thieu, giay_tuoi_toi_thieu, sai_so_ec):
    du_lieu_da_loc = []
    
    for item in json_data:
        if str(item.get('STT')) == stt_can_tim and item.get('Thời gian'):
            # Lấy EC Yêu cầu
            ec_raw = str(item.get('EC', ''))
            ec_yeu_cau = 0.0
            if '/' in ec_raw:
                try:
                    ec_yeu_cau = float(ec_raw.split('/')[-1])
                except ValueError:
                    pass
            
            du_lieu_da_loc.append({
                'Thời gian': datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S'),
                'Trạng thái': str(item.get('Trạng thái', '')).strip(),
                'EC_Yeu_Cau': ec_yeu_cau,
                'EC_Thuc_Te': float(item.get('TBEC', 0)) / 100.0,
                'pH': float(item.get('TBPH', 0)) / 100.0
            })

    if not du_lieu_da_loc:
        return []

    du_lieu_da_loc.sort(key=lambda x: x['Thời gian'])

    # BƯỚC 1: CẮT MÙA VỤ
    danh_sach_mua_vu = []
    mua_hien_tai = [du_lieu_da_loc[0]]
    for i in range(1, len(du_lieu_da_loc)):
        if (du_lieu_da_loc[i]['Thời gian'] - du_lieu_da_loc[i-1]['Thời gian']) > timedelta(days=so_ngay_chuyen_vu):
            danh_sach_mua_vu.append(mua_hien_tai)
            mua_hien_tai = []
        mua_hien_tai.append(du_lieu_da_loc[i])
    if mua_hien_tai:
        danh_sach_mua_vu.append(mua_hien_tai)

    ket_qua_mua_vu = []

    # BƯỚC 2: PHÂN TÍCH CHI TIẾT
    for mua_vu in danh_sach_mua_vu:
        ngay_bat_dau = mua_vu[0]['Thời gian']
        ngay_ket_thuc = mua_vu[-1]['Thời gian']
        
        if (ngay_ket_thuc - ngay_bat_dau).days < so_ngay_toi_thieu:
            continue
        
        cac_cu_tuoi_thanh_cong = []
        tg_bat_tam_thoi = None
        
        for dong in mua_vu:
            if dong['Trạng thái'] == 'Bật':
                tg_bat_tam_thoi = dong['Thời gian']
            elif dong['Trạng thái'] == 'Tắt':
                if tg_bat_tam_thoi is not None:
                    giay_chay = (dong['Thời gian'] - tg_bat_tam_thoi).total_seconds()
                    if giay_chay >= giay_tuoi_toi_thieu:
                        cac_cu_tuoi_thanh_cong.append({
                            'Ngày': tg_bat_tam_thoi.date(),
                            'Giây chạy': giay_chay,
                            'EC_Yeu_Cau': dong['EC_Yeu_Cau'],
                            'EC_Thuc_Te': dong['EC_Thuc_Te'],
                            'pH': dong['pH']
                        })
                    tg_bat_tam_thoi = None

        # Gom nhóm theo ngày
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

        # Phân chia giai đoạn DỰA TRÊN EC THỰC TẾ
        danh_sach_ngay = sorted(thong_ke_ngay.keys())
        giai_doan_hien_tai = 1
        ec_goc_cua_giai_doan = None

        for ngay in danh_sach_ngay:
            so_lan = thong_ke_ngay[ngay]['So_lan']
            ec_tt_tb_hom_nay = thong_ke_ngay[ngay]['Tong_EC_TT'] / so_lan
            
            if ec_goc_cua_giai_doan is None:
                ec_goc_cua_giai_doan = ec_tt_tb_hom_nay
            else:
                do_lech = abs(ec_tt_tb_hom_nay - ec_goc_cua_giai_doan)
                if do_lech > sai_so_ec:
                    giai_doan_hien_tai += 1
                    ec_goc_cua_giai_doan = ec_tt_tb_hom_nay 
            thong_ke_ngay[ngay]['Giai_doan'] = giai_doan_hien_tai

        # Xuất DataFrame
        bang_bao_cao = []
        for ngay in danh_sach_ngay:
            so_lan = thong_ke_ngay[ngay]['So_lan']
            bang_bao_cao.append({
                "Ngày": ngay,
                "Giai đoạn": f"GĐ {thong_ke_ngay[ngay]['Giai_doan']}",
                "Số Lần Tưới": so_lan,
                "Tổng Thời Gian (Phút)": round(thong_ke_ngay[ngay]['Tong_giay'] / 60, 2),
                "EC Yêu Cầu": round(thong_ke_ngay[ngay]['Tong_EC_YC'] / so_lan, 2),
                "EC Thực Tế": round(thong_ke_ngay[ngay]['Tong_EC_TT'] / so_lan, 2),
                "pH": round(thong_ke_ngay[ngay]['Tong_pH'] / so_lan, 2)
            })
            
        ket_qua_mua_vu.append({
            'Tu_ngay': ngay_bat_dau,
            'Den_ngay': ngay_ket_thuc,
            'Dataframe': pd.DataFrame(bang_bao_cao)
        })

    return ket_qua_mua_vu


# ==========================================
# 🎨 XÂY DỰNG GIAO DIỆN STREAMLIT
# ==========================================
st.title("👨‍🌾 BẢNG ĐIỀU KHIỂN & PHÂN TÍCH TƯỚI TIÊU NÔNG NGHIỆP")
st.markdown("---")

# --- KHU VỰC SIDEBAR (CÀI ĐẶT & UPLOAD) ---
with st.sidebar:
    st.header("📂 Tải Dữ Liệu")
    uploaded_file = st.file_uploader("Chọn file Lịch Nhỏ Giọt (JSON)", type="json")
    
    st.header("⚙️ Cài Đặt Thông Số")
    stt_input = st.text_input("Khu vực cần xem (STT)", value="2")
    sai_so = st.slider("Sai số EC để chuyển giai đoạn", min_value=0.05, max_value=0.5, value=0.2, step=0.05)
    
    with st.expander("🛠️ Cài đặt nâng cao (Kỹ thuật)"):
        so_ngay_chuyen = st.number_input("Cắt vụ nếu nghỉ quá (ngày)", value=2.0)
        ngay_toi_thieu = st.number_input("Số ngày tối thiểu 1 vụ", value=7)
        giay_toi_thieu = st.number_input("Lọc cữ tưới dưới (giây)", value=20)

# --- KHU VỰC CHÍNH (HIỂN THỊ KẾT QUẢ) ---
if uploaded_file is not None:
    # Đọc file JSON từ Upload
    try:
        json_data = json.load(uploaded_file)
        st.success("Tải dữ liệu thành công! Đang tiến hành phân tích...")
        
        # Chạy thuật toán
        danh_sach_mua = process_data(
            json_data, stt_input, so_ngay_chuyen, ngay_toi_thieu, giay_toi_thieu, sai_so
        )
        
        if not danh_sach_mua:
            st.warning(f"Không tìm thấy mùa vụ nào hợp lệ cho STT = {stt_input}.")
        else:
            # Nếu có nhiều mùa vụ, tạo selectbox để chọn mùa
            mua_vu_options = [f"Mùa {i+1}: {m['Tu_ngay'].strftime('%d/%m/%Y')} - {m['Den_ngay'].strftime('%d/%m/%Y')}" for i, m in enumerate(danh_sach_mua)]
            chon_mua = st.selectbox("🌱 Chọn mùa vụ để xem", options=mua_vu_options)
            
            # Lấy index của mùa vụ đang được chọn
            idx = mua_vu_options.index(chon_mua)
            df = danh_sach_mua[idx]['Dataframe']
            
            # CHIA LÀM 2 TAB: NÔNG DÂN VÀ KỸ THUẬT
            tab_nong_dan, tab_ky_thuat = st.tabs(["👨‍🌾 Dành cho Nông dân (Trực quan)", "🔬 Dành cho Kỹ thuật (Chi tiết)"])
            
            # ==========================================
            # TAB 1: DÀNH CHO NÔNG DÂN
            # ==========================================
            with tab_nong_dan:
                st.subheader("📊 Biểu Đồ Dinh Dưỡng Theo Giai Đoạn")
                st.markdown("Biểu đồ cột hiển thị mức phân bón cây được ăn. **Các màu sắc khác nhau đại diện cho các giai đoạn phát triển khác nhau**.")
                
                # Vẽ biểu đồ Plotly
                fig = px.bar(
                    df, 
                    x='Ngày', 
                    y='EC Thực Tế', 
                    color='Giai đoạn',
                    text='EC Thực Tế',
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    labels={'EC Thực Tế': 'Lượng Dinh Dưỡng (EC)'}
                )
                
                # Thêm đường line nét đứt thể hiện EC Yêu cầu
                fig.add_trace(go.Scatter(
                    x=df['Ngày'], y=df['EC Yêu Cầu'], 
                    mode='lines+markers', name='Chỉ tiêu cài đặt (EC Yêu Cầu)',
                    line=dict(color='red', dash='dash')
                ))

                fig.update_traces(textposition='outside')
                fig.update_layout(
                    height=500, 
                    xaxis_title="Ngày Tháng",
                    yaxis_title="Chỉ số EC",
                    legend_title="Giai Đoạn",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)

                # Số liệu tóm tắt cho nông dân dễ đọc
                col1, col2, col3 = st.columns(3)
                col1.info(f"**Tổng số ngày:** {len(df)} ngày")
                col2.success(f"**Đã trải qua:** {df['Giai đoạn'].nunique()} giai đoạn")
                col3.warning(f"**EC Hiện tại (Gần nhất):** {df['EC Thực Tế'].iloc[-1]}")

            # ==========================================
            # TAB 2: DÀNH CHO KỸ THUẬT
            # ==========================================
            with tab_ky_thuat:
                st.subheader("🗄️ Bảng Dữ Liệu Chuyên Sâu")
                st.markdown("Bảng tổng hợp chi tiết các chỉ số trung bình theo từng ngày để xuất file báo cáo.")
                
                # Hiển thị DataFrame dưới dạng bảng tương tác của Streamlit
                st.dataframe(
                    df.style.highlight_max(subset=['EC Thực Tế', 'Tổng Thời Gian (Phút)'], color='lightgreen')
                            .highlight_min(subset=['pH'], color='lightcoral'),
                    use_container_width=True,
                    height=400
                )
                
                # Nút tải file Excel/CSV (Tuỳ chọn cho kỹ sư)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Tải Bảng Dữ Liệu (CSV)",
                    data=csv,
                    file_name=f"Bao_cao_STT_{stt_input}.csv",
                    mime="text/csv",
                )
                
    except Exception as e:
        st.error(f"❌ Có lỗi xảy ra trong quá trình xử lý file: {e}")
else:
    st.info("👈 Vui lòng tải lên file JSON ở thanh công cụ bên trái để bắt đầu.")
