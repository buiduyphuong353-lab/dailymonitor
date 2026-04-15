import streamlit as st
import json
from datetime import datetime, timedelta
import plotly.express as px

# ==============================================================================
# PHẦN 1: ĐỌC FILE VÀ THU THẬP DỮ LIỆU TỪ NGƯỜI DÙNG (NẰM Ở ĐẦU CODE)
# ==============================================================================
st.set_page_config(page_title="Dashboard Phân Tích Tưới", page_icon="🌱", layout="wide")

st.sidebar.header("📁 1. TẢI DỮ LIỆU LÊN")

# Đọc file Tưới
file_tuoi_uploads = st.sidebar.file_uploader("Tải file Lịch nhỏ giọt (.json)", type=['json'], accept_multiple_files=True)
danh_sach_file_tuoi = []
if file_tuoi_uploads:
    for f in file_tuoi_uploads:
        if st.sidebar.checkbox(f"📄 {f.name}", value=True, key=f"tuoi_{f.name}"):
            danh_sach_file_tuoi.append(f)

st.sidebar.markdown("<br>", unsafe_allow_html=True)

# Đọc file Châm Phân
file_cham_phan_uploads = st.sidebar.file_uploader("Tải file Châm phân (.json)", type=['json'], accept_multiple_files=True)
danh_sach_file_cp = []
if file_cham_phan_uploads:
    for f in file_cham_phan_uploads:
        if st.sidebar.checkbox(f"📄 {f.name}", value=True, key=f"cp_{f.name}"):
            danh_sach_file_cp.append(f)

# Đọc các thông số cấu hình cắt Mùa Vụ
st.sidebar.header("⚙️ 2. CẤU HÌNH CẮT MÙA VỤ")
STT_CAN_TIM = st.sidebar.text_input("STT Thiết bị cần phân tích", value="4")

st.sidebar.subheader("Yếu tố 1: Tổng thời gian tưới (Ngày nghỉ)")
NGAY_NGHI_KET_THUC_VU = st.sidebar.number_input("Số ngày nghỉ tưới (Để cắt vụ)", value=2.0, help="Quá số ngày này không tưới sẽ tự động cắt vụ cũ.")

st.sidebar.subheader("Yếu tố 2: EC Thực Tế (TBEC)")
EC_TT_BAT_DAU = st.sidebar.number_input("Ngưỡng EC Thực Tế (Bắt đầu vụ)", value=0.8, step=0.1)
EC_TT_KET_THUC = st.sidebar.number_input("Ngưỡng EC Thực Tế (Kết thúc vụ)", value=0.3, step=0.1)

st.sidebar.subheader("Yếu tố 3: EC Yêu Cầu")
EC_YC_BAT_DAU = st.sidebar.number_input("Ngưỡng EC Yêu Cầu (Bắt đầu vụ)", value=0.8, step=0.1)
EC_YC_KET_THUC = st.sidebar.number_input("Ngưỡng EC Yêu Cầu (Kết thúc vụ)", value=0.3, step=0.1)

# Các thông số tính toán Giai đoạn và Lọc nhiễu
st.sidebar.header("⚙️ 3. CẤU HÌNH GIAI ĐOẠN & LỌC NHIỄU")
SO_NGAY_ON_DINH = st.sidebar.number_input("Số ngày ổn định (Để chuyển GĐ)", value=2, step=1)
SAI_SO_EC_TT = st.sidebar.number_input("Sai số EC Thực Tế", value=0.20, step=0.05)
SAI_SO_EC_YC = st.sidebar.number_input("Sai số EC Yêu Cầu", value=0.15, step=0.05)
SAI_SO_TONG_PHUT = st.sidebar.number_input("Sai số Tổng Thời Gian (Phút)", value=10.0, step=1.0)

GIAY_TUOI_MIN = st.sidebar.number_input("Giây tưới tối thiểu (Lọc rác)", value=20)
GIAY_TUOI_MAX = st.sidebar.number_input("Giây tưới tối đa (Lọc lỗi)", value=3600)
SO_LAN_TUOI_MIN = st.sidebar.number_input("Số cữ tưới tối thiểu/Vụ", value=10)
SO_GD_MIN = st.sidebar.number_input("Số giai đoạn tối thiểu/Vụ", value=4)


# ==============================================================================
# PHẦN 2: LÕI THUẬT TOÁN XỬ LÝ DỮ LIỆU VÀ CHIA MÙA VỤ (NẰM Ở GIỮA CODE)
# ==============================================================================

