import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.express as px # 🌟 Thêm thư viện vẽ biểu đồ chuyên nghiệp

# ==========================================
# 🎨 CẤU HÌNH GIAO DIỆN STREAMLIT
# ==========================================
st.set_page_config(page_title="Phân Tích Nông Nghiệp", page_icon="🌱", layout="wide")

st.title("🌱 Dashboard Phân Tích Lịch Tưới & Châm Phân")
st.markdown("Hệ thống đồng bộ dữ liệu cài đặt EC từ file châm phân và lọc cữ tưới thông minh.")

# ==========================================
# ⚙️ SIDEBAR: KHU VỰC CÀI ĐẶT THÔNG SỐ
# ==========================================
with st.sidebar:
    st.header("⚙️ Cài đặt & Upload")
    
    # Khu vực tải file trực tiếp trên giao diện Web
    file_tuoi = st.file_uploader("📂 Upload 'Lich nho giotj.json'", type=['json'])
    file_cham_phan = st.file_uploader("📂 Upload 'châm phân trung gian.json'", type=['json'])
    
    st.markdown("---")
    # STT mặc định là "4" theo ảnh của bạn
    stt_can_tim = st.text_input("STT Cần tìm (Bồn/Van):", value="4")
    
    st.markdown("**Thông số phân tích:**")
    so_ngay_chuyen_vu = st.number_input("Cắt mùa nếu nghỉ tưới quá (ngày):", value=2.0, step=0.5)
    so_ngay_toi_thieu = st.number_input("Loại bỏ mùa vụ ngắn hơn (ngày):", value=7, step=1)
    giay_tuoi_toi_thieu = st.number_input("Lọc cữ tưới ảo dưới (giây):", value=20, step=5)
    sai_so_ec = st.number_input("Ngưỡng chênh lệch EC Thực Tế nhảy GĐ:", value=0.2, step=0.1)

# ==========================================
# 🧠 HÀM XỬ LÝ LÕI
# ==========================================
def lay_ec_yeu_cau_tai_thoi_diem(tg_tuoi, lich_su_ec):
    ec_hien_tai = 0.0
    for record in lich_su_ec:
        if record['Thoi_gian'] <= tg_tuoi:
            ec_hien_tai = record['EC_YC']
        else:
            break
    return ec_hien_tai