def lay_ec_yeu_cau_tai_thoi_diem(thoi_gian_tuoi, lich_su_ec_yc):
    """Tìm mức EC Yêu Cầu được cài đặt ngay trước lúc cữ tưới bắt đầu"""
    ec_hien_tai = 0.0
    for ban_ghi in lich_su_ec_yc:
        if ban_ghi['Thoi_gian'] <= thoi_gian_tuoi:
            ec_hien_tai = ban_ghi['EC_YC']
        else:
            break
    return ec_hien_tai

def kiem_tra_moc_ec(gia_tri_ec, nguong_bat_dau, nguong_ket_thuc):
    """
    Hàm dùng chung cho cả EC Thực tế và EC Yêu cầu để xác định trạng thái.
    Trả về Tuple 2 giá trị: (Có_phải_bắt_đầu_không, Có_phải_kết_thúc_không)
    """
    is_bat_dau = gia_tri_ec >= nguong_bat_dau
    is_ket_thuc = gia_tri_ec <= nguong_ket_thuc
    return is_bat_dau, is_ket_thuc

def xac_dinh_giai_doan_chung(danh_sach_ngay, danh_sach_gia_tri, sai_so, so_ngay_on_dinh):
    """Thuật toán dán nhãn Giai đoạn 1, 2, 3... dựa vào sự thay đổi giá trị theo thời gian"""
    if not danh_sach_gia_tri or len(danh_sach_ngay) != len(danh_sach_gia_tri):
        return {}

    tu_dien_giai_doan = {}
    giai_doan_hien_tai = 1
    gia_tri_moc = danh_sach_gia_tri[0] 
    dem_so_ngay_lech = 0       
    
    for i in range(len(danh_sach_ngay)):
        ngay = danh_sach_ngay[i]
        gia_tri_hom_nay = danh_sach_gia_tri[i]
        
        # Nếu mức chênh lệch vượt quá sai số cho phép -> Bắt đầu đếm ngày lệch
        if abs(gia_tri_hom_nay - gia_tri_moc) >= sai_so:
            dem_so_ngay_lech += 1
        else:
            dem_so_ngay_lech = 0 # Nhiễu -> reset
            
        # Nếu lệch liên tục đủ số ngày -> Chốt chuyển giai đoạn mới
        if dem_so_ngay_lech >= so_ngay_on_dinh:
            giai_doan_hien_tai += 1
            gia_tri_moc = gia_tri_hom_nay 
            dem_so_ngay_lech = 0             
            
            # Quay lùi lại gán nhãn cho những ngày chống nhiễu vừa qua
            for buoc_lui in range(so_ngay_on_dinh):
                ngay_truoc = danh_sach_ngay[i - buoc_lui]
                tu_dien_giai_doan[ngay_truoc] = giai_doan_hien_tai
                
        # Gán nhãn cho ngày hiện tại nếu chưa có
        if ngay not in tu_dien_giai_doan or tu_dien_giai_doan[ngay] < giai_doan_hien_tai:
            tu_dien_giai_doan[ngay] = giai_doan_hien_tai
            
    return tu_dien_giai_doan