# ==========================================
# 🚀 CHẠY PHÂN TÍCH KHI BẤM NÚT
# ==========================================
if st.button("🚀 Chạy Phân Tích Dữ Liệu", type="primary", use_container_width=True):
    if not file_tuoi or not file_cham_phan:
        st.warning("⚠️ Vui lòng upload đầy đủ cả 2 file JSON ở thanh công cụ bên trái trước khi chạy.")
    else:
        with st.spinner('Đang đồng bộ dữ liệu và tính toán thuật toán...'):
            try:
                # 1. Đọc nội dung file JSON từ web upload
                data_tuoi = json.load(file_tuoi)
                data_cp = json.load(file_cham_phan)

                # 2. Xây dựng Lịch sử EC Yêu cầu từ file Châm Phân
                lich_su_ec_yc = []
                for item in data_cp:
                    if str(item.get('STT')) == stt_can_tim and item.get('Thời gian') and 'EC yêu cầu' in item:
                        try:
                            tg = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                            ec_val = float(item.get('EC yêu cầu', 0)) / 100.0 
                            lich_su_ec_yc.append({'Thoi_gian': tg, 'EC_YC': ec_val})
                        except ValueError:
                            pass
                lich_su_ec_yc.sort(key=lambda x: x['Thoi_gian'])

                # 3. Đồng bộ EC Yêu Cầu vào file Lịch Tưới
                du_lieu_da_loc = []
                for item in data_tuoi:
                    if str(item.get('STT')) == stt_can_tim and item.get('Thời gian'):
                        tg_hien_tai = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                        # Link dữ liệu: Tìm EC YC tương ứng với thời gian này
                        ec_yeu_cau_chuan = lay_ec_yeu_cau_tai_thoi_diem(tg_hien_tai, lich_su_ec_yc)

                        du_lieu_da_loc.append({
                            'Thời gian': tg_hien_tai,
                            'Trạng thái': str(item.get('Trạng thái', '')).strip(),
                            'EC_Yeu_Cau': ec_yeu_cau_chuan,
                            'EC_Thuc_Te': float(item.get('TBEC', 0)) / 100.0,
                            'pH': float(item.get('TBPH', 0)) / 100.0
                        })

                if not du_lieu_da_loc:
                    st.error(f"❌ Không có dữ liệu hợp lệ cho STT {stt_can_tim}.")
                else:
                    du_lieu_da_loc.sort(key=lambda x: x['Thời gian'])

                    # 4. Cắt mùa vụ
                    danh_sach_mua_vu = []
                    mua_hien_tai = [du_lieu_da_loc[0]]
                    for i in range(1, len(du_lieu_da_loc)):
                        if (du_lieu_da_loc[i]['Thời gian'] - du_lieu_da_loc[i-1]['Thời gian']) > timedelta(days=so_ngay_chuyen_vu):
                            danh_sach_mua_vu.append(mua_hien_tai)
                            mua_hien_tai = []
                        mua_hien_tai.append(du_lieu_da_loc[i])
                    if mua_hien_tai:
                        danh_sach_mua_vu.append(mua_hien_tai)

                    # 5. Phân tích chi tiết từng mùa
                    so_thu_tu_mua_that = 1
                    co_du_lieu = False

                    for mua_vu in danh_sach_mua_vu:
                        ngay_bat_dau = mua_vu[0]['Thời gian']
                        ngay_ket_thuc = mua_vu[-1]['Thời gian']

                        if (ngay_ket_thuc - ngay_bat_dau).days < so_ngay_toi_thieu:
                            continue
                        
                        co_du_lieu = True
                        cac_cu_tuoi_thanh_cong = []
                        tg_bat_tam_thoi = None
                        tong_lan_tuoi_ca_mua = 0

                        # Lọc thời gian < 20s
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
                                        tong_lan_tuoi_ca_mua += 1
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

                        # Phân Giai Đoạn theo EC Thực Tế
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

                        # --- IN RA UI GIAO DIỆN ---
                        st.subheader(f"🌱 Mùa Vụ Số {so_thu_tu_mua_that} (Từ {ngay_bat_dau.strftime('%d/%m/%Y')} đến {ngay_ket_thuc.strftime('%d/%m/%Y')})")
                        st.info(f"💧 **Tổng số lần tưới hợp lệ trong mùa:** {tong_lan_tuoi_ca_mua} lần (Đã lọc bỏ tưới ảo < {giay_tuoi_toi_thieu}s)")

                        bang_bao_cao_ngay = []
                        for ngay in danh_sach_ngay:
                            so_lan = thong_ke_ngay[ngay]['So_lan']
                            tong_giay = thong_ke_ngay[ngay]['Tong_giay']
                            ec_yc_tb = thong_ke_ngay[ngay]['Tong_EC_YC'] / so_lan
                            ec_tt_tb = thong_ke_ngay[ngay]['Tong_EC_TT'] / so_lan
                            ph_tb = thong_ke_ngay[ngay]['Tong_pH'] / so_lan
                            giai_doan = thong_ke_ngay[ngay]['Giai_doan']

                            bang_bao_cao_ngay.append({
                                "📅 Ngày": ngay.strftime("%d/%m/%Y"),
                                "🏷️ GĐ": f"GĐ {giai_doan}",
                                "💧 Số Lần": so_lan,
                                "⏱️ Tổng TG (Ph)": round(tong_giay / 60, 2),
                                "⏳ TB/Lần (Ph)": round((tong_giay / so_lan) / 60, 2),
                                "🎯 EC Yêu Cầu": round(ec_yc_tb, 2),        
                                "🧪 EC Thực Tế": round(ec_tt_tb, 2),
                                "⚗️ pH TB": round(ph_tb, 2)
                            })

                        if bang_bao_cao_ngay:
                            # 1. Hiển thị bảng dữ liệu (Giữ nguyên)
                            df = pd.DataFrame(bang_bao_cao_ngay)
                            df_table = df.copy() # Tạo bản sao cho bảng hiển thị
                            df_table.index = df_table.index + 1
                            st.dataframe(df_table, use_container_width=True)
                            
                            # 🌟 2. PHẦN MỚI: TẠO VÀ HIỂN THỊ BIỂU ĐỒ TRỰC QUAN 🌟
                            st.markdown("#### 📊 Biểu Đồ Xu Hướng EC Thực Tế Theo Giai Đoạn")
                            
                            # Chuẩn bị dữ liệu riêng cho biểu đồ
                            df_chart = df.copy()
                            # Chuyển đổi cột Ngày sang kiểu datetime để trục X chạy đúng
                            df_chart['📅 Ngày'] = pd.to_datetime(df_chart['📅 Ngày'], format='%d/%m/%Y')
                            # Đảm bảo cột Giai đoạn là chuỗi để Plotly phân loại màu
                            df_chart['🏷️ GĐ'] = df_chart['🏷️ GĐ'].astype(str)

                            # Vẽ biểu đồ đường với Plotly Express
                            fig = px.line(df_chart, 
                                          x='📅 Ngày', 
                                          y='🧪 EC Thực Tế', 
                                          color='🏷️ GĐ', # 🌟 Đây là chìa khóa để phân màu theo giai đoạn
                                          title=f'Xu hướng EC Thực Tế TB hàng ngày - Mùa Vụ Số {so_thu_tu_mua_that}',
                                          labels={'📅 Ngày': 'Thời gian (Ngày)', '🧪 EC Thực Tế': 'EC Thực Tế (TB)', '🏷️ GĐ': 'Giai đoạn'},
                                          markers=True # Thêm điểm tròn tại mỗi ngày dữ liệu
                                         )
                            
                            # Tùy chỉnh thêm một chút cho đẹp và tương tác tốt hơn
                            fig.update_traces(hovertemplate='Ngày: %{x|%d/%m/%Y}<br>EC Thực Tế: %{y:.2f}')
                            fig.update_layout(xaxis_tickformat='%d/%m/%Y') # Định dạng ngày trên trục X

                            # Hiển thị biểu đồ vào Streamlit
                            st.plotly_chart(fig, use_container_width=True)

                        st.markdown("---")
                        so_thu_tu_mua_that += 1

                    if not co_du_lieu:
                        st.warning("Không tìm thấy mùa vụ nào đủ điều kiện (có thể do các mùa vụ quá ngắn).")
                    else:
                        st.success("✅ Đã phân tích và trực quan hóa xong toàn bộ dữ liệu!")
            
            except Exception as e:
                st.error(f"❌ Đã xảy ra lỗi trong quá trình xử lý: {e}")