@st.cache_data
def xu_ly_va_phan_tich_du_lieu(stt_thiet_bi, du_lieu_tuoi, du_lieu_cp):
    try:
        # BƯỚC 1: LỌC VÀ CHUẨN HÓA DỮ LIỆU
        # Trích xuất lịch sử châm phân
        lich_su_ec_yc = []
        for item in du_lieu_cp:
            if str(item.get('STT')) == stt_thiet_bi and item.get('Thời gian') and 'EC yêu cầu' in item:
                try:
                    tg = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                    ec_val = float(item.get('EC yêu cầu', 0)) / 100.0
                    lich_su_ec_yc.append({'Thoi_gian': tg, 'EC_YC': ec_val})
                except ValueError: pass
        lich_su_ec_yc.sort(key=lambda x: x['Thoi_gian'])

        # Gắn dữ liệu Châm phân vào dữ liệu Tưới theo mốc thời gian
        du_lieu_da_loc = []
        for item in du_lieu_tuoi:
            if str(item.get('STT')) == stt_thiet_bi and item.get('Thời gian'):
                try:
                    tg_hien_tai = datetime.strptime(item.get('Thời gian'), '%Y-%m-%d %H-%M-%S')
                    raw_tbec = str(item.get('TBEC', '0')).strip()
                    ec_tt = float(raw_tbec) / 100.0 if raw_tbec else 0.0
                    ec_yc = lay_ec_yeu_cau_tai_thoi_diem(tg_hien_tai, lich_su_ec_yc)

                    du_lieu_da_loc.append({
                        'Thời gian': tg_hien_tai,
                        'Trạng thái': str(item.get('Trạng thái', '')).strip(),
                        'EC_Yeu_Cau': ec_yc,
                        'EC_Thuc_Te': ec_tt
                    })
                except ValueError: pass

        if not du_lieu_da_loc: 
            return None, f"❌ Không có dữ liệu hợp lệ cho thiết bị số {stt_thiet_bi}."
        du_lieu_da_loc.sort(key=lambda x: x['Thời gian'])

        # BƯỚC 2: CẮT MÙA VỤ THEO 3 YẾU TỐ (THỜI GIAN, EC_TT, EC_YC)
        danh_sach_mua_vu = []
        mua_vu_hien_tai = []

        for dong in du_lieu_da_loc:
            # Dùng chung 1 hàm logic cho cả 2 loại EC
            bat_dau_tt, ket_thuc_tt = kiem_tra_moc_ec(dong['EC_Thuc_Te'], EC_TT_BAT_DAU, EC_TT_KET_THUC)
            bat_dau_yc, ket_thuc_yc = kiem_tra_moc_ec(dong['EC_Yeu_Cau'], EC_YC_BAT_DAU, EC_YC_KET_THUC)

            # Nếu đang có mùa vụ chạy, kiểm tra xem có nên CẮT (kết thúc) không
            if mua_vu_hien_tai:
                thoi_gian_truoc = mua_vu_hien_tai[-1]['Thời gian']
                nghi_qua_lau = (dong['Thời gian'] - thoi_gian_truoc).days >= NGAY_NGHI_KET_THUC_VU
                
                # Mùa vụ kết thúc khi: Nghỉ lâu HOẶC Thực tế tụt đáy HOẶC Yêu cầu tụt đáy
                if nghi_qua_lau or ket_thuc_tt or ket_thuc_yc:
                    danh_sach_mua_vu.append(mua_vu_hien_tai)
                    mua_vu_hien_tai = [] # Xóa đi để chuẩn bị cho vụ mới

            # Nếu không có vụ nào đang chạy, kiểm tra xem có đủ điều kiện BẮT ĐẦU vụ mới không
            if not mua_vu_hien_tai:
                # Đk Mở vụ: Không nằm trong khoảng xả rác/kết thúc VÀ (EC TT hoặc EC YC đạt ngưỡng bắt đầu)
                if not (ket_thuc_tt or ket_thuc_yc) and (bat_dau_tt or bat_dau_yc):
                    mua_vu_hien_tai.append(dong)
            else:
                # Đang trong vụ thì tiếp tục lưu trữ dữ liệu
                mua_vu_hien_tai.append(dong)

        # Lưu mùa vụ cuối cùng nếu file kết thúc giữa chừng
        if mua_vu_hien_tai: 
            danh_sach_mua_vu.append(mua_vu_hien_tai)

        # BƯỚC 3: TỔNG HỢP VÀ DÁN NHÃN GIAI ĐOẠN CHO TỪNG MÙA VỤ
        ket_qua_cuoi_cung = []
        for mua_vu in danh_sach_mua_vu:
            ngay_bat_dau = mua_vu[0]['Thời gian']
            ngay_ket_thuc = mua_vu[-1]['Thời gian']

            cac_cu_tuoi = []
            thoi_gian_bat_bom = None
            tong_lan_tuoi = 0
            
            # Tính toán độ dài cữ tưới
            for dong in mua_vu:
                if dong['Trạng thái'] == 'Bật': 
                    thoi_gian_bat_bom = dong['Thời gian']
                elif dong['Trạng thái'] == 'Tắt' and thoi_gian_bat_bom is not None:
                    giay_chay = (dong['Thời gian'] - thoi_gian_bat_bom).total_seconds()
                    if GIAY_TUOI_MIN <= giay_chay <= GIAY_TUOI_MAX:
                        cac_cu_tuoi.append({
                            'Ngày': thoi_gian_bat_bom.date(), 
                            'Giây_chạy': giay_chay,
                            'EC_Yeu_Cau': dong['EC_Yeu_Cau'], 
                            'EC_Thuc_Te': dong['EC_Thuc_Te']
                        })
                        tong_lan_tuoi += 1
                    thoi_gian_bat_bom = None

            # Bỏ qua những mùa rác quá ít cữ tưới
            if tong_lan_tuoi < SO_LAN_TUOI_MIN: continue

            # Gom nhóm theo từng Ngày
            thong_ke_ngay = {}
            for cu in cac_cu_tuoi:
                ng = cu['Ngày']
                if ng not in thong_ke_ngay: 
                    thong_ke_ngay[ng] = {'So_lan': 0, 'Tong_giay': 0, 'Tong_EC_YC': 0, 'Tong_EC_TT': 0}
                
                thong_ke_ngay[ng]['So_lan'] += 1
                thong_ke_ngay[ng]['Tong_giay'] += cu['Giây_chạy']
                thong_ke_ngay[ng]['Tong_EC_YC'] += cu['EC_Yeu_Cau']
                thong_ke_ngay[ng]['Tong_EC_TT'] += cu['EC_Thuc_Te']

            if not thong_ke_ngay: continue

            # Rút trích mảng để nạp vào hàm chia giai đoạn
            danh_sach_ngay = sorted(thong_ke_ngay.keys())
            mang_ec_tt_tb = [thong_ke_ngay[n]['Tong_EC_TT'] / thong_ke_ngay[n]['So_lan'] for n in danh_sach_ngay]
            mang_ec_yc_tb = [thong_ke_ngay[n]['Tong_EC_YC'] / thong_ke_ngay[n]['So_lan'] for n in danh_sach_ngay]
            mang_phut_tb = [thong_ke_ngay[n]['Tong_giay'] / 60 for n in danh_sach_ngay]
            
            # Chạy thuật toán chia Giai đoạn
            gd_ec_tt = xac_dinh_giai_doan_chung(danh_sach_ngay, mang_ec_tt_tb, SAI_SO_EC_TT, SO_NGAY_ON_DINH)
            gd_ec_yc = xac_dinh_giai_doan_chung(danh_sach_ngay, mang_ec_yc_tb, SAI_SO_EC_YC, SO_NGAY_ON_DINH)
            gd_tuoi = xac_dinh_giai_doan_chung(danh_sach_ngay, mang_phut_tb, SAI_SO_TONG_PHUT, SO_NGAY_ON_DINH)

            # Lọc bỏ mùa vụ nếu trải qua quá ít giai đoạn
            max_gd_chung = max(max(gd_ec_tt.values() or [0]), max(gd_ec_yc.values() or [0]), max(gd_tuoi.values() or [0]))
            if max_gd_chung < SO_GD_MIN: continue

            # Chuẩn bị dữ liệu hiển thị (Bảng DataFrame)
            bang_du_lieu_hien_thi = []
            for i, ngay in enumerate(danh_sach_ngay):
                bang_du_lieu_hien_thi.append({
                    "Ngày_Str": ngay.strftime("%d/%m/%Y"),
                    "GĐ_EC_Thực": f"GĐ {gd_ec_tt[ngay]}",
                    "GĐ_EC_YC": f"GĐ {gd_ec_yc[ngay]}",
                    "GĐ_Tưới": f"GĐ {gd_tuoi[ngay]}",
                    "Số_Lần": thong_ke_ngay[ngay]['So_lan'],
                    "Tổng_TG_Phút": round(mang_phut_tb[i], 2),
                    "EC_Yêu_Cầu": round(mang_ec_yc_tb[i], 2),
                    "EC_Thực_Tế": round(mang_ec_tt_tb[i], 2)
                })

            ket_qua_cuoi_cung.append({
                "ngay_bat_dau": ngay_bat_dau, 
                "ngay_ket_thuc": ngay_ket_thuc, 
                "tong_lan_tuoi": tong_lan_tuoi, 
                "data": bang_du_lieu_hien_thi
            })
            
        return ket_qua_cuoi_cung, "Thành công"
    except Exception as e: 
        return None, f"❌ Lỗi xử lý dữ liệu: {e}"


# ==============================================================================
# PHẦN 3: GIAO DIỆN HIỂN THỊ KẾT QUẢ VÀ BIỂU ĐỒ (NẰM Ở CUỐI CODE)
# ==============================================================================

st.title("🌱 Dashboard Phân Tích Giai Đoạn Tưới Nhỏ Giọt")

if not danh_sach_file_tuoi or not danh_sach_file_cp:
    st.info("👈 Vui lòng tải lên và TÍCH CHỌN ít nhất 1 file Lịch nhỏ giọt và 1 file Châm phân ở thanh bên trái để bắt đầu phân tích.")
else:
    try:
        # Gộp tất cả nội dung JSON vào biến chung
        du_lieu_tho_tuoi = []
        du_lieu_tho_cp = []
        
        for f in danh_sach_file_tuoi:
            f.seek(0)
            data = json.load(f)
            if isinstance(data, list): du_lieu_tho_tuoi.extend(data)
            else: du_lieu_tho_tuoi.append(data)
                
        for f in danh_sach_file_cp:
            f.seek(0)
            data = json.load(f)
            if isinstance(data, list): du_lieu_tho_cp.extend(data)
            else: du_lieu_tho_cp.append(data)
        
        # Chạy thuật toán chính
        with st.spinner('Đang phân tích, cắt mùa vụ và chia giai đoạn...'):
            ket_qua, thong_bao = xu_ly_va_phan_tich_du_lieu(STT_CAN_TIM, du_lieu_tho_tuoi, du_lieu_tho_cp)

        if ket_qua is None:
            st.error(thong_bao)
        elif len(ket_qua) == 0:
            st.warning("⚠️ Không tìm thấy mùa vụ nào đủ điều kiện. Hãy kiểm tra lại cấu hình thông số ở thanh bên trái (có thể ngưỡng lọc đang quá khắt khe).")
        else:
            st.success("✅ Phân tích thành công! Hệ thống đã cắt vụ dựa trên 3 tiêu chí: Khoảng thời gian nghỉ, Sự thay đổi của EC Thực tế và EC Yêu cầu.")
            
            # Duyệt qua từng mùa vụ và hiển thị
            for idx, mua_vu in enumerate(ket_qua):
                st.markdown(f"### 🌿 MÙA VỤ SỐ {idx + 1}")
                so_ngay_mua_vu = (mua_vu['ngay_ket_thuc'] - mua_vu['ngay_bat_dau']).days + 1
                st.caption(f"🗓️ Từ **{mua_vu['ngay_bat_dau'].strftime('%d/%m/%Y')}** đến **{mua_vu['ngay_ket_thuc'].strftime('%d/%m/%Y')}** ({so_ngay_mua_vu} ngày) | 💧 Cữ tưới hợp lệ: **{mua_vu['tong_lan_tuoi']}** lần")
                
                bang_du_lieu = mua_vu['data'] 
                
                # --- ĐÁNH GIÁ TƯƠNG THÍCH THIẾT BỊ ---
                tong_tuong_thich = 0
                so_ngay_tinh = 0
                for row in bang_du_lieu:
                    if row['EC_Yêu_Cầu'] > 0:
                        sai_lech = abs(row['EC_Thực_Tế'] - row['EC_Yêu_Cầu']) / row['EC_Yêu_Cầu']
                        ty_le_chinh_xac = max(0, 100 - sai_lech * 100)
                        tong_tuong_thich += ty_le_chinh_xac
                        so_ngay_tinh += 1
                
                trung_binh_tuong_thich = (tong_tuong_thich / so_ngay_tinh) if so_ngay_tinh > 0 else 0
                
                with st.expander(f"💡 ĐÁNH GIÁ VẬN HÀNH (Bấm để xem kết luận)", expanded=True):
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        st.metric("Tương thích EC Thiết bị", f"{round(trung_binh_tuong_thich, 1)}%")
                    with col_b:
                        if trung_binh_tuong_thich >= 90:
                            st.success("**🟢 VẬN HÀNH TỐI ƯU:** Hệ thống châm phân đáp ứng cực kỳ chính xác lệnh.")
                        elif trung_binh_tuong_thich >= 80:
                            st.warning("**🟡 CẢNH BÁO NHẸ:** Có độ lệch nhỏ giữa Yêu cầu và Thực tế, cần theo dõi thêm.")
                        else:
                            st.error("**🔴 RỦI RO HỆ THỐNG:** Sai lệch lớn (>20%). Cần kiểm tra rò rỉ phân, khí trong bơm hoặc cảm biến bẩn.")
                
                # --- VẼ BIỂU ĐỒ TRỰC QUAN ---
                tu_dien_tieu_chi = {
                    "🎯 EC Yêu Cầu (Trung bình)": {"cot_gia_tri": "EC_Yêu_Cầu", "cot_giai_doan": "GĐ_EC_YC"},
                    "🧪 EC Thực Tế (Trung bình)": {"cot_gia_tri": "EC_Thực_Tế", "cot_giai_doan": "GĐ_EC_Thực"},
                    "⏱️ Tổng Thời Gian Tưới / Ngày (Phút)": {"cot_gia_tri": "Tổng_TG_Phút", "cot_giai_doan": "GĐ_Tưới"}
                }
                
                col_chart_1, col_chart_2 = st.columns([1, 2])
                with col_chart_1:
                    tieu_chi_duoc_chon = st.selectbox(f"📊 Chọn tiêu chí vẽ biểu đồ:", list(tu_dien_tieu_chi.keys()), key=f"chart_{idx}")
                
                cot_y = tu_dien_tieu_chi[tieu_chi_duoc_chon]["cot_gia_tri"]
                cot_mau_sac = tu_dien_tieu_chi[tieu_chi_duoc_chon]["cot_giai_doan"]
                truc_y_max = max([row[cot_y] for row in bang_du_lieu]) * 1.2 if bang_du_lieu else 1

                fig = px.bar(
                    bang_du_lieu, x="Ngày_Str", y=cot_y, color=cot_mau_sac, text=cot_y,
                    title=f"Sự thay đổi {tieu_chi_duoc_chon.split('(')[0].strip()}",
                    labels={"Ngày_Str": "Ngày", cot_y: "Giá trị", cot_mau_sac: "Nhãn Giai đoạn"},
                    color_discrete_sequence=px.colors.qualitative.Plotly 
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(xaxis_tickangle=-45, yaxis=dict(range=[0, truc_y_max])) 
                st.plotly_chart(fig, use_container_width=True)
                
                # --- BẢNG DỮ LIỆU CHI TIẾT ---
                st.markdown(f"#### 🔍 Chi Tiết Bảng Dữ Liệu")
                
                danh_sach_nhan_gd = list(set([row[cot_mau_sac] for row in bang_du_lieu]))
                danh_sach_nhan_gd.sort(key=lambda x: int(x.replace('GĐ ', ''))) 
                danh_sach_loc_gd = ["Hiển thị tất cả"] + danh_sach_nhan_gd
                
                lua_chon_gd = st.selectbox("👉 Lọc bảng dữ liệu theo Giai đoạn:", danh_sach_loc_gd, key=f"table_{idx}")
                
                if lua_chon_gd == "Hiển thị tất cả":
                    bang_du_lieu_da_loc = bang_du_lieu
                else:
                    bang_du_lieu_da_loc = [row for row in bang_du_lieu if row[cot_mau_sac] == lua_chon_gd]
                    if bang_du_lieu_da_loc:
                        # Hiển thị số liệu thống kê ngắn gọn cho GĐ đang chọn
                        c1, c2, c3, c4, c5 = st.columns(5)
                        sn = len(bang_du_lieu_da_loc)
                        c1.metric("Bắt đầu từ", f"{bang_du_lieu_da_loc[0]['Ngày_Str']}")
                        c2.metric("Kéo dài", f"{sn} ngày")
                        c3.metric("EC Yêu Cầu (TB)", f"{round(sum(r['EC_Yêu_Cầu'] for r in bang_du_lieu_da_loc)/sn, 2)}")
                        c4.metric("EC Thực Tế (TB)", f"{round(sum(r['EC_Thực_Tế'] for r in bang_du_lieu_da_loc)/sn, 2)}")
                        c5.metric("TG Tưới (TB)", f"{round(sum(r['Tổng_TG_Phút'] for r in bang_du_lieu_da_loc)/sn, 2)} phút")
                        st.markdown("<br>", unsafe_allow_html=True)

                # Format lại tên cột cho đẹp
                bang_hien_thi_cuoi = []
                for row in bang_du_lieu_da_loc:
                    bang_hien_thi_cuoi.append({
                        "📅 Ngày": row["Ngày_Str"],
                        "🏷️ GĐ(EC.Thực)": row["GĐ_EC_Thực"],
                        "🏷️ GĐ(EC.YC)": row["GĐ_EC_YC"],
                        "🏷️ GĐ(Tưới)": row["GĐ_Tưới"],
                        "💧 Số Lần": row["Số_Lần"],
                        "⏱️ Tổng TG (Phút)": row["Tổng_TG_Phút"],
                        "🎯 EC Y.Cầu": row["EC_Yêu_Cầu"],
                        "🧪 EC T.Tế": row["EC_Thực_Tế"]
                    })
                
                st.dataframe(bang_hien_thi_cuoi, use_container_width=True)
                st.divider()

    except json.JSONDecodeError:
        st.error("❌ Lỗi định dạng file! Vui lòng đảm bảo bạn tải lên file .json hợp lệ.")
